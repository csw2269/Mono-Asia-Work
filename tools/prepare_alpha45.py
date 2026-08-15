from pathlib import Path
import runpy
import re

# Recovery build: start from Alpha 4.2, which was confirmed to load in SC2.
# Do not inherit Alpha 4.4/4.4.1 upgrade/roster rewrites.
runpy.run_path('tools/prepare_alpha42.py', run_name='__main__')
path = Path('build/MapScript.galaxy')
src = path.read_text(encoding='utf-8')

# Restore the safe icon-layer model. Alpha 4.2 switched the click target to a CommandButton
# template and hid gv_mbSDIcon, which caused the candidate art to disappear.
old_button = '''        // Native production-button look: the same 76x76 CommandButton template used by SC2's command card.
        gv_mbSDButton[i] = DialogControlCreateFromTemplate(gv_mbSDDialog, c_triggerControlTypeButton, "CommandButton/CommandButtonTemplate");
        DialogControlSetSize(gv_mbSDButton[i], PlayerGroupAll(), 76, 76);
        DialogControlSetPosition(gv_mbSDButton[i], PlayerGroupAll(), c_anchorTopLeft, x + 13, y);
        DialogControlSetPropertyAsBool(gv_mbSDButton[i], c_triggerControlPropertyBorderVisible, PlayerGroupAll(), true);
'''
new_button = '''        // Transparent click target over a dedicated icon image. This keeps the full unit art visible.
        gv_mbSDButton[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeButton);
        DialogControlSetSize(gv_mbSDButton[i], PlayerGroupAll(), 76, 76);
        DialogControlSetPosition(gv_mbSDButton[i], PlayerGroupAll(), c_anchorTopLeft, x + 13, y);
        DialogControlSetPropertyAsBool(gv_mbSDButton[i], c_triggerControlPropertyBackgroundVisible, PlayerGroupAll(), false);
        DialogControlSetPropertyAsBool(gv_mbSDButton[i], c_triggerControlPropertyBorderVisible, PlayerGroupAll(), true);
'''
if old_button not in src:
    raise SystemExit('Alpha 4.2 command-button block missing')
src = src.replace(old_button, new_button, 1)

update_pattern = re.compile(r'void MB_SDUpdateBoardButtons \(\) \{.*?\n\}\n\nvoid MB_SDUpdateOrderText', re.S)
update_replacement = r'''void MB_SDUpdateBoardButtons () {
    int i = 0;
    string icon;
    string display;
    int picker;
    int team;
    color borderColor;

    while (i < MB_SD_CANDIDATES) {
        icon = MB_UnitIcon(gv_mbSDCandidate[i]);
        display = MB_DisplayName(gv_mbSDCandidate[i]);
        picker = gv_mbSDPickedBy[i];

        if (icon != "") {
            DialogControlSetPropertyAsString(gv_mbSDIcon[i], c_triggerControlPropertyImage, PlayerGroupAll(), icon);
            DialogControlSetPropertyAsInt(gv_mbSDIcon[i], c_triggerControlPropertyImageType, PlayerGroupAll(), c_triggerImageTypeNormal);
            DialogControlSetVisible(gv_mbSDIcon[i], PlayerGroupAll(), true);
        }
        else {
            DialogControlSetVisible(gv_mbSDIcon[i], PlayerGroupAll(), false);
        }

        DialogControlSetPropertyAsBool(gv_mbSDIcon[i], c_triggerControlPropertyDesaturated, PlayerGroupAll(), gv_mbSDTaken[i]);
        DialogControlSetPropertyAsText(gv_mbSDButton[i], c_triggerControlPropertyText, PlayerGroupAll(), StringToText(""));
        DialogControlSetPropertyAsText(gv_mbSDButton[i], c_triggerControlPropertyTooltip, PlayerGroupAll(), StringToText(display));
        DialogControlSetPropertyAsText(gv_mbSDNameLabel[i], c_triggerControlPropertyText, PlayerGroupAll(), StringToText(display));

        if (picker > 0) {
            team = MB_SDPlayerTeam(picker);
            if (team == 0) { borderColor = Color(25.0, 65.0, 100.0); }
            else { borderColor = Color(100.0, 30.0, 25.0); }
            DialogControlSetPropertyAsColor(gv_mbSDButton[i], c_triggerControlPropertyBorderColor, PlayerGroupAll(), borderColor);
            DialogControlSetPropertyAsText(gv_mbSDPickBadge[i], c_triggerControlPropertyText, PlayerGroupAll(),
                MB_TeamTagText(team, "P" + IntToString(picker)));
            DialogControlSetVisible(gv_mbSDPickBadge[i], PlayerGroupAll(), true);
        }
        else {
            DialogControlSetPropertyAsColor(gv_mbSDButton[i], c_triggerControlPropertyBorderColor, PlayerGroupAll(), Color(28.0, 52.0, 68.0));
            DialogControlSetVisible(gv_mbSDPickBadge[i], PlayerGroupAll(), false);
        }

        DialogControlSetEnabled(gv_mbSDButton[i], PlayerGroupAll(), !gv_mbSDTaken[i]);
        i += 1;
    }
}

void MB_SDUpdateOrderText'''
src, n = update_pattern.subn(lambda _m: update_replacement, src, count=1)
if n != 1:
    raise SystemExit(f'failed to replace SD updater: {n}')

# Recovery guards: the broken 4.4 upgrade code must not be inherited.
for forbidden in (
    'MB_ApplyUpgradeRestrictionsAll',
    'MB_DisableStandardResearch',
    'MB_EnablePickResearch',
    'MB_UpgradeAllowIfValid',
):
    if forbidden in src:
        raise SystemExit(f'Alpha 4.5 inherited unstable 4.4 code: {forbidden}')

# Confirm the known-good TEST BOOST implementation is still present exactly once and before use.
for fn in ('MB_ApplyTestBoostAll', 'MB_TestBoostPulseAll'):
    definition = 'void ' + fn + ' ()'
    if src.count(definition) != 1:
        raise SystemExit(f'{fn}: expected one definition')
    if src.find(definition) > src.find(fn + '();'):
        raise SystemExit(f'{fn}: definition must precede runtime call')

for marker in (
    'DialogControlSetVisible(gv_mbSDIcon[i], PlayerGroupAll(), true)',
    'c_triggerControlPropertyDesaturated',
    'c_triggerControlPropertyBorderColor',
    'MB_TeamTagText(team, "P" + IntToString(picker))',
    'DialogControlSetPropertyAsBool(gv_mbSDButton[i], c_triggerControlPropertyBackgroundVisible, PlayerGroupAll(), false)',
):
    if marker not in src:
        raise SystemExit(f'Alpha 4.5 marker missing: {marker}')

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
print('Alpha 4.5 recovery prepared: stable 4.2 base + restored SD art/owner border')
