#pragma once
#include <cstddef>
#include <cstdint>
#include <functional>
#include <vector>

namespace pluto {

struct ProviderCaps {
    std::size_t max_message_size = 0;
    int call_delay = 0;
};

struct TurnBufferView {
    std::uint8_t* data = nullptr;
    std::uint32_t* queued_bytes = nullptr;
    std::size_t capacity = 512;
};

enum class QueueGameCommandResult {
    Queued,
    SentTurnAndQueued,
    DroppedInvalid,
    DroppedGameMode,
    DroppedLatency,
    DroppedProvider,
};

QueueGameCommandResult queue_game_command_bwapi440(
    TurnBufferView view,
    const std::uint8_t* packet,
    std::size_t length,
    bool correct_version,
    bool game_mode_is_glues,
    bool net_mode,
    ProviderCaps caps,
    const std::function<bool(int&)>& get_turns_in_transit,
    const std::function<void()>& send_turn);

class DeferredTurnBufferSink {
public:
    void queue_command(const std::uint8_t* packet, std::size_t length);
    std::vector<QueueGameCommandResult> flush(
        TurnBufferView view,
        bool correct_version,
        bool game_mode_is_glues,
        bool net_mode,
        ProviderCaps caps,
        const std::function<bool(int&)>& get_turns_in_transit,
        const std::function<void()>& send_turn);

    std::size_t packet_count() const noexcept { return lengths_.size(); }
    std::size_t byte_count() const noexcept { return bytes_.size(); }
    void clear();

private:
    std::vector<std::uint8_t> bytes_;
    std::vector<std::uint32_t> lengths_;
};

} // namespace pluto
