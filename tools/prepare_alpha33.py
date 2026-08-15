from pathlib import Path
import runpy
import re

# Build on the runtime-hardened Alpha 3.2 source.
runpy.run_path('tools/prepare_alpha31.py', run_name='__main__')
path = Path('build/MapScript.galaxy')
src = path.read_text(encoding='utf-8')

# Correct the actual SC2 unit catalog id. "Hellbat" is the display concept; the melee unit id is HellionTank.
src = src.replace('"Hellbat"', '"HellionTank"')

# Use the production Button catalog for unit icons. Unit entries do not reliably expose an Icon field.
icon_pattern = re.compile(r'string MB_UnitIcon \(string unitId\) \{.*?\n\}', re.S)
icon_replacement = '''string MB_UnitButtonId (string unitId) {
    // Most melee unit train-button ids match their unit ids. Keep this helper so exceptions can be
    // added without touching draft/gameplay ids.
    return unitId;
}

string MB_UnitIcon (string unitId) {
    string buttonId = MB_UnitButtonId(unitId);
    if (!CatalogEntryIsValid(c_gameCatalogButton, buttonId)) {
        return "";
    }
    return CatalogFieldValueGet(c_gameCatalogButton, buttonId, "Icon", c_playerAny);
}'''
src, n = icon_pattern.subn(icon_replacement, src, count=1)
if n != 1:
    raise SystemExit(f'failed to replace unit icon helper: {n}')

# Do not assign an empty image path. Invalid/missing icon metadata should degrade gracefully to the
# base button visual instead of producing runtime "required object" errors.
needle = '''        DialogControlSetPropertyAsString(gv_mbSDButton[i], c_triggerControlPropertyImage, PlayerGroupAll(), icon);
        DialogControlSetPropertyAsString(gv_mbSDButton[i], c_triggerControlPropertyHoverImage, PlayerGroupAll(), icon);
        DialogControlSetPropertyAsInt(gv_mbSDButton[i], c_triggerControlPropertyImageType, PlayerGroupAll(), c_triggerImageTypeNormal);
'''
replacement = '''        if (icon != "") {
            DialogControlSetPropertyAsString(gv_mbSDButton[i], c_triggerControlPropertyImage, PlayerGroupAll(), icon);
            DialogControlSetPropertyAsString(gv_mbSDButton[i], c_triggerControlPropertyHoverImage, PlayerGroupAll(), icon);
            DialogControlSetPropertyAsInt(gv_mbSDButton[i], c_triggerControlPropertyImageType, PlayerGroupAll(), c_triggerImageTypeNormal);
        }
'''
if needle not in src:
    raise SystemExit('SD icon assignment anchor missing')
src = src.replace(needle, replacement, 1)

# Persistent in-game loadout roster. It becomes visible only after all final picks are locked.
global_anchor = 'int[24] gv_mbSDNameLabel;\n'
if global_anchor not in src:
    raise SystemExit('Alpha 3 SD name-label global missing')
roster_globals = '''int[24] gv_mbSDNameLabel;

// Persistent game roster UI: each viewer sees four allied and four enemy Monobattle picks.
int gv_mbRosterDialog;
int gv_mbRosterTitle;
int gv_mbRosterAllyHeader;
int gv_mbRosterEnemyHeader;
int[4] gv_mbRosterAllyIcon;
int[4] gv_mbRosterAllyText;
int[4] gv_mbRosterEnemyIcon;
int[4] gv_mbRosterEnemyText;
'''
src = src.replace(global_anchor, roster_globals, 1)

ui_anchor = '//--------------------------------------------------------------------------------------------------\n// Production restrictions\n'
if ui_anchor not in src:
    raise SystemExit('production restriction section anchor missing')
roster_funcs = r'''//--------------------------------------------------------------------------------------------------
// Persistent team loadout roster
//--------------------------------------------------------------------------------------------------
void MB_RosterClearFor (int viewer) {
    int i = 0;
    playergroup one = PlayerGroupSingle(viewer);
    while (i < 4) {
        DialogControlSetVisible(gv_mbRosterAllyIcon[i], one, false);
        DialogControlSetVisible(gv_mbRosterAllyText[i], one, false);
        DialogControlSetVisible(gv_mbRosterEnemyIcon[i], one, false);
        DialogControlSetVisible(gv_mbRosterEnemyText[i], one, false);
        i += 1;
    }
}

void MB_RosterSetRow (int viewer, bool ally, int row, int targetPlayer) {
    playergroup one = PlayerGroupSingle(viewer);
    string icon = MB_UnitIcon(gv_mbUnit[targetPlayer]);
    text label = StringToText("P" + IntToString(targetPlayer) + "  " + TextToString(PlayerName(targetPlayer)) + "  ·  " + MB_DisplayName(gv_mbUnit[targetPlayer]));
    int iconControl;
    int textControl;

    if (ally) {
        iconControl = gv_mbRosterAllyIcon[row];
        textControl = gv_mbRosterAllyText[row];
    }
    else {
        iconControl = gv_mbRosterEnemyIcon[row];
        textControl = gv_mbRosterEnemyText[row];
    }

    if (icon != "") {
        DialogControlSetPropertyAsString(iconControl, c_triggerControlPropertyImage, one, icon);
        DialogControlSetPropertyAsInt(iconControl, c_triggerControlPropertyImageType, one, c_triggerImageTypeNormal);
    }
    DialogControlSetPropertyAsText(textControl, c_triggerControlPropertyText, one, label);
    DialogControlSetVisible(iconControl, one, true);
    DialogControlSetVisible(textControl, one, true);
}

void MB_UpdateRosterFor (int viewer) {
    int p = 1;
    int allyRow = 0;
    int enemyRow = 0;
    playergroup allies;
    playergroup one;

    if (!MB_PlayerActive(viewer)) { return; }
    one = PlayerGroupSingle(viewer);
    allies = PlayerGroupAlliance(c_playerGroupAlly, viewer);
    PlayerGroupAdd(allies, viewer);
    MB_RosterClearFor(viewer);

    while (p <= 8) {
        if (MB_PlayerActive(p) && gv_mbUnit[p] != "") {
            if (PlayerGroupHasPlayer(allies, p)) {
                if (allyRow < 4) {
                    MB_RosterSetRow(viewer, true, allyRow, p);
                    allyRow += 1;
                }
            }
            else {
                if (enemyRow < 4) {
                    MB_RosterSetRow(viewer, false, enemyRow, p);
                    enemyRow += 1;
                }
            }
        }
        p += 1;
    }
    DialogSetVisible(gv_mbRosterDialog, one, true);
}

void MB_UpdateRosterAll () {
    int p = 1;
    while (p <= 8) {
        MB_UpdateRosterFor(p);
        p += 1;
    }
}

void MB_CreateRosterUI () {
    int i = 0;
    int y;
    gv_mbRosterDialog = DialogCreate(570, 235, c_anchorTop, 0, 72, false);
    DialogSetTransparency(gv_mbRosterDialog, 18.0);

    gv_mbRosterTitle = DialogControlCreate(gv_mbRosterDialog, c_triggerControlTypeLabel);
    DialogControlSetSize(gv_mbRosterTitle, PlayerGroupAll(), 530, 28);
    DialogControlSetPosition(gv_mbRosterTitle, PlayerGroupAll(), c_anchorTop, 0, 10);
    DialogControlSetPropertyAsText(gv_mbRosterTitle, c_triggerControlPropertyText, PlayerGroupAll(),
        TextWithColor(StringToText("MONOBATTLE · UNIT LOADOUT"), Color(45.0, 82.0, 100.0)));

    gv_mbRosterAllyHeader = DialogControlCreate(gv_mbRosterDialog, c_triggerControlTypeLabel);
    DialogControlSetSize(gv_mbRosterAllyHeader, PlayerGroupAll(), 245, 24);
    DialogControlSetPosition(gv_mbRosterAllyHeader, PlayerGroupAll(), c_anchorTopLeft, 18, 42);
    DialogControlSetPropertyAsText(gv_mbRosterAllyHeader, c_triggerControlPropertyText, PlayerGroupAll(),
        TextWithColor(StringToText("ALLY"), Color(35.0, 75.0, 100.0)));

    gv_mbRosterEnemyHeader = DialogControlCreate(gv_mbRosterDialog, c_triggerControlTypeLabel);
    DialogControlSetSize(gv_mbRosterEnemyHeader, PlayerGroupAll(), 245, 24);
    DialogControlSetPosition(gv_mbRosterEnemyHeader, PlayerGroupAll(), c_anchorTopLeft, 302, 42);
    DialogControlSetPropertyAsText(gv_mbRosterEnemyHeader, c_triggerControlPropertyText, PlayerGroupAll(),
        TextWithColor(StringToText("ENEMY"), Color(100.0, 45.0, 35.0)));

    while (i < 4) {
        y = 72 + (i * 39);

        gv_mbRosterAllyIcon[i] = DialogControlCreate(gv_mbRosterDialog, c_triggerControlTypeImage);
        DialogControlSetSize(gv_mbRosterAllyIcon[i], PlayerGroupAll(), 32, 32);
        DialogControlSetPosition(gv_mbRosterAllyIcon[i], PlayerGroupAll(), c_anchorTopLeft, 18, y);
        gv_mbRosterAllyText[i] = DialogControlCreate(gv_mbRosterDialog, c_triggerControlTypeLabel);
        DialogControlSetSize(gv_mbRosterAllyText[i], PlayerGroupAll(), 220, 32);
        DialogControlSetPosition(gv_mbRosterAllyText[i], PlayerGroupAll(), c_anchorTopLeft, 56, y);

        gv_mbRosterEnemyIcon[i] = DialogControlCreate(gv_mbRosterDialog, c_triggerControlTypeImage);
        DialogControlSetSize(gv_mbRosterEnemyIcon[i], PlayerGroupAll(), 32, 32);
        DialogControlSetPosition(gv_mbRosterEnemyIcon[i], PlayerGroupAll(), c_anchorTopLeft, 302, y);
        gv_mbRosterEnemyText[i] = DialogControlCreate(gv_mbRosterDialog, c_triggerControlTypeLabel);
        DialogControlSetSize(gv_mbRosterEnemyText[i], PlayerGroupAll(), 220, 32);
        DialogControlSetPosition(gv_mbRosterEnemyText[i], PlayerGroupAll(), c_anchorTopLeft, 340, y);
        i += 1;
    }
    DialogSetVisible(gv_mbRosterDialog, PlayerGroupAll(), false);
}

'''
src = src.replace(ui_anchor, roster_funcs + ui_anchor, 1)

# Create the roster at map init with other UI, but reveal/fill it only after final picks.
create_anchor = '    MB_CreateSDUI();\n    MB_StartVote();\n'
if create_anchor not in src:
    raise SystemExit('UI init anchor missing')
src = src.replace(create_anchor, '    MB_CreateSDUI();\n    MB_CreateRosterUI();\n    MB_StartVote();\n', 1)

finish_anchor = '    MB_ApplyProductionRestrictionsAll();\n'
if finish_anchor not in src:
    raise SystemExit('finish selection production anchor missing')
src = src.replace(finish_anchor, '    MB_ApplyProductionRestrictionsAll();\n    MB_UpdateRosterAll();\n', 1)

# Safety checks.
if '"Hellbat"' in src:
    raise SystemExit('invalid Hellbat unit catalog id remains')
for marker in (
    '"HellionTank"', 'c_gameCatalogButton', 'CatalogEntryIsValid',
    'MB_CreateRosterUI', 'MB_UpdateRosterAll', 'MB_RosterSetRow',
    'gv_mbRosterAllyIcon', 'gv_mbRosterEnemyIcon'
):
    if marker not in src:
        raise SystemExit(f'Alpha 3.3 marker missing: {marker}')

# A raw newline inside a Galaxy quoted literal is a syntax error. Keep the Alpha 3.2 guard.
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
print('Alpha 3.3 prepared: safe button icons + HellionTank id + persistent ally/enemy roster')
