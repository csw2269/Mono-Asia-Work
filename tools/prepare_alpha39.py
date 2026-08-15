from pathlib import Path
import runpy
import re

# Build on Alpha 3.8 (stable TEST BOOST + morph progress acceleration).
runpy.run_path('tools/prepare_alpha38.py', run_name='__main__')
path = Path('build/MapScript.galaxy')
src = path.read_text(encoding='utf-8')

# -------------------------------------------------------------------------------------------------
# 1) SD icon rendering: separate the art from the clickable button.
#    The prior approach painted the icon directly into a button control, which clips the source
#    texture to the button's render region. Use a smaller image control inside a transparent
#    clickable card so the complete icon is scaled down and remains visible.
# -------------------------------------------------------------------------------------------------
global_anchor = 'int[24] gv_mbSDNameLabel;\n'
if global_anchor not in src:
    raise SystemExit('SD name label global anchor missing')
src = src.replace(global_anchor, global_anchor + 'int[24] gv_mbSDIcon;\n', 1)

# Update board visuals: image goes to gv_mbSDIcon; button remains click target/tooltip only.
update_pattern = re.compile(r'void MB_SDUpdateBoardButtons \(\) \{.*?\n\}\n\nvoid MB_SDUpdateOrderText', re.S)
update_replacement = r'''void MB_SDUpdateBoardButtons () {
    int i = 0;
    string icon;
    string display;
    while (i < MB_SD_CANDIDATES) {
        icon = MB_UnitIcon(gv_mbSDCandidate[i]);
        display = MB_DisplayName(gv_mbSDCandidate[i]);
        if (icon != "") {
            DialogControlSetPropertyAsString(gv_mbSDIcon[i], c_triggerControlPropertyImage, PlayerGroupAll(), icon);
            DialogControlSetPropertyAsInt(gv_mbSDIcon[i], c_triggerControlPropertyImageType, PlayerGroupAll(), c_triggerImageTypeNormal);
            DialogControlSetVisible(gv_mbSDIcon[i], PlayerGroupAll(), true);
        }
        else {
            DialogControlSetVisible(gv_mbSDIcon[i], PlayerGroupAll(), false);
        }
        DialogControlSetPropertyAsText(gv_mbSDButton[i], c_triggerControlPropertyText, PlayerGroupAll(), StringToText(""));
        DialogControlSetPropertyAsText(gv_mbSDButton[i], c_triggerControlPropertyTooltip, PlayerGroupAll(), StringToText(display));
        DialogControlSetPropertyAsText(gv_mbSDNameLabel[i], c_triggerControlPropertyText, PlayerGroupAll(), StringToText(display));
        DialogControlSetPropertyAsBool(gv_mbSDIcon[i], c_triggerControlPropertyDesaturated, PlayerGroupAll(), gv_mbSDTaken[i]);
        DialogControlSetEnabled(gv_mbSDButton[i], PlayerGroupAll(), false);
        i += 1;
    }
    if (gv_mbSDPickIndex < gv_mbSDOrderCount) {
        i = 0;
        while (i < MB_SD_CANDIDATES) {
            if (!gv_mbSDTaken[i]) {
                DialogControlSetEnabled(gv_mbSDButton[i], PlayerGroupSingle(gv_mbSDOrder[gv_mbSDPickIndex]), true);
            }
            i += 1;
        }
    }
}

void MB_SDUpdateOrderText'''
src, n = update_pattern.subn(lambda _m: update_replacement, src, count=1)
if n != 1:
    raise SystemExit(f'failed to replace SD updater: {n}')

# Alpha 3.8 final card geometry block. Replace it with icon-first art + transparent click overlay.
old_card = '''        gv_mbSDButton[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeButton);
        DialogControlSetSize(gv_mbSDButton[i], PlayerGroupAll(), 84, 84);
        DialogControlSetPosition(gv_mbSDButton[i], PlayerGroupAll(), c_anchorTopLeft, x + 6, y);
        DialogControlSetPropertyAsBool(gv_mbSDButton[i], c_triggerControlPropertyBorderVisible, PlayerGroupAll(), true);

        gv_mbSDNameLabel[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeLabel);
        DialogControlSetSize(gv_mbSDNameLabel[i], PlayerGroupAll(), 102, 24);
        DialogControlSetPosition(gv_mbSDNameLabel[i], PlayerGroupAll(), c_anchorTopLeft, x, y + 86);
'''
new_card = '''        // Dedicated art control: scale the full source icon into a 58x58 box so no edge is clipped.
        gv_mbSDIcon[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeImage);
        DialogControlSetSize(gv_mbSDIcon[i], PlayerGroupAll(), 58, 58);
        DialogControlSetPosition(gv_mbSDIcon[i], PlayerGroupAll(), c_anchorTopLeft, x + 22, y + 5);
        DialogControlSetPropertyAsInt(gv_mbSDIcon[i], c_triggerControlPropertyImageType, PlayerGroupAll(), c_triggerImageTypeNormal);

        // Transparent overlay receives clicks/tooltip and supplies a subtle selection border.
        gv_mbSDButton[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeButton);
        DialogControlSetSize(gv_mbSDButton[i], PlayerGroupAll(), 88, 68);
        DialogControlSetPosition(gv_mbSDButton[i], PlayerGroupAll(), c_anchorTopLeft, x + 7, y);
        DialogControlSetPropertyAsBool(gv_mbSDButton[i], c_triggerControlPropertyBackgroundVisible, PlayerGroupAll(), false);
        DialogControlSetPropertyAsBool(gv_mbSDButton[i], c_triggerControlPropertyBorderVisible, PlayerGroupAll(), true);

        gv_mbSDNameLabel[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeLabel);
        DialogControlSetSize(gv_mbSDNameLabel[i], PlayerGroupAll(), 102, 24);
        DialogControlSetPosition(gv_mbSDNameLabel[i], PlayerGroupAll(), c_anchorTopLeft, x, y + 69);
'''
if old_card not in src:
    raise SystemExit('Alpha 3.8 SD card geometry anchor missing')
src = src.replace(old_card, new_card, 1)

# Tighten vertical spacing now that the art is deliberately smaller inside each card.
src = src.replace('        y = 104 + (row * 112);', '        y = 106 + (row * 104);', 1)
src = src.replace('    DialogControlSetPosition(gv_mbSDHintLabel, PlayerGroupAll(), c_anchorTopLeft, 24, 574);',
                  '    DialogControlSetPosition(gv_mbSDHintLabel, PlayerGroupAll(), c_anchorTopLeft, 24, 548);', 1)

# -------------------------------------------------------------------------------------------------
# 2) Vote UX: current choice is disabled/marked, all-voted shortens the wait, and the winning mode
#    is visibly announced before entering Blind/SD.
# -------------------------------------------------------------------------------------------------
phase_anchor = 'const int MB_PHASE_RUNNING    = 4;\n'
if phase_anchor not in src:
    raise SystemExit('phase constants anchor missing')
src = src.replace(phase_anchor, phase_anchor + 'const int MB_PHASE_MODE_RESULT = 5;\n', 1)

vote_helper_anchor = 'int MB_CountVotes (int mode) {'
if vote_helper_anchor not in src:
    raise SystemExit('vote count anchor missing')
new_vote_helpers = r'''void MB_UpdateVoteChoiceFor (int p) {
    playergroup one = PlayerGroupSingle(p);
    if (gv_mbVote[p] == MB_MODE_BLIND) {
        DialogControlSetEnabled(gv_mbVoteBlindButton, one, false);
        DialogControlSetEnabled(gv_mbVoteSDButton, one, true);
        DialogControlSetPropertyAsText(gv_mbVoteBlindButton, c_triggerControlPropertyText, one,
            StringToText("BLIND RANDOM\n✓ 선택됨"));
        DialogControlSetPropertyAsText(gv_mbVoteSDButton, c_triggerControlPropertyText, one,
            StringToText("SINGLE DRAFT\n24개 후보 드래프트"));
    }
    else if (gv_mbVote[p] == MB_MODE_SD) {
        DialogControlSetEnabled(gv_mbVoteBlindButton, one, true);
        DialogControlSetEnabled(gv_mbVoteSDButton, one, false);
        DialogControlSetPropertyAsText(gv_mbVoteBlindButton, c_triggerControlPropertyText, one,
            StringToText("BLIND RANDOM\n종족 선택 + 즉시 추첨"));
        DialogControlSetPropertyAsText(gv_mbVoteSDButton, c_triggerControlPropertyText, one,
            StringToText("SINGLE DRAFT\n✓ 선택됨"));
    }
    else {
        DialogControlSetEnabled(gv_mbVoteBlindButton, one, true);
        DialogControlSetEnabled(gv_mbVoteSDButton, one, true);
        DialogControlSetPropertyAsText(gv_mbVoteBlindButton, c_triggerControlPropertyText, one,
            StringToText("BLIND RANDOM\n종족 선택 + 즉시 추첨"));
        DialogControlSetPropertyAsText(gv_mbVoteSDButton, c_triggerControlPropertyText, one,
            StringToText("SINGLE DRAFT\n24개 후보 드래프트"));
    }
}

int MB_CountActivePlayers () {
    int p = 1;
    int count = 0;
    while (p <= 8) {
        if (MB_PlayerActive(p)) { count += 1; }
        p += 1;
    }
    return count;
}

int MB_CountVotesCast () {
    int p = 1;
    int count = 0;
    while (p <= 8) {
        if (MB_PlayerActive(p) && gv_mbVote[p] != MB_MODE_NONE) { count += 1; }
        p += 1;
    }
    return count;
}

bool MB_AllActivePlayersVoted () {
    int active = MB_CountActivePlayers();
    return (active > 0 && MB_CountVotesCast() >= active);
}

void MB_TryAccelerateVote () {
    fixed remain;
    if (!MB_AllActivePlayersVoted()) { return; }
    remain = TimerGetRemaining(gv_mbTimer);
    if (remain > 3.0) {
        TimerStart(gv_mbTimer, 3.0, false, c_timeReal);
    }
    DialogControlSetPropertyAsText(gv_mbVoteFooter, c_triggerControlPropertyText, PlayerGroupAll(),
        StringToText("모든 플레이어 투표 완료 · 3초 후 확정"));
}

'''
src = src.replace(vote_helper_anchor, new_vote_helpers + vote_helper_anchor, 1)

# More informative live tally.
old_vote_ui = '''void MB_UpdateVoteUI () {
    int blind = MB_CountVotes(MB_MODE_BLIND);
    int sd = MB_CountVotes(MB_MODE_SD);
    int remain = FixedToInt(TimerGetRemaining(gv_mbTimer));
    string s = "BLIND  " + IntToString(blind) + "표     |     SINGLE DRAFT  " + IntToString(sd) + "표     |     " + IntToString(remain) + "초";
    DialogControlSetPropertyAsText(gv_mbVoteInfo, c_triggerControlPropertyText, PlayerGroupAll(), StringToText(s));
}'''
new_vote_ui = '''void MB_UpdateVoteUI () {
    int blind = MB_CountVotes(MB_MODE_BLIND);
    int sd = MB_CountVotes(MB_MODE_SD);
    int cast = MB_CountVotesCast();
    int active = MB_CountActivePlayers();
    int remain = FixedToInt(TimerGetRemaining(gv_mbTimer));
    string s = "BLIND  " + IntToString(blind) + "표     |     SINGLE DRAFT  " + IntToString(sd) + "표     |     투표 " + IntToString(cast) + "/" + IntToString(active) + "     |     " + IntToString(remain) + "초";
    DialogControlSetPropertyAsText(gv_mbVoteInfo, c_triggerControlPropertyText, PlayerGroupAll(), StringToText(s));
}'''
if old_vote_ui not in src:
    raise SystemExit('vote UI function anchor missing')
src = src.replace(old_vote_ui, new_vote_ui, 1)

# Start vote: reset each viewer's selected/disabled state and restore normal footer.
start_vote_anchor = '''    DialogControlSetPropertyAsText(gv_mbVoteSDButton, c_triggerControlPropertyText, PlayerGroupAll(),
        StringToText("SINGLE DRAFT\\n24개 후보 드래프트"));
    DialogSetVisible(gv_mbBlindDialog, PlayerGroupAll(), false);'''
start_vote_replacement = '''    DialogControlSetPropertyAsText(gv_mbVoteSDButton, c_triggerControlPropertyText, PlayerGroupAll(),
        StringToText("SINGLE DRAFT\\n24개 후보 드래프트"));
    p = 1;
    while (p <= 8) {
        MB_UpdateVoteChoiceFor(p);
        p += 1;
    }
    DialogControlSetPropertyAsText(gv_mbVoteFooter, c_triggerControlPropertyText, PlayerGroupAll(),
        StringToText("20초 동안 자유롭게 표를 바꿀 수 있습니다"));
    DialogSetVisible(gv_mbBlindDialog, PlayerGroupAll(), false);'''
if start_vote_anchor not in src:
    raise SystemExit('start vote display anchor missing')
src = src.replace(start_vote_anchor, start_vote_replacement, 1)

# Replace resolve with a 2-second result-announcement phase.
resolve_pattern = re.compile(r'void MB_ResolveVote \(\) \{.*?\n\}\n\n//--------------------------------------------------------------------------------------------------\n// Trigger handlers', re.S)
resolve_replacement = r'''void MB_ResolveVote () {
    int blind = MB_CountVotes(MB_MODE_BLIND);
    int sd = MB_CountVotes(MB_MODE_SD);
    if (blind > sd) { gv_mbMode = MB_MODE_BLIND; }
    else if (sd > blind) { gv_mbMode = MB_MODE_SD; }
    else { gv_mbMode = RandomInt(MB_MODE_BLIND, MB_MODE_SD); }

    gv_mbPhase = MB_PHASE_MODE_RESULT;
    DialogControlSetEnabled(gv_mbVoteBlindButton, PlayerGroupAll(), false);
    DialogControlSetEnabled(gv_mbVoteSDButton, PlayerGroupAll(), false);
    DialogControlSetPropertyAsText(gv_mbVoteTitle, c_triggerControlPropertyText, PlayerGroupAll(),
        TextWithColor(StringToText("MODE SELECTED"), Color(45.0, 82.0, 100.0)));
    if (gv_mbMode == MB_MODE_SD) {
        DialogControlSetPropertyAsText(gv_mbVoteSubtitle, c_triggerControlPropertyText, PlayerGroupAll(),
            StringToText("SINGLE DRAFT"));
        DialogControlSetPropertyAsText(gv_mbVoteInfo, c_triggerControlPropertyText, PlayerGroupAll(),
            StringToText("24개 후보 · 스네이크 드래프트"));
    }
    else {
        DialogControlSetPropertyAsText(gv_mbVoteSubtitle, c_triggerControlPropertyText, PlayerGroupAll(),
            StringToText("BLIND RANDOM"));
        DialogControlSetPropertyAsText(gv_mbVoteInfo, c_triggerControlPropertyText, PlayerGroupAll(),
            StringToText("종족 선택 · 즉시 추첨 · Random 리롤 1회"));
    }
    DialogControlSetPropertyAsText(gv_mbVoteFooter, c_triggerControlPropertyText, PlayerGroupAll(),
        StringToText("2초 후 선택 화면으로 이동합니다"));
    TimerStart(gv_mbTimer, 2.0, false, c_timeReal);
}

//--------------------------------------------------------------------------------------------------
// Trigger handlers'''
src, n = resolve_pattern.subn(lambda _m: resolve_replacement, src, count=1)
if n != 1:
    raise SystemExit(f'failed to replace vote resolver: {n}')

# Click handler: mark/disable current choice and check for all-voted early finish.
old_clicks = '''        if (control == gv_mbVoteBlindButton) { gv_mbVote[p] = MB_MODE_BLIND; MB_UpdateVoteUI(); }
        else if (control == gv_mbVoteSDButton) { gv_mbVote[p] = MB_MODE_SD; MB_UpdateVoteUI(); }
        return true;'''
new_clicks = '''        if (control == gv_mbVoteBlindButton) { gv_mbVote[p] = MB_MODE_BLIND; }
        else if (control == gv_mbVoteSDButton) { gv_mbVote[p] = MB_MODE_SD; }
        MB_UpdateVoteChoiceFor(p);
        MB_TryAccelerateVote();
        MB_UpdateVoteUI();
        return true;'''
if old_clicks not in src:
    raise SystemExit('vote click handler anchor missing')
src = src.replace(old_clicks, new_clicks, 1)

# Timeout handler: result phase waits 2 seconds, then enters the selected mode.
old_timeout = '''    if (gv_mbPhase == MB_PHASE_MODE_VOTE) { MB_ResolveVote(); }
    else if (gv_mbPhase == MB_PHASE_BLIND) { MB_FinishBlind(); }
    else if (gv_mbPhase == MB_PHASE_SD) { MB_SDAutoPick(); }'''
new_timeout = '''    if (gv_mbPhase == MB_PHASE_MODE_VOTE) { MB_ResolveVote(); }
    else if (gv_mbPhase == MB_PHASE_MODE_RESULT) {
        if (gv_mbMode == MB_MODE_SD) { MB_StartSD(); }
        else { MB_StartBlind(); }
    }
    else if (gv_mbPhase == MB_PHASE_BLIND) { MB_FinishBlind(); }
    else if (gv_mbPhase == MB_PHASE_SD) { MB_SDAutoPick(); }'''
if old_timeout not in src:
    raise SystemExit('phase timeout anchor missing')
src = src.replace(old_timeout, new_timeout, 1)

# Tick: during result announcement, show a small countdown in the footer.
old_tick = '''    if (gv_mbPhase == MB_PHASE_MODE_VOTE) { MB_UpdateVoteUI(); }
    else if (gv_mbPhase == MB_PHASE_BLIND) {'''
new_tick = '''    if (gv_mbPhase == MB_PHASE_MODE_VOTE) { MB_UpdateVoteUI(); }
    else if (gv_mbPhase == MB_PHASE_MODE_RESULT) {
        remain = FixedToInt(TimerGetRemaining(gv_mbTimer));
        DialogControlSetPropertyAsText(gv_mbVoteFooter, c_triggerControlPropertyText, PlayerGroupAll(),
            StringToText("선택 모드 확정 · " + IntToString(remain) + "초 후 시작"));
    }
    else if (gv_mbPhase == MB_PHASE_BLIND) {'''
if old_tick not in src:
    raise SystemExit('tick mode-vote anchor missing')
src = src.replace(old_tick, new_tick, 1)

# Validation markers.
for marker in (
    'int[24] gv_mbSDIcon',
    'c_triggerControlTypeImage',
    'DialogControlSetSize(gv_mbSDIcon[i], PlayerGroupAll(), 58, 58)',
    'DialogControlSetPropertyAsBool(gv_mbSDButton[i], c_triggerControlPropertyBackgroundVisible, PlayerGroupAll(), false)',
    'MB_PHASE_MODE_RESULT', 'MB_UpdateVoteChoiceFor', 'MB_AllActivePlayersVoted',
    'TimerStart(gv_mbTimer, 3.0, false, c_timeReal)',
    'MODE SELECTED', '2초 후 선택 화면으로 이동합니다',
    '✓ 선택됨'
):
    if marker not in src:
        raise SystemExit(f'Alpha 3.9 marker missing: {marker}')

# The SD button itself must no longer receive the unit image; only the dedicated image control does.
update_start = src.index('void MB_SDUpdateBoardButtons')
update_end = src.index('void MB_SDUpdateOrderText', update_start)
update_block = src[update_start:update_end]
if 'c_triggerControlPropertyImage, PlayerGroupAll(), icon' in update_block and 'gv_mbSDButton[i], c_triggerControlPropertyImage' in update_block:
    raise SystemExit('SD icon is still being painted directly into the button')

# Keep Galaxy string safety guard.
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
print('Alpha 3.9 prepared: unclipped SD image controls + accelerated/visible vote UX')
