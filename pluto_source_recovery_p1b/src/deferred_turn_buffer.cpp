#include "deferred_turn_buffer.hpp"

#include <algorithm>
#include <cstring>

namespace pluto {

QueueGameCommandResult queue_game_command_bwapi440(
    TurnBufferView view,
    const std::uint8_t* packet,
    std::size_t length,
    bool correct_version,
    bool game_mode_is_glues,
    bool net_mode,
    ProviderCaps caps,
    const std::function<bool(int&)>& get_turns_in_transit,
    const std::function<void()>& send_turn) {

    if (!packet || length == 0 || !correct_version ||
        !view.data || !view.queued_bytes || length >= view.capacity) {
        return QueueGameCommandResult::DroppedInvalid;
    }

    const std::size_t max_buffer = std::min(caps.max_message_size, view.capacity);
    if (length + *view.queued_bytes <= max_buffer) {
        std::memcpy(view.data + *view.queued_bytes, packet, length);
        *view.queued_bytes += static_cast<std::uint32_t>(length);
        return QueueGameCommandResult::Queued;
    }

    if (game_mode_is_glues) return QueueGameCommandResult::DroppedGameMode;

    int turns = 0;
    if (!get_turns_in_transit || !get_turns_in_transit(turns))
        return QueueGameCommandResult::DroppedProvider;

    const int call_delay = net_mode ? std::clamp(caps.call_delay, 2, 8) : 1;
    if (turns >= 16 - call_delay)
        return QueueGameCommandResult::DroppedLatency;

    if (!send_turn) return QueueGameCommandResult::DroppedProvider;
    send_turn(); // BWFXN_sendTurn resets StarCraft's queued-byte counter.

    if (length + *view.queued_bytes > max_buffer)
        return QueueGameCommandResult::DroppedProvider;

    std::memcpy(view.data + *view.queued_bytes, packet, length);
    *view.queued_bytes += static_cast<std::uint32_t>(length);
    return QueueGameCommandResult::SentTurnAndQueued;
}

void DeferredTurnBufferSink::queue_command(const std::uint8_t* packet, std::size_t length) {
    if (!packet || length == 0 || length > 0xffffffffu) return;
    bytes_.insert(bytes_.end(), packet, packet + length);
    lengths_.push_back(static_cast<std::uint32_t>(length));
}

std::vector<QueueGameCommandResult> DeferredTurnBufferSink::flush(
    TurnBufferView view,
    bool correct_version,
    bool game_mode_is_glues,
    bool net_mode,
    ProviderCaps caps,
    const std::function<bool(int&)>& get_turns_in_transit,
    const std::function<void()>& send_turn) {

    std::vector<QueueGameCommandResult> results;
    results.reserve(lengths_.size());
    std::size_t off = 0;
    for (std::uint32_t len : lengths_) {
        if (off + len > bytes_.size()) {
            results.push_back(QueueGameCommandResult::DroppedInvalid);
            break;
        }
        // Current Pluto's flush only replays lengths 1..0x1ff.
        if (len >= 1 && len <= 0x1ff) {
            results.push_back(queue_game_command_bwapi440(
                view, bytes_.data() + off, len, correct_version,
                game_mode_is_glues, net_mode, caps,
                get_turns_in_transit, send_turn));
        } else {
            results.push_back(QueueGameCommandResult::DroppedInvalid);
        }
        off += len;
    }
    clear();
    return results;
}

void DeferredTurnBufferSink::clear() {
    bytes_.clear();
    lengths_.clear();
}

} // namespace pluto
