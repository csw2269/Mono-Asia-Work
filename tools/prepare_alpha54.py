from pathlib import Path
import runpy
import re

# Alpha 5.4 starts from the last runtime-visible build (5.2), NOT 5.3.
# 5.3 used DialogSetTransparency(..., 100), which could hide the whole SD dialog.
# This revision uses Blizzard's own frameless-dialog technique:
# DialogSetImageVisible(dialog, false) hides only the stock race skin while preserving children.
runpy.run_path('tools/prepare_alpha52.py', run_name='__main__')
path = Path('build/MapScript.galaxy')
src = path.read_text(encoding='utf-8')

# -------------------------------------------------------------------------------------------------
# 1) Globals for explicit team-colored shells behind Vote / Blind / Single Draft.
# -------------------------------------------------------------------------------------------------
global_anchor = 'int gv_mbFocusPanel;\n'
if global_anchor not in src:
    raise SystemExit('focus-panel global anchor missing')
src = src.replace(
    global_anchor,
    global_anchor + '''\n// Alpha 5.4: race-skin-independent selection shells\nint gv_mbVoteThemeBack;\nint gv_mbVoteThemeAccent;\nint gv_mbBlindThemeBack;\nint gv_mbBlindThemeAccent;\nint gv_mbSDThemeBack;\nint gv_mbSDThemeAccent;\n''',
    1,
)

# -------------------------------------------------------------------------------------------------
# 2) Remove the stock race-dependent Dialog image WITHOUT changing child-control visibility.
#    Create our own backdrop/accent immediately after dialog creation, before all other controls.
# -------------------------------------------------------------------------------------------------
def patch_dialog(dialog_var, back_var, accent_var):
    global src
    pat = re.compile(
        rf'(    {re.escape(dialog_var)} = DialogCreate\((\d+), (\d+),[^;]+;\n)'
        rf'(    DialogSetTransparency\({re.escape(dialog_var)}, [^;]+;\n)'
    )
    m = pat.search(src)
    if not m:
        raise SystemExit(f'{dialog_var}: create/transparency block missing')
    w = int(m.group(2))
    h = int(m.group(3))
    replacement = m.group(1) + m.group(4) + f'''    // Hide only Blizzard's race-specific dialog artwork; child controls stay visible.\n    DialogSetImageVisible({dialog_var}, false);\n\n    {back_var} = DialogControlCreate({dialog_var}, c_triggerControlTypePanel);\n    DialogControlSetSize({back_var}, PlayerGroupAll(), {w - 8}, {h - 8});\n    DialogControlSetPosition({back_var}, PlayerGroupAll(), c_anchorCenter, 0, 0);\n    DialogControlSetPropertyAsBool({back_var}, c_triggerControlPropertyBackgroundVisible, PlayerGroupAll(), true);\n    DialogControlSetPropertyAsBool({back_var}, c_triggerControlPropertyBorderVisible, PlayerGroupAll(), true);\n    DialogControlSetPropertyAsColor({back_var}, c_triggerControlPropertyColor, PlayerGroupAll(), Color(5.0, 7.0, 10.0));\n    DialogControlSetPropertyAsColor({back_var}, c_triggerControlPropertyBorderColor, PlayerGroupAll(), Color(32.0, 32.0, 36.0));\n\n    {accent_var} = DialogControlCreate({dialog_var}, c_triggerControlTypePanel);\n    DialogControlSetSize({accent_var}, PlayerGroupAll(), {w - 24}, 5);\n    DialogControlSetPosition({accent_var}, PlayerGroupAll(), c_anchorTop, 0, 6);\n    DialogControlSetPropertyAsBool({accent_var}, c_triggerControlPropertyBackgroundVisible, PlayerGroupAll(), true);\n    DialogControlSetPropertyAsBool({accent_var}, c_triggerControlPropertyBorderVisible, PlayerGroupAll(), false);\n    DialogControlSetPropertyAsColor({accent_var}, c_triggerControlPropertyColor, PlayerGroupAll(), Color(32.0, 32.0, 36.0));\n\n'''
    src = src[:m.start()] + replacement + src[m.end():]

patch_dialog('gv_mbVoteDialog', 'gv_mbVoteThemeBack', 'gv_mbVoteThemeAccent')
patch_dialog('gv_mbBlindDialog', 'gv_mbBlindThemeBack', 'gv_mbBlindThemeAccent')
patch_dialog('gv_mbSDDialog', 'gv_mbSDThemeBack', 'gv_mbSDThemeAccent')

# -------------------------------------------------------------------------------------------------
# 3) Viewer-team resolution independent of draft order. The first active player's alliance defines
#    BLUE; everyone outside that alliance is RED. This works during mode voting, before SD exists.
# -------------------------------------------------------------------------------------------------
phase_anchor = '//--------------------------------------------------------------------------------------------------\n// Phase flow\n//--------------------------------------------------------------------------------------------------\n'
if phase_anchor not in src:
    raise SystemExit('phase-flow anchor missing')

theme_code = r'''//--------------------------------------------------------------------------------------------------
// Selection-phase team theme
//--------------------------------------------------------------------------------------------------
int MB_SelectionTeam (int p) {
    int first = 1;
    playergroup allies;

    while (first <= 8 && !MB_PlayerActive(first)) { first += 1; }
    if (first > 8) { return 0; }

    allies = PlayerGroupAlliance(c_playerGroupAlly, first);
    PlayerGroupAdd(allies, first);
    if (PlayerGroupHasPlayer(allies, p)) { return 0; }
    return 1;
}

void MB_ApplySelectionThemeFor (int p) {
    playergroup one;
    int team;
    color shell;
    color border;
    color accent;
    color title;
    color focus;

    if (!MB_PlayerActive(p)) { return; }
    one = PlayerGroupSingle(p);
    team = MB_SelectionTeam(p);

    if (team == 0) {
        // BLUE team: dark navy shell with an unmistakable blue edge/accent.
        shell = Color(2.0, 7.0, 15.0);
        border = Color(8.0, 55.0, 100.0);
        accent = Color(12.0, 68.0, 100.0);
        title = Color(42.0, 82.0, 100.0);
        focus = Color(0.0, 3.0, 8.0);
    }
    else {
        // RED team: dark crimson shell with an unmistakable red edge/accent.
        shell = Color(15.0, 3.0, 3.0);
        border = Color(100.0, 10.0, 7.0);
        accent = Color(100.0, 24.0, 18.0);
        title = Color(100.0, 48.0, 40.0);
        focus = Color(8.0, 0.0, 0.0);
    }

    // Whole selection phase: the focus mask itself now follows the viewer's team tone.
    DialogControlSetPropertyAsColor(gv_mbFocusPanel, c_triggerControlPropertyColor, one, focus);

    // Vote shell.
    DialogControlSetPropertyAsColor(gv_mbVoteThemeBack, c_triggerControlPropertyColor, one, shell);
    DialogControlSetPropertyAsColor(gv_mbVoteThemeBack, c_triggerControlPropertyBorderColor, one, border);
    DialogControlSetPropertyAsColor(gv_mbVoteThemeAccent, c_triggerControlPropertyColor, one, accent);
    DialogControlSetPropertyAsColor(gv_mbVoteHeaderPanel, c_triggerControlPropertyColor, one, accent);
    DialogControlSetPropertyAsText(gv_mbVoteTitle, c_triggerControlPropertyText, one,
        TextWithColor(StringToText("MONOBATTLE"), title));
    DialogControlSetPropertyAsColor(gv_mbVoteBlindButton, c_triggerControlPropertyColor, one, border);
    DialogControlSetPropertyAsColor(gv_mbVoteSDButton, c_triggerControlPropertyColor, one, border);

    // Blind Random shell.
    DialogControlSetPropertyAsColor(gv_mbBlindThemeBack, c_triggerControlPropertyColor, one, shell);
    DialogControlSetPropertyAsColor(gv_mbBlindThemeBack, c_triggerControlPropertyBorderColor, one, border);
    DialogControlSetPropertyAsColor(gv_mbBlindThemeAccent, c_triggerControlPropertyColor, one, accent);
    DialogControlSetPropertyAsColor(gv_mbBlindHeaderPanel, c_triggerControlPropertyColor, one, accent);
    DialogControlSetPropertyAsText(gv_mbBlindTitle, c_triggerControlPropertyText, one,
        TextWithColor(StringToText("BLIND RANDOM"), title));
    DialogControlSetPropertyAsColor(gv_mbTerranButton, c_triggerControlPropertyColor, one, border);
    DialogControlSetPropertyAsColor(gv_mbZergButton, c_triggerControlPropertyColor, one, border);
    DialogControlSetPropertyAsColor(gv_mbProtossButton, c_triggerControlPropertyColor, one, border);
    DialogControlSetPropertyAsColor(gv_mbRandomButton, c_triggerControlPropertyColor, one, border);
    DialogControlSetPropertyAsColor(gv_mbRerollButton, c_triggerControlPropertyColor, one, border);

    // Single Draft shell. Candidate ownership colors remain tied to the actual picker/team.
    DialogControlSetPropertyAsColor(gv_mbSDThemeBack, c_triggerControlPropertyColor, one, shell);
    DialogControlSetPropertyAsColor(gv_mbSDThemeBack, c_triggerControlPropertyBorderColor, one, border);
    DialogControlSetPropertyAsColor(gv_mbSDThemeAccent, c_triggerControlPropertyColor, one, accent);
    DialogControlSetPropertyAsColor(gv_mbSDHeaderPanel, c_triggerControlPropertyColor, one, accent);
    DialogControlSetPropertyAsText(gv_mbSDTitle, c_triggerControlPropertyText, one,
        TextWithColor(StringToText("SINGLE DRAFT"), title));
}

void MB_ApplySelectionThemeAll () {
    int p = 1;
    while (p <= 8) {
        MB_ApplySelectionThemeFor(p);
        p += 1;
    }
}

'''
src = src.replace(phase_anchor, theme_code + phase_anchor, 1)

# Apply once at each selection phase start. This intentionally does not depend on race or picked unit.
for timer_line in (
    '    TimerStart(gv_mbTimer, MB_VOTE_SECONDS, false, c_timeReal);\n',
    '    TimerStart(gv_mbTimer, MB_BLIND_SECONDS, false, c_timeReal);\n',
    '    TimerStart(gv_mbTimer, MB_SD_PICK_SECONDS, false, c_timeReal);\n',
):
    if timer_line not in src:
        raise SystemExit(f'phase timer anchor missing: {timer_line.strip()}')
    src = src.replace(timer_line, '    MB_ApplySelectionThemeAll();\n' + timer_line, 1)

# -------------------------------------------------------------------------------------------------
# 4) Guards: 5.3's destructive whole-dialog transparency must never return. 5.2 label fixes stay.
# -------------------------------------------------------------------------------------------------
for forbidden in (
    'DialogSetTransparency(gv_mbSDDialog, 100.0)',
    'MB_ApplyUpgradeRestrictionsAll',
    'MB_DisableStandardResearch',
    'MB_EnablePickResearch',
    'MB_UpgradeAllowIfValid',
):
    if forbidden in src:
        raise SystemExit(f'Alpha 5.4 forbidden regression: {forbidden}')

for marker in (
    'DialogSetImageVisible(gv_mbVoteDialog, false)',
    'DialogSetImageVisible(gv_mbBlindDialog, false)',
    'DialogSetImageVisible(gv_mbSDDialog, false)',
    'void MB_ApplySelectionThemeFor (int p)',
    'DialogControlSetPropertyAsColor(gv_mbFocusPanel, c_triggerControlPropertyColor, one, focus)',
    'DialogControlSetPropertyAsColor(gv_mbVoteThemeBack, c_triggerControlPropertyBorderColor, one, border)',
    'DialogControlSetPropertyAsColor(gv_mbBlindThemeBack, c_triggerControlPropertyBorderColor, one, border)',
    'DialogControlSetPropertyAsColor(gv_mbSDThemeBack, c_triggerControlPropertyBorderColor, one, border)',
    'DialogControlSetSize(gv_mbSDPickBadge[i], PlayerGroupAll(), 88, 18)',
    'DialogControlSetPosition(gv_mbSDNameLabel[i], PlayerGroupAll(), c_anchorTopLeft, x + 4, y + 93)',
    'ownerText = TextWithColor(PlayerName(picker), ownerColor)',
):
    if marker not in src:
        raise SystemExit(f'Alpha 5.4 marker missing: {marker}')

# Exactly three race-skin dialog images should be suppressed: Vote, Blind, SD.
if src.count('DialogSetImageVisible(gv_mb') < 3:
    raise SystemExit('expected race-skin suppression on all three selection dialogs')

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
print('Alpha 5.4 prepared: stable visible dialogs + race-skin-free BLUE/RED selection theme')
