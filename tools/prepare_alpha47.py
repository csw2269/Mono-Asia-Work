from pathlib import Path
import runpy
import re

# UI-only refinement on the runtime-confirmed Alpha 4.6 line.
# Do not touch production/upgrade/gameplay restrictions here.
runpy.run_path('tools/prepare_alpha46.py', run_name='__main__')
path = Path('build/MapScript.galaxy')
src = path.read_text(encoding='utf-8')

# --------------------------------------------------------------------------------------
# 1) Remove the redundant YOUR TEAM text. The SD header/theme already carries the viewer's
#    team color; an extra top-right label only competes with PICK ORDER.
# --------------------------------------------------------------------------------------
team_label_anchor = '''    gv_mbSDMyTeamLabel = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeLabel);\n    DialogControlSetSize(gv_mbSDMyTeamLabel, PlayerGroupAll(), 300, 34);\n    DialogControlSetPosition(gv_mbSDMyTeamLabel, PlayerGroupAll(), c_anchorTopRight, -38, 58);\n    DialogControlSetPropertyAsString(gv_mbSDMyTeamLabel, c_triggerControlPropertyStyle, PlayerGroupAll(), "DirectiveDisplay");\n\n'''
if team_label_anchor not in src:
    raise SystemExit('Alpha 4.6 YOUR TEAM label creation anchor missing')
src = src.replace(
    team_label_anchor,
    '''    gv_mbSDMyTeamLabel = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeLabel);\n    DialogControlSetVisible(gv_mbSDMyTeamLabel, PlayerGroupAll(), false);\n\n''',
    1,
)

# --------------------------------------------------------------------------------------
# 2) Reorder each SD card's controls. The transparent click target must sit UNDER the art.
#    SC2 button skins can visually darken controls beneath them even with the background hidden.
#    New order: click target -> neutral/team plate -> icon.
# --------------------------------------------------------------------------------------
plate_block = '''        gv_mbSDTeamPlate[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypePanel);\n        DialogControlSetSize(gv_mbSDTeamPlate[i], PlayerGroupAll(), 68, 68);\n        DialogControlSetPosition(gv_mbSDTeamPlate[i], PlayerGroupAll(), c_anchorTopLeft, x + 17, y);\n        DialogControlSetPropertyAsBool(gv_mbSDTeamPlate[i], c_triggerControlPropertyBackgroundVisible, PlayerGroupAll(), true);\n        DialogControlSetPropertyAsBool(gv_mbSDTeamPlate[i], c_triggerControlPropertyBorderVisible, PlayerGroupAll(), false);\n        DialogControlSetVisible(gv_mbSDTeamPlate[i], PlayerGroupAll(), false);\n\n'''
icon_block = '''        gv_mbSDIcon[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeImage);\n        DialogControlSetSize(gv_mbSDIcon[i], PlayerGroupAll(), 58, 58);\n        DialogControlSetPosition(gv_mbSDIcon[i], PlayerGroupAll(), c_anchorTopLeft, x + 22, y + 5);\n        DialogControlSetPropertyAsInt(gv_mbSDIcon[i], c_triggerControlPropertyImageType, PlayerGroupAll(), c_triggerImageTypeNormal);\n\n'''
button_block = '''        // Transparent click target over a dedicated icon image. This keeps the full unit art visible.\n        gv_mbSDButton[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeButton);\n        DialogControlSetSize(gv_mbSDButton[i], PlayerGroupAll(), 76, 76);\n        DialogControlSetPosition(gv_mbSDButton[i], PlayerGroupAll(), c_anchorTopLeft, x + 13, y);\n        DialogControlSetPropertyAsBool(gv_mbSDButton[i], c_triggerControlPropertyBackgroundVisible, PlayerGroupAll(), false);\n        DialogControlSetPropertyAsBool(gv_mbSDButton[i], c_triggerControlPropertyBorderVisible, PlayerGroupAll(), true);\n'''
sequence = plate_block + icon_block + button_block
if sequence not in src:
    raise SystemExit('Alpha 4.6 SD card control order anchor missing')

new_sequence = '''        // Invisible click target is created first, so it cannot tint/dim the unit art above it.\n        gv_mbSDButton[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeButton);\n        DialogControlSetSize(gv_mbSDButton[i], PlayerGroupAll(), 76, 76);\n        DialogControlSetPosition(gv_mbSDButton[i], PlayerGroupAll(), c_anchorTopLeft, x + 13, y);\n        DialogControlSetPropertyAsBool(gv_mbSDButton[i], c_triggerControlPropertyBackgroundVisible, PlayerGroupAll(), false);\n        DialogControlSetPropertyAsBool(gv_mbSDButton[i], c_triggerControlPropertyBorderVisible, PlayerGroupAll(), false);\n\n        // Neutral slot plate improves contrast. When picked, this same plate becomes a thick\n        // red/blue ownership frame.\n        gv_mbSDTeamPlate[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypePanel);\n        DialogControlSetSize(gv_mbSDTeamPlate[i], PlayerGroupAll(), 74, 74);\n        DialogControlSetPosition(gv_mbSDTeamPlate[i], PlayerGroupAll(), c_anchorTopLeft, x + 14, y - 1);\n        DialogControlSetPropertyAsBool(gv_mbSDTeamPlate[i], c_triggerControlPropertyBackgroundVisible, PlayerGroupAll(), true);\n        DialogControlSetPropertyAsBool(gv_mbSDTeamPlate[i], c_triggerControlPropertyBorderVisible, PlayerGroupAll(), false);\n        DialogControlSetPropertyAsColor(gv_mbSDTeamPlate[i], c_triggerControlPropertyColor, PlayerGroupAll(), Color(16.0, 19.0, 24.0));\n        DialogControlSetVisible(gv_mbSDTeamPlate[i], PlayerGroupAll(), true);\n\n        // Art is the top layer. Slightly larger than before, but still inset enough to avoid\n        // clipping the original SC2 icon texture.\n        gv_mbSDIcon[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeImage);\n        DialogControlSetSize(gv_mbSDIcon[i], PlayerGroupAll(), 62, 62);\n        DialogControlSetPosition(gv_mbSDIcon[i], PlayerGroupAll(), c_anchorTopLeft, x + 20, y + 5);\n        DialogControlSetPropertyAsInt(gv_mbSDIcon[i], c_triggerControlPropertyImageType, PlayerGroupAll(), c_triggerImageTypeNormal);\n\n'''
src = src.replace(sequence, new_sequence, 1)

# --------------------------------------------------------------------------------------
# 3) Make picked ownership unmistakable. Unpicked slots keep a neutral dark plate; picked slots
#    become saturated red/blue with a 6px visible rim around the 62px icon.
# --------------------------------------------------------------------------------------
old_else = '''        else {\n            DialogControlSetVisible(gv_mbSDTeamPlate[i], PlayerGroupAll(), false);\n            DialogControlSetVisible(gv_mbSDPickBadge[i], PlayerGroupAll(), false);\n        }\n'''
new_else = '''        else {\n            DialogControlSetPropertyAsColor(gv_mbSDTeamPlate[i], c_triggerControlPropertyColor, PlayerGroupAll(), Color(16.0, 19.0, 24.0));\n            DialogControlSetVisible(gv_mbSDTeamPlate[i], PlayerGroupAll(), true);\n            DialogControlSetVisible(gv_mbSDPickBadge[i], PlayerGroupAll(), false);\n        }\n'''
if old_else not in src:
    raise SystemExit('Alpha 4.6 unpicked plate branch missing')
src = src.replace(old_else, new_else, 1)

# Stronger team colors for selected-card rim.
src = src.replace(
    'if (team == 0) { borderColor = Color(15.0, 55.0, 100.0); }\n            else { borderColor = Color(100.0, 18.0, 12.0); }',
    'if (team == 0) { borderColor = Color(8.0, 62.0, 100.0); }\n            else { borderColor = Color(100.0, 10.0, 6.0); }',
    1,
)

# --------------------------------------------------------------------------------------
# Guards: keep this as a pure UI patch on the stable recovery branch.
# --------------------------------------------------------------------------------------
for forbidden in (
    'MB_ApplyUpgradeRestrictionsAll',
    'MB_DisableStandardResearch',
    'MB_EnablePickResearch',
    'MB_UpgradeAllowIfValid',
):
    if forbidden in src:
        raise SystemExit(f'Alpha 4.7 inherited unstable upgrade code: {forbidden}')

for marker in (
    'DialogControlSetVisible(gv_mbSDMyTeamLabel, PlayerGroupAll(), false)',
    'DialogControlSetSize(gv_mbSDTeamPlate[i], PlayerGroupAll(), 74, 74)',
    'DialogControlSetSize(gv_mbSDIcon[i], PlayerGroupAll(), 62, 62)',
    'DialogControlSetPropertyAsBool(gv_mbSDButton[i], c_triggerControlPropertyBorderVisible, PlayerGroupAll(), false)',
    'Color(16.0, 19.0, 24.0)',
    'Color(8.0, 62.0, 100.0)',
    'Color(100.0, 10.0, 6.0)',
):
    if marker not in src:
        raise SystemExit(f'Alpha 4.7 marker missing: {marker}')

# TEST BOOST must remain untouched and defined before use.
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
print('Alpha 4.7 prepared: clearer SD art + strong ownership rim + no redundant team label')
