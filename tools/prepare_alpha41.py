from pathlib import Path
import runpy
import re

# Build on Alpha 4.0: stable vote flow, SD final wait, TEST BOOST, and roster.
runpy.run_path('tools/prepare_alpha40.py', run_name='__main__')
path = Path('build/MapScript.galaxy')
src = path.read_text(encoding='utf-8')

# -------------------------------------------------------------------------------------------------
# 1) Vote lock: once every active player has voted and the 3-second confirmation starts,
#    both choices are frozen for everybody. No last-second vote changes.
# -------------------------------------------------------------------------------------------------
anchor = 'int[9] gv_mbVote;\n'
if anchor not in src:
    raise SystemExit('vote global anchor missing')
src = src.replace(anchor, anchor + 'bool gv_mbVoteLocked;\n', 1)

# Reset lock when a new vote begins.
start_anchor = '    gv_mbPhase = MB_PHASE_MODE_VOTE;\n'
if start_anchor not in src:
    raise SystemExit('vote phase start anchor missing')
src = src.replace(start_anchor, start_anchor + '    gv_mbVoteLocked = false;\n', 1)

# If the lock is active, both buttons must stay disabled regardless of the player-specific vote.
choice_pattern = re.compile(r'void MB_UpdateVoteChoiceFor \(int p\) \{.*?\n\}\n\nint MB_CountActivePlayers', re.S)
choice_replacement = r'''void MB_UpdateVoteChoiceFor (int p) {
    playergroup one = PlayerGroupSingle(p);

    DialogControlSetPropertyAsText(gv_mbVoteBlindButton, c_triggerControlPropertyText, one,
        StringToText("BLIND RANDOM\n종족 선택 + 즉시 추첨"));
    DialogControlSetPropertyAsText(gv_mbVoteSDButton, c_triggerControlPropertyText, one,
        StringToText("SINGLE DRAFT\n24개 후보 드래프트"));

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
    raise SystemExit(f'failed to replace vote-choice helper: {n}')

accelerate_pattern = re.compile(r'void MB_TryAccelerateVote \(\) \{.*?\n\}', re.S)
accelerate_replacement = r'''void MB_TryAccelerateVote () {
    if (gv_mbVoteLocked || !MB_AllActivePlayersVoted()) { return; }

    gv_mbVoteLocked = true;
    DialogControlSetEnabled(gv_mbVoteBlindButton, PlayerGroupAll(), false);
    DialogControlSetEnabled(gv_mbVoteSDButton, PlayerGroupAll(), false);
    TimerStart(gv_mbTimer, 3.0, false, c_timeReal);
    DialogControlSetPropertyAsText(gv_mbVoteFooter, c_triggerControlPropertyText, PlayerGroupAll(),
        StringToText("모든 플레이어 투표 완료 · 선택 잠금 · 3초 후 확정"));
}'''
src, n = accelerate_pattern.subn(lambda _m: accelerate_replacement, src, count=1)
if n != 1:
    raise SystemExit(f'failed to replace all-voted accelerator: {n}')

# Ignore any queued click events after lock.
click_anchor = '    if (gv_mbPhase == MB_PHASE_MODE_VOTE) {\n'
if click_anchor not in src:
    raise SystemExit('mode-vote click anchor missing')
src = src.replace(click_anchor, click_anchor + '        if (gv_mbVoteLocked) { return true; }\n', 1)

# -------------------------------------------------------------------------------------------------
# 2) Result presentation: move the chosen mode into the visual center and use Blizzard's
#    CinematicLabel (38px) + DirectiveDisplay (26px) styles. Only mode + pick rule remain.
# -------------------------------------------------------------------------------------------------
resolve_pattern = re.compile(r'void MB_ResolveVote \(\) \{.*?\n\}\n\n//--------------------------------------------------------------------------------------------------\n// Trigger handlers', re.S)
resolve_replacement = r'''void MB_ResolveVote () {
    int blind = MB_CountVotes(MB_MODE_BLIND);
    int sd = MB_CountVotes(MB_MODE_SD);
    if (blind > sd) { gv_mbMode = MB_MODE_BLIND; }
    else if (sd > blind) { gv_mbMode = MB_MODE_SD; }
    else { gv_mbMode = RandomInt(MB_MODE_BLIND, MB_MODE_SD); }

    gv_mbPhase = MB_PHASE_MODE_RESULT;

    // Everything except the final mode name and its pick rule disappears.
    DialogControlSetVisible(gv_mbVoteHeaderPanel, PlayerGroupAll(), false);
    DialogControlSetVisible(gv_mbVoteBlindButton, PlayerGroupAll(), false);
    DialogControlSetVisible(gv_mbVoteSDButton, PlayerGroupAll(), false);
    DialogControlSetVisible(gv_mbVoteInfo, PlayerGroupAll(), false);
    DialogControlSetVisible(gv_mbVoteFooter, PlayerGroupAll(), false);

    DialogControlSetVisible(gv_mbVoteTitle, PlayerGroupAll(), true);
    DialogControlSetVisible(gv_mbVoteSubtitle, PlayerGroupAll(), true);
    DialogControlSetSize(gv_mbVoteTitle, PlayerGroupAll(), 790, 80);
    DialogControlSetPosition(gv_mbVoteTitle, PlayerGroupAll(), c_anchorCenter, 0, -42);
    DialogControlSetPropertyAsString(gv_mbVoteTitle, c_triggerControlPropertyStyle, PlayerGroupAll(), "CinematicLabel");
    DialogControlSetSize(gv_mbVoteSubtitle, PlayerGroupAll(), 790, 68);
    DialogControlSetPosition(gv_mbVoteSubtitle, PlayerGroupAll(), c_anchorCenter, 0, 48);
    DialogControlSetPropertyAsString(gv_mbVoteSubtitle, c_triggerControlPropertyStyle, PlayerGroupAll(), "DirectiveDisplay");

    if (gv_mbMode == MB_MODE_SD) {
        DialogControlSetPropertyAsText(gv_mbVoteTitle, c_triggerControlPropertyText, PlayerGroupAll(),
            TextWithColor(StringToText("SINGLE DRAFT"), Color(45.0, 82.0, 100.0)));
        DialogControlSetPropertyAsText(gv_mbVoteSubtitle, c_triggerControlPropertyText, PlayerGroupAll(),
            StringToText("24개 후보 · ABBAABBA 스네이크 픽 · 15초 제한"));
    }
    else {
        DialogControlSetPropertyAsText(gv_mbVoteTitle, c_triggerControlPropertyText, PlayerGroupAll(),
            TextWithColor(StringToText("BLIND RANDOM"), Color(45.0, 82.0, 100.0)));
        DialogControlSetPropertyAsText(gv_mbVoteSubtitle, c_triggerControlPropertyText, PlayerGroupAll(),
            StringToText("종족 선택 즉시 추첨 · Random 선택 시 리롤 1회"));
    }

    TimerStart(gv_mbTimer, 2.0, false, c_timeReal);
}

//--------------------------------------------------------------------------------------------------
// Trigger handlers'''
src, n = resolve_pattern.subn(lambda _m: resolve_replacement, src, count=1)
if n != 1:
    raise SystemExit(f'failed to replace centered mode result: {n}')

# -------------------------------------------------------------------------------------------------
# 3) Single Draft card ownership: remember who took each candidate and show a colored badge
#    directly on that unit card: [BLUE] P1 or [RED] P6.
# -------------------------------------------------------------------------------------------------
global_anchor = 'int[24] gv_mbSDIcon;\n'
if global_anchor not in src:
    raise SystemExit('SD icon global anchor missing')
src = src.replace(global_anchor,
                  global_anchor + 'int[24] gv_mbSDPickBadge;\nint[24] gv_mbSDPickedBy;\n', 1)

# Reset the owner array whenever a fresh board is generated.
reset_old = 'while (i < MB_SD_CANDIDATES) { gv_mbSDCandidate[i] = ""; gv_mbSDTaken[i] = false; i += 1; }'
reset_new = 'while (i < MB_SD_CANDIDATES) { gv_mbSDCandidate[i] = ""; gv_mbSDTaken[i] = false; gv_mbSDPickedBy[i] = 0; i += 1; }'
if reset_old not in src:
    raise SystemExit('SD board reset anchor missing')
src = src.replace(reset_old, reset_new, 1)

# Record the picker before advancing the draft turn.
pick_anchor = '    gv_mbUnit[player] = gv_mbSDCandidate[slot];\n    gv_mbSDTaken[slot] = true;\n'
if pick_anchor not in src:
    raise SystemExit('SD pick assignment anchor missing')
src = src.replace(pick_anchor,
                  '    gv_mbUnit[player] = gv_mbSDCandidate[slot];\n    gv_mbSDTaken[slot] = true;\n    gv_mbSDPickedBy[slot] = player;\n', 1)

# Add badge rendering to the board updater.
update_pattern = re.compile(r'void MB_SDUpdateBoardButtons \(\) \{.*?\n\}\n\nvoid MB_SDUpdateOrderText', re.S)
match = update_pattern.search(src)
if not match:
    raise SystemExit('SD board updater missing')
block = match.group(0)
if 'gv_mbSDPickBadge' in block:
    raise SystemExit('SD pick badge unexpectedly already present')

# Extend local declarations.
block = block.replace('    string display;\n',
                      '    string display;\n    int picker;\n    int team;\n    string badge;\n', 1)

# Insert badge state immediately after name text is updated.
name_line = '        DialogControlSetPropertyAsText(gv_mbSDNameLabel[i], c_triggerControlPropertyText, PlayerGroupAll(), StringToText(display));\n'
if name_line not in block:
    raise SystemExit('SD name label update anchor missing')
badge_code = r'''        DialogControlSetPropertyAsText(gv_mbSDNameLabel[i], c_triggerControlPropertyText, PlayerGroupAll(), StringToText(display));
        picker = gv_mbSDPickedBy[i];
        if (picker > 0) {
            team = MB_SDPlayerTeam(picker);
            if (team == 0) { badge = "[BLUE] P" + IntToString(picker); }
            else { badge = "[RED] P" + IntToString(picker); }
            DialogControlSetPropertyAsText(gv_mbSDPickBadge[i], c_triggerControlPropertyText, PlayerGroupAll(),
                MB_TeamTagText(team, badge));
            DialogControlSetVisible(gv_mbSDPickBadge[i], PlayerGroupAll(), true);
        }
        else {
            DialogControlSetVisible(gv_mbSDPickBadge[i], PlayerGroupAll(), false);
        }
'''
block = block.replace(name_line, badge_code, 1)
src = src[:match.start()] + block + src[match.end():]

# Create the small badge as an overlay in the top-right of every draft card.
card_anchor = '''        gv_mbSDNameLabel[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeLabel);
        DialogControlSetSize(gv_mbSDNameLabel[i], PlayerGroupAll(), 102, 24);
        DialogControlSetPosition(gv_mbSDNameLabel[i], PlayerGroupAll(), c_anchorTopLeft, x, y + 69);
'''
if card_anchor not in src:
    raise SystemExit('SD card label creation anchor missing')
badge_create = card_anchor + '''
        gv_mbSDPickBadge[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeLabel);
        DialogControlSetSize(gv_mbSDPickBadge[i], PlayerGroupAll(), 96, 22);
        DialogControlSetPosition(gv_mbSDPickBadge[i], PlayerGroupAll(), c_anchorTopLeft, x + 8, y + 4);
        DialogControlSetPropertyAsString(gv_mbSDPickBadge[i], c_triggerControlPropertyStyle, PlayerGroupAll(), "GameButtonChargeSmall");
        DialogControlSetVisible(gv_mbSDPickBadge[i], PlayerGroupAll(), false);
'''
src = src.replace(card_anchor, badge_create, 1)

# -------------------------------------------------------------------------------------------------
# Guards
# -------------------------------------------------------------------------------------------------
for marker in (
    'bool gv_mbVoteLocked',
    '모든 플레이어 투표 완료 · 선택 잠금 · 3초 후 확정',
    '"CinematicLabel"', '"DirectiveDisplay"',
    'int[24] gv_mbSDPickBadge', 'int[24] gv_mbSDPickedBy',
    'gv_mbSDPickedBy[slot] = player', '[BLUE] P', '[RED] P',
    'MB_SD_FINAL_WAIT_SECONDS = 3.0'
):
    if marker not in src:
        raise SystemExit(f'Alpha 4.1 marker missing: {marker}')

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
print('Alpha 4.1 prepared: vote lock + centered result + colored SD picker badges')
