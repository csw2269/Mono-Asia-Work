from pathlib import Path
import runpy
import re

# UI-only refinement on runtime-tested Alpha 4.9.
# Replace decorative ownership lines with a compact team-colored player-name tag.
runpy.run_path('tools/prepare_alpha49.py', run_name='__main__')
path = Path('build/MapScript.galaxy')
src = path.read_text(encoding='utf-8')

# Widen and center the ownership label so a short Battle.net player name can sit above the icon.
old_create = '''        // Reliable ownership ribbon: text color rendering is independent of panel/button skins.\n        gv_mbSDOwnerRibbon[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeLabel);\n        DialogControlSetSize(gv_mbSDOwnerRibbon[i], PlayerGroupAll(), 76, 20);\n        DialogControlSetPosition(gv_mbSDOwnerRibbon[i], PlayerGroupAll(), c_anchorTopLeft, x + 13, y - 3);\n        DialogControlSetPropertyAsString(gv_mbSDOwnerRibbon[i], c_triggerControlPropertyStyle, PlayerGroupAll(), "GameButtonChargeSmall");\n        DialogControlSetVisible(gv_mbSDOwnerRibbon[i], PlayerGroupAll(), false);\n\n'''
if old_create not in src:
    raise SystemExit('Alpha 4.9 ownership-ribbon creation block missing')
new_create = '''        // Pick owner tag: actual player name, rendered above the icon in team color.\n        // The label is deliberately wider than the icon; long names naturally clip instead of\n        // covering neighboring unit art.\n        gv_mbSDOwnerRibbon[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeLabel);\n        DialogControlSetSize(gv_mbSDOwnerRibbon[i], PlayerGroupAll(), 100, 20);\n        DialogControlSetPosition(gv_mbSDOwnerRibbon[i], PlayerGroupAll(), c_anchorTopLeft, x + 1, y - 3);\n        DialogControlSetPropertyAsString(gv_mbSDOwnerRibbon[i], c_triggerControlPropertyStyle, PlayerGroupAll(), "GameButtonChargeSmall");\n        DialogControlSetVisible(gv_mbSDOwnerRibbon[i], PlayerGroupAll(), false);\n\n'''
src = src.replace(old_create, new_create, 1)

# Replace only Alpha 4.9's picked-owner rendering. Keep the clear neutral icon art unchanged.
old_owner = '''        if (picker > 0) {\n            team = MB_SDPlayerTeam(picker);\n            ownerText = MB_TeamTagText(team, "━━━━  P" + IntToString(picker) + "  ━━━━");\n            DialogControlSetPropertyAsText(gv_mbSDOwnerRibbon[i], c_triggerControlPropertyText, PlayerGroupAll(), ownerText);\n            DialogControlSetVisible(gv_mbSDOwnerRibbon[i], PlayerGroupAll(), true);\n\n            DialogControlSetPropertyAsBool(gv_mbSDIcon[i], c_triggerControlPropertyDesaturated, PlayerGroupAll(), true);\n            DialogControlSetPropertyAsText(gv_mbSDPickBadge[i], c_triggerControlPropertyText, PlayerGroupAll(),\n                MB_TeamTagText(team, "P" + IntToString(picker)));\n            DialogControlSetVisible(gv_mbSDPickBadge[i], PlayerGroupAll(), true);\n        }\n        else {\n            DialogControlSetPropertyAsBool(gv_mbSDIcon[i], c_triggerControlPropertyDesaturated, PlayerGroupAll(), false);\n            DialogControlSetVisible(gv_mbSDOwnerRibbon[i], PlayerGroupAll(), false);\n            DialogControlSetVisible(gv_mbSDPickBadge[i], PlayerGroupAll(), false);\n        }\n'''
if old_owner not in src:
    raise SystemExit('Alpha 4.9 picked-owner renderer missing')
new_owner = '''        if (picker > 0) {\n            team = MB_SDPlayerTeam(picker);\n            if (team == 0) { ownerColor = Color(35.0, 70.0, 100.0); }\n            else { ownerColor = Color(100.0, 45.0, 35.0); }\n\n            // P# is kept as a compact fallback identifier, while the actual player name carries\n            // the ownership information the old decorative line could not communicate.\n            ownerText = TextWithColor(StringToText("P" + IntToString(picker) + " ") + PlayerName(picker), ownerColor);\n            DialogControlSetPropertyAsText(gv_mbSDOwnerRibbon[i], c_triggerControlPropertyText, PlayerGroupAll(), ownerText);\n            DialogControlSetVisible(gv_mbSDOwnerRibbon[i], PlayerGroupAll(), true);\n\n            DialogControlSetPropertyAsBool(gv_mbSDIcon[i], c_triggerControlPropertyDesaturated, PlayerGroupAll(), true);\n            // The old lower P# badge is redundant now that the name tag owns this job.\n            DialogControlSetVisible(gv_mbSDPickBadge[i], PlayerGroupAll(), false);\n        }\n        else {\n            DialogControlSetPropertyAsBool(gv_mbSDIcon[i], c_triggerControlPropertyDesaturated, PlayerGroupAll(), false);\n            DialogControlSetVisible(gv_mbSDOwnerRibbon[i], PlayerGroupAll(), false);\n            DialogControlSetVisible(gv_mbSDPickBadge[i], PlayerGroupAll(), false);\n        }\n'''
src = src.replace(old_owner, new_owner, 1)

# Alpha 4.9 renderer has a text owner variable; add the team color used by the new name tag.
old_vars = '''    int picker;\n    int team;\n    text ownerText;\n'''
if old_vars not in src:
    raise SystemExit('Alpha 4.9 owner renderer variables missing')
src = src.replace(old_vars, '''    int picker;\n    int team;\n    color ownerColor;\n    text ownerText;\n''', 1)

# Keep this revision UI-only on the stable test line.
for forbidden in (
    'MB_ApplyUpgradeRestrictionsAll',
    'MB_DisableStandardResearch',
    'MB_EnablePickResearch',
    'MB_UpgradeAllowIfValid',
):
    if forbidden in src:
        raise SystemExit(f'Alpha 5.0 inherited unstable upgrade code: {forbidden}')

for marker in (
    'DialogControlSetSize(gv_mbSDOwnerRibbon[i], PlayerGroupAll(), 100, 20)',
    'PlayerName(picker)',
    'ownerColor = Color(35.0, 70.0, 100.0)',
    'ownerColor = Color(100.0, 45.0, 35.0)',
    'StringToText("P" + IntToString(picker) + " ") + PlayerName(picker)',
    'DialogControlSetVisible(gv_mbSDPickBadge[i], PlayerGroupAll(), false)',
    'Color(100.0, 100.0, 100.0)',
):
    if marker not in src:
        raise SystemExit(f'Alpha 5.0 marker missing: {marker}')

if '━━━━  P' in src:
    raise SystemExit('Alpha 5.0 still contains the old decorative ownership line')

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
print('Alpha 5.0 prepared: team-colored P# + player-name tags above picked SD icons')
