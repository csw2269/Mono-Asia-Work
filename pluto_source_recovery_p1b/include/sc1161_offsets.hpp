#pragma once
#include <cstddef>
#include <cstdint>

namespace pluto::sc1161::bwapi440 {

// VERIFIED against BWAPI v4.4.0 commit
// 7687da8abc4726f8366401f11ab648d421385793.
inline constexpr std::uintptr_t kGame                 = 0x0057F0F0;
inline constexpr std::uintptr_t kPlayers              = 0x0057EEE0;
inline constexpr std::uintptr_t kTurnBuffer           = 0x00654880;
inline constexpr std::uintptr_t kBytesInCommandQueue  = 0x00654AA0;
inline constexpr std::uintptr_t kSendTurn             = 0x00485A40;
inline constexpr std::uintptr_t kQueueGameCommand     = 0x00485BD0;
inline constexpr std::uintptr_t kVisibleUnitFirst     = 0x00628430;
inline constexpr std::uintptr_t kHiddenUnitFirst      = 0x006283EC;
inline constexpr std::uintptr_t kScannerSweepFirst    = 0x006283F4;
inline constexpr std::uintptr_t kUnitTable            = 0x0059CCA8;
inline constexpr std::uintptr_t kGameSpeed            = 0x006CDFD4;
inline constexpr std::uintptr_t kLatencyFrames        = 0x0051CE70;
inline constexpr std::uintptr_t kLatencySetting       = 0x006556E4;
inline constexpr std::uintptr_t kNetMode              = 0x0059688C;
inline constexpr std::uintptr_t kGameMode             = 0x00596904;
inline constexpr std::uintptr_t kClientSelectionGroup = 0x00597208;
inline constexpr std::uintptr_t kClientSelectionCount = 0x0059723D;

inline constexpr std::size_t kCUnitSize = 336;
inline constexpr std::size_t kTurnBufferSize = 512;

namespace command {
inline constexpr std::uint8_t Select       = 0x09;
inline constexpr std::uint8_t Stop         = 0x1A;
inline constexpr std::uint8_t CarrierStop  = 0x1B;
inline constexpr std::uint8_t ReaverStop   = 0x1C;
inline constexpr std::uint8_t RightClick   = 0x14;
inline constexpr std::uint8_t Attack       = 0x15;
inline constexpr std::uint8_t HoldPosition = 0x2B;
} // namespace command

} // namespace pluto::sc1161::bwapi440
