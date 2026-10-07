# Pluto Source Recovery — Phase 1B vertical slice

Canonical target: **CoG 2026 latest pluto.dll**.

This directory is a deliberately narrow source-recovery slice. It does not pretend to be the complete Pluto source tree.

## Implemented in P1B

- PLSM v3 / PLO1 v3 layout and validation.
- Exact request serialization order for shared-memory and pipe transports.
- Windows ProcClient skeleton for anonymous pipes, optional SHM+events, inherited handle environment, quoted no-argument engine launch, handshake, polling, and shutdown.
- Engine path resolution relative to the loaded DLL.
- Current engine launch retry envelope: up to 9 attempts, 750 ms retry delay, 180000 ms handshake timeout.
- Deferred command sink and BWAPI 4.4.0 QueueGameCommand-equivalent replay seam.
- Minimal response slice: action 0 no-op; action 8 Stop / CarrierStop / ReaverStop.
- Host protocol/packet tests plus Windows x86 compile/test CI.

## Evidence boundary

hwkim3330/pluto-re at c25f0bb1c286c28564221a90a6d18e4ad76b6f91 is used as external Ghidra 12.1.4 corroboration for the same CoG release archive. Its [V] claims are not treated as literal Version Tracking or BinDiff results.

The exact tiny busy-spin instruction sequence used by current pipe polling is still not independently promoted. P1B uses SwitchToThread() at that scheduling seam while preserving the documented deadline/nonblocking behavior. This is explicitly not claimed as byte parity.

## Build

Linux host validation:

    cmake -S . -B build
    cmake --build build
    ctest --test-dir build --output-on-failure
    python3 tools/check_protocol_layout.py

Windows x86 validation:

    cmake -S . -B build-win32 -G "Visual Studio 17 2022" -A Win32
    cmake --build build-win32 --config Release
    ctest --test-dir build-win32 -C Release --output-on-failure

## Not yet implemented

- Full BWAPI AIModule ABI / injected DLL target.
- Full observation builder.
- Full 20-action command emitter.
- Build-order bandit and records.
- Battle Environment runtime A/B.
- Literal Ghidra Version Tracking and BinDiff reconciliation.
