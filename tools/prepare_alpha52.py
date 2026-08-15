from pathlib import Path
import runpy
import re

# UI-only refinement on Alpha 5.1.
# Goals from runtime screenshot:
#   1) prevent SC2's default button hover/disabled skin from flashing green over SD cards;
#   2) keep player-name and unit-name labels fully inside each 106px card cell.
runpy.run_path('tools/prepare_alpha51.py', run_name='__main__')
path = Path('build/MapScript.galaxy')
src = path.read_text(encoding='utf-8')

# --------------------------------------------------------------------------------------
# 1) SD click targets must be truly invisible. They remain mouse-active, but alpha 0 prevents
#    default SC2 hover/focus/disabled artwork (including the green state) from ever being drawn.
#    Wrong-turn and already-taken clicks are rejected by MB_SDPickSlot, so visual disabling is
#    unnecessary and can safely be removed.
# --------------------------------------------------------------------------------------
button_anchor = '''        gv_mbSDButton[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeButton);\n        DialogControlSetSize(gv_mbSDButton[i], PlayerGroupAll(), 76, 76);\n        DialogControlSetPosition(gv_mbSDButton[i], PlayerGroupAll(), c_anchorTopLeft, x + 13, y);\n        DialogControlSetPropertyAsBool(gv_mbSDButton[i], c_triggerControlPropertyBackgroundVisible, PlayerGroupAll(), false);\n        DialogControlSetPropertyAsBool(gv_mbSDButton[i], c_triggerControlPropertyBorderVisible, PlayerGroupAll(), false);\n'''
if button_anchor not in src:
    raise SystemExit('Alpha 5.1 transparent SD button creation anchor missing')
button_replacement = button_anchor + '''        DialogControlSetPropertyAsInt(gv_mbSDButton[i], c_triggerControlPropertyAlpha, PlayerGroupAll(), 0);\n        DialogControlSetPropertyAsBool(gv_mbSDButton[i], c_triggerControlPropertyAcceptMouseTarget, PlayerGroupAll(), true);\n'''
src = src.replace(button_anchor, button_replacement, 1)

old_enabled = '        DialogControlSetEnabled(gv_mbSDButton[i], PlayerGroupAll(), !gv_mbSDTaken[i]);\n'
if old_enabled not in src:
    raise SystemExit('Alpha 5.1 SD button enabled-state line missing')
src = src.replace(
    old_enabled,
    '''        // Never invoke the default disabled/hover skin. Gameplay legality is enforced in MB_SDPickSlot.\n        DialogControlSetEnabled(gv_mbSDButton[i], PlayerGroupAll(), true);\n''',
    1,
)

# --------------------------------------------------------------------------------------
# 2) Put the actual player name on its own compact line BELOW the icon. Alpha 5.1 used a 100px
#    label beginning at x+1 and y+63; that was too wide and touched the icon/unit-name line.
#    New geometry stays safely inside the 106px cell and leaves a clear vertical gap.
# --------------------------------------------------------------------------------------
old_badge = '''        DialogControlSetSize(gv_mbSDPickBadge[i], PlayerGroupAll(), 100, 18);\n        DialogControlSetPosition(gv_mbSDPickBadge[i], PlayerGroupAll(), c_anchorTopLeft, x + 1, y + 63);'''
new_badge = '''        DialogControlSetSize(gv_mbSDPickBadge[i], PlayerGroupAll(), 88, 18);\n        DialogControlSetPosition(gv_mbSDPickBadge[i], PlayerGroupAll(), c_anchorTopLeft, x + 4, y + 72);'''
if old_badge not in src:
    raise SystemExit('Alpha 5.1 player-name badge geometry missing')
src = src.replace(old_badge, new_badge, 1)

# Keep the unit name on a separate centered-width line with a few pixels left/right margin.
# Alpha 4.6+ currently places it at y+81, directly touching Alpha 5.1's player-name badge.
old_name_size = '        DialogControlSetSize(gv_mbSDNameLabel[i], PlayerGroupAll(), 96, 22);\n'
new_name_size = '        DialogControlSetSize(gv_mbSDNameLabel[i], PlayerGroupAll(), 88, 18);\n'
if old_name_size not in src:
    raise SystemExit('SD unit-name size anchor missing')
src = src.replace(old_name_size, new_name_size, 1)

old_name_pos = '        DialogControlSetPosition(gv_mbSDNameLabel[i], PlayerGroupAll(), c_anchorTopLeft, x, y + 81);\n'
new_name_pos = '''        DialogControlSetPosition(gv_mbSDNameLabel[i], PlayerGroupAll(), c_anchorTopLeft, x + 4, y + 93);\n        DialogControlSetPropertyAsString(gv_mbSDNameLabel[i], c_triggerControlPropertyStyle, PlayerGroupAll(), "GameButtonChargeSmall");\n'''
if old_name_pos not in src:
    raise SystemExit('SD unit-name position anchor missing')
src = src.replace(old_name_pos, new_name_pos, 1)

# Player-name badge already uses GameButtonChargeSmall from the stable SD layout. Keep that small
# native font and the existing team-colored PlayerName(picker) rendering from Alpha 5.1.

# --------------------------------------------------------------------------------------
# Guards: this remains a UI-only change. Stable TEST BOOST/morph behavior must remain intact and
# the old upgrade-restriction experiment must remain absent.
# --------------------------------------------------------------------------------------
for forbidden in (
    'MB_ApplyUpgradeRestrictionsAll',
    'MB_DisableStandardResearch',
    'MB_EnablePickResearch',
    'MB_UpgradeAllowIfValid',
):
    if forbidden in src:
        raise SystemExit(f'Alpha 5.2 inherited unstable upgrade code: {forbidden}')

for marker in (
    'DialogControlSetPropertyAsInt(gv_mbSDButton[i], c_triggerControlPropertyAlpha, PlayerGroupAll(), 0)',
    'DialogControlSetPropertyAsBool(gv_mbSDButton[i], c_triggerControlPropertyAcceptMouseTarget, PlayerGroupAll(), true)',
    'DialogControlSetEnabled(gv_mbSDButton[i], PlayerGroupAll(), true)',
    'DialogControlSetSize(gv_mbSDPickBadge[i], PlayerGroupAll(), 88, 18)',
    'DialogControlSetPosition(gv_mbSDPickBadge[i], PlayerGroupAll(), c_anchorTopLeft, x + 4, y + 72)',
    'DialogControlSetSize(gv_mbSDNameLabel[i], PlayerGroupAll(), 88, 18)',
    'DialogControlSetPosition(gv_mbSDNameLabel[i], PlayerGroupAll(), c_anchorTopLeft, x + 4, y + 93)',
    'ownerText = TextWithColor(PlayerName(picker), ownerColor)',
    'Color(100.0, 100.0, 100.0)',
):
    if marker not in src:
        raise SystemExit(f'Alpha 5.2 marker missing: {marker}')

if 'DialogControlSetEnabled(gv_mbSDButton[i], PlayerGroupAll(), !gv_mbSDTaken[i])' in src:
    raise SystemExit('Alpha 5.2 still invokes taken-card disabled skin')
if 'StringToText("P" + IntToString(picker) + " ") + PlayerName(picker)' in src:
    raise SystemExit('Alpha 5.2 unexpectedly restored P# prefix')
if '━━━━  P' in src:
    raise SystemExit('Alpha 5.2 unexpectedly restored decorative owner line')

for fn in ('MB_ApplyTestBoostAll', 'MB_TestBoostPulseAll'):
    definition = 'void ' + fn + ' ()'
    if src.count(definition) != 1:
        raise SystemExit(f'{fn}: expected one definition')
    if src.find(definition) > src.find(fn + '();'):
        raise SystemExit(f'{fn}: definition must precede runtime call')

clean = re.sub(r'"(?:\\.|[^"\\])*"', '""', src)
clean = re.sub(r'//.*', '', clean)
depth = 0
for pos, ch in enumerate(clean):
    if ch == '{':
        depth += 1
    elif ch == '}':
        depth -= 1
        if depth < 0:
            raise SystemExit(f'negative brace depth near {pos}')
if depth != 0:
    raise SystemExit(f'unbalanced braces: {depth}')

path.write_text(src, encoding='utf-8', newline='\n')
print('Alpha 5.2 prepared: invisible hit targets + contained player/unit labels')
