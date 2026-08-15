from pathlib import Path
import runpy
import re

# UI-only refinement on Alpha 5.0.
# Put ownership information in the original lower P# badge position and show only the player name.
runpy.run_path('tools/prepare_alpha50.py', run_name='__main__')
path = Path('build/MapScript.galaxy')
src = path.read_text(encoding='utf-8')

# The upper ownership ribbon is no longer used. Keep the allocated control for compatibility,
# but force it hidden. Reuse the original lower pick badge, widened around the same center point.
create_anchor = '''        // Pick owner tag: actual player name, rendered above the icon in team color.\n        // The label is deliberately wider than the icon; long names naturally clip instead of\n        // covering neighboring unit art.\n        gv_mbSDOwnerRibbon[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeLabel);\n        DialogControlSetSize(gv_mbSDOwnerRibbon[i], PlayerGroupAll(), 100, 20);\n        DialogControlSetPosition(gv_mbSDOwnerRibbon[i], PlayerGroupAll(), c_anchorTopLeft, x + 1, y - 3);\n        DialogControlSetPropertyAsString(gv_mbSDOwnerRibbon[i], c_triggerControlPropertyStyle, PlayerGroupAll(), "GameButtonChargeSmall");\n        DialogControlSetVisible(gv_mbSDOwnerRibbon[i], PlayerGroupAll(), false);\n\n'''
if create_anchor not in src:
    raise SystemExit('Alpha 5.0 upper owner-tag creation block missing')
replacement = '''        // Alpha 5.1: ownership is shown in the original lower badge position instead.\n        // Keep this legacy control allocated but permanently hidden.\n        gv_mbSDOwnerRibbon[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeLabel);\n        DialogControlSetVisible(gv_mbSDOwnerRibbon[i], PlayerGroupAll(), false);\n\n'''
src = src.replace(create_anchor, replacement, 1)

# Widen the original P# badge while preserving its center and vertical position.
old_badge = '''        DialogControlSetSize(gv_mbSDPickBadge[i], PlayerGroupAll(), 76, 18);\n        DialogControlSetPosition(gv_mbSDPickBadge[i], PlayerGroupAll(), c_anchorTopLeft, x + 13, y + 63);'''
new_badge = '''        DialogControlSetSize(gv_mbSDPickBadge[i], PlayerGroupAll(), 100, 18);\n        DialogControlSetPosition(gv_mbSDPickBadge[i], PlayerGroupAll(), c_anchorTopLeft, x + 1, y + 63);'''
if old_badge not in src:
    raise SystemExit('existing lower P# badge geometry missing')
src = src.replace(old_badge, new_badge, 1)

# Replace Alpha 5.0 ownership rendering: no P-number, no upper ribbon, actual player name only.
old_owner = '''        if (picker > 0) {\n            team = MB_SDPlayerTeam(picker);\n            if (team == 0) { ownerColor = Color(35.0, 70.0, 100.0); }\n            else { ownerColor = Color(100.0, 45.0, 35.0); }\n\n            // P# is kept as a compact fallback identifier, while the actual player name carries\n            // the ownership information the old decorative line could not communicate.\n            ownerText = TextWithColor(StringToText("P" + IntToString(picker) + " ") + PlayerName(picker), ownerColor);\n            DialogControlSetPropertyAsText(gv_mbSDOwnerRibbon[i], c_triggerControlPropertyText, PlayerGroupAll(), ownerText);\n            DialogControlSetVisible(gv_mbSDOwnerRibbon[i], PlayerGroupAll(), true);\n\n            DialogControlSetPropertyAsBool(gv_mbSDIcon[i], c_triggerControlPropertyDesaturated, PlayerGroupAll(), true);\n            // The old lower P# badge is redundant now that the name tag owns this job.\n            DialogControlSetVisible(gv_mbSDPickBadge[i], PlayerGroupAll(), false);\n        }\n        else {\n            DialogControlSetPropertyAsBool(gv_mbSDIcon[i], c_triggerControlPropertyDesaturated, PlayerGroupAll(), false);\n            DialogControlSetVisible(gv_mbSDOwnerRibbon[i], PlayerGroupAll(), false);\n            DialogControlSetVisible(gv_mbSDPickBadge[i], PlayerGroupAll(), false);\n        }\n'''
if old_owner not in src:
    raise SystemExit('Alpha 5.0 ownership renderer missing')
new_owner = '''        if (picker > 0) {\n            team = MB_SDPlayerTeam(picker);\n            if (team == 0) { ownerColor = Color(35.0, 70.0, 100.0); }\n            else { ownerColor = Color(100.0, 45.0, 35.0); }\n\n            // Player number is intentionally omitted: the real player name is enough.\n            ownerText = TextWithColor(PlayerName(picker), ownerColor);\n            DialogControlSetVisible(gv_mbSDOwnerRibbon[i], PlayerGroupAll(), false);\n            DialogControlSetPropertyAsText(gv_mbSDPickBadge[i], c_triggerControlPropertyText, PlayerGroupAll(), ownerText);\n            DialogControlSetVisible(gv_mbSDPickBadge[i], PlayerGroupAll(), true);\n\n            DialogControlSetPropertyAsBool(gv_mbSDIcon[i], c_triggerControlPropertyDesaturated, PlayerGroupAll(), true);\n        }\n        else {\n            DialogControlSetPropertyAsBool(gv_mbSDIcon[i], c_triggerControlPropertyDesaturated, PlayerGroupAll(), false);\n            DialogControlSetVisible(gv_mbSDOwnerRibbon[i], PlayerGroupAll(), false);\n            DialogControlSetVisible(gv_mbSDPickBadge[i], PlayerGroupAll(), false);\n        }\n'''
src = src.replace(old_owner, new_owner, 1)

# Keep this revision UI-only on the stable test line.
for forbidden in (
    'MB_ApplyUpgradeRestrictionsAll',
    'MB_DisableStandardResearch',
    'MB_EnablePickResearch',
    'MB_UpgradeAllowIfValid',
):
    if forbidden in src:
        raise SystemExit(f'Alpha 5.1 inherited unstable upgrade code: {forbidden}')

for marker in (
    'DialogControlSetSize(gv_mbSDPickBadge[i], PlayerGroupAll(), 100, 18)',
    'DialogControlSetPosition(gv_mbSDPickBadge[i], PlayerGroupAll(), c_anchorTopLeft, x + 1, y + 63)',
    'ownerText = TextWithColor(PlayerName(picker), ownerColor)',
    'DialogControlSetPropertyAsText(gv_mbSDPickBadge[i], c_triggerControlPropertyText, PlayerGroupAll(), ownerText)',
    'DialogControlSetVisible(gv_mbSDPickBadge[i], PlayerGroupAll(), true)',
    'Color(100.0, 100.0, 100.0)',
):
    if marker not in src:
        raise SystemExit(f'Alpha 5.1 marker missing: {marker}')

# P-number ownership text must be gone from the final source. Pick-order P# remains elsewhere by design.
if 'StringToText("P" + IntToString(picker) + " ") + PlayerName(picker)' in src:
    raise SystemExit('Alpha 5.1 still prefixes the player name with P#')
if '━━━━  P' in src:
    raise SystemExit('Alpha 5.1 still contains old decorative ownership line')

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
print('Alpha 5.1 prepared: team-colored player name only in the original lower badge position')
