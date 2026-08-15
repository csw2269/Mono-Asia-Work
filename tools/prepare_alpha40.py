from pathlib import Path
import runpy
import re

# Build on Alpha 3.9: icon-image cards + improved vote flow + TEST BOOST.
runpy.run_path('tools/prepare_alpha39.py', run_name='__main__')
path = Path('build/MapScript.galaxy')
src = path.read_text(encoding='utf-8')

# -------------------------------------------------------------------------------------------------
# 1) Vote selection state: no glyph/checkmark. The disabled button alone communicates the choice.
# -------------------------------------------------------------------------------------------------
choice_pattern = re.compile(r'void MB_UpdateVoteChoiceFor \(int p\) \{.*?\n\}\n\nint MB_CountActivePlayers', re.S)
choice_replacement = r'''void MB_UpdateVoteChoiceFor (int p) {
    playergroup one = PlayerGroupSingle(p);

    DialogControlSetPropertyAsText(gv_mbVoteBlindButton, c_triggerControlPropertyText, one,
        StringToText("BLIND RANDOM\n종족 선택 + 즉시 추첨"));
    DialogControlSetPropertyAsText(gv_mbVoteSDButton, c_triggerControlPropertyText, one,
        StringToText("SINGLE DRAFT\n24개 후보 드래프트"));

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
    raise SystemExit(f'failed to replace vote choice function: {n}')

# Remove any stale checkmark text from unused legacy helpers too, so the glyph can never leak back.
src = src.replace('✓ 선택됨', '선택')

# -------------------------------------------------------------------------------------------------
# 2) Mode result: show ONLY the chosen mode name + its pick rule, large and centered.
# -------------------------------------------------------------------------------------------------
resolve_pattern = re.compile(r'void MB_ResolveVote \(\) \{.*?\n\}\n\n//--------------------------------------------------------------------------------------------------\n// Trigger handlers', re.S)
resolve_replacement = r'''void MB_ResolveVote () {
    int blind = MB_CountVotes(MB_MODE_BLIND);
    int sd = MB_CountVotes(MB_MODE_SD);
    if (blind > sd) { gv_mbMode = MB_MODE_BLIND; }
    else if (sd > blind) { gv_mbMode = MB_MODE_SD; }
    else { gv_mbMode = RandomInt(MB_MODE_BLIND, MB_MODE_SD); }

    gv_mbPhase = MB_PHASE_MODE_RESULT;

    // Clear the voting interface. Only the selected mode and its pick rule remain on screen.
    DialogControlSetVisible(gv_mbVoteHeaderPanel, PlayerGroupAll(), false);
    DialogControlSetVisible(gv_mbVoteBlindButton, PlayerGroupAll(), false);
    DialogControlSetVisible(gv_mbVoteSDButton, PlayerGroupAll(), false);
    DialogControlSetVisible(gv_mbVoteInfo, PlayerGroupAll(), false);
    DialogControlSetVisible(gv_mbVoteFooter, PlayerGroupAll(), false);

    DialogControlSetSize(gv_mbVoteTitle, PlayerGroupAll(), 740, 64);
    DialogControlSetPosition(gv_mbVoteTitle, PlayerGroupAll(), c_anchorTop, 0, 105);
    DialogControlSetSize(gv_mbVoteSubtitle, PlayerGroupAll(), 740, 58);
    DialogControlSetPosition(gv_mbVoteSubtitle, PlayerGroupAll(), c_anchorTop, 0, 185);

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
    raise SystemExit(f'failed to replace mode result UI: {n}')

# -------------------------------------------------------------------------------------------------
# 3) Single Draft: after the eighth/final pick, keep the completed board visible for 3 seconds.
# -------------------------------------------------------------------------------------------------
phase_anchor = 'const int MB_PHASE_MODE_RESULT = 5;\n'
if phase_anchor not in src:
    raise SystemExit('mode result phase anchor missing')
src = src.replace(phase_anchor, phase_anchor + 'const fixed MB_SD_FINAL_WAIT_SECONDS = 3.0;\n', 1)

global_anchor = 'int gv_mbSDPickIndex;\n'
if global_anchor not in src:
    raise SystemExit('SD pick index global missing')
src = src.replace(global_anchor, global_anchor + 'bool gv_mbSDPostPickWait;\n', 1)

# Reset the post-pick flag on every new SD round.
start_sd_anchor = '    gv_mbSDPickIndex = 0;\n'
if start_sd_anchor not in src:
    raise SystemExit('start SD pick-index anchor missing')
src = src.replace(start_sd_anchor, '    gv_mbSDPickIndex = 0;\n    gv_mbSDPostPickWait = false;\n', 1)

pick_pattern = re.compile(r'void MB_SDPickSlot \(int player, int slot\) \{.*?\n\}\n\nvoid MB_SDAutoPick', re.S)
pick_replacement = r'''void MB_SDPickSlot (int player, int slot) {
    if (gv_mbPhase != MB_PHASE_SD || gv_mbSDPostPickWait || gv_mbSDPickIndex >= gv_mbSDOrderCount) { return; }
    if (player != gv_mbSDOrder[gv_mbSDPickIndex]) { return; }
    if (slot < 0 || slot >= MB_SD_CANDIDATES || gv_mbSDTaken[slot]) { return; }

    gv_mbUnit[player] = gv_mbSDCandidate[slot];
    gv_mbSDTaken[slot] = true;
    gv_mbSDPickIndex += 1;

    if (gv_mbSDPickIndex >= gv_mbSDOrderCount) {
        gv_mbSDPostPickWait = true;
        MB_SDUpdateBoardButtons();
        MB_SDUpdateOrderText();
        DialogControlSetPropertyAsText(gv_mbSDCurrentLabel, c_triggerControlPropertyText, PlayerGroupAll(),
            TextWithColor(StringToText("ALL PICKS LOCKED"), Color(45.0, 82.0, 100.0)));
        DialogControlSetPropertyAsText(gv_mbSDInfo, c_triggerControlPropertyText, PlayerGroupAll(),
            StringToText("모든 픽이 확정되었습니다 · 3초 후 게임 시작"));
        TimerStart(gv_mbTimer, MB_SD_FINAL_WAIT_SECONDS, false, c_timeReal);
        return;
    }

    TimerStart(gv_mbTimer, MB_SD_PICK_SECONDS, false, c_timeReal);
    MB_SDUpdateTurn();
}

void MB_SDAutoPick'''
src, n = pick_pattern.subn(lambda _m: pick_replacement, src, count=1)
if n != 1:
    raise SystemExit(f'failed to replace SD pick handler: {n}')

# Timeout: during final 3-second display, start the game rather than attempting another auto-pick.
timeout_old = '    else if (gv_mbPhase == MB_PHASE_SD) { MB_SDAutoPick(); }\n'
timeout_new = '''    else if (gv_mbPhase == MB_PHASE_SD) {
        if (gv_mbSDPostPickWait) { MB_FinishSelection(); }
        else { MB_SDAutoPick(); }
    }
'''
if timeout_old not in src:
    raise SystemExit('SD timeout anchor missing')
src = src.replace(timeout_old, timeout_new, 1)

# Tick: show the remaining final-lock countdown while leaving the completed board visible.
tick_old = '    else if (gv_mbPhase == MB_PHASE_SD) { MB_SDUpdateTurn(); }\n'
tick_new = '''    else if (gv_mbPhase == MB_PHASE_SD) {
        if (gv_mbSDPostPickWait) {
            remain = FixedToInt(TimerGetRemaining(gv_mbTimer));
            DialogControlSetPropertyAsText(gv_mbSDInfo, c_triggerControlPropertyText, PlayerGroupAll(),
                StringToText("모든 픽 확정 · " + IntToString(remain) + "초 후 게임 시작"));
        }
        else { MB_SDUpdateTurn(); }
    }
'''
if tick_old not in src:
    raise SystemExit('SD tick anchor missing')
src = src.replace(tick_old, tick_new, 1)

# -------------------------------------------------------------------------------------------------
# 4) TEST BOOST: catch construction/morph start events directly.
#    Blizzard campaign scripts use ConstructProgress Start + progress slot 1 for this purpose.
# -------------------------------------------------------------------------------------------------
trigger_anchor = 'trigger gt_MBTick;\n'
if trigger_anchor not in src:
    raise SystemExit('trigger declaration anchor missing')
src = src.replace(trigger_anchor, trigger_anchor + 'trigger gt_MBTestConstructBoost;\n', 1)

handler_anchor = '//--------------------------------------------------------------------------------------------------\n// Melee Initialization\n'
if handler_anchor not in src:
    raise SystemExit('melee initialization section anchor missing')
construct_handler = r'''//--------------------------------------------------------------------------------------------------
// TEST BOOST construction/morph start event
//--------------------------------------------------------------------------------------------------
bool gt_MBTestConstructBoost_Func (bool testConds, bool runActions) {
    unit u;
    int p;
    if (!runActions) { return true; }
    if (gv_mbPhase != MB_PHASE_RUNNING) { return true; }

    u = EventUnitProgressUnit();
    if (u == null) { return true; }
    p = UnitGetOwner(u);
    if (!MB_PlayerActive(p)) { return true; }

    // Construction and structure morphs expose their visible build progress on slot 1.
    UnitSetProgressComplete(u, 1, 85);
    return true;
}

void gt_MBTestConstructBoost_Init () {
    gt_MBTestConstructBoost = TriggerCreate("gt_MBTestConstructBoost_Func");
    TriggerAddEventUnitConstructProgress(gt_MBTestConstructBoost, null, c_unitProgressStageStart);
}

'''
src = src.replace(handler_anchor, construct_handler + handler_anchor, 1)

init_anchor = '    gt_MBTick_Init();\n'
if init_anchor not in src:
    raise SystemExit('trigger init anchor missing')
src = src.replace(init_anchor, init_anchor + '    gt_MBTestConstructBoost_Init();\n', 1)

# -------------------------------------------------------------------------------------------------
# Guards
# -------------------------------------------------------------------------------------------------
for marker in (
    'MB_SD_FINAL_WAIT_SECONDS = 3.0', 'gv_mbSDPostPickWait', 'ALL PICKS LOCKED',
    'DialogControlSetVisible(gv_mbVoteBlindButton, PlayerGroupAll(), false)',
    '24개 후보 · ABBAABBA 스네이크 픽 · 15초 제한',
    '종족 선택 즉시 추첨 · Random 선택 시 리롤 1회',
    'gt_MBTestConstructBoost_Func', 'TriggerAddEventUnitConstructProgress',
    'UnitSetProgressComplete(u, 1, 85)'
):
    if marker not in src:
        raise SystemExit(f'Alpha 4.0 marker missing: {marker}')

if '✓ 선택됨' in src:
    raise SystemExit('checkmark selected label must not remain')

# Keep Galaxy string literal safety validation.
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
print('Alpha 4.0 prepared: SD final wait + clean vote result UI + construct/morph event boost')
