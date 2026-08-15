from pathlib import Path
import runpy
import re

# First generate the Alpha 3 source (pick-matched starting race + icon SD UI).
runpy.run_path('tools/prepare_alpha3.py', run_name='__main__')

path = Path('build/MapScript.galaxy')
src = path.read_text(encoding='utf-8')

# With starting units now created only AFTER selection, there is nothing to pause during
# vote/draft. Removing UnitPauseAll also avoids the compile error reported by the live SC2 runtime.
src = src.replace('    UnitPauseAll(true);\n', '')
src = src.replace('    UnitPauseAll(false);\n', '')

# SC2 reported the compact vote-reset loop as the other compile-error site. Keep the same
# vote initialization, but remove the per-player helper call and give everyone the default
# labels directly. Personal "my selection" highlighting can be reintroduced after runtime QA.
pattern = re.compile(
    r'    while \(p <= 8\) \{ gv_mbVote\[p\] = MB_MODE_NONE; MB_ResetVoteButtonTextFor\(p\); p \+= 1; \}\n'
)
replacement = '''    while (p <= 8) {
        gv_mbVote[p] = MB_MODE_NONE;
        p += 1;
    }
    DialogControlSetPropertyAsText(gv_mbVoteBlindButton, c_triggerControlPropertyText, PlayerGroupAll(),
        StringToText("BLIND RANDOM\\n종족 선택 + 즉시 추첨"));
    DialogControlSetPropertyAsText(gv_mbVoteSDButton, c_triggerControlPropertyText, PlayerGroupAll(),
        StringToText("SINGLE DRAFT\\n24개 후보 드래프트"));
'''
src, n = pattern.subn(replacement, src, count=1)
if n != 1:
    raise SystemExit(f'failed to replace reported vote-reset error site: {n}')

# Remove the same optional personal-label helper from click handling for this QA build.
src = src.replace(' MB_ResetVoteButtonTextFor(p);', '')
src = src.replace('MB_ResetVoteButtonTextFor(p); ', '')

if 'UnitPauseAll(' in src:
    raise SystemExit('Alpha 3.1 must not call UnitPauseAll during pre-game selection')
if 'MB_ResetVoteButtonTextFor(p)' in src:
    raise SystemExit('Alpha 3.1 must not call the reported vote-label helper')
for marker in ('MB_InitStartingUnitsAll', 'MeleeInitUnitsForPlayer', 'PlayerSetRace', 'MB_UnitIcon', 'gv_mbSDNameLabel'):
    if marker not in src:
        raise SystemExit(f'Alpha 3 functionality regressed: {marker}')

path.write_text(src, encoding='utf-8', newline='\n')
print('Alpha 3.1 hardened: removed both runtime-reported compile-error call sites')
