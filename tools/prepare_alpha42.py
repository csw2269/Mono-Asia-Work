from pathlib import Path
import runpy
import re

# Build on Alpha 4.1: vote lock, SD final wait, picker badges, TEST Lair/Hive morph data.
runpy.run_path('tools/prepare_alpha41.py', run_name='__main__')
path = Path('build/MapScript.galaxy')
src = path.read_text(encoding='utf-8')

# -------------------------------------------------------------------------------------------------
# 1) Mode vote/result presentation: names only, no mode descriptions.
# -------------------------------------------------------------------------------------------------
choice_pattern = re.compile(r'void MB_UpdateVoteChoiceFor \(int p\) \{.*?\n\}\n\nint MB_CountActivePlayers', re.S)
choice_replacement = r'''void MB_UpdateVoteChoiceFor (int p) {
    playergroup one = PlayerGroupSingle(p);

    // The mode names stand on their own. The disabled button is the player's current choice.
    DialogControlSetPropertyAsText(gv_mbVoteBlindButton, c_triggerControlPropertyText, one,
        StringToText("BLIND RANDOM"));
    DialogControlSetPropertyAsText(gv_mbVoteSDButton, c_triggerControlPropertyText, one,
        StringToText("SINGLE DRAFT"));

    if (gv_mbVoteLocked) {
        DialogControlSetEnabled(gv_mbVoteBlindButton, one, false);
        DialogControlSetEnabled(gv_mbVoteSDButton, one, false);
        return;
    }

    if (gv_mbVote[p] == MB_MODE_BLIND) {
        DialogControlSetEnabled(gv_mbVoteBlindButton, one, false);
        DialogControlSetEnabled(gv_mbVoteSDButton, one, true);
    }
    else if (gv_mbVote[p] == MB_MODE_SD) {
        DialogControlSetEnabled(gv_mbVoteBlindButton, one, true);
        DialogControlSetEnabled(gv_mbVoteSDButton, one, false);
    }
    else {
        DialogControlSetEnabled(gv_mbVoteBlindButton, one, true);
        DialogControlSetEnabled(gv_mbVoteSDButton, one, true);
    }
}

int MB_CountActivePlayers'''
src, n = choice_pattern.subn(lambda _m: choice_replacement, src, count=1)
if n != 1:
    raise SystemExit(f'failed to replace vote choice UI: {n}')

# Hide the explanatory subtitle during the vote itself.
start_vote_anchor = '    gv_mbVoteLocked = false;\n'
if start_vote_anchor not in src:
    raise SystemExit('vote-lock reset anchor missing')
src = src.replace(start_vote_anchor,
                  start_vote_anchor + '    DialogControlSetVisible(gv_mbVoteSubtitle, PlayerGroupAll(), false);\n', 1)

resolve_pattern = re.compile(r'void MB_ResolveVote \(\) \{.*?\n\}\n\n//--------------------------------------------------------------------------------------------------\n// Trigger handlers', re.S)
resolve_replacement = r'''void MB_ResolveVote () {
    int blind = MB_CountVotes(MB_MODE_BLIND);
    int sd = MB_CountVotes(MB_MODE_SD);
    if (blind > sd) { gv_mbMode = MB_MODE_BLIND; }
    else if (sd > blind) { gv_mbMode = MB_MODE_SD; }
    else { gv_mbMode = RandomInt(MB_MODE_BLIND, MB_MODE_SD); }

    gv_mbPhase = MB_PHASE_MODE_RESULT;

    // Clear everything. The center of the screen shows only the chosen mode name.
    DialogControlSetVisible(gv_mbVoteHeaderPanel, PlayerGroupAll(), false);
    DialogControlSetVisible(gv_mbVoteBlindButton, PlayerGroupAll(), false);
    DialogControlSetVisible(gv_mbVoteSDButton, PlayerGroupAll(), false);
    DialogControlSetVisible(gv_mbVoteInfo, PlayerGroupAll(), false);
    DialogControlSetVisible(gv_mbVoteFooter, PlayerGroupAll(), false);
    DialogControlSetVisible(gv_mbVoteSubtitle, PlayerGroupAll(), false);

    DialogControlSetVisible(gv_mbVoteTitle, PlayerGroupAll(), true);
    DialogControlSetSize(gv_mbVoteTitle, PlayerGroupAll(), 900, 100);
    DialogControlSetPosition(gv_mbVoteTitle, PlayerGroupAll(), c_anchorCenter, 0, 0);
    // ReplayLabel is the native 38px centered label used by Blizzard's game UI.
    DialogControlSetPropertyAsString(gv_mbVoteTitle, c_triggerControlPropertyStyle, PlayerGroupAll(), "ReplayLabel");

    if (gv_mbMode == MB_MODE_SD) {
        DialogControlSetPropertyAsText(gv_mbVoteTitle, c_triggerControlPropertyText, PlayerGroupAll(),
            TextWithColor(StringToText("SINGLE DRAFT"), Color(45.0, 82.0, 100.0)));
    }
    else {
        DialogControlSetPropertyAsText(gv_mbVoteTitle, c_triggerControlPropertyText, PlayerGroupAll(),
            TextWithColor(StringToText("BLIND RANDOM"), Color(45.0, 82.0, 100.0)));
    }

    TimerStart(gv_mbTimer, 2.0, false, c_timeReal);
}

//--------------------------------------------------------------------------------------------------
// Trigger handlers'''
src, n = resolve_pattern.subn(lambda _m: resolve_replacement, src, count=1)
if n != 1:
    raise SystemExit(f'failed to replace mode result UI: {n}')

# -------------------------------------------------------------------------------------------------
# 2) Focus mask: from mode vote through final unit lock, hide the battlefield behind a black layer.
#    The mask dialog is created before the pick dialogs, so all Monobattle controls stay above it.
# -------------------------------------------------------------------------------------------------
global_anchor = 'int gv_mbVoteFooter;\n'
if global_anchor not in src:
    raise SystemExit('vote footer global anchor missing')
src = src.replace(global_anchor,
                  global_anchor + '\n// Pick-phase battlefield focus mask\nint gv_mbFocusDialog;\nint gv_mbFocusPanel;\n', 1)

ui_anchor = '//--------------------------------------------------------------------------------------------------\n// UI creation\n//--------------------------------------------------------------------------------------------------\n'
if ui_anchor not in src:
    raise SystemExit('UI creation anchor missing')
focus_fn = r'''//--------------------------------------------------------------------------------------------------
// Pick-phase battlefield focus mask
//--------------------------------------------------------------------------------------------------
void MB_CreateFocusUI () {
    gv_mbFocusDialog = DialogCreate(2200, 1400, c_anchorCenter, 0, 0, false);
    DialogSetTransparency(gv_mbFocusDialog, 0.0);

    gv_mbFocusPanel = DialogControlCreate(gv_mbFocusDialog, c_triggerControlTypePanel);
    DialogControlSetSize(gv_mbFocusPanel, PlayerGroupAll(), 2200, 1400);
    DialogControlSetPosition(gv_mbFocusPanel, PlayerGroupAll(), c_anchorCenter, 0, 0);
    DialogControlSetPropertyAsBool(gv_mbFocusPanel, c_triggerControlPropertyBackgroundVisible, PlayerGroupAll(), true);
    DialogControlSetPropertyAsBool(gv_mbFocusPanel, c_triggerControlPropertyBorderVisible, PlayerGroupAll(), false);
    DialogControlSetPropertyAsColor(gv_mbFocusPanel, c_triggerControlPropertyColor, PlayerGroupAll(), Color(0.0, 0.0, 0.0));

    DialogSetVisible(gv_mbFocusDialog, PlayerGroupAll(), false);
}

'''
src = src.replace(ui_anchor, ui_anchor + focus_fn, 1)

# Create the blackout first so vote/blind/SD dialogs are layered above it.
init_anchor = '    MB_InitUnitPool();\n    MB_CreateVoteUI();\n'
if init_anchor not in src:
    raise SystemExit('UI init order anchor missing')
src = src.replace(init_anchor,
                  '    MB_InitUnitPool();\n    MB_CreateFocusUI();\n    MB_CreateVoteUI();\n', 1)

# Show at the beginning of voting and release only after all unit selection has actually finished.
start_focus_anchor = '    gv_mbVoteLocked = false;\n    DialogControlSetVisible(gv_mbVoteSubtitle, PlayerGroupAll(), false);\n'
if start_focus_anchor not in src:
    raise SystemExit('focus show anchor missing')
src = src.replace(start_focus_anchor,
                  start_focus_anchor + '    DialogSetVisible(gv_mbFocusDialog, PlayerGroupAll(), true);\n', 1)

finish_anchor = 'void MB_FinishSelection () {\n    gv_mbPhase = MB_PHASE_RUNNING;\n'
if finish_anchor not in src:
    raise SystemExit('finish selection anchor missing')
src = src.replace(finish_anchor,
                  'void MB_FinishSelection () {\n    gv_mbPhase = MB_PHASE_RUNNING;\n    DialogSetVisible(gv_mbFocusDialog, PlayerGroupAll(), false);\n', 1)

# -------------------------------------------------------------------------------------------------
# 3) Single Draft cards: use the real SC2 CommandButton visual and color only P# by team.
# -------------------------------------------------------------------------------------------------
# Replace the transparent generic click overlay with Blizzard's actual 76x76 command-button template.
old_button = '''        // Transparent overlay receives clicks/tooltip and supplies a subtle selection border.
        gv_mbSDButton[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeButton);
        DialogControlSetSize(gv_mbSDButton[i], PlayerGroupAll(), 88, 68);
        DialogControlSetPosition(gv_mbSDButton[i], PlayerGroupAll(), c_anchorTopLeft, x + 7, y);
        DialogControlSetPropertyAsBool(gv_mbSDButton[i], c_triggerControlPropertyBackgroundVisible, PlayerGroupAll(), false);
        DialogControlSetPropertyAsBool(gv_mbSDButton[i], c_triggerControlPropertyBorderVisible, PlayerGroupAll(), true);
'''
new_button = '''        // Native production-button look: the same 76x76 CommandButton template used by SC2's command card.
        gv_mbSDButton[i] = DialogControlCreateFromTemplate(gv_mbSDDialog, c_triggerControlTypeButton, "CommandButton/CommandButtonTemplate");
        DialogControlSetSize(gv_mbSDButton[i], PlayerGroupAll(), 76, 76);
        DialogControlSetPosition(gv_mbSDButton[i], PlayerGroupAll(), c_anchorTopLeft, x + 13, y);
        DialogControlSetPropertyAsBool(gv_mbSDButton[i], c_triggerControlPropertyBorderVisible, PlayerGroupAll(), true);
'''
if old_button not in src:
    raise SystemExit('transparent SD button geometry anchor missing')
src = src.replace(old_button, new_button, 1)

# Put the name cleanly below the command button.
src = src.replace(
    'DialogControlSetPosition(gv_mbSDNameLabel[i], PlayerGroupAll(), c_anchorTopLeft, x, y + 69);',
    'DialogControlSetPosition(gv_mbSDNameLabel[i], PlayerGroupAll(), c_anchorTopLeft, x, y + 78);',
    1,
)

# Smaller picker tag in the top-right of the card; P# only, actual text color carries team identity.
src = src.replace(
    'DialogControlSetSize(gv_mbSDPickBadge[i], PlayerGroupAll(), 96, 22);\n        DialogControlSetPosition(gv_mbSDPickBadge[i], PlayerGroupAll(), c_anchorTopLeft, x + 8, y + 4);',
    'DialogControlSetSize(gv_mbSDPickBadge[i], PlayerGroupAll(), 46, 20);\n        DialogControlSetPosition(gv_mbSDPickBadge[i], PlayerGroupAll(), c_anchorTopLeft, x + 55, y + 3);',
    1,
)

# Full board updater: render the icon directly on CommandButton, keep all untaken cards vivid for
# everybody, and rely on MB_SDPickSlot's existing turn check to reject clicks from non-current players.
update_pattern = re.compile(r'void MB_SDUpdateBoardButtons \(\) \{.*?\n\}\n\nvoid MB_SDUpdateOrderText', re.S)
update_replacement = r'''void MB_SDUpdateBoardButtons () {
    int i = 0;
    string icon;
    string display;
    int picker;
    int team;
    string badge;

    while (i < MB_SD_CANDIDATES) {
        icon = MB_UnitIcon(gv_mbSDCandidate[i]);
        display = MB_DisplayName(gv_mbSDCandidate[i]);

        // The CommandButton template owns the art, exactly like a normal unit-production button.
        DialogControlSetVisible(gv_mbSDIcon[i], PlayerGroupAll(), false);
        if (icon != "") {
            DialogControlSetPropertyAsString(gv_mbSDButton[i], c_triggerControlPropertyImage, PlayerGroupAll(), icon);
            DialogControlSetPropertyAsString(gv_mbSDButton[i], c_triggerControlPropertyHoverImage, PlayerGroupAll(), icon);
            DialogControlSetPropertyAsInt(gv_mbSDButton[i], c_triggerControlPropertyImageType, PlayerGroupAll(), c_triggerImageTypeNormal);
        }
        DialogControlSetPropertyAsText(gv_mbSDButton[i], c_triggerControlPropertyText, PlayerGroupAll(), StringToText(""));
        DialogControlSetPropertyAsText(gv_mbSDButton[i], c_triggerControlPropertyTooltip, PlayerGroupAll(), StringToText(display));
        DialogControlSetPropertyAsText(gv_mbSDNameLabel[i], c_triggerControlPropertyText, PlayerGroupAll(), StringToText(display));

        picker = gv_mbSDPickedBy[i];
        if (picker > 0) {
            team = MB_SDPlayerTeam(picker);
            badge = "P" + IntToString(picker);
            DialogControlSetPropertyAsText(gv_mbSDPickBadge[i], c_triggerControlPropertyText, PlayerGroupAll(),
                MB_TeamTagText(team, badge));
            DialogControlSetVisible(gv_mbSDPickBadge[i], PlayerGroupAll(), true);
        }
        else {
            DialogControlSetVisible(gv_mbSDPickBadge[i], PlayerGroupAll(), false);
        }

        DialogControlSetPropertyAsBool(gv_mbSDButton[i], c_triggerControlPropertyDesaturated, PlayerGroupAll(), gv_mbSDTaken[i]);
        // Untaken cards stay visually enabled for everyone. Wrong-turn clicks are already rejected by MB_SDPickSlot.
        DialogControlSetEnabled(gv_mbSDButton[i], PlayerGroupAll(), !gv_mbSDTaken[i]);
        i += 1;
    }
}

void MB_SDUpdateOrderText'''
src, n = update_pattern.subn(lambda _m: update_replacement, src, count=1)
if n != 1:
    raise SystemExit(f'failed to replace SD board rendering: {n}')

# -------------------------------------------------------------------------------------------------
# Guards
# -------------------------------------------------------------------------------------------------
for marker in (
    'StringToText("BLIND RANDOM")',
    'StringToText("SINGLE DRAFT")',
    '"ReplayLabel"',
    'int gv_mbFocusDialog',
    'void MB_CreateFocusUI ()',
    'DialogSetVisible(gv_mbFocusDialog, PlayerGroupAll(), true)',
    'DialogSetVisible(gv_mbFocusDialog, PlayerGroupAll(), false)',
    '"CommandButton/CommandButtonTemplate"',
    'badge = "P" + IntToString(picker)',
    'DialogControlSetEnabled(gv_mbSDButton[i], PlayerGroupAll(), !gv_mbSDTaken[i])',
    'MB_SD_FINAL_WAIT_SECONDS = 3.0'
):
    if marker not in src:
        raise SystemExit(f'Alpha 4.2 marker missing: {marker}')

# Mode descriptions must no longer leak into selection/result UI.
for forbidden in (
    'BLIND RANDOM\\n종족 선택 + 즉시 추첨',
    'SINGLE DRAFT\\n24개 후보 드래프트',
    '24개 후보 · ABBAABBA 스네이크 픽 · 15초 제한',
    '종족 선택 즉시 추첨 · Random 선택 시 리롤 1회',
    '[BLUE] P', '[RED] P'
):
    if forbidden in src:
        raise SystemExit(f'Alpha 4.2 stale UI text remains: {forbidden}')

# Galaxy quoted strings may contain escaped \n but never literal line breaks.
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
print('Alpha 4.2 prepared: names-only mode UI + centered result + focus mask + native SD command buttons')
