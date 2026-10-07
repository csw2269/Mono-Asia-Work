# Pluto Source Recovery cumulative checkpoint — Phase 1B / 2026-10-07

## Parent

- Parent checkpoint: PLUTO_SOURCE_RECOVERY_CHECKPOINT_P1_20261007.zip
- Parent SHA-256: f1cbaeee029cee24b68f0bbe4cd8242748cc18cee1043c31c314c91529bd2cbc
- Canonical target remains CoG 2026 latest pluto.dll.
- Original archives remain immutable.

## Source pins

- hwkim3330/pluto-re: c25f0bb1c286c28564221a90a6d18e4ad76b6f91
- official tscmoo/pluto: d41f473aeebafcfc90e28527b57324656c0ffca1
- BWAPI v4.4.0: 7687da8abc4726f8366401f11ab648d421385793

## Evidence policy change in P1B

Literal Ghidra Version Tracking / BinDiff remains OPEN because the chat-local execution backend could not run the uploaded Ghidra distribution. P1B explicitly separates local/raw verification, external Ghidra corroboration, inferred names/signatures, and literal VT/BinDiff scores.

The external analysis reproduces against the same latest CoG archive hash used by this recovery: d4e2225446f5048e131065357173952f0286586da77ebb8bddf7fc766c3844a5.

## P1B implementation

- ProcClient launch / sendFeatures / poll_or_recv / shutdown.
- PLSM v3 single-slot request/response transport.
- Pipe fallback with exact payload order.
- PLO1 0x88 handshake validation.
- engine path: DLL directory + pluto\pluto_infer.exe.
- 9 launch attempts / 750 ms retry / 180000 ms handshake timeout.
- deferred command queue.
- BWAPI 4.4.0 QueueGameCommand-equivalent replay seam.
- no-op response.
- Stop / CarrierStop / ReaverStop packet generation.

No full observation or action reconstruction has been added.

## Exact Stop parity fixture

For BW net id 0x1234:

- normal: 09 01 34 12 1A 00
- Carrier: 09 01 34 12 1B
- Reaver: 09 01 34 12 1C

Each actor receives its own Select(1) prefix, matching the current command emitter.

## VERIFIED anchors used by this slice

- latest ProcClient::poll_or_recv: 0x63f83050
- latest mod_onStart: 0x63f85f90
- latest mod_onFrame: 0x63f8baf0
- latest ProcClient::sendFeatures: 0x63fb4bc0
- latest ProcClient::launch: 0x63fb5420
- latest ProcClient::shutdown: 0x63fb7190
- latest DeferredTurnBufferSink::queueCommand: 0x63faf100
- latest command emitter: 0x63fb8770

BWAPI 4.4.0 anchors: TurnBuffer 0x00654880; sgdwBytesInCmdQueue 0x00654AA0; sendTurn 0x00485A40; QueueGameCommand 0x00485BD0; NetMode 0x0059688C; gwGameMode 0x00596904; TURN_BUFFER_SIZE 512.

## Deliberately non-parity seam

The external current-binary notes establish that pipe-mode polling spins briefly between PeekNamedPipe checks, but do not promote the exact scheduling instruction sequence. P1B uses SwitchToThread() for that tiny wait seam. Transport ordering/deadline semantics are retained, but this instruction choice is not claimed as byte-identical.

## OPEN

- Literal Ghidra Version Tracking scores/matches.
- Literal BinDiff scores/matches.
- Exact latest source-level boundary/name for BwAccessor::enumerate; remains INFERRED.
- Exact original source spelling/calling convention where only likely signatures are known.
- Full mod_onStart/mod_onFrame/handle_response/mod_onEnd transcription.
- Remaining action types beyond no-op and Stop.
- Actual StarCraft/BWAPI injected runtime test.
- Battle Environment clean-state A/B.
- Historical workkit extracted-member hash mismatch cause.
- Inference-model nonblocking OPEN items from Phase 1A.

## Acceptance for P1B

P1B is accepted only if both Linux host protocol/packet tests and Windows x86 MSVC build/tests pass.
CI output is packaged by .github/workflows/pluto-p1b-ci.yml.
