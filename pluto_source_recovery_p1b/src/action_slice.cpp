#include "action_slice.hpp"
#include "sc1161_offsets.hpp"

namespace pluto {

std::vector<std::uint8_t> make_stop_packet(std::uint16_t id, StopKind kind) {
    using namespace sc1161::bwapi440;
    std::vector<std::uint8_t> out{
        command::Select,
        0x01,
        static_cast<std::uint8_t>(id & 0xff),
        static_cast<std::uint8_t>((id >> 8) & 0xff),
    };

    switch (kind) {
    case StopKind::Carrier:
        out.push_back(command::CarrierStop);
        break;
    case StopKind::Reaver:
        out.push_back(command::ReaverStop);
        break;
    case StopKind::Normal:
    default:
        out.push_back(command::Stop);
        out.push_back(0x00); // queued flag = 0
        break;
    }
    return out;
}

MinimalApplyResult apply_minimal_response(
    const protocol::EngineResponse& r,
    const std::vector<ActorRef>& actors,
    DeferredTurnBufferSink& sink) {

    if (r.action == 0) return MinimalApplyResult::NoOp;
    if (r.action != 8) return MinimalApplyResult::Unsupported;

    for (const auto& actor : actors) {
        auto packet = make_stop_packet(actor.bw_net_id, actor.stop_kind);
        sink.queue_command(packet.data(), packet.size());
    }
    return MinimalApplyResult::StopQueued;
}

} // namespace pluto
