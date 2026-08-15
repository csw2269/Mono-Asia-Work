from pathlib import Path
import runpy
import re

# Build from the last runtime-stable UI branch. Do NOT inherit Alpha 4.3 catalog-scanning code.
runpy.run_path('tools/prepare_alpha42.py', run_name='__main__')
path = Path('build/MapScript.galaxy')
src = path.read_text(encoding='utf-8')

# -------------------------------------------------------------------------------------------------
# Globals used by the cleaner SD cards and compact in-game roster.
# -------------------------------------------------------------------------------------------------
anchor = 'int[24] gv_mbSDNameLabel;\n'
if anchor not in src:
    raise SystemExit('SD global anchor missing')
src = src.replace(anchor, anchor + 'int[24] gv_mbSDFrame;\n', 1)

roster_anchor = 'int[4] gv_mbRosterEnemyText;\n'
if roster_anchor not in src:
    raise SystemExit('roster global anchor missing')
src = src.replace(roster_anchor,
                  roster_anchor + 'int[4] gv_mbRosterAllyBorder;\nint[4] gv_mbRosterEnemyBorder;\n', 1)

# -------------------------------------------------------------------------------------------------
# 1) Polished mode screen: sparse, centered, no explanatory copy. The focus layer already hides
#    the battlefield; this dialog only carries title, vote status and two clean horizontal choices.
# -------------------------------------------------------------------------------------------------
vote_pattern = re.compile(r'void MB_CreateVoteUI \(\) \{.*?\n\}\n\nvoid MB_CreateBlindUI', re.S)
vote_replacement = r'''void MB_CreateVoteUI () {
    gv_mbVoteDialog = DialogCreate(900, 430, c_anchorCenter, 0, -20, false);
    DialogSetTransparency(gv_mbVoteDialog, 100.0);

    gv_mbVoteHeaderPanel = DialogControlCreate(gv_mbVoteDialog, c_triggerControlTypePanel);
    DialogControlSetSize(gv_mbVoteHeaderPanel, PlayerGroupAll(), 720, 2);
    DialogControlSetPosition(gv_mbVoteHeaderPanel, PlayerGroupAll(), c_anchorTop, 0, 110);
    DialogControlSetPropertyAsBool(gv_mbVoteHeaderPanel, c_triggerControlPropertyBackgroundVisible, PlayerGroupAll(), true);
    DialogControlSetPropertyAsBool(gv_mbVoteHeaderPanel, c_triggerControlPropertyBorderVisible, PlayerGroupAll(), false);
    DialogControlSetPropertyAsColor(gv_mbVoteHeaderPanel, c_triggerControlPropertyColor, PlayerGroupAll(), Color(20.0, 55.0, 75.0));

    gv_mbVoteTitle = DialogControlCreate(gv_mbVoteDialog, c_triggerControlTypeLabel);
    DialogControlSetSize(gv_mbVoteTitle, PlayerGroupAll(), 760, 70);
    DialogControlSetPosition(gv_mbVoteTitle, PlayerGroupAll(), c_anchorTop, 0, 24);
    DialogControlSetPropertyAsString(gv_mbVoteTitle, c_triggerControlPropertyStyle, PlayerGroupAll(), "ReplayLabel");
    DialogControlSetPropertyAsText(gv_mbVoteTitle, c_triggerControlPropertyText, PlayerGroupAll(),
        TextWithColor(StringToText("GAME MODE"), Color(62.0, 86.0, 100.0)));

    gv_mbVoteSubtitle = DialogControlCreate(gv_mbVoteDialog, c_triggerControlTypeLabel);
    DialogControlSetVisible(gv_mbVoteSubtitle, PlayerGroupAll(), false);

    gv_mbVoteBlindButton = DialogControlCreateFromTemplate(gv_mbVoteDialog, c_triggerControlTypeButton,
        "StandardTemplates/StandardButtonTemplate");
    DialogControlSetSize(gv_mbVoteBlindButton, PlayerGroupAll(), 560, 64);
    DialogControlSetPosition(gv_mbVoteBlindButton, PlayerGroupAll(), c_anchorTop, 0, 145);
    DialogControlSetPropertyAsText(gv_mbVoteBlindButton, c_triggerControlPropertyText, PlayerGroupAll(), StringToText("BLIND RANDOM"));

    gv_mbVoteSDButton = DialogControlCreateFromTemplate(gv_mbVoteDialog, c_triggerControlTypeButton,
        "StandardTemplates/StandardButtonTemplate");
    DialogControlSetSize(gv_mbVoteSDButton, PlayerGroupAll(), 560, 64);
    DialogControlSetPosition(gv_mbVoteSDButton, PlayerGroupAll(), c_anchorTop, 0, 224);
    DialogControlSetPropertyAsText(gv_mbVoteSDButton, c_triggerControlPropertyText, PlayerGroupAll(), StringToText("SINGLE DRAFT"));

    gv_mbVoteInfo = DialogControlCreate(gv_mbVoteDialog, c_triggerControlTypeLabel);
    DialogControlSetSize(gv_mbVoteInfo, PlayerGroupAll(), 720, 34);
    DialogControlSetPosition(gv_mbVoteInfo, PlayerGroupAll(), c_anchorTop, 0, 314);

    gv_mbVoteFooter = DialogControlCreate(gv_mbVoteDialog, c_triggerControlTypeLabel);
    DialogControlSetVisible(gv_mbVoteFooter, PlayerGroupAll(), false);

    DialogSetVisible(gv_mbVoteDialog, PlayerGroupAll(), false);
}

void MB_CreateBlindUI'''
src, n = vote_pattern.subn(lambda _m: vote_replacement, src, count=1)
if n != 1:
    raise SystemExit(f'failed to replace vote UI: {n}')

# -------------------------------------------------------------------------------------------------
# 2) Blind screen: original layout, not a copy of the reference. Four compact race choices live on
#    the left; the player's result and allied reveal occupy the right side.
# -------------------------------------------------------------------------------------------------
blind_pattern = re.compile(r'void MB_CreateBlindUI \(\) \{.*?\n\}\n\nvoid MB_CreateSDUI', re.S)
blind_replacement = r'''void MB_CreateBlindUI () {
    int i = 0;
    gv_mbBlindDialog = DialogCreate(900, 520, c_anchorCenter, 0, -10, false);
    DialogSetTransparency(gv_mbBlindDialog, 100.0);

    gv_mbBlindHeaderPanel = DialogControlCreate(gv_mbBlindDialog, c_triggerControlTypePanel);
    DialogControlSetSize(gv_mbBlindHeaderPanel, PlayerGroupAll(), 2, 330);
    DialogControlSetPosition(gv_mbBlindHeaderPanel, PlayerGroupAll(), c_anchorTopLeft, 286, 104);
    DialogControlSetPropertyAsBool(gv_mbBlindHeaderPanel, c_triggerControlPropertyBackgroundVisible, PlayerGroupAll(), true);
    DialogControlSetPropertyAsBool(gv_mbBlindHeaderPanel, c_triggerControlPropertyBorderVisible, PlayerGroupAll(), false);
    DialogControlSetPropertyAsColor(gv_mbBlindHeaderPanel, c_triggerControlPropertyColor, PlayerGroupAll(), Color(20.0, 55.0, 75.0));

    gv_mbBlindTitle = DialogControlCreate(gv_mbBlindDialog, c_triggerControlTypeLabel);
    DialogControlSetSize(gv_mbBlindTitle, PlayerGroupAll(), 820, 58);
    DialogControlSetPosition(gv_mbBlindTitle, PlayerGroupAll(), c_anchorTop, 0, 18);
    DialogControlSetPropertyAsString(gv_mbBlindTitle, c_triggerControlPropertyStyle, PlayerGroupAll(), "ReplayLabel");
    DialogControlSetPropertyAsText(gv_mbBlindTitle, c_triggerControlPropertyText, PlayerGroupAll(),
        TextWithColor(StringToText("SELECT RACE"), Color(62.0, 86.0, 100.0)));

    gv_mbBlindInfo = DialogControlCreate(gv_mbBlindDialog, c_triggerControlTypeLabel);
    DialogControlSetSize(gv_mbBlindInfo, PlayerGroupAll(), 820, 28);
    DialogControlSetPosition(gv_mbBlindInfo, PlayerGroupAll(), c_anchorTop, 0, 74);

    gv_mbRandomButton = DialogControlCreateFromTemplate(gv_mbBlindDialog, c_triggerControlTypeButton,
        "StandardTemplates/StandardButtonTemplate");
    DialogControlSetSize(gv_mbRandomButton, PlayerGroupAll(), 210, 52);
    DialogControlSetPosition(gv_mbRandomButton, PlayerGroupAll(), c_anchorTopLeft, 42, 120);
    DialogControlSetPropertyAsText(gv_mbRandomButton, c_triggerControlPropertyText, PlayerGroupAll(), StringToText("RANDOM"));

    gv_mbTerranButton = DialogControlCreateFromTemplate(gv_mbBlindDialog, c_triggerControlTypeButton,
        "StandardTemplates/StandardButtonTemplate");
    DialogControlSetSize(gv_mbTerranButton, PlayerGroupAll(), 210, 52);
    DialogControlSetPosition(gv_mbTerranButton, PlayerGroupAll(), c_anchorTopLeft, 42, 184);
    DialogControlSetPropertyAsText(gv_mbTerranButton, c_triggerControlPropertyText, PlayerGroupAll(), StringToText("TERRAN"));

    gv_mbZergButton = DialogControlCreateFromTemplate(gv_mbBlindDialog, c_triggerControlTypeButton,
        "StandardTemplates/StandardButtonTemplate");
    DialogControlSetSize(gv_mbZergButton, PlayerGroupAll(), 210, 52);
    DialogControlSetPosition(gv_mbZergButton, PlayerGroupAll(), c_anchorTopLeft, 42, 248);
    DialogControlSetPropertyAsText(gv_mbZergButton, c_triggerControlPropertyText, PlayerGroupAll(), StringToText("ZERG"));

    gv_mbProtossButton = DialogControlCreateFromTemplate(gv_mbBlindDialog, c_triggerControlTypeButton,
        "StandardTemplates/StandardButtonTemplate");
    DialogControlSetSize(gv_mbProtossButton, PlayerGroupAll(), 210, 52);
    DialogControlSetPosition(gv_mbProtossButton, PlayerGroupAll(), c_anchorTopLeft, 42, 312);
    DialogControlSetPropertyAsText(gv_mbProtossButton, c_triggerControlPropertyText, PlayerGroupAll(), StringToText("PROTOSS"));

    gv_mbBlindStatus = DialogControlCreate(gv_mbBlindDialog, c_triggerControlTypeLabel);
    DialogControlSetSize(gv_mbBlindStatus, PlayerGroupAll(), 520, 44);
    DialogControlSetPosition(gv_mbBlindStatus, PlayerGroupAll(), c_anchorTopLeft, 326, 122);
    DialogControlSetPropertyAsString(gv_mbBlindStatus, c_triggerControlPropertyStyle, PlayerGroupAll(), "DirectiveDisplay");

    while (i < 4) {
        gv_mbTeamRow[i] = DialogControlCreate(gv_mbBlindDialog, c_triggerControlTypeLabel);
        DialogControlSetSize(gv_mbTeamRow[i], PlayerGroupAll(), 500, 48);
        DialogControlSetPosition(gv_mbTeamRow[i], PlayerGroupAll(), c_anchorTopLeft, 326, 190 + (i * 54));
        i += 1;
    }

    gv_mbRerollButton = DialogControlCreateFromTemplate(gv_mbBlindDialog, c_triggerControlTypeButton,
        "StandardTemplates/StandardButtonTemplate");
    DialogControlSetSize(gv_mbRerollButton, PlayerGroupAll(), 260, 50);
    DialogControlSetPosition(gv_mbRerollButton, PlayerGroupAll(), c_anchorBottomRight, -52, -28);
    DialogControlSetPropertyAsText(gv_mbRerollButton, c_triggerControlPropertyText, PlayerGroupAll(), StringToText("REROLL"));
    DialogControlSetVisible(gv_mbRerollButton, PlayerGroupAll(), false);

    DialogSetVisible(gv_mbBlindDialog, PlayerGroupAll(), false);
}

void MB_CreateSDUI'''
src, n = blind_pattern.subn(lambda _m: blind_replacement, src, count=1)
if n != 1:
    raise SystemExit(f'failed to replace blind UI: {n}')

# -------------------------------------------------------------------------------------------------
# 3) SD cards. Never ask a template to draw the unit icon: frame -> image -> transparent click layer.
#    This prevents the Alpha 4.2 regression where template children covered all candidate artwork.
# -------------------------------------------------------------------------------------------------
sd_create_pattern = re.compile(r'void MB_CreateSDUI \(\) \{.*?\n\}\n\n//--------------------------------------------------------------------------------------------------\n// Phase flow', re.S)
sd_create_replacement = r'''void MB_CreateSDUI () {
    int i = 0;
    int col;
    int row;
    int x;
    int y;

    gv_mbSDDialog = DialogCreate(1120, 680, c_anchorCenter, 0, -4, false);
    DialogSetTransparency(gv_mbSDDialog, 100.0);

    gv_mbSDHeaderPanel = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypePanel);
    DialogControlSetSize(gv_mbSDHeaderPanel, PlayerGroupAll(), 1040, 2);
    DialogControlSetPosition(gv_mbSDHeaderPanel, PlayerGroupAll(), c_anchorTop, 0, 92);
    DialogControlSetPropertyAsBool(gv_mbSDHeaderPanel, c_triggerControlPropertyBackgroundVisible, PlayerGroupAll(), true);
    DialogControlSetPropertyAsBool(gv_mbSDHeaderPanel, c_triggerControlPropertyBorderVisible, PlayerGroupAll(), false);
    DialogControlSetPropertyAsColor(gv_mbSDHeaderPanel, c_triggerControlPropertyColor, PlayerGroupAll(), Color(20.0, 55.0, 75.0));

    gv_mbSDTitle = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeLabel);
    DialogControlSetSize(gv_mbSDTitle, PlayerGroupAll(), 1020, 54);
    DialogControlSetPosition(gv_mbSDTitle, PlayerGroupAll(), c_anchorTop, 0, 14);
    DialogControlSetPropertyAsString(gv_mbSDTitle, c_triggerControlPropertyStyle, PlayerGroupAll(), "ReplayLabel");
    DialogControlSetPropertyAsText(gv_mbSDTitle, c_triggerControlPropertyText, PlayerGroupAll(),
        TextWithColor(StringToText("SINGLE DRAFT"), Color(62.0, 86.0, 100.0)));

    gv_mbSDInfo = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeLabel);
    DialogControlSetSize(gv_mbSDInfo, PlayerGroupAll(), 1020, 26);
    DialogControlSetPosition(gv_mbSDInfo, PlayerGroupAll(), c_anchorTop, 0, 62);

    while (i < MB_SD_CANDIDATES) {
        col = i % 6;
        row = i / 6;
        x = 28 + (col * 106);
        y = 118 + (row * 116);

        gv_mbSDFrame[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypePanel);
        DialogControlSetSize(gv_mbSDFrame[i], PlayerGroupAll(), 72, 72);
        DialogControlSetPosition(gv_mbSDFrame[i], PlayerGroupAll(), c_anchorTopLeft, x + 12, y);
        DialogControlSetPropertyAsBool(gv_mbSDFrame[i], c_triggerControlPropertyBackgroundVisible, PlayerGroupAll(), true);
        DialogControlSetPropertyAsBool(gv_mbSDFrame[i], c_triggerControlPropertyBorderVisible, PlayerGroupAll(), true);
        DialogControlSetPropertyAsColor(gv_mbSDFrame[i], c_triggerControlPropertyFillColor, PlayerGroupAll(), ColorWithAlpha(2.0, 6.0, 10.0, 96.0));
        DialogControlSetPropertyAsColor(gv_mbSDFrame[i], c_triggerControlPropertyBorderColor, PlayerGroupAll(), Color(25.0, 55.0, 72.0));

        gv_mbSDIcon[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeImage);
        DialogControlSetSize(gv_mbSDIcon[i], PlayerGroupAll(), 62, 62);
        DialogControlSetPosition(gv_mbSDIcon[i], PlayerGroupAll(), c_anchorTopLeft, x + 17, y + 5);
        DialogControlSetPropertyAsInt(gv_mbSDIcon[i], c_triggerControlPropertyImageType, PlayerGroupAll(), c_triggerImageTypeNormal);

        // Pure hit target. It draws nothing, so the icon can never be hidden by a button template.
        gv_mbSDButton[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeButton);
        DialogControlSetSize(gv_mbSDButton[i], PlayerGroupAll(), 72, 72);
        DialogControlSetPosition(gv_mbSDButton[i], PlayerGroupAll(), c_anchorTopLeft, x + 12, y);
        DialogControlSetPropertyAsBool(gv_mbSDButton[i], c_triggerControlPropertyBackgroundVisible, PlayerGroupAll(), false);
        DialogControlSetPropertyAsBool(gv_mbSDButton[i], c_triggerControlPropertyBorderVisible, PlayerGroupAll(), false);

        gv_mbSDNameLabel[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeLabel);
        DialogControlSetSize(gv_mbSDNameLabel[i], PlayerGroupAll(), 96, 22);
        DialogControlSetPosition(gv_mbSDNameLabel[i], PlayerGroupAll(), c_anchorTopLeft, x, y + 75);

        gv_mbSDPickBadge[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeLabel);
        DialogControlSetSize(gv_mbSDPickBadge[i], PlayerGroupAll(), 48, 20);
        DialogControlSetPosition(gv_mbSDPickBadge[i], PlayerGroupAll(), c_anchorTopLeft, x + 53, y + 2);
        DialogControlSetPropertyAsString(gv_mbSDPickBadge[i], c_triggerControlPropertyStyle, PlayerGroupAll(), "GameButtonChargeSmall");
        DialogControlSetVisible(gv_mbSDPickBadge[i], PlayerGroupAll(), false);
        i += 1;
    }

    gv_mbSDOrderLabel = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeLabel);
    DialogControlSetSize(gv_mbSDOrderLabel, PlayerGroupAll(), 330, 370);
    DialogControlSetPosition(gv_mbSDOrderLabel, PlayerGroupAll(), c_anchorTopLeft, 720, 122);

    gv_mbSDCurrentLabel = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeLabel);
    DialogControlSetSize(gv_mbSDCurrentLabel, PlayerGroupAll(), 330, 52);
    DialogControlSetPosition(gv_mbSDCurrentLabel, PlayerGroupAll(), c_anchorTopLeft, 720, 505);

    gv_mbSDHintLabel = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeLabel);
    DialogControlSetSize(gv_mbSDHintLabel, PlayerGroupAll(), 650, 45);
    DialogControlSetPosition(gv_mbSDHintLabel, PlayerGroupAll(), c_anchorTopLeft, 28, 596);
    DialogControlSetPropertyAsText(gv_mbSDHintLabel, c_triggerControlPropertyText, PlayerGroupAll(), StringToText(""));

    DialogSetVisible(gv_mbSDDialog, PlayerGroupAll(), false);
}

//--------------------------------------------------------------------------------------------------
// Phase flow'''
src, n = sd_create_pattern.subn(lambda _m: sd_create_replacement, src, count=1)
if n != 1:
    raise SystemExit(f'failed to replace SD creation: {n}')

sd_update_pattern = re.compile(r'void MB_SDUpdateBoardButtons \(\) \{.*?\n\}\n\nvoid MB_SDUpdateOrderText', re.S)
sd_update_replacement = r'''void MB_SDUpdateBoardButtons () {
    int i = 0;
    string icon;
    string display;
    int picker;
    int team;
    color frameColor;

    while (i < MB_SD_CANDIDATES) {
        icon = MB_UnitIcon(gv_mbSDCandidate[i]);
        display = MB_DisplayName(gv_mbSDCandidate[i]);
        picker = gv_mbSDPickedBy[i];

        if (icon != "") {
            DialogControlSetPropertyAsString(gv_mbSDIcon[i], c_triggerControlPropertyImage, PlayerGroupAll(), icon);
            DialogControlSetVisible(gv_mbSDIcon[i], PlayerGroupAll(), true);
        }
        else {
            DialogControlSetVisible(gv_mbSDIcon[i], PlayerGroupAll(), false);
        }
        DialogControlSetPropertyAsBool(gv_mbSDIcon[i], c_triggerControlPropertyDesaturated, PlayerGroupAll(), gv_mbSDTaken[i]);
        DialogControlSetPropertyAsText(gv_mbSDButton[i], c_triggerControlPropertyTooltip, PlayerGroupAll(), StringToText(display));
        DialogControlSetPropertyAsText(gv_mbSDNameLabel[i], c_triggerControlPropertyText, PlayerGroupAll(), StringToText(display));

        if (picker > 0) {
            team = MB_SDPlayerTeam(picker);
            if (team == 0) { frameColor = Color(30.0, 68.0, 100.0); }
            else { frameColor = Color(100.0, 38.0, 30.0); }
            DialogControlSetPropertyAsColor(gv_mbSDFrame[i], c_triggerControlPropertyBorderColor, PlayerGroupAll(), frameColor);
            DialogControlSetPropertyAsText(gv_mbSDPickBadge[i], c_triggerControlPropertyText, PlayerGroupAll(),
                MB_TeamTagText(team, "P" + IntToString(picker)));
            DialogControlSetVisible(gv_mbSDPickBadge[i], PlayerGroupAll(), true);
        }
        else {
            DialogControlSetPropertyAsColor(gv_mbSDFrame[i], c_triggerControlPropertyBorderColor, PlayerGroupAll(), Color(25.0, 55.0, 72.0));
            DialogControlSetVisible(gv_mbSDPickBadge[i], PlayerGroupAll(), false);
        }

        DialogControlSetEnabled(gv_mbSDButton[i], PlayerGroupAll(), !gv_mbSDTaken[i]);
        i += 1;
    }
}

void MB_SDUpdateOrderText'''
src, n = sd_update_pattern.subn(lambda _m: sd_update_replacement, src, count=1)
if n != 1:
    raise SystemExit(f'failed to replace SD updater: {n}')

# -------------------------------------------------------------------------------------------------
# 4) Running-game roster: two rows of four small desaturated icons, player-color frame and P# below.
#    This uses the same information density as replay production displays without copying the
#    reference's textures, positions or artwork.
# -------------------------------------------------------------------------------------------------
roster_pattern = re.compile(r'void MB_RosterClearFor \(int viewer\) \{.*?\n\}\n\n//--------------------------------------------------------------------------------------------------\n// Production restrictions', re.S)
roster_replacement = r'''void MB_RosterClearFor (int viewer) {
    int i = 0;
    playergroup one = PlayerGroupSingle(viewer);
    while (i < 4) {
        DialogControlSetVisible(gv_mbRosterAllyBorder[i], one, false);
        DialogControlSetVisible(gv_mbRosterAllyIcon[i], one, false);
        DialogControlSetVisible(gv_mbRosterAllyText[i], one, false);
        DialogControlSetVisible(gv_mbRosterEnemyBorder[i], one, false);
        DialogControlSetVisible(gv_mbRosterEnemyIcon[i], one, false);
        DialogControlSetVisible(gv_mbRosterEnemyText[i], one, false);
        i += 1;
    }
}

void MB_RosterSetRow (int viewer, bool ally, int row, int targetPlayer) {
    playergroup one = PlayerGroupSingle(viewer);
    string icon = MB_UnitIcon(gv_mbUnit[targetPlayer]);
    color pc = ColorFromIndex(PlayerGetColorIndex(targetPlayer, false), c_teamColorDiffuse);
    int borderControl;
    int iconControl;
    int textControl;

    if (ally) {
        borderControl = gv_mbRosterAllyBorder[row];
        iconControl = gv_mbRosterAllyIcon[row];
        textControl = gv_mbRosterAllyText[row];
    }
    else {
        borderControl = gv_mbRosterEnemyBorder[row];
        iconControl = gv_mbRosterEnemyIcon[row];
        textControl = gv_mbRosterEnemyText[row];
    }

    DialogControlSetPropertyAsColor(borderControl, c_triggerControlPropertyBorderColor, one, pc);
    DialogControlSetPropertyAsColor(textControl, c_triggerControlPropertyColor, one, pc);
    DialogControlSetPropertyAsText(textControl, c_triggerControlPropertyText, one, StringToText("P" + IntToString(targetPlayer)));

    if (icon != "") {
        DialogControlSetPropertyAsString(iconControl, c_triggerControlPropertyImage, one, icon);
    }
    DialogControlSetPropertyAsBool(iconControl, c_triggerControlPropertyDesaturated, one, true);
    DialogControlSetPropertyAsText(iconControl, c_triggerControlPropertyTooltip, one,
        StringToText(MB_DisplayName(gv_mbUnit[targetPlayer])));

    DialogControlSetVisible(borderControl, one, true);
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
                if (allyRow < 4) { MB_RosterSetRow(viewer, true, allyRow, p); allyRow += 1; }
            }
            else {
                if (enemyRow < 4) { MB_RosterSetRow(viewer, false, enemyRow, p); enemyRow += 1; }
            }
        }
        p += 1;
    }
    DialogSetVisible(gv_mbRosterDialog, one, true);
}

void MB_UpdateRosterAll () {
    int p = 1;
    while (p <= 8) { MB_UpdateRosterFor(p); p += 1; }
}

void MB_CreateRosterUI () {
    int i = 0;
    int x;
    gv_mbRosterDialog = DialogCreate(270, 126, c_anchorTopLeft, 14, 18, false);
    DialogSetTransparency(gv_mbRosterDialog, 100.0);

    // Reuse old labels only as tiny row markers.
    gv_mbRosterTitle = DialogControlCreate(gv_mbRosterDialog, c_triggerControlTypeLabel);
    DialogControlSetSize(gv_mbRosterTitle, PlayerGroupAll(), 26, 18);
    DialogControlSetPosition(gv_mbRosterTitle, PlayerGroupAll(), c_anchorTopLeft, 2, 18);
    DialogControlSetPropertyAsText(gv_mbRosterTitle, c_triggerControlPropertyText, PlayerGroupAll(),
        TextWithColor(StringToText("A"), Color(35.0, 75.0, 100.0)));

    gv_mbRosterAllyHeader = DialogControlCreate(gv_mbRosterDialog, c_triggerControlTypeLabel);
    DialogControlSetSize(gv_mbRosterAllyHeader, PlayerGroupAll(), 26, 18);
    DialogControlSetPosition(gv_mbRosterAllyHeader, PlayerGroupAll(), c_anchorTopLeft, 2, 78);
    DialogControlSetPropertyAsText(gv_mbRosterAllyHeader, c_triggerControlPropertyText, PlayerGroupAll(),
        TextWithColor(StringToText("E"), Color(100.0, 45.0, 35.0)));
    DialogControlSetVisible(gv_mbRosterEnemyHeader, PlayerGroupAll(), false);

    while (i < 4) {
        x = 30 + (i * 58);

        gv_mbRosterAllyBorder[i] = DialogControlCreate(gv_mbRosterDialog, c_triggerControlTypePanel);
        DialogControlSetSize(gv_mbRosterAllyBorder[i], PlayerGroupAll(), 48, 48);
        DialogControlSetPosition(gv_mbRosterAllyBorder[i], PlayerGroupAll(), c_anchorTopLeft, x, 2);
        DialogControlSetPropertyAsBool(gv_mbRosterAllyBorder[i], c_triggerControlPropertyBackgroundVisible, PlayerGroupAll(), false);
        DialogControlSetPropertyAsBool(gv_mbRosterAllyBorder[i], c_triggerControlPropertyBorderVisible, PlayerGroupAll(), true);

        gv_mbRosterAllyIcon[i] = DialogControlCreate(gv_mbRosterDialog, c_triggerControlTypeImage);
        DialogControlSetSize(gv_mbRosterAllyIcon[i], PlayerGroupAll(), 42, 42);
        DialogControlSetPosition(gv_mbRosterAllyIcon[i], PlayerGroupAll(), c_anchorTopLeft, x + 3, 5);
        gv_mbRosterAllyText[i] = DialogControlCreate(gv_mbRosterDialog, c_triggerControlTypeLabel);
        DialogControlSetSize(gv_mbRosterAllyText[i], PlayerGroupAll(), 48, 15);
        DialogControlSetPosition(gv_mbRosterAllyText[i], PlayerGroupAll(), c_anchorTopLeft, x, 49);

        gv_mbRosterEnemyBorder[i] = DialogControlCreate(gv_mbRosterDialog, c_triggerControlTypePanel);
        DialogControlSetSize(gv_mbRosterEnemyBorder[i], PlayerGroupAll(), 48, 48);
        DialogControlSetPosition(gv_mbRosterEnemyBorder[i], PlayerGroupAll(), c_anchorTopLeft, x, 64);
        DialogControlSetPropertyAsBool(gv_mbRosterEnemyBorder[i], c_triggerControlPropertyBackgroundVisible, PlayerGroupAll(), false);
        DialogControlSetPropertyAsBool(gv_mbRosterEnemyBorder[i], c_triggerControlPropertyBorderVisible, PlayerGroupAll(), true);

        gv_mbRosterEnemyIcon[i] = DialogControlCreate(gv_mbRosterDialog, c_triggerControlTypeImage);
        DialogControlSetSize(gv_mbRosterEnemyIcon[i], PlayerGroupAll(), 42, 42);
        DialogControlSetPosition(gv_mbRosterEnemyIcon[i], PlayerGroupAll(), c_anchorTopLeft, x + 3, 67);
        gv_mbRosterEnemyText[i] = DialogControlCreate(gv_mbRosterDialog, c_triggerControlTypeLabel);
        DialogControlSetSize(gv_mbRosterEnemyText[i], PlayerGroupAll(), 48, 15);
        DialogControlSetPosition(gv_mbRosterEnemyText[i], PlayerGroupAll(), c_anchorTopLeft, x, 111);
        i += 1;
    }
    DialogSetVisible(gv_mbRosterDialog, PlayerGroupAll(), false);
}

//--------------------------------------------------------------------------------------------------
// Production restrictions'''
src, n = roster_pattern.subn(lambda _m: roster_replacement, src, count=1)
if n != 1:
    raise SystemExit(f'failed to replace roster: {n}')

# -------------------------------------------------------------------------------------------------
# 5) Safe upgrade gating. Avoid the Alpha 4.3 dynamic AffectedUnitArray scan. We disable the normal
#    ladder research set explicitly, then re-open generic lines + unit-specific research for the pick.
# -------------------------------------------------------------------------------------------------
prod_anchor = '//--------------------------------------------------------------------------------------------------\n// Production restrictions\n'
if prod_anchor not in src:
    raise SystemExit('production restriction anchor missing')
upgrade_code = r'''//--------------------------------------------------------------------------------------------------
// Upgrade restrictions - explicit ladder whitelist
//--------------------------------------------------------------------------------------------------
void MB_UpgradeAllowIfValid (int player, string id, bool allowed) {
    if (CatalogEntryIsValid(c_gameCatalogUpgrade, id)) { TechTreeUpgradeAllow(player, id, allowed); }
}

void MB_UpgradeLine (int player, string prefix, bool allowed) {
    MB_UpgradeAllowIfValid(player, prefix + "Level1", allowed);
    MB_UpgradeAllowIfValid(player, prefix + "Level2", allowed);
    MB_UpgradeAllowIfValid(player, prefix + "Level3", allowed);
}

void MB_DisableStandardResearch (int p) {
    MB_UpgradeLine(p, "TerranInfantryWeapons", false);
    MB_UpgradeLine(p, "TerranInfantryArmors", false);
    MB_UpgradeLine(p, "TerranVehicleWeapons", false);
    MB_UpgradeLine(p, "TerranShipWeapons", false);
    MB_UpgradeLine(p, "TerranVehicleAndShipArmors", false);
    MB_UpgradeLine(p, "ZergMeleeWeapons", false);
    MB_UpgradeLine(p, "ZergMissileWeapons", false);
    MB_UpgradeLine(p, "ZergGroundArmors", false);
    MB_UpgradeLine(p, "ZergFlyerWeapons", false);
    MB_UpgradeLine(p, "ZergFlyerArmors", false);
    MB_UpgradeLine(p, "ProtossGroundWeapons", false);
    MB_UpgradeLine(p, "ProtossGroundArmors", false);
    MB_UpgradeLine(p, "ProtossShields", false);
    MB_UpgradeLine(p, "ProtossAirWeapons", false);
    MB_UpgradeLine(p, "ProtossAirArmors", false);

    MB_UpgradeAllowIfValid(p, "Stimpack", false);
    MB_UpgradeAllowIfValid(p, "CombatShield", false);
    MB_UpgradeAllowIfValid(p, "ConcussiveShells", false);
    MB_UpgradeAllowIfValid(p, "InfernalPreIgniter", false);
    MB_UpgradeAllowIfValid(p, "DrillingClaws", false);
    MB_UpgradeAllowIfValid(p, "SmartServos", false);
    MB_UpgradeAllowIfValid(p, "MagFieldAccelerator", false);
    MB_UpgradeAllowIfValid(p, "PersonalCloaking", false);
    MB_UpgradeAllowIfValid(p, "BansheeCloak", false);
    MB_UpgradeAllowIfValid(p, "BansheeSpeed", false);
    MB_UpgradeAllowIfValid(p, "RavenCorvidReactor", false);
    MB_UpgradeAllowIfValid(p, "BattlecruiserEnableSpecializations", false);

    MB_UpgradeAllowIfValid(p, "Burrow", false);
    MB_UpgradeAllowIfValid(p, "MetabolicBoost", false);
    MB_UpgradeAllowIfValid(p, "AdrenalGlands", false);
    MB_UpgradeAllowIfValid(p, "CentrifugalHooks", false);
    MB_UpgradeAllowIfValid(p, "GlialReconstitution", false);
    MB_UpgradeAllowIfValid(p, "TunnelingClaws", false);
    MB_UpgradeAllowIfValid(p, "MuscularAugments", false);
    MB_UpgradeAllowIfValid(p, "GroovedSpines", false);
    MB_UpgradeAllowIfValid(p, "PathogenGlands", false);
    MB_UpgradeAllowIfValid(p, "NeuralParasite", false);
    MB_UpgradeAllowIfValid(p, "ChitinousPlating", false);
    MB_UpgradeAllowIfValid(p, "AnabolicSynthesis", false);
    MB_UpgradeAllowIfValid(p, "PneumatizedCarapace", false);
    MB_UpgradeAllowIfValid(p, "OverlordTransport", false);

    MB_UpgradeAllowIfValid(p, "WarpGateResearch", false);
    MB_UpgradeAllowIfValid(p, "Charge", false);
    MB_UpgradeAllowIfValid(p, "BlinkTech", false);
    MB_UpgradeAllowIfValid(p, "AdeptPiercingAttack", false);
    MB_UpgradeAllowIfValid(p, "PsiStormTech", false);
    MB_UpgradeAllowIfValid(p, "DarkTemplarBlinkUpgrade", false);
    MB_UpgradeAllowIfValid(p, "ExtendedThermalLance", false);
    MB_UpgradeAllowIfValid(p, "GraviticBooster", false);
    MB_UpgradeAllowIfValid(p, "GraviticDrive", false);
    MB_UpgradeAllowIfValid(p, "AnionPulseCrystals", false);
    MB_UpgradeAllowIfValid(p, "VoidRaySpeedUpgrade", false);
}

bool MB_IsTerranInfantryPick44 (string u) {
    return (u == "Marine" || u == "Marauder" || u == "Reaper" || u == "Ghost");
}
bool MB_IsTerranVehiclePick44 (string u) {
    return (u == "Hellion" || u == "HellionTank" || u == "WidowMine" || u == "Cyclone" || u == "SiegeTank" || u == "Thor");
}
bool MB_IsTerranAirPick44 (string u) {
    return (u == "VikingFighter" || u == "Banshee" || u == "Raven" || u == "Battlecruiser" || u == "Liberator");
}
bool MB_IsZergMissilePick44 (string u) {
    return (u == "Roach" || u == "Ravager" || u == "Hydralisk" || u == "LurkerMP" || u == "Queen" || u == "Infestor" || u == "SwarmHostMP");
}

void MB_EnablePickResearch (int p, string pick) {
    int race = MB_UnitRace(pick);
    bool air = MB_IsAir(pick);

    if (race == MB_RACE_TERRAN) {
        if (MB_IsTerranInfantryPick44(pick)) {
            MB_UpgradeLine(p, "TerranInfantryWeapons", true);
            MB_UpgradeLine(p, "TerranInfantryArmors", true);
        }
        if (MB_IsTerranVehiclePick44(pick)) {
            MB_UpgradeLine(p, "TerranVehicleWeapons", true);
            MB_UpgradeLine(p, "TerranVehicleAndShipArmors", true);
        }
        if (MB_IsTerranAirPick44(pick) || pick == "VikingFighter") {
            MB_UpgradeLine(p, "TerranShipWeapons", true);
            MB_UpgradeLine(p, "TerranVehicleAndShipArmors", true);
        }
        if (pick == "Marine") { MB_UpgradeAllowIfValid(p, "Stimpack", true); MB_UpgradeAllowIfValid(p, "CombatShield", true); }
        if (pick == "Marauder") { MB_UpgradeAllowIfValid(p, "Stimpack", true); MB_UpgradeAllowIfValid(p, "ConcussiveShells", true); }
        if (pick == "Hellion" || pick == "HellionTank") { MB_UpgradeAllowIfValid(p, "InfernalPreIgniter", true); MB_UpgradeAllowIfValid(p, "SmartServos", true); }
        if (pick == "WidowMine") { MB_UpgradeAllowIfValid(p, "DrillingClaws", true); }
        if (pick == "Cyclone") { MB_UpgradeAllowIfValid(p, "MagFieldAccelerator", true); }
        if (pick == "Ghost") { MB_UpgradeAllowIfValid(p, "PersonalCloaking", true); }
        if (pick == "Banshee") { MB_UpgradeAllowIfValid(p, "BansheeCloak", true); MB_UpgradeAllowIfValid(p, "BansheeSpeed", true); }
        if (pick == "Raven") { MB_UpgradeAllowIfValid(p, "RavenCorvidReactor", true); }
        if (pick == "Battlecruiser") { MB_UpgradeAllowIfValid(p, "BattlecruiserEnableSpecializations", true); }
    }
    else if (race == MB_RACE_ZERG) {
        if (air) { MB_UpgradeLine(p, "ZergFlyerWeapons", true); MB_UpgradeLine(p, "ZergFlyerArmors", true); }
        else { MB_UpgradeLine(p, "ZergGroundArmors", true); }
        if (pick == "Zergling" || pick == "Baneling" || pick == "Ultralisk" || pick == "BroodLord") { MB_UpgradeLine(p, "ZergMeleeWeapons", true); }
        if (MB_IsZergMissilePick44(pick)) { MB_UpgradeLine(p, "ZergMissileWeapons", true); }
        if (!air) { MB_UpgradeAllowIfValid(p, "Burrow", true); }
        if (pick == "Zergling") { MB_UpgradeAllowIfValid(p, "MetabolicBoost", true); MB_UpgradeAllowIfValid(p, "AdrenalGlands", true); }
        if (pick == "Baneling") { MB_UpgradeAllowIfValid(p, "CentrifugalHooks", true); }
        if (pick == "Roach" || pick == "Ravager") { MB_UpgradeAllowIfValid(p, "GlialReconstitution", true); MB_UpgradeAllowIfValid(p, "TunnelingClaws", true); }
        if (pick == "Hydralisk" || pick == "LurkerMP") { MB_UpgradeAllowIfValid(p, "MuscularAugments", true); MB_UpgradeAllowIfValid(p, "GroovedSpines", true); }
        if (pick == "Infestor") { MB_UpgradeAllowIfValid(p, "PathogenGlands", true); MB_UpgradeAllowIfValid(p, "NeuralParasite", true); }
        if (pick == "Ultralisk") { MB_UpgradeAllowIfValid(p, "ChitinousPlating", true); MB_UpgradeAllowIfValid(p, "AnabolicSynthesis", true); }
        // Shared Overlord support remains useful regardless of the main pick.
        MB_UpgradeAllowIfValid(p, "PneumatizedCarapace", true);
        MB_UpgradeAllowIfValid(p, "OverlordTransport", true);
    }
    else {
        MB_UpgradeLine(p, "ProtossShields", true);
        if (air) { MB_UpgradeLine(p, "ProtossAirWeapons", true); MB_UpgradeLine(p, "ProtossAirArmors", true); }
        else { MB_UpgradeLine(p, "ProtossGroundWeapons", true); MB_UpgradeLine(p, "ProtossGroundArmors", true); }
        if (pick == "Zealot") { MB_UpgradeAllowIfValid(p, "Charge", true); MB_UpgradeAllowIfValid(p, "WarpGateResearch", true); }
        if (pick == "Stalker") { MB_UpgradeAllowIfValid(p, "BlinkTech", true); MB_UpgradeAllowIfValid(p, "WarpGateResearch", true); }
        if (pick == "Sentry" || pick == "HighTemplar" || pick == "DarkTemplar" || pick == "Adept") { MB_UpgradeAllowIfValid(p, "WarpGateResearch", true); }
        if (pick == "Adept") { MB_UpgradeAllowIfValid(p, "AdeptPiercingAttack", true); }
        if (pick == "HighTemplar") { MB_UpgradeAllowIfValid(p, "PsiStormTech", true); }
        if (pick == "DarkTemplar") { MB_UpgradeAllowIfValid(p, "DarkTemplarBlinkUpgrade", true); }
        if (pick == "Colossus") { MB_UpgradeAllowIfValid(p, "ExtendedThermalLance", true); }
        if (pick == "Phoenix") { MB_UpgradeAllowIfValid(p, "AnionPulseCrystals", true); }
        if (pick == "VoidRay") { MB_UpgradeAllowIfValid(p, "VoidRaySpeedUpgrade", true); }
        // Shared Observer/Warp Prism support upgrades remain available.
        MB_UpgradeAllowIfValid(p, "GraviticBooster", true);
        MB_UpgradeAllowIfValid(p, "GraviticDrive", true);
    }
}

void MB_ApplyUpgradeRestrictionsForPlayer (int p) {
    if (!MB_PlayerActive(p) || gv_mbUnit[p] == "") { return; }
    MB_DisableStandardResearch(p);
    MB_EnablePickResearch(p, gv_mbUnit[p]);
}

void MB_ApplyUpgradeRestrictionsAll () {
    int p = 1;
    while (p <= 8) { MB_ApplyUpgradeRestrictionsForPlayer(p); p += 1; }
}

'''
src = src.replace(prod_anchor, upgrade_code + prod_anchor, 1)

finish_marker = '    MB_ApplyProductionRestrictionsAll();\n'
if finish_marker not in src:
    raise SystemExit('finish production call missing')
src = src.replace(finish_marker, finish_marker + '    MB_ApplyUpgradeRestrictionsAll();\n', 1)

# -------------------------------------------------------------------------------------------------
# 6) Focus layer is full-screen and deliberately abstract: dark navy, no copied starfield/artwork.
# -------------------------------------------------------------------------------------------------
src = src.replace(
    'DialogControlSetPropertyAsColor(gv_mbFocusPanel, c_triggerControlPropertyColor, PlayerGroupAll(), Color(0.0, 0.0, 0.0));',
    'DialogControlSetPropertyAsColor(gv_mbFocusPanel, c_triggerControlPropertyColor, PlayerGroupAll(), Color(1.0, 4.0, 8.0));',
    1,
)

# Remove stale explanatory copy inherited from early alphas.
src = src.replace('StringToText("20초 동안 자유롭게 표를 바꿀 수 있습니다")', 'StringToText("")')
src = src.replace('StringToText("종족을 고르는 즉시 유닛이 확정됩니다")', 'StringToText("")')

# Structural guards.
required = [
    'int[24] gv_mbSDFrame',
    'void MB_CreateVoteUI ()',
    'TextWithColor(StringToText("GAME MODE")',
    'void MB_CreateBlindUI ()',
    'TextWithColor(StringToText("SELECT RACE")',
    'gv_mbSDFrame[i] = DialogControlCreate',
    'DialogControlSetVisible(gv_mbSDIcon[i]',
    'void MB_CreateRosterUI ()',
    'PlayerGetColorIndex(targetPlayer, false)',
    'void MB_ApplyUpgradeRestrictionsAll ()',
    'MB_ApplyUpgradeRestrictionsAll();',
]
for marker in required:
    if marker not in src:
        raise SystemExit(f'Alpha 4.4 marker missing: {marker}')

# The broken Alpha 4.3 dynamic catalog-field scanner must not return.
for forbidden in ('CatalogFieldValueCount(c_gameCatalogUpgrade', 'MB_UpgradeAffectsRelatedUnit'):
    if forbidden in src:
        raise SystemExit(f'Alpha 4.4 forbidden legacy upgrade scanner remains: {forbidden}')

# Galaxy string literal safety.
in_string = False
escaped = False
for pos, ch in enumerate(src):
    if ch == '\n' and in_string:
        raise SystemExit(f'raw newline inside Galaxy string literal near character {pos}')
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
print('Alpha 4.4 prepared: reference-informed original UI + reliable SD art + compact roster + safe upgrade whitelist')
