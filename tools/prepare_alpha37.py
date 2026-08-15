from pathlib import Path
import runpy

# Start from Alpha 3.5: stable icons/roster/support/victory without the faulty Alpha 3.6 catalog-time edits.
runpy.run_path('tools/prepare_alpha35.py', run_name='__main__')
path = Path('build/MapScript.galaxy')
src = path.read_text(encoding='utf-8')

# Additional real button-id exception found during runtime QA.
old_button_helper = '''string MB_UnitButtonId (string unitId) {
    // Most melee unit train-button ids match their unit ids. Keep this helper so exceptions can be
    // added without touching draft/gameplay ids.
    return unitId;
}'''
new_button_helper = '''string MB_UnitButtonId (string unitId) {
    // Most melee unit train-button ids match their unit ids. Known exceptions are mapped here.
    if (unitId == "Cyclone") { return "BuildCyclone"; }
    return unitId;
}'''
if old_button_helper not in src:
    raise SystemExit('unit button helper anchor missing')
src = src.replace(old_button_helper, new_button_helper, 1)

# Temporary QA-only boost. Do NOT mutate sparse InfoArray catalog paths: those caused runtime
# "required object not found" errors. Instead use the engine progress API. Any active construction,
# training, morph or similar progress is advanced to 85% once it starts, leaving the last 15% to
# complete normally. This also speeds tech buildings without changing combat/game speed.
anchor = '//--------------------------------------------------------------------------------------------------\n// Production restrictions\n'
if anchor not in src:
    raise SystemExit('production section anchor missing')

test_boost = r'''//--------------------------------------------------------------------------------------------------
// TEST BOOST - QA ONLY, REMOVE BEFORE RELEASE
//--------------------------------------------------------------------------------------------------
void MB_TestBoostPulseFor (int p) {
    unitgroup g;
    int n;
    unit u;
    int slot;
    fixed progress;

    if (!MB_PlayerActive(p)) { return; }
    g = UnitGroup(null, p, RegionPlayableMap(), null, c_noMaxCount);
    n = UnitGroupCount(g, c_unitCountAlive);
    while (n > 0) {
        u = UnitGroupUnit(g, n);
        if (u != null) {
            slot = 0;
            while (slot < 8) {
                if (UnitCheckProgressState(u, slot, c_unitProgressStateActive)) {
                    progress = UnitGetProgressComplete(u, slot);
                    if (progress > 0.0 && progress < 85.0) {
                        UnitSetProgressComplete(u, slot, 85);
                    }
                }
                slot += 1;
            }
        }
        n -= 1;
    }
}

void MB_TestBoostPulseAll () {
    int p = 1;
    while (p <= 8) {
        MB_TestBoostPulseFor(p);
        p += 1;
    }
}

void MB_ApplyTestBoostFor (int p) {
    if (!MB_PlayerActive(p)) { return; }
    PlayerModifyPropertyInt(p, c_playerPropMinerals, c_playerPropOperSetTo, 10000);
    PlayerModifyPropertyInt(p, c_playerPropVespene, c_playerPropOperSetTo, 10000);
    PlayerModifyPropertyInt(p, c_playerPropSuppliesLimit, c_playerPropOperSetTo, 200);
    PlayerModifyPropertyInt(p, c_playerPropSuppliesMade, c_playerPropOperSetTo, 200);
}

void MB_ApplyTestBoostAll () {
    int p = 1;
    while (p <= 8) {
        MB_ApplyTestBoostFor(p);
        p += 1;
    }
    UIDisplayMessage(PlayerGroupAll(), c_messageAreaSubtitle,
        StringToText("TEST BOOST · 광물/가스 10000 · 보급 200 · 건설/생산/변태 진행 85% 가속"));
}

'''
src = src.replace(anchor, test_boost + anchor, 1)

# Apply the economy boost after final picks are locked.
finish_anchor = '    MB_ApplySupportRulesAll();\n    MB_UpdateRosterAll();\n'
if finish_anchor not in src:
    raise SystemExit('finish selection anchor missing')
src = src.replace(finish_anchor,
    '    MB_ApplySupportRulesAll();\n    MB_ApplyTestBoostAll();\n    MB_UpdateRosterAll();\n', 1)

# Reuse the existing one-second runtime tick. This keeps QA acceleration isolated and avoids a
# second periodic trigger. Every newly started construction/train/morph gets advanced on the next tick.
tick_anchor = '    else if (gv_mbPhase == MB_PHASE_RUNNING) { MB_CheckVictory(); }\n'
if tick_anchor not in src:
    raise SystemExit('running tick anchor missing')
src = src.replace(tick_anchor,
    '    else if (gv_mbPhase == MB_PHASE_RUNNING) { MB_CheckVictory(); MB_TestBoostPulseAll(); }\n', 1)

# Guards: the faulty sparse catalog time mutator must not return.
for forbidden in ('CatalogFieldValueCount(c_gameCatalogAbil', 'InfoArray[" + IntToString(i) + "].Time', 'oldTime * 0.20'):
    if forbidden in src:
        raise SystemExit(f'faulty Alpha 3.6 catalog speed code remains: {forbidden}')

for marker in (
    'return "BuildCyclone"', 'MB_TestBoostPulseAll', 'UnitCheckProgressState',
    'UnitGetProgressComplete', 'UnitSetProgressComplete', 'progress < 85.0',
    'PlayerModifyPropertyInt(p, c_playerPropMinerals, c_playerPropOperSetTo, 10000)',
    'PlayerModifyPropertyInt(p, c_playerPropVespene, c_playerPropOperSetTo, 10000)',
    'PlayerModifyPropertyInt(p, c_playerPropSuppliesLimit, c_playerPropOperSetTo, 200)'
):
    if marker not in src:
        raise SystemExit(f'Alpha 3.7 marker missing: {marker}')

# Keep the stable Galaxy string guard.
in_string = False
escaped = False
for i, ch in enumerate(src):
    if ch == '\n' and in_string:
        raise SystemExit(f'raw newline inside Galaxy string literal near character {i}')
    if not in_string:
        if ch == '"':
            in_string = True
            escaped = False
    else:
        if escaped:
            escaped = False
        elif ch == '\\':
            escaped = True
        elif ch == '"':
            in_string = False
if in_string:
    raise SystemExit('unterminated Galaxy string literal')

path.write_text(src, encoding='utf-8', newline='\n')
print('Alpha 3.7 prepared: Cyclone icon mapping + safe engine progress QA boost')
