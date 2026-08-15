from pathlib import Path
import runpy
import re

# UI-only refinement on Alpha 5.2.
# Runtime feedback: the whole SD screen had fallen back to Blizzard's default teal/gold dialog skin.
# Alpha 5.3 removes that stock dialog chrome and replaces it with a viewer-team blue/red theme.
runpy.run_path('tools/prepare_alpha52.py', run_name='__main__')
path = Path('build/MapScript.galaxy')
src = path.read_text(encoding='utf-8')

# --------------------------------------------------------------------------------------
# 1) Add dedicated SD backdrop/accent controls. They are created before all normal SD controls,
#    so they stay behind icons/text and cannot interfere with clicks.
# --------------------------------------------------------------------------------------
global_anchor = 'int gv_mbSDMyTeamLabel;\n'
if global_anchor not in src:
    raise SystemExit('Alpha 5.2 SD team-label global anchor missing')
src = src.replace(
    global_anchor,
    global_anchor + 'int gv_mbSDTeamBackdrop;\nint gv_mbSDTeamAccent;\n',
    1,
)

# Locate the SD dialog dimensions rather than hard-coding them. Hide Blizzard's own dialog chrome
# with 100% dialog-background transparency, then draw our own dark team-tinted panel + accent strip.
create_re = re.compile(
    r'(gv_mbSDDialog = DialogCreate\((\d+), (\d+), c_anchorCenter, [^;]+;\n)'
    r'\s*DialogSetTransparency\(gv_mbSDDialog, 5\.0\);\n'
)
m = create_re.search(src)
if not m:
    raise SystemExit('Alpha 5.2 SD dialog create/transparency block missing')
w = int(m.group(2))
h = int(m.group(3))
replacement = m.group(1) + '''    // Hide Blizzard's default teal/gold dialog chrome. All Monobattle visuals are explicit controls.\n    DialogSetTransparency(gv_mbSDDialog, 100.0);\n\n    gv_mbSDTeamBackdrop = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypePanel);\n    DialogControlSetSize(gv_mbSDTeamBackdrop, PlayerGroupAll(), %d, %d);\n    DialogControlSetPosition(gv_mbSDTeamBackdrop, PlayerGroupAll(), c_anchorCenter, 0, 0);\n    DialogControlSetPropertyAsBool(gv_mbSDTeamBackdrop, c_triggerControlPropertyBackgroundVisible, PlayerGroupAll(), true);\n    DialogControlSetPropertyAsBool(gv_mbSDTeamBackdrop, c_triggerControlPropertyBorderVisible, PlayerGroupAll(), true);\n    DialogControlSetPropertyAsColor(gv_mbSDTeamBackdrop, c_triggerControlPropertyColor, PlayerGroupAll(), Color(4.0, 7.0, 12.0));\n    DialogControlSetPropertyAsColor(gv_mbSDTeamBackdrop, c_triggerControlPropertyBorderColor, PlayerGroupAll(), Color(25.0, 45.0, 65.0));\n\n    gv_mbSDTeamAccent = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypePanel);\n    DialogControlSetSize(gv_mbSDTeamAccent, PlayerGroupAll(), %d, 5);\n    DialogControlSetPosition(gv_mbSDTeamAccent, PlayerGroupAll(), c_anchorTop, 0, 0);\n    DialogControlSetPropertyAsBool(gv_mbSDTeamAccent, c_triggerControlPropertyBackgroundVisible, PlayerGroupAll(), true);\n    DialogControlSetPropertyAsBool(gv_mbSDTeamAccent, c_triggerControlPropertyBorderVisible, PlayerGroupAll(), false);\n    DialogControlSetPropertyAsColor(gv_mbSDTeamAccent, c_triggerControlPropertyColor, PlayerGroupAll(), Color(25.0, 45.0, 65.0));\n\n''' % (w - 8, h - 8, w - 10)
src = src[:m.start()] + replacement + src[m.end():]

# --------------------------------------------------------------------------------------
# 2) The viewer's own team drives the persistent screen theme.
#    Pick-order/player-name colors continue to describe the actual picker and are intentionally
#    left alone. Only the shell/title/accent are viewer-team themed.
# --------------------------------------------------------------------------------------
blue_header = '''                DialogControlSetPropertyAsColor(gv_mbSDHeaderPanel, c_triggerControlPropertyColor, one, Color(15.0, 58.0, 100.0));\n'''
red_header = '''                DialogControlSetPropertyAsColor(gv_mbSDHeaderPanel, c_triggerControlPropertyColor, one, Color(100.0, 22.0, 15.0));\n'''
if blue_header not in src or red_header not in src:
    raise SystemExit('Alpha 5.2 viewer-team header tint anchors missing')

blue_theme = blue_header + '''                DialogControlSetPropertyAsColor(gv_mbSDTeamBackdrop, c_triggerControlPropertyColor, one, Color(3.0, 9.0, 18.0));\n                DialogControlSetPropertyAsColor(gv_mbSDTeamBackdrop, c_triggerControlPropertyBorderColor, one, Color(8.0, 62.0, 100.0));\n                DialogControlSetPropertyAsColor(gv_mbSDTeamAccent, c_triggerControlPropertyColor, one, Color(8.0, 62.0, 100.0));\n                DialogControlSetPropertyAsText(gv_mbSDTitle, c_triggerControlPropertyText, one,\n                    TextWithColor(StringToText("SINGLE DRAFT"), Color(35.0, 72.0, 100.0)));\n'''
red_theme = red_header + '''                DialogControlSetPropertyAsColor(gv_mbSDTeamBackdrop, c_triggerControlPropertyColor, one, Color(18.0, 5.0, 4.0));\n                DialogControlSetPropertyAsColor(gv_mbSDTeamBackdrop, c_triggerControlPropertyBorderColor, one, Color(100.0, 14.0, 8.0));\n                DialogControlSetPropertyAsColor(gv_mbSDTeamAccent, c_triggerControlPropertyColor, one, Color(100.0, 14.0, 8.0));\n                DialogControlSetPropertyAsText(gv_mbSDTitle, c_triggerControlPropertyText, one,\n                    TextWithColor(StringToText("SINGLE DRAFT"), Color(100.0, 42.0, 34.0)));\n'''
src = src.replace(blue_header, blue_theme, 1)
src = src.replace(red_header, red_theme, 1)

# --------------------------------------------------------------------------------------
# 3) Remove the remaining fixed teal header default. Before team identity is applied it should be
#    neutral dark, never Blizzard teal. Per-viewer StartSD theming immediately replaces it.
# --------------------------------------------------------------------------------------
src = src.replace(
    'DialogControlSetPropertyAsColor(gv_mbSDHeaderPanel, c_triggerControlPropertyColor, PlayerGroupAll(), Color(20.0, 55.0, 75.0));',
    'DialogControlSetPropertyAsColor(gv_mbSDHeaderPanel, c_triggerControlPropertyColor, PlayerGroupAll(), Color(24.0, 24.0, 28.0));',
)

# Keep the initial title neutral until MB_StartSD assigns each viewer a team theme.
src = src.replace(
    'TextWithColor(StringToText("SINGLE DRAFT"), Color(45.0, 82.0, 100.0))',
    'TextWithColor(StringToText("SINGLE DRAFT"), Color(82.0, 82.0, 86.0))',
)

# --------------------------------------------------------------------------------------
# Guards. This is still UI-only: no gameplay/production/upgrade experiments.
# --------------------------------------------------------------------------------------
for forbidden in (
    'MB_ApplyUpgradeRestrictionsAll',
    'MB_DisableStandardResearch',
    'MB_EnablePickResearch',
    'MB_UpgradeAllowIfValid',
):
    if forbidden in src:
        raise SystemExit(f'Alpha 5.3 inherited unstable upgrade code: {forbidden}')

for marker in (
    'int gv_mbSDTeamBackdrop',
    'int gv_mbSDTeamAccent',
    'DialogSetTransparency(gv_mbSDDialog, 100.0)',
    'DialogControlSetPropertyAsColor(gv_mbSDTeamBackdrop, c_triggerControlPropertyBorderColor, one, Color(8.0, 62.0, 100.0))',
    'DialogControlSetPropertyAsColor(gv_mbSDTeamBackdrop, c_triggerControlPropertyBorderColor, one, Color(100.0, 14.0, 8.0))',
    'TextWithColor(StringToText("SINGLE DRAFT"), Color(35.0, 72.0, 100.0))',
    'TextWithColor(StringToText("SINGLE DRAFT"), Color(100.0, 42.0, 34.0))',
    'DialogControlSetPropertyAsInt(gv_mbSDButton[i], c_triggerControlPropertyAlpha, PlayerGroupAll(), 0)',
    'ownerText = TextWithColor(PlayerName(picker), ownerColor)',
):
    if marker not in src:
        raise SystemExit(f'Alpha 5.3 marker missing: {marker}')

# The SD dialog itself must no longer use the stock low-transparency chrome.
if 'DialogSetTransparency(gv_mbSDDialog, 5.0)' in src:
    raise SystemExit('Alpha 5.3 still exposes Blizzard default SD dialog chrome')

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
print('Alpha 5.3 prepared: stock teal/gold SD chrome removed + viewer-team blue/red shell')
