from pathlib import Path
import runpy
import re

# Start from Alpha 4.4 UI/roster/upgrade work.
runpy.run_path('tools/prepare_alpha44.py', run_name='__main__')
path = Path('build/MapScript.galaxy')
src = path.read_text(encoding='utf-8')

# Alpha 4.4 inherited the TEST BOOST calls from the runtime tick/final-selection path,
# but an earlier section replacement had removed the function definitions themselves.
# Restore the last stable QA-only implementation. Lair/Hive morphs are still handled by
# the dedicated 12-second AbilData TEST patch, so this pulse mainly accelerates other
# construction/training/research progress.
if 'void MB_ApplyTestBoostAll ()' not in src:
    anchor = '// Upgrade restrictions - explicit ladder whitelist\n'
    if anchor not in src:
        raise SystemExit('upgrade restriction anchor missing')

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
            while (slot < 32) {
                progress = UnitGetProgressComplete(u, slot);
                if (progress > 0.0 && progress < 85.0) {
                    UnitSetProgressComplete(u, slot, 85);
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
        StringToText("TEST BOOST · 광물/가스 10000 · 보급 200"));
}

'''
    src = src.replace(anchor, test_boost + anchor, 1)

# Critical function-definition guard: these calls must never survive without definitions again.
for fn in ('MB_ApplyTestBoostAll', 'MB_TestBoostPulseAll'):
    calls = len(re.findall(r'\b' + re.escape(fn) + r'\s*\(', src))
    defs = len(re.findall(r'\bvoid\s+' + re.escape(fn) + r'\s*\(', src))
    if calls < 2:  # at least one definition + one runtime call
        raise SystemExit(f'{fn}: expected definition and runtime call, got {calls} occurrences')
    if defs != 1:
        raise SystemExit(f'{fn}: expected exactly one definition, got {defs}')

# Top-level brace sanity outside comments/strings.
clean = re.sub(r'"(?:\\.|[^"\\])*"', '""', src)
clean = re.sub(r'//.*', '', clean)
depth = 0
for i, ch in enumerate(clean):
    if ch == '{':
        depth += 1
    elif ch == '}':
        depth -= 1
        if depth < 0:
            raise SystemExit(f'brace depth became negative near character {i}')
if depth != 0:
    raise SystemExit(f'unbalanced Galaxy braces: final depth {depth}')

# String literal safety.
in_string = False
escaped = False
for pos, ch in enumerate(src):
    if ch == '\n' and in_string:
        raise SystemExit(f'raw newline inside Galaxy string literal near character {pos}')
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
print('Alpha 4.4.1 prepared: restored TEST BOOST definitions + function/brace guards')
