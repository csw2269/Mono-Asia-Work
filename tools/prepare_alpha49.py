from pathlib import Path
import runpy
import re

# UI-only refinement on Alpha 4.8. Keep the now-clear icon rendering exactly as-is.
runpy.run_path('tools/prepare_alpha48.py', run_name='__main__')
path = Path('build/MapScript.galaxy')
src = path.read_text(encoding='utf-8')

# The Panel-based borders have repeatedly failed to remain visible under SC2 dialog skins.
# Use a text-rendered ownership ribbon instead; team-colored text is already proven visible
# in the SD pick-order UI and picker badge.
global_anchor = 'int[24] gv_mbSDFrameRight;\n'
if global_anchor not in src:
    raise SystemExit('Alpha 4.8 frame globals missing')
src = src.replace(global_anchor, global_anchor + 'int[24] gv_mbSDOwnerRibbon;\n', 1)

# Create the ribbon AFTER the old frame controls so the ribbon is the top-most ownership layer.
right_frame_create = '''        gv_mbSDFrameRight[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypePanel);\n        DialogControlSetSize(gv_mbSDFrameRight[i], PlayerGroupAll(), 7, 69);\n        DialogControlSetPosition(gv_mbSDFrameRight[i], PlayerGroupAll(), c_anchorTopLeft, x + 79, y + 2);\n        DialogControlSetPropertyAsBool(gv_mbSDFrameRight[i], c_triggerControlPropertyBackgroundVisible, PlayerGroupAll(), true);\n        DialogControlSetPropertyAsBool(gv_mbSDFrameRight[i], c_triggerControlPropertyBorderVisible, PlayerGroupAll(), false);\n        DialogControlSetVisible(gv_mbSDFrameRight[i], PlayerGroupAll(), false);\n\n'''
if right_frame_create not in src:
    raise SystemExit('Alpha 4.8 right-frame creation block missing')
ribbon_create = right_frame_create + '''        // Reliable ownership ribbon: text color rendering is independent of panel/button skins.\n        gv_mbSDOwnerRibbon[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeLabel);\n        DialogControlSetSize(gv_mbSDOwnerRibbon[i], PlayerGroupAll(), 76, 20);\n        DialogControlSetPosition(gv_mbSDOwnerRibbon[i], PlayerGroupAll(), c_anchorTopLeft, x + 13, y - 3);\n        DialogControlSetPropertyAsString(gv_mbSDOwnerRibbon[i], c_triggerControlPropertyStyle, PlayerGroupAll(), "GameButtonChargeSmall");\n        DialogControlSetVisible(gv_mbSDOwnerRibbon[i], PlayerGroupAll(), false);\n\n'''
src = src.replace(right_frame_create, ribbon_create, 1)

# Replace the renderer with a ribbon-first ownership treatment. The old frame controls remain
# allocated for compatibility with Alpha 4.8 but are forced hidden at every update.
update_pattern = re.compile(r'void MB_SDUpdateBoardButtons \(\) \{.*?\n\}\n\nvoid MB_SDUpdateOrderText', re.S)
update_replacement = r'''void MB_SDUpdateBoardButtons () {
    int i = 0;
    string icon;
    string display;
    int picker;
    int team;
    text ownerText;

    while (i < MB_SD_CANDIDATES) {
        icon = MB_UnitIcon(gv_mbSDCandidate[i]);
        display = MB_DisplayName(gv_mbSDCandidate[i]);
        picker = gv_mbSDPickedBy[i];

        // Preserve Alpha 4.8's clear, neutral icon rendering.
        if (icon != "") {
            DialogControlSetPropertyAsString(gv_mbSDIcon[i], c_triggerControlPropertyImage, PlayerGroupAll(), icon);
            DialogControlSetPropertyAsInt(gv_mbSDIcon[i], c_triggerControlPropertyImageType, PlayerGroupAll(), c_triggerImageTypeNormal);
            DialogControlSetPropertyAsColor(gv_mbSDIcon[i], c_triggerControlPropertyColor, PlayerGroupAll(), Color(100.0, 100.0, 100.0));
            DialogControlSetVisible(gv_mbSDIcon[i], PlayerGroupAll(), true);
        }
        else {
            DialogControlSetVisible(gv_mbSDIcon[i], PlayerGroupAll(), false);
        }

        DialogControlSetPropertyAsText(gv_mbSDButton[i], c_triggerControlPropertyText, PlayerGroupAll(), StringToText(""));
        DialogControlSetPropertyAsText(gv_mbSDButton[i], c_triggerControlPropertyTooltip, PlayerGroupAll(), StringToText(display));
        DialogControlSetPropertyAsText(gv_mbSDNameLabel[i], c_triggerControlPropertyText, PlayerGroupAll(), StringToText(display));
        DialogControlSetPropertyAsColor(gv_mbSDTeamPlate[i], c_triggerControlPropertyColor, PlayerGroupAll(), Color(20.0, 23.0, 28.0));
        DialogControlSetVisible(gv_mbSDTeamPlate[i], PlayerGroupAll(), true);

        // Panel borders are deliberately retired: they were not reliable in-game.
        DialogControlSetVisible(gv_mbSDFrameTop[i], PlayerGroupAll(), false);
        DialogControlSetVisible(gv_mbSDFrameBottom[i], PlayerGroupAll(), false);
        DialogControlSetVisible(gv_mbSDFrameLeft[i], PlayerGroupAll(), false);
        DialogControlSetVisible(gv_mbSDFrameRight[i], PlayerGroupAll(), false);

        if (picker > 0) {
            team = MB_SDPlayerTeam(picker);
            ownerText = MB_TeamTagText(team, "━━━━  P" + IntToString(picker) + "  ━━━━");
            DialogControlSetPropertyAsText(gv_mbSDOwnerRibbon[i], c_triggerControlPropertyText, PlayerGroupAll(), ownerText);
            DialogControlSetVisible(gv_mbSDOwnerRibbon[i], PlayerGroupAll(), true);

            DialogControlSetPropertyAsBool(gv_mbSDIcon[i], c_triggerControlPropertyDesaturated, PlayerGroupAll(), true);
            DialogControlSetPropertyAsText(gv_mbSDPickBadge[i], c_triggerControlPropertyText, PlayerGroupAll(),
                MB_TeamTagText(team, "P" + IntToString(picker)));
            DialogControlSetVisible(gv_mbSDPickBadge[i], PlayerGroupAll(), true);
        }
        else {
            DialogControlSetPropertyAsBool(gv_mbSDIcon[i], c_triggerControlPropertyDesaturated, PlayerGroupAll(), false);
            DialogControlSetVisible(gv_mbSDOwnerRibbon[i], PlayerGroupAll(), false);
            DialogControlSetVisible(gv_mbSDPickBadge[i], PlayerGroupAll(), false);
        }

        DialogControlSetEnabled(gv_mbSDButton[i], PlayerGroupAll(), !gv_mbSDTaken[i]);
        i += 1;
    }
}

void MB_SDUpdateOrderText'''
src, n = update_pattern.subn(lambda _m: update_replacement, src, count=1)
if n != 1:
    raise SystemExit(f'failed to replace Alpha 4.9 SD renderer: {n}')

# Keep this revision UI-only on the stable branch.
for forbidden in (
    'MB_ApplyUpgradeRestrictionsAll',
    'MB_DisableStandardResearch',
    'MB_EnablePickResearch',
    'MB_UpgradeAllowIfValid',
):
    if forbidden in src:
        raise SystemExit(f'Alpha 4.9 inherited unstable upgrade code: {forbidden}')

for marker in (
    'int[24] gv_mbSDOwnerRibbon',
    'gv_mbSDOwnerRibbon[i] = DialogControlCreate',
    '━━━━  P',
    'DialogControlSetVisible(gv_mbSDOwnerRibbon[i], PlayerGroupAll(), true)',
    'DialogControlSetPropertyAsColor(gv_mbSDIcon[i], c_triggerControlPropertyColor, PlayerGroupAll(), Color(100.0, 100.0, 100.0))',
):
    if marker not in src:
        raise SystemExit(f'Alpha 4.9 marker missing: {marker}')

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
print('Alpha 4.9 prepared: clear icons + reliable team-color ownership ribbons')
