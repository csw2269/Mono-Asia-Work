from pathlib import Path
import runpy
import re

# UI-only refinement on the runtime-confirmed Alpha 4.7 line.
# Goal: preserve the clear icon rendering condition without copying the old green UI skin.
runpy.run_path('tools/prepare_alpha47.py', run_name='__main__')
path = Path('build/MapScript.galaxy')
src = path.read_text(encoding='utf-8')

# --------------------------------------------------------------------------------------
# 1) Strong ownership frame controls. A single colored plate behind the icon was too subtle
#    under SC2's UI rendering. Draw four explicit bars ABOVE the icon instead.
# --------------------------------------------------------------------------------------
global_anchor = 'int[24] gv_mbSDTeamPlate;\n'
if global_anchor not in src:
    raise SystemExit('Alpha 4.7 team-plate global missing')
src = src.replace(
    global_anchor,
    global_anchor
    + 'int[24] gv_mbSDFrameTop;\n'
    + 'int[24] gv_mbSDFrameBottom;\n'
    + 'int[24] gv_mbSDFrameLeft;\n'
    + 'int[24] gv_mbSDFrameRight;\n',
    1,
)

# Insert the four frame bars immediately after the icon control is created, so they render above
# both the click target and the icon art. They stay hidden until a unit is picked.
icon_create_anchor = '''        gv_mbSDIcon[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeImage);\n        DialogControlSetSize(gv_mbSDIcon[i], PlayerGroupAll(), 62, 62);\n        DialogControlSetPosition(gv_mbSDIcon[i], PlayerGroupAll(), c_anchorTopLeft, x + 20, y + 5);\n        DialogControlSetPropertyAsInt(gv_mbSDIcon[i], c_triggerControlPropertyImageType, PlayerGroupAll(), c_triggerImageTypeNormal);\n\n'''
if icon_create_anchor not in src:
    raise SystemExit('Alpha 4.7 icon creation anchor missing')
frame_create = icon_create_anchor + '''        // Explicit top-layer ownership frame. Four bars are more reliable than a skinned border.\n        gv_mbSDFrameTop[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypePanel);\n        DialogControlSetSize(gv_mbSDFrameTop[i], PlayerGroupAll(), 70, 7);\n        DialogControlSetPosition(gv_mbSDFrameTop[i], PlayerGroupAll(), c_anchorTopLeft, x + 16, y + 2);\n        DialogControlSetPropertyAsBool(gv_mbSDFrameTop[i], c_triggerControlPropertyBackgroundVisible, PlayerGroupAll(), true);\n        DialogControlSetPropertyAsBool(gv_mbSDFrameTop[i], c_triggerControlPropertyBorderVisible, PlayerGroupAll(), false);\n        DialogControlSetVisible(gv_mbSDFrameTop[i], PlayerGroupAll(), false);\n\n        gv_mbSDFrameBottom[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypePanel);\n        DialogControlSetSize(gv_mbSDFrameBottom[i], PlayerGroupAll(), 70, 7);\n        DialogControlSetPosition(gv_mbSDFrameBottom[i], PlayerGroupAll(), c_anchorTopLeft, x + 16, y + 64);\n        DialogControlSetPropertyAsBool(gv_mbSDFrameBottom[i], c_triggerControlPropertyBackgroundVisible, PlayerGroupAll(), true);\n        DialogControlSetPropertyAsBool(gv_mbSDFrameBottom[i], c_triggerControlPropertyBorderVisible, PlayerGroupAll(), false);\n        DialogControlSetVisible(gv_mbSDFrameBottom[i], PlayerGroupAll(), false);\n\n        gv_mbSDFrameLeft[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypePanel);\n        DialogControlSetSize(gv_mbSDFrameLeft[i], PlayerGroupAll(), 7, 69);\n        DialogControlSetPosition(gv_mbSDFrameLeft[i], PlayerGroupAll(), c_anchorTopLeft, x + 16, y + 2);\n        DialogControlSetPropertyAsBool(gv_mbSDFrameLeft[i], c_triggerControlPropertyBackgroundVisible, PlayerGroupAll(), true);\n        DialogControlSetPropertyAsBool(gv_mbSDFrameLeft[i], c_triggerControlPropertyBorderVisible, PlayerGroupAll(), false);\n        DialogControlSetVisible(gv_mbSDFrameLeft[i], PlayerGroupAll(), false);\n\n        gv_mbSDFrameRight[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypePanel);\n        DialogControlSetSize(gv_mbSDFrameRight[i], PlayerGroupAll(), 7, 69);\n        DialogControlSetPosition(gv_mbSDFrameRight[i], PlayerGroupAll(), c_anchorTopLeft, x + 79, y + 2);\n        DialogControlSetPropertyAsBool(gv_mbSDFrameRight[i], c_triggerControlPropertyBackgroundVisible, PlayerGroupAll(), true);\n        DialogControlSetPropertyAsBool(gv_mbSDFrameRight[i], c_triggerControlPropertyBorderVisible, PlayerGroupAll(), false);\n        DialogControlSetVisible(gv_mbSDFrameRight[i], PlayerGroupAll(), false);\n\n'''
src = src.replace(icon_create_anchor, frame_create, 1)

# --------------------------------------------------------------------------------------
# 2) Replace the board renderer. Force unpicked art to neutral/full-color rendering, keep the
#    background plate neutral, and use the four explicit bars only for picked ownership.
# --------------------------------------------------------------------------------------
update_pattern = re.compile(r'void MB_SDUpdateBoardButtons \(\) \{.*?\n\}\n\nvoid MB_SDUpdateOrderText', re.S)
update_replacement = r'''void MB_SDUpdateBoardButtons () {
    int i = 0;
    string icon;
    string display;
    int picker;
    int team;
    color teamColor;

    while (i < MB_SD_CANDIDATES) {
        icon = MB_UnitIcon(gv_mbSDCandidate[i]);
        display = MB_DisplayName(gv_mbSDCandidate[i]);
        picker = gv_mbSDPickedBy[i];

        // Keep the art itself neutral. No team/race tint is ever applied to candidate icons.
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

        // Neutral modern charcoal behind every icon. Ownership is communicated only by the
        // explicit red/blue frame and the colored P# label.
        DialogControlSetPropertyAsColor(gv_mbSDTeamPlate[i], c_triggerControlPropertyColor, PlayerGroupAll(), Color(20.0, 23.0, 28.0));
        DialogControlSetVisible(gv_mbSDTeamPlate[i], PlayerGroupAll(), true);

        if (picker > 0) {
            team = MB_SDPlayerTeam(picker);
            if (team == 0) { teamColor = Color(8.0, 62.0, 100.0); }
            else { teamColor = Color(100.0, 10.0, 6.0); }

            DialogControlSetPropertyAsColor(gv_mbSDFrameTop[i], c_triggerControlPropertyColor, PlayerGroupAll(), teamColor);
            DialogControlSetPropertyAsColor(gv_mbSDFrameBottom[i], c_triggerControlPropertyColor, PlayerGroupAll(), teamColor);
            DialogControlSetPropertyAsColor(gv_mbSDFrameLeft[i], c_triggerControlPropertyColor, PlayerGroupAll(), teamColor);
            DialogControlSetPropertyAsColor(gv_mbSDFrameRight[i], c_triggerControlPropertyColor, PlayerGroupAll(), teamColor);
            DialogControlSetVisible(gv_mbSDFrameTop[i], PlayerGroupAll(), true);
            DialogControlSetVisible(gv_mbSDFrameBottom[i], PlayerGroupAll(), true);
            DialogControlSetVisible(gv_mbSDFrameLeft[i], PlayerGroupAll(), true);
            DialogControlSetVisible(gv_mbSDFrameRight[i], PlayerGroupAll(), true);

            DialogControlSetPropertyAsBool(gv_mbSDIcon[i], c_triggerControlPropertyDesaturated, PlayerGroupAll(), true);
            DialogControlSetPropertyAsText(gv_mbSDPickBadge[i], c_triggerControlPropertyText, PlayerGroupAll(),
                MB_TeamTagText(team, "P" + IntToString(picker)));
            DialogControlSetVisible(gv_mbSDPickBadge[i], PlayerGroupAll(), true);
        }
        else {
            DialogControlSetPropertyAsBool(gv_mbSDIcon[i], c_triggerControlPropertyDesaturated, PlayerGroupAll(), false);
            DialogControlSetVisible(gv_mbSDFrameTop[i], PlayerGroupAll(), false);
            DialogControlSetVisible(gv_mbSDFrameBottom[i], PlayerGroupAll(), false);
            DialogControlSetVisible(gv_mbSDFrameLeft[i], PlayerGroupAll(), false);
            DialogControlSetVisible(gv_mbSDFrameRight[i], PlayerGroupAll(), false);
            DialogControlSetVisible(gv_mbSDPickBadge[i], PlayerGroupAll(), false);
        }

        DialogControlSetEnabled(gv_mbSDButton[i], PlayerGroupAll(), !gv_mbSDTaken[i]);
        i += 1;
    }
}

void MB_SDUpdateOrderText'''
src, n = update_pattern.subn(lambda _m: update_replacement, src, count=1)
if n != 1:
    raise SystemExit(f'failed to replace Alpha 4.8 SD board renderer: {n}')

# --------------------------------------------------------------------------------------
# 3) Keep team identity deterministic and modern: explicit blue/red accent on the header only.
#    Do not let the hidden YOUR TEAM label or any green fallback communicate the team.
# --------------------------------------------------------------------------------------
src = src.replace(
    'DialogControlSetPropertyAsColor(gv_mbSDHeaderPanel, c_triggerControlPropertyColor, one, Color(15.0, 58.0, 100.0));',
    'DialogControlSetPropertyAsColor(gv_mbSDHeaderPanel, c_triggerControlPropertyColor, one, Color(8.0, 46.0, 72.0));',
)
src = src.replace(
    'DialogControlSetPropertyAsColor(gv_mbSDHeaderPanel, c_triggerControlPropertyColor, one, Color(100.0, 22.0, 15.0));',
    'DialogControlSetPropertyAsColor(gv_mbSDHeaderPanel, c_triggerControlPropertyColor, one, Color(72.0, 14.0, 10.0));',
)

# --------------------------------------------------------------------------------------
# Guards. This remains a UI-only patch on the stable recovery branch.
# --------------------------------------------------------------------------------------
for forbidden in (
    'MB_ApplyUpgradeRestrictionsAll',
    'MB_DisableStandardResearch',
    'MB_EnablePickResearch',
    'MB_UpgradeAllowIfValid',
):
    if forbidden in src:
        raise SystemExit(f'Alpha 4.8 inherited unstable upgrade code: {forbidden}')

for marker in (
    'int[24] gv_mbSDFrameTop',
    'int[24] gv_mbSDFrameBottom',
    'int[24] gv_mbSDFrameLeft',
    'int[24] gv_mbSDFrameRight',
    'DialogControlSetPropertyAsColor(gv_mbSDIcon[i], c_triggerControlPropertyColor, PlayerGroupAll(), Color(100.0, 100.0, 100.0))',
    'DialogControlSetSize(gv_mbSDFrameTop[i], PlayerGroupAll(), 70, 7)',
    'DialogControlSetVisible(gv_mbSDFrameRight[i], PlayerGroupAll(), true)',
    'Color(20.0, 23.0, 28.0)',
    'Color(8.0, 46.0, 72.0)',
    'Color(72.0, 14.0, 10.0)',
):
    if marker not in src:
        raise SystemExit(f'Alpha 4.8 marker missing: {marker}')

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
print('Alpha 4.8 prepared: neutral full-color icons + explicit top-layer ownership frame')
