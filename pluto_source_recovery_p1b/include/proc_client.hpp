#pragma once
#include "protocol.hpp"

#include <cstddef>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

namespace pluto {

struct FeatureBatch {
    protocol::RequestHeader header{};
    const std::int64_t* unit_i64 = nullptr;   // N * 6
    const float* unit_f32 = nullptr;          // N * 109
    const std::uint8_t* unit_mask_a = nullptr;// N
    const std::uint8_t* unit_mask_b = nullptr;// N
    const std::uint8_t* action_mask = nullptr;// 20
    const std::uint8_t* arg_mask = nullptr;   // 233
    const float* globals = nullptr;           // 292
    const std::uint16_t* spatial_u16 = nullptr;// 128*128
    const std::uint8_t* static_u8 = nullptr;  // 128*128
    const std::int64_t* history_i64 = nullptr;// 4
};

bool valid_feature_batch(const FeatureBatch& batch, std::int32_t max_units);
bool serialize_feature_batch_to_shm(
    std::uint8_t* shm,
    std::size_t shm_size,
    const FeatureBatch& batch,
    std::uint32_t request_seq);
std::vector<std::uint8_t> serialize_feature_batch_to_pipe(const FeatureBatch& batch);

enum class PollResult : int {
    Error = -1,
    NotReady = 0,
    Ready = 1,
};

class ProcClient {
public:
    ProcClient();
    ~ProcClient();

    ProcClient(const ProcClient&) = delete;
    ProcClient& operator=(const ProcClient&) = delete;

    // Current CoG behavior: quoted exe path, no engine arguments, inherited CWD.
    bool start(const std::wstring& exe_path,
               const std::string& log_path,
               std::uint32_t handshake_timeout_ms = 180000);

    bool send_features(const FeatureBatch& batch);
    PollResult poll_or_recv(protocol::EngineResponse& out,
                            std::int64_t deadline_qpc,
                            bool lockstep);
    void shutdown();

    bool ok() const noexcept;
    bool retryable() const noexcept;
    bool using_shm() const noexcept;
    std::uint32_t request_seq() const noexcept;
    std::int32_t frames_per_step() const noexcept;
    std::int32_t max_units() const noexcept;
    std::int64_t qpc_now() const noexcept;
    std::int64_t qpc_frequency() const noexcept;
    const std::string& model() const noexcept;
    const std::string& engine() const noexcept;
    const std::string& error() const noexcept;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace pluto
