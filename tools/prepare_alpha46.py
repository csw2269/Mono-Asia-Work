from pathlib import Path
import runpy
import re

# Build only on the runtime-confirmed Alpha 4.5 recovery source.
# Keep this revision UI-only: no upgrade/restriction logic changes.
runpy.run_path('tools/prepare_alpha45.py', run_name='__main__')
path = Path('build/MapScript.galaxy')
src = path.read_text(encoding='utf-8')

# --------------------------------------------------------------------------------------
# Globals: a solid plate behind each icon creates a reliable visible team-colored frame.
# Unlike Button BorderColor, this does not depend on the active SC2 button skin.
# --------------------------------------------------------------------------------------
global_anchor = 'int[24] gv_mbSDNameLabel;\n'
if global_anchor not in src:
    raise SystemExit('SD name-label global anchor missing')
src = src.replace(
    global_anchor,
    global_anchor + 'int[24] gv_mbSDTeamPlate;\nint gv_mbSDMyTeamLabel;\n',
    1,
)

# --------------------------------------------------------------------------------------
# Create the personalized team label near the top of the SD screen.
# --------------------------------------------------------------------------------------
info_anchor = '''    gv_mbSDInfo = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeLabel);\n'''
if info_anchor not in src:
    raise SystemExit('SD info creation anchor missing')
team_label_create = '''    gv_mbSDMyTeamLabel = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeLabel);\n    DialogControlSetSize(gv_mbSDMyTeamLabel, PlayerGroupAll(), 300, 34);\n    DialogControlSetPosition(gv_mbSDMyTeamLabel, PlayerGroupAll(), c_anchorTopRight, -38, 58);\n    DialogControlSetPropertyAsString(gv_mbSDMyTeamLabel, c_triggerControlPropertyStyle, PlayerGroupAll(), "DirectiveDisplay");\n\n'''
src = src.replace(info_anchor, team_label_create + info_anchor, 1)

# --------------------------------------------------------------------------------------
# Each card gets a 68x68 colored plate immediately behind the existing 58x58 icon.
# Only 5px is visible around the icon, giving a strong team-color frame when picked.
# --------------------------------------------------------------------------------------
icon_create_anchor = '''        gv_mbSDIcon[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeImage);\n'''
if icon_create_anchor not in src:
    raise SystemExit('SD icon creation anchor missing')
plate_create = '''        gv_mbSDTeamPlate[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypePanel);\n        DialogControlSetSize(gv_mbSDTeamPlate[i], PlayerGroupAll(), 68, 68);\n        DialogControlSetPosition(gv_mbSDTeamPlate[i], PlayerGroupAll(), c_anchorTopLeft, x + 17, y);\n        DialogControlSetPropertyAsBool(gv_mbSDTeamPlate[i], c_triggerControlPropertyBackgroundVisible, PlayerGroupAll(), true);\n        DialogControlSetPropertyAsBool(gv_mbSDTeamPlate[i], c_triggerControlPropertyBorderVisible, PlayerGroupAll(), false);\n        DialogControlSetVisible(gv_mbSDTeamPlate[i], PlayerGroupAll(), false);\n\n'''
src = src.replace(icon_create_anchor, plate_create + icon_create_anchor, 1)

# Put P# directly below the icon instead of floating above it.
src = src.replace(
    '        DialogControlSetSize(gv_mbSDPickBadge[i], PlayerGroupAll(), 46, 20);\n        DialogControlSetPosition(gv_mbSDPickBadge[i], PlayerGroupAll(), c_anchorTopLeft, x + 55, y + 3);',
    '        DialogControlSetSize(gv_mbSDPickBadge[i], PlayerGroupAll(), 76, 18);\n        DialogControlSetPosition(gv_mbSDPickBadge[i], PlayerGroupAll(), c_anchorTopLeft, x + 13, y + 63);',
    1,
)
# Move the unit name down just enough to sit below the P# line.
src = src.replace(
    '        DialogControlSetPosition(gv_mbSDNameLabel[i], PlayerGroupAll(), c_anchorTopLeft, x, y + 78);',
    '        DialogControlSetPosition(gv_mbSDNameLabel[i], PlayerGroupAll(), c_anchorTopLeft, x, y + 81);',
    1,
)

# --------------------------------------------------------------------------------------
# Render the picked-card frame via the solid plate. Keep the existing disabled/desaturated art.
# --------------------------------------------------------------------------------------
old_picked = '''        if (picker > 0) {\n            team = MB_SDPlayerTeam(picker);\n            if (team == 0) { borderColor = Color(25.0, 65.0, 100.0); }\n            else { borderColor = Color(100.0, 30.0, 25.0); }\n            DialogControlSetPropertyAsColor(gv_mbSDButton[i], c_triggerControlPropertyBorderColor, PlayerGroupAll(), borderColor);\n            DialogControlSetPropertyAsText(gv_mbSDPickBadge[i], c_triggerControlPropertyText, PlayerGroupAll(),\n                MB_TeamTagText(team, "P" + IntToString(picker)));\n            DialogControlSetVisible(gv_mbSDPickBadge[i], PlayerGroupAll(), true);\n        }\n        else {\n            DialogControlSetPropertyAsColor(gv_mbSDButton[i], c_triggerControlPropertyBorderColor, PlayerGroupAll(), Color(28.0, 52.0, 68.0));\n            DialogControlSetVisible(gv_mbSDPickBadge[i], PlayerGroupAll(), false);\n        }\n'''
new_picked = '''        if (picker > 0) {\n            team = MB_SDPlayerTeam(picker);\n            if (team == 0) { borderColor = Color(15.0, 55.0, 100.0); }\n            else { borderColor = Color(100.0, 18.0, 12.0); }\n            DialogControlSetPropertyAsColor(gv_mbSDTeamPlate[i], c_triggerControlPropertyColor, PlayerGroupAll(), borderColor);\n            DialogControlSetVisible(gv_mbSDTeamPlate[i], PlayerGroupAll(), true);\n            DialogControlSetPropertyAsText(gv_mbSDPickBadge[i], c_triggerControlPropertyText, PlayerGroupAll(),\n                MB_TeamTagText(team, "P" + IntToString(picker)));\n            DialogControlSetVisible(gv_mbSDPickBadge[i], PlayerGroupAll(), true);\n        }\n        else {\n            DialogControlSetVisible(gv_mbSDTeamPlate[i], PlayerGroupAll(), false);\n            DialogControlSetVisible(gv_mbSDPickBadge[i], PlayerGroupAll(), false);\n        }\n'''
if old_picked not in src:
    raise SystemExit('Alpha 4.5 picked-card rendering anchor missing')
src = src.replace(old_picked, new_picked, 1)

# --------------------------------------------------------------------------------------
# After teams/order are built, clearly identify each viewer's team and tint the header line.
# --------------------------------------------------------------------------------------
start_decl = 'void MB_StartSD () {\n    int p = 1;\n'
if start_decl not in src:
    raise SystemExit('MB_StartSD declaration anchor missing')
src = src.replace(start_decl, 'void MB_StartSD () {\n    int p = 1;\n    int team;\n    playergroup one;\n', 1)

team_order_anchor = '    MB_SDBuildTeamsAndOrder();\n'
if team_order_anchor not in src:
    raise SystemExit('SD team/order anchor missing')
team_identity = '''    MB_SDBuildTeamsAndOrder();\n    p = 1;\n    while (p <= 8) {\n        if (MB_PlayerActive(p)) {\n            team = MB_SDPlayerTeam(p);\n            one = PlayerGroupSingle(p);\n            if (team == 0) {\n                DialogControlSetPropertyAsText(gv_mbSDMyTeamLabel, c_triggerControlPropertyText, one,\n                    TextWithColor(StringToText("YOUR TEAM  ·  BLUE"), Color(15.0, 58.0, 100.0)));\n                DialogControlSetPropertyAsColor(gv_mbSDHeaderPanel, c_triggerControlPropertyColor, one, Color(15.0, 58.0, 100.0));\n            }\n            else {\n                DialogControlSetPropertyAsText(gv_mbSDMyTeamLabel, c_triggerControlPropertyText, one,\n                    TextWithColor(StringToText("YOUR TEAM  ·  RED"), Color(100.0, 22.0, 15.0)));\n                DialogControlSetPropertyAsColor(gv_mbSDHeaderPanel, c_triggerControlPropertyColor, one, Color(100.0, 22.0, 15.0));\n            }\n        }\n        p += 1;\n    }\n'''
src = src.replace(team_order_anchor, team_identity, 1)

# --------------------------------------------------------------------------------------
# Guards. Keep Alpha 4.5's stable boundary: no upgrade-restriction code may sneak back in.
# --------------------------------------------------------------------------------------
for forbidden in (
    'MB_ApplyUpgradeRestrictionsAll',
    'MB_DisableStandardResearch',
    'MB_EnablePickResearch',
    'MB_UpgradeAllowIfValid',
):
    if forbidden in src:
        raise SystemExit(f'Alpha 4.6 inherited unstable upgrade code: {forbidden}')

for marker in (
    'int[24] gv_mbSDTeamPlate',
    'int gv_mbSDMyTeamLabel',
    'gv_mbSDTeamPlate[i] = DialogControlCreate',
    'DialogControlSetVisible(gv_mbSDTeamPlate[i], PlayerGroupAll(), true)',
    'YOUR TEAM  ·  BLUE',
    'YOUR TEAM  ·  RED',
    'DialogControlSetPropertyAsColor(gv_mbSDHeaderPanel',
):
    if marker not in src:
        raise SystemExit(f'Alpha 4.6 marker missing: {marker}')

# Known-good TEST BOOST definitions must remain before their calls.
for fn in ('MB_ApplyTestBoostAll', 'MB_TestBoostPulseAll'):
    definition = 'void ' + fn + ' ()'
    if src.count(definition) != 1:
        raise SystemExit(f'{fn}: expected one definition')
    if src.find(definition) > src.find(fn + '();'):
        raise SystemExit(f'{fn}: definition must precede runtime call')

# Conservative Galaxy structural checks.
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
print('Alpha 4.6 prepared: reliable picked-team frame + personalized team identity')
