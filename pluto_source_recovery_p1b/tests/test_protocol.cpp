#include "action_slice.hpp"
#include "deferred_turn_buffer.hpp"
#include "proc_client.hpp"
#include "protocol.hpp"
#include "sc1161_offsets.hpp"

#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <vector>

using namespace pluto;

static FeatureBatch make_batch(
    protocol::RequestHeader& h,
    std::vector<std::int64_t>& ints,
    std::vector<float>& floats,
    std::vector<std::uint8_t>& a,
    std::vector<std::uint8_t>& b,
    std::array<std::uint8_t, protocol::kActionCount>& am,
    std::array<std::uint8_t, protocol::kArgCount>& arm,
    std::array<float, protocol::kGlobalCount>& globals,
    std::array<std::uint16_t, 128 * 128>& map16,
    std::array<std::uint8_t, 128 * 128>& map8,
    std::array<std::int64_t, protocol::kHistoryCount>& hist) {

    return FeatureBatch{h, ints.data(), floats.data(), a.data(), b.data(),
                        am.data(), arm.data(), globals.data(),
                        map16.data(), map8.data(), hist.data()};
}

int main() {
    static_assert(sizeof(protocol::RequestHeader) == 0x30);
    static_assert(sizeof(protocol::EngineResponse) == 0x28);
    static_assert(sizeof(protocol::PlutoHandshake) == 0x88);
    static_assert(sc1161::bwapi440::kTurnBufferSize == 512);

    std::vector<std::uint8_t> shm(protocol::kShmSize, 0xCC);
    protocol::init_shm_static_header(shm.data(), shm.size());
    assert(protocol::valid_shm_static_header(shm.data(), shm.size()));
    assert(protocol::load_pod<std::uint32_t>(shm.data(), protocol::shm_off::engine_ack) == 0);

    protocol::PlutoHandshake hs{};
    hs.magic = protocol::kHandshakeMagic;
    hs.version = 3;
    hs.frames_per_step = 6;
    hs.max_units = 768;
    assert(protocol::valid_handshake(hs));
    hs.max_units = 1025;
    assert(!protocol::valid_handshake(hs));

    protocol::RequestHeader hdr{};
    hdr.n = 2;
    hdr.width = 128;
    hdr.height = 128;

    std::vector<std::int64_t> ints(2 * 6, 0);
    std::vector<float> floats(2 * 109, 0.0f);
    std::vector<std::uint8_t> maskA(2, 0), maskB(2, 0);
    std::array<std::uint8_t, protocol::kActionCount> actionMask{};
    std::array<std::uint8_t, protocol::kArgCount> argMask{};
    std::array<float, protocol::kGlobalCount> globals{};
    std::array<std::uint16_t, 128 * 128> map16{};
    std::array<std::uint8_t, 128 * 128> map8{};
    std::array<std::int64_t, protocol::kHistoryCount> hist{};

    ints[0] = 0x1122334455667788LL;
    floats[0] = 1.25f;
    maskA[0] = 0xA1;
    maskB[1] = 0xB2;
    actionMask[8] = 1;
    argMask[0] = 1;
    globals[0] = 2.5f;
    map16[0] = 0x1234;
    map8[0] = 0x56;
    hist[0] = 8;

    auto batch = make_batch(hdr, ints, floats, maskA, maskB,
                            actionMask, argMask, globals, map16, map8, hist);
    assert(valid_feature_batch(batch, 768));
    assert(serialize_feature_batch_to_shm(shm.data(), shm.size(), batch, 7));
    assert(protocol::load_pod<std::uint32_t>(shm.data(), protocol::shm_off::request_seq) == 7);
    assert(protocol::load_pod<std::int64_t>(shm.data(), protocol::shm_off::unit_i64) == ints[0]);
    assert(protocol::load_pod<std::uint16_t>(shm.data(), protocol::shm_off::spatial_u16) == 0x1234);
    assert(shm[protocol::shm_off::action_mask + 8] == 1);

    auto pipe = serialize_feature_batch_to_pipe(batch);
    const std::size_t expected_pipe =
        0x30 + 2 * 0x30 + 2 * 0x1B4 + 2 + 2 + 20 + 233 +
        292 * 4 + 0x8000 + 0x4000 + 0x20;
    assert(pipe.size() == expected_pipe);
    protocol::RequestHeader pipe_hdr{};
    std::memcpy(&pipe_hdr, pipe.data(), sizeof(pipe_hdr));
    assert(pipe_hdr.n == 2 && pipe_hdr.width == 128 && pipe_hdr.height == 128);

    // Exact current Pluto Stop packets from the latest command-emitter disassembly.
    assert((make_stop_packet(0x1234, StopKind::Normal) ==
            std::vector<std::uint8_t>{0x09,0x01,0x34,0x12,0x1A,0x00}));
    assert((make_stop_packet(0x1234, StopKind::Carrier) ==
            std::vector<std::uint8_t>{0x09,0x01,0x34,0x12,0x1B}));
    assert((make_stop_packet(0x1234, StopKind::Reaver) ==
            std::vector<std::uint8_t>{0x09,0x01,0x34,0x12,0x1C}));

    DeferredTurnBufferSink sink;
    protocol::EngineResponse noop{};
    noop.action = 0;
    assert(apply_minimal_response(noop, {{0x1234, StopKind::Normal}}, sink) ==
           MinimalApplyResult::NoOp);
    assert(sink.packet_count() == 0);

    protocol::EngineResponse stop{};
    stop.action = 8;
    assert(apply_minimal_response(stop,
        {{0x1234, StopKind::Normal}, {0x5678, StopKind::Carrier}}, sink) ==
        MinimalApplyResult::StopQueued);
    assert(sink.packet_count() == 2);

    std::array<std::uint8_t, 512> turn{};
    std::uint32_t queued = 0;
    TurnBufferView view{turn.data(), &queued, turn.size()};
    ProviderCaps caps{512, 4};
    int send_count = 0;
    auto get_turns = [](int& t) { t = 0; return true; };
    auto send_turn = [&]() { ++send_count; queued = 0; };
    auto results = sink.flush(view, true, false, true, caps, get_turns, send_turn);
    assert(results.size() == 2);
    assert(queued == 11);
    assert(turn[0] == 0x09 && turn[4] == 0x1A && turn[5] == 0x00);
    assert(turn[6] == 0x09 && turn[10] == 0x1B);

    // BWAPI QueueGameCommand overflow path: send current turn, then append.
    queued = 510;
    std::array<std::uint8_t, 6> pkt{0x09,0x01,0x34,0x12,0x1A,0x00};
    auto qr = queue_game_command_bwapi440(
        view, pkt.data(), pkt.size(), true, false, true, caps, get_turns, send_turn);
    assert(qr == QueueGameCommandResult::SentTurnAndQueued);
    assert(send_count == 1);
    assert(queued == 6);

    // GLUES and latency guards drop rather than force an unsafe send.
    queued = 510;
    qr = queue_game_command_bwapi440(
        view, pkt.data(), pkt.size(), true, true, true, caps, get_turns, send_turn);
    assert(qr == QueueGameCommandResult::DroppedGameMode);

    auto high_turns = [](int& t) { t = 12; return true; }; // callDelay 4 => threshold 12
    qr = queue_game_command_bwapi440(
        view, pkt.data(), pkt.size(), true, false, true, caps, high_turns, send_turn);
    assert(qr == QueueGameCommandResult::DroppedLatency);

    std::cout << "P1B protocol/action/TurnBuffer tests passed\n";
    return 0;
}
