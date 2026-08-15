from pathlib import Path
import runpy

# Start from Alpha 3.7: stable QA resources + engine progress acceleration.
runpy.run_path('tools/prepare_alpha37.py', run_name='__main__')
path = Path('build/MapScript.galaxy')
src = path.read_text(encoding='utf-8')

# Cyclone still rendered blank at runtime through its button catalog entry, so use the verified
# melee unit texture directly, like the existing Adept/Disruptor exceptions.
icon_anchor = '''string MB_UnitIcon (string unitId) {
    string buttonId;
    if (unitId == "Adept") { return "Assets\\\\Textures\\\\btn-unit-protoss-adept.dds"; }
    if (unitId == "Disruptor") { return "Assets\\\\Textures\\\\btn-unit-protoss-disruptor.dds"; }
'''
if icon_anchor not in src:
    raise SystemExit('Alpha 3.7 icon helper anchor missing')
src = src.replace(icon_anchor, icon_anchor + '    if (unitId == "Cyclone") { return "Assets\\\\Textures\\\\btn-unit-terran-cyclone.dds"; }\n', 1)

# SC2 unit button art is commonly 76px-ish. The previous 72x72 controls clipped the outer pixels.
# Increase the icon cards while preserving a six-column board and move labels/hint accordingly.
src = src.replace('        x = 30 + (col * 108);\n        y = 112 + (row * 106);',
                  '        x = 24 + (col * 108);\n        y = 104 + (row * 112);', 1)
src = src.replace('        DialogControlSetSize(gv_mbSDButton[i], PlayerGroupAll(), 72, 72);',
                  '        DialogControlSetSize(gv_mbSDButton[i], PlayerGroupAll(), 84, 84);', 1)
src = src.replace('        DialogControlSetPosition(gv_mbSDButton[i], PlayerGroupAll(), c_anchorTopLeft, x + 12, y);',
                  '        DialogControlSetPosition(gv_mbSDButton[i], PlayerGroupAll(), c_anchorTopLeft, x + 6, y);', 1)
src = src.replace('        DialogControlSetSize(gv_mbSDNameLabel[i], PlayerGroupAll(), 96, 24);',
                  '        DialogControlSetSize(gv_mbSDNameLabel[i], PlayerGroupAll(), 102, 24);', 1)
src = src.replace('        DialogControlSetPosition(gv_mbSDNameLabel[i], PlayerGroupAll(), c_anchorTopLeft, x, y + 74);',
                  '        DialogControlSetPosition(gv_mbSDNameLabel[i], PlayerGroupAll(), c_anchorTopLeft, x, y + 86);', 1)
src = src.replace('    DialogControlSetPosition(gv_mbSDHintLabel, PlayerGroupAll(), c_anchorTopLeft, 30, 548);',
                  '    DialogControlSetPosition(gv_mbSDHintLabel, PlayerGroupAll(), c_anchorTopLeft, 24, 574);', 1)

# Structure morphs (e.g. Hatchery -> Lair) do not always report c_unitProgressStateActive the same
# way normal train/construct progress does. For the QA build, inspect raw progress values on a wider
# slot range instead. Inactive slots safely read as 0/100 and are untouched; any genuine 1..84%
# construction/train/morph/research progress is advanced to 85%.
old_pulse = '''            slot = 0;
            while (slot < 8) {
                if (UnitCheckProgressState(u, slot, c_unitProgressStateActive)) {
                    progress = UnitGetProgressComplete(u, slot);
                    if (progress > 0.0 && progress < 85.0) {
                        UnitSetProgressComplete(u, slot, 85);
                    }
                }
                slot += 1;
            }
'''
new_pulse = '''            slot = 0;
            while (slot < 32) {
                progress = UnitGetProgressComplete(u, slot);
                if (progress > 0.0 && progress < 85.0) {
                    UnitSetProgressComplete(u, slot, 85);
                }
                slot += 1;
            }
'''
if old_pulse not in src:
    raise SystemExit('Alpha 3.7 progress pulse anchor missing')
src = src.replace(old_pulse, new_pulse, 1)
src = src.replace('TEST BOOST · 광물/가스 10000 · 보급 200 · 건설/생산/변태 진행 85% 가속',
                  'TEST BOOST · 광물/가스 10000 · 보급 200 · 건설/생산/변태/연구 진행 85% 가속', 1)

for marker in (
    'btn-unit-terran-cyclone.dds',
    'DialogControlSetSize(gv_mbSDButton[i], PlayerGroupAll(), 84, 84)',
    'while (slot < 32)',
    'progress = UnitGetProgressComplete(u, slot)',
    '건설/생산/변태/연구 진행 85% 가속'
):
    if marker not in src:
        raise SystemExit(f'Alpha 3.8 marker missing: {marker}')

# The old active-state gate is intentionally gone from the QA pulse.
pulse_start = src.index('void MB_TestBoostPulseFor')
pulse_end = src.index('void MB_TestBoostPulseAll', pulse_start)
if 'UnitCheckProgressState' in src[pulse_start:pulse_end]:
    raise SystemExit('active-state gate still blocks structure morph progress')

# Keep the Galaxy string safety guard.
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
print('Alpha 3.8 prepared: larger SD icon cards + Cyclone texture + raw progress morph acceleration')
