from pathlib import Path
import re

src = Path('overlay/MapScript.galaxy').read_text(encoding='utf-8')
src = src.replace(
    'Alpha 2: polished UI + Blind Random + Single Draft + first production restriction pass',
    'Alpha 3: pick-matched starting race + icon Single Draft UI',
    1,
)

marker = 'include "TriggerLibs/NativeLib"\n'
if marker not in src:
    raise SystemExit('NativeLib include missing')
src = src.replace(marker, marker + 'native string TextToString(text inText);\n', 1)

global_marker = 'int gv_mbSDPickIndex;\n'
if global_marker not in src:
    raise SystemExit('SD pick-index global missing')
src = src.replace(global_marker, global_marker + 'int[3] gv_mbSDQuota;\n', 1)
src = src.replace('void MB_SDComputeQuotas (int[3] q) {', 'void MB_SDComputeQuotas () {')
src = src.replace('q[', 'gv_mbSDQuota[')
src = src.replace('    int[3] quota;\n', '')
src = src.replace('MB_SDComputeQuotas(quota);', 'MB_SDComputeQuotas();')
src = src.replace('quota[race - 1]', 'gv_mbSDQuota[race - 1]')

button_global = 'int[24] gv_mbSDButton;\n'
if button_global not in src:
    raise SystemExit('SD button global missing')
src = src.replace(button_global, button_global + 'int[24] gv_mbSDNameLabel;\n', 1)

helper_anchor = 'bool MB_IsAir (string u) {'
if helper_anchor not in src:
    raise SystemExit('metadata helper anchor missing')
helper = '''string MB_RaceLinkForUnit (string unitId) {
    int race = MB_UnitRace(unitId);
    if (race == MB_RACE_TERRAN) { return "Terr"; }
    if (race == MB_RACE_ZERG) { return "Zerg"; }
    return "Prot";
}

string MB_UnitIcon (string unitId) {
    return CatalogFieldValueGet(c_gameCatalogUnit, unitId, "Icon", c_playerAny);
}

void MB_InitStartingUnitsAll () {
    int p = 1;
    string raceLink;
    while (p <= 8) {
        if (MB_PlayerActive(p) && gv_mbUnit[p] != "") {
            raceLink = MB_RaceLinkForUnit(gv_mbUnit[p]);
            PlayerSetRace(p, raceLink);
            MeleeInitUnitsForPlayer(p, raceLink, PlayerStartLocation(p));
        }
        p += 1;
    }
    MeleeInitAI();
}

'''
src = src.replace(helper_anchor, helper + helper_anchor, 1)

update_pattern = re.compile(
    r'void MB_SDUpdateBoardButtons \(\) \{.*?\n\}\n\nvoid MB_SDUpdateOrderText', re.S
)
update_replacement = '''void MB_SDUpdateBoardButtons () {
    int i = 0;
    string icon;
    string display;
    while (i < MB_SD_CANDIDATES) {
        icon = MB_UnitIcon(gv_mbSDCandidate[i]);
        display = MB_DisplayName(gv_mbSDCandidate[i]);
        DialogControlSetPropertyAsString(gv_mbSDButton[i], c_triggerControlPropertyImage, PlayerGroupAll(), icon);
        DialogControlSetPropertyAsString(gv_mbSDButton[i], c_triggerControlPropertyHoverImage, PlayerGroupAll(), icon);
        DialogControlSetPropertyAsInt(gv_mbSDButton[i], c_triggerControlPropertyImageType, PlayerGroupAll(), c_triggerImageTypeNormal);
        DialogControlSetPropertyAsText(gv_mbSDButton[i], c_triggerControlPropertyText, PlayerGroupAll(), StringToText(""));
        DialogControlSetPropertyAsText(gv_mbSDButton[i], c_triggerControlPropertyTooltip, PlayerGroupAll(), StringToText(display));
        DialogControlSetPropertyAsText(gv_mbSDNameLabel[i], c_triggerControlPropertyText, PlayerGroupAll(), StringToText(display));
        DialogControlSetPropertyAsBool(gv_mbSDButton[i], c_triggerControlPropertyDesaturated, PlayerGroupAll(), gv_mbSDTaken[i]);
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
src, n = update_pattern.subn(update_replacement, src, count=1)
if n != 1:
    raise SystemExit(f'failed to replace SD board updater: {n}')

create_pattern = re.compile(
    r'void MB_CreateSDUI \(\) \{.*?\n\}\n\n//--------------------------------------------------------------------------------------------------\n// Phase flow',
    re.S,
)
create_replacement = '''void MB_CreateSDUI () {
    int i = 0;
    int col;
    int row;
    int x;
    int y;
    gv_mbSDDialog = DialogCreate(1060, 650, c_anchorCenter, 0, -5, false);
    DialogSetTransparency(gv_mbSDDialog, 5.0);

    gv_mbSDHeaderPanel = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypePanel);
    DialogControlSetSize(gv_mbSDHeaderPanel, PlayerGroupAll(), 1010, 78);
    DialogControlSetPosition(gv_mbSDHeaderPanel, PlayerGroupAll(), c_anchorTop, 0, 14);
    MB_SetPanelLook(gv_mbSDHeaderPanel);

    gv_mbSDTitle = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeLabel);
    DialogControlSetSize(gv_mbSDTitle, PlayerGroupAll(), 960, 32);
    DialogControlSetPosition(gv_mbSDTitle, PlayerGroupAll(), c_anchorTop, 0, 25);
    DialogControlSetPropertyAsText(gv_mbSDTitle, c_triggerControlPropertyText, PlayerGroupAll(),
        TextWithColor(StringToText("SINGLE DRAFT"), Color(45.0, 82.0, 100.0)));

    gv_mbSDInfo = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeLabel);
    DialogControlSetSize(gv_mbSDInfo, PlayerGroupAll(), 960, 26);
    DialogControlSetPosition(gv_mbSDInfo, PlayerGroupAll(), c_anchorTop, 0, 58);

    i = 0;
    while (i < MB_SD_CANDIDATES) {
        col = i % 6;
        row = i / 6;
        x = 30 + (col * 108);
        y = 112 + (row * 106);

        gv_mbSDButton[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeButton);
        DialogControlSetSize(gv_mbSDButton[i], PlayerGroupAll(), 72, 72);
        DialogControlSetPosition(gv_mbSDButton[i], PlayerGroupAll(), c_anchorTopLeft, x + 12, y);
        DialogControlSetPropertyAsBool(gv_mbSDButton[i], c_triggerControlPropertyBorderVisible, PlayerGroupAll(), true);

        gv_mbSDNameLabel[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeLabel);
        DialogControlSetSize(gv_mbSDNameLabel[i], PlayerGroupAll(), 96, 24);
        DialogControlSetPosition(gv_mbSDNameLabel[i], PlayerGroupAll(), c_anchorTopLeft, x, y + 74);
        i += 1;
    }

    gv_mbSDOrderLabel = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeLabel);
    DialogControlSetSize(gv_mbSDOrderLabel, PlayerGroupAll(), 320, 350);
    DialogControlSetPosition(gv_mbSDOrderLabel, PlayerGroupAll(), c_anchorTopLeft, 720, 108);

    gv_mbSDCurrentLabel = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeLabel);
    DialogControlSetSize(gv_mbSDCurrentLabel, PlayerGroupAll(), 320, 54);
    DialogControlSetPosition(gv_mbSDCurrentLabel, PlayerGroupAll(), c_anchorTopLeft, 720, 475);

    gv_mbSDHintLabel = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeLabel);
    DialogControlSetSize(gv_mbSDHintLabel, PlayerGroupAll(), 650, 62);
    DialogControlSetPosition(gv_mbSDHintLabel, PlayerGroupAll(), c_anchorTopLeft, 30, 548);
    DialogControlSetPropertyAsText(gv_mbSDHintLabel, c_triggerControlPropertyText, PlayerGroupAll(),
        StringToText("아이콘에 마우스를 올리면 유닛명을 확인할 수 있습니다\\n후보 24개 · 전원 고유 유닛 · 공중 4~10 · 순수 캐스터 최대 4"));

    DialogSetVisible(gv_mbSDDialog, PlayerGroupAll(), false);
}

//--------------------------------------------------------------------------------------------------
// Phase flow'''
src, n = create_pattern.subn(create_replacement, src, count=1)
if n != 1:
    raise SystemExit(f'failed to replace SD UI creation: {n}')

finish_old = '''    DialogSetVisible(gv_mbBlindDialog, PlayerGroupAll(), false);
    DialogSetVisible(gv_mbSDDialog, PlayerGroupAll(), false);
    MB_ApplyProductionRestrictionsAll();
'''
finish_new = '''    DialogSetVisible(gv_mbBlindDialog, PlayerGroupAll(), false);
    DialogSetVisible(gv_mbSDDialog, PlayerGroupAll(), false);
    MB_InitStartingUnitsAll();
    MB_ApplyProductionRestrictionsAll();
'''
if finish_old not in src:
    raise SystemExit('finish-selection anchor missing')
src = src.replace(finish_old, finish_new, 1)

if '    MeleeInitUnits();\n' not in src:
    raise SystemExit('early MeleeInitUnits anchor missing')
src = src.replace('    MeleeInitUnits();\n', '', 1)
# Remove only the original early AI initialization; MB_InitStartingUnitsAll owns the new call.
init_fn = re.search(r'bool gt_MeleeInitialization_Func \(.*?\n\}', src, re.S)
if not init_fn:
    raise SystemExit('melee init function missing')
block = init_fn.group(0)
block2 = block.replace('    MeleeInitAI();\n', '', 1)
src = src[:init_fn.start()] + block2 + src[init_fn.end():]

replacements = {
    'DialogControlCreate(gv_mbVoteDialog, c_triggerControlTypeButton)':
        'DialogControlCreateFromTemplate(gv_mbVoteDialog, c_triggerControlTypeButton, "StandardTemplates/StandardButtonTemplate")',
    'DialogControlCreate(gv_mbBlindDialog, c_triggerControlTypeButton)':
        'DialogControlCreateFromTemplate(gv_mbBlindDialog, c_triggerControlTypeButton, "StandardTemplates/StandardButtonTemplate")',
}
for old, new in replacements.items():
    src = src.replace(old, new)

if src.count('gv_mbTimer = TimerCreate();') != 1:
    raise SystemExit('expected exactly one Monobattle timer creation')
if 'MeleeInitOptions();' in src:
    raise SystemExit('stock melee victory logic must remain disabled')
if '    MeleeInitUnits();' in src:
    raise SystemExit('lobby-race starting units are still created early')
if 'int[3] q' in src or 'int[3] quota' in src:
    raise SystemExit('array quota compatibility transform failed')
for required in (
    'MB_StartVote', 'MB_StartBlind', 'MB_StartSD', 'MB_SDGenerateInitialBoard',
    'MB_SDPickSlot', 'MB_SDAutoPick', 'MB_ApplyProductionRestrictionsAll',
    'MB_InitStartingUnitsAll', 'MeleeInitUnitsForPlayer', 'PlayerSetRace',
    'MB_UnitIcon', 'c_triggerControlPropertyImage', 'gv_mbSDNameLabel',
    'TechTreeUnitAllow', 'MB_RerollPlayer',
):
    if required not in src:
        raise SystemExit(f'missing Alpha 3 marker: {required}')

no_strings = re.sub(r'"(?:\\.|[^"\\])*"', '""', src)
no_comments = re.sub(r'//.*', '', no_strings)
if no_comments.count('{') != no_comments.count('}'):
    raise SystemExit('unbalanced Galaxy braces')

assert 30 + 108 * 5 + 96 <= 720
assert 112 + 106 * 3 + 98 <= 548
assert 720 + 320 <= 1060

Path('build').mkdir(exist_ok=True)
Path('build/MapScript.galaxy').write_text(src, encoding='utf-8', newline='\n')
print('Galaxy source prepared: pick-matched starting race + icon-first SD board')
