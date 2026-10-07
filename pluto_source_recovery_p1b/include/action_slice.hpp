#pragma once
#include "deferred_turn_buffer.hpp"
#include "protocol.hpp"

#include <cstdint>
#include <vector>

namespace pluto {

enum class StopKind {
    Normal,
    Carrier,
    Reaver,
};

struct ActorRef {
    std::uint16_t bw_net_id = 0;
    StopKind stop_kind = StopKind::Normal;
};

enum class MinimalApplyResult {
    NoOp,
    StopQueued,
    Unsupported,
};

std::vector<std::uint8_t> make_stop_packet(std::uint16_t bw_net_id, StopKind kind);
MinimalApplyResult apply_minimal_response(
    const protocol::EngineResponse& response,
    const std::vector<ActorRef>& actors,
    DeferredTurnBufferSink& sink);

} // namespace pluto
