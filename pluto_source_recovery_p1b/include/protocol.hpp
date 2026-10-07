#pragma once
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <type_traits>

namespace pluto::protocol {

inline constexpr std::uint32_t kShmMagic = 0x4D534C50u;       // 'PLSM'
inline constexpr std::uint32_t kHandshakeMagic = 0x314F4C50u; // 'PLO1'
inline constexpr std::uint32_t kProtocolVersion = 3;
inline constexpr std::uint32_t kShmSize = 0x85F80;
inline constexpr std::uint32_t kMaxUnitsCap = 1024;
inline constexpr std::int32_t kSpatialWidth = 128;
inline constexpr std::int32_t kSpatialHeight = 128;
inline constexpr std::size_t kCategoricalPerUnit = 6;
inline constexpr std::size_t kContinuousPerUnit = 109;
inline constexpr std::size_t kActionCount = 20;
inline constexpr std::size_t kArgCount = 233;
inline constexpr std::size_t kGlobalCount = 292;
inline constexpr std::size_t kHistoryCount = 4;

namespace shm_off {
inline constexpr std::size_t magic          = 0x000;
inline constexpr std::size_t version        = 0x004;
inline constexpr std::size_t size           = 0x008;
inline constexpr std::size_t max_units_cap  = 0x00C;
inline constexpr std::size_t engine_ack     = 0x010;
inline constexpr std::size_t quit           = 0x014;
inline constexpr std::size_t request_seq    = 0x040;
inline constexpr std::size_t response_seq   = 0x080;
inline constexpr std::size_t request_header = 0x0C0;
inline constexpr std::size_t unit_i64       = 0x00100;
inline constexpr std::size_t unit_f32       = 0x0C100;
inline constexpr std::size_t unit_mask_a    = 0x79100;
inline constexpr std::size_t unit_mask_b    = 0x79500;
inline constexpr std::size_t action_mask    = 0x79900;
inline constexpr std::size_t arg_mask       = 0x79940;
inline constexpr std::size_t globals        = 0x79A40;
inline constexpr std::size_t spatial_u16    = 0x79F00;
inline constexpr std::size_t static_u8      = 0x81F00;
inline constexpr std::size_t history_i64    = 0x85F00;
inline constexpr std::size_t response       = 0x85F40;
inline constexpr std::size_t end            = 0x85F80;
} // namespace shm_off

#pragma pack(push, 1)
struct RequestHeader {
    std::int32_t n;
    std::int32_t width;
    std::int32_t height;
    std::uint32_t flags;
    std::int64_t forced[4];
};

struct EngineResponse {
    std::int64_t action;
    std::int64_t arg;
    std::int64_t pos;
    std::int64_t unit_index;
    float win;
    float log_prob;
};

struct PlutoHandshake {
    std::uint32_t magic;
    std::int32_t version;
    std::int32_t frames_per_step;
    std::int32_t max_units;
    std::int64_t model_version;
    char model[0x30];
    char engine[0x40];
};
#pragma pack(pop)

static_assert(sizeof(RequestHeader) == 0x30, "RequestHeader must be 0x30 bytes");
static_assert(sizeof(EngineResponse) == 0x28, "EngineResponse must be 0x28 bytes");
static_assert(sizeof(PlutoHandshake) == 0x88, "PlutoHandshake must be 0x88 bytes");

inline constexpr std::size_t kUnitI64Bytes =
    kMaxUnitsCap * kCategoricalPerUnit * sizeof(std::int64_t);
inline constexpr std::size_t kUnitF32Bytes =
    kMaxUnitsCap * kContinuousPerUnit * sizeof(float);
inline constexpr std::size_t kSpatialU16Bytes =
    kSpatialWidth * kSpatialHeight * sizeof(std::uint16_t);
inline constexpr std::size_t kStaticU8Bytes =
    kSpatialWidth * kSpatialHeight * sizeof(std::uint8_t);

static_assert(shm_off::unit_i64 + kUnitI64Bytes == shm_off::unit_f32);
static_assert(shm_off::unit_f32 + kUnitF32Bytes == shm_off::unit_mask_a);
static_assert(shm_off::unit_mask_a + kMaxUnitsCap == shm_off::unit_mask_b);
static_assert(shm_off::unit_mask_b + kMaxUnitsCap == shm_off::action_mask);
static_assert(shm_off::spatial_u16 + kSpatialU16Bytes == shm_off::static_u8);
static_assert(shm_off::static_u8 + kStaticU8Bytes == shm_off::history_i64);
static_assert(shm_off::response + sizeof(EngineResponse) <= shm_off::end);
static_assert(shm_off::end == kShmSize);

template <typename T>
inline T load_pod(const std::uint8_t* base, std::size_t off) {
    static_assert(std::is_trivially_copyable<T>::value, "POD only");
    T out{};
    std::memcpy(&out, base + off, sizeof(T));
    return out;
}

template <typename T>
inline void store_pod(std::uint8_t* base, std::size_t off, const T& value) {
    static_assert(std::is_trivially_copyable<T>::value, "POD only");
    std::memcpy(base + off, &value, sizeof(T));
}

inline bool valid_request_header(const RequestHeader& h, std::int32_t max_units) {
    return h.n >= 1 && h.n <= max_units &&
           h.width == kSpatialWidth && h.height == kSpatialHeight;
}

inline bool valid_handshake(const PlutoHandshake& h) {
    return h.magic == kHandshakeMagic &&
           h.version == static_cast<std::int32_t>(kProtocolVersion) &&
           h.frames_per_step > 0 &&
           h.max_units > 0 &&
           h.max_units <= static_cast<std::int32_t>(kMaxUnitsCap);
}

inline void init_shm_static_header(std::uint8_t* base, std::size_t size) {
    if (!base || size < kShmSize) return;
    std::memset(base + shm_off::engine_ack, 0, shm_off::request_header - shm_off::engine_ack);
    store_pod(base, shm_off::magic, kShmMagic);
    store_pod(base, shm_off::version, kProtocolVersion);
    store_pod(base, shm_off::size, kShmSize);
    store_pod(base, shm_off::max_units_cap, kMaxUnitsCap);
}

inline bool valid_shm_static_header(const std::uint8_t* base, std::size_t size) {
    if (!base || size < kShmSize) return false;
    return load_pod<std::uint32_t>(base, shm_off::magic) == kShmMagic &&
           load_pod<std::uint32_t>(base, shm_off::version) == kProtocolVersion &&
           load_pod<std::uint32_t>(base, shm_off::size) == kShmSize &&
           load_pod<std::uint32_t>(base, shm_off::max_units_cap) == kMaxUnitsCap;
}

} // namespace pluto::protocol
