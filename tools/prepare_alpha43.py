from pathlib import Path
import runpy
import re

# Build on Alpha 4.2: names-only mode UI, focus mask, stable TEST morph patch.
runpy.run_path('tools/prepare_alpha42.py', run_name='__main__')
path = Path('build/MapScript.galaxy')
src = path.read_text(encoding='utf-8')

# -------------------------------------------------------------------------------------------------
# 1) Restore SD unit art while retaining the native SC2 CommandButton frame.
#    Alpha 4.2 switched the click control to CommandButtonTemplate, but that template owns its icon
#    in a child frame and does not render c_triggerControlPropertyImage like a plain Button.
#    Keep the production-button frame BEHIND a dedicated image control, which was already proven
#    reliable in Alpha 3.9-4.1.
# -------------------------------------------------------------------------------------------------
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

        // CommandButton supplies the familiar production-button border/background.
        // The dedicated image supplies the actual unit art without relying on template child frames.
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

        DialogControlSetPropertyAsBool(gv_mbSDIcon[i], c_triggerControlPropertyDesaturated, PlayerGroupAll(), gv_mbSDTaken[i]);
        DialogControlSetEnabled(gv_mbSDButton[i], PlayerGroupAll(), !gv_mbSDTaken[i]);
        i += 1;
    }
}

void MB_SDUpdateOrderText'''
src, n = update_pattern.subn(lambda _m: update_replacement, src, count=1)
if n != 1:
    raise SystemExit(f'failed to restore SD art updater: {n}')

# Put a 62x62 icon inside the 76x76 native command-button frame.
old_icon_geometry = '''        gv_mbSDIcon[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeImage);
        DialogControlSetSize(gv_mbSDIcon[i], PlayerGroupAll(), 58, 58);
        DialogControlSetPosition(gv_mbSDIcon[i], PlayerGroupAll(), c_anchorTopLeft, x + 22, y + 5);
        DialogControlSetPropertyAsInt(gv_mbSDIcon[i], c_triggerControlPropertyImageType, PlayerGroupAll(), c_triggerImageTypeNormal);
'''
new_icon_geometry = '''        gv_mbSDIcon[i] = DialogControlCreate(gv_mbSDDialog, c_triggerControlTypeImage);
        DialogControlSetSize(gv_mbSDIcon[i], PlayerGroupAll(), 62, 62);
        DialogControlSetPosition(gv_mbSDIcon[i], PlayerGroupAll(), c_anchorTopLeft, x + 20, y + 7);
        DialogControlSetPropertyAsInt(gv_mbSDIcon[i], c_triggerControlPropertyImageType, PlayerGroupAll(), c_triggerImageTypeNormal);
'''
if old_icon_geometry not in src:
    raise SystemExit('SD icon geometry anchor missing')
src = src.replace(old_icon_geometry, new_icon_geometry, 1)

# -------------------------------------------------------------------------------------------------
# 2) Upgrade gating. Disable research globally for each player, then re-enable only upgrades that
#    are relevant to the selected Monobattle unit, its generated combat units, or shared support.
#    Specific unit upgrades are detected through Upgrade.AffectedUnitArray at runtime.
# -------------------------------------------------------------------------------------------------
prod_anchor = '//--------------------------------------------------------------------------------------------------\n// Production restrictions\n'
if prod_anchor not in src:
    raise SystemExit('production restriction anchor missing')
upgrade_code = r'''//--------------------------------------------------------------------------------------------------
// Upgrade restrictions
//--------------------------------------------------------------------------------------------------
bool MB_IsSharedSupportUnit (string u) {
    return (u == "Medivac" || u == "Overlord" || u == "Overseer" ||
            u == "Observer" || u == "ObserverSiegeMode" ||
            u == "WarpPrism" || u == "WarpPrismPhasing");
}

bool MB_IsGeneratedForPick (string pick, string u) {
    if (pick == "Carrier" && u == "Interceptor") { return true; }
    if (pick == "BroodLord" && (u == "Broodling" || u == "BroodlingEscort")) { return true; }
    if (pick == "SwarmHostMP" && (u == "LocustMP" || u == "LocustMPFlying")) { return true; }
    if (pick == "Raven" && (u == "AutoTurret" || u == "PointDefenseDrone")) { return true; }
    return false;
}

bool MB_UpgradeAffectsRelatedUnit (int player, string upgradeId, string pick) {
    int i = 0;
    int count;
    string u;
    if (!CatalogEntryIsValid(c_gameCatalogUpgrade, upgradeId)) { return false; }
    count = CatalogFieldValueCount(c_gameCatalogUpgrade, upgradeId, "AffectedUnitArray", player);
    while (i < count) {
        u = CatalogFieldValueGet(c_gameCatalogUpgrade, upgradeId,
            "AffectedUnitArray[" + IntToString(i) + "]", player);
        if (u == pick || MB_IsSharedSupportUnit(u) || MB_IsGeneratedForPick(pick, u)) { return true; }
        i += 1;
    }
    return false;
}

void MB_AllowUpgradeIfValid (int player, string upgradeId) {
    if (CatalogEntryIsValid(c_gameCatalogUpgrade, upgradeId)) {
        TechTreeUpgradeAllow(player, upgradeId, true);
    }
}

void MB_AllowThreeLevelLine (int player, string prefix) {
    MB_AllowUpgradeIfValid(player, prefix + "Level1");
    MB_AllowUpgradeIfValid(player, prefix + "Level2");
    MB_AllowUpgradeIfValid(player, prefix + "Level3");
}

bool MB_IsTerranInfantryPick (string u) {
    return (u == "Marine" || u == "Marauder" || u == "Reaper" || u == "Ghost");
}

bool MB_IsTerranVehiclePick (string u) {
    return (u == "Hellion" || u == "HellionTank" || u == "WidowMine" || u == "Cyclone" ||
            u == "SiegeTank" || u == "Thor" || u == "VikingFighter");
}

bool MB_IsTerranAirPick (string u) {
    return (u == "VikingFighter" || u == "Banshee" || u == "Raven" ||
            u == "Battlecruiser" || u == "Liberator");
}

bool MB_IsZergMeleePick (string u) {
    return (u == "Zergling" || u == "Baneling" || u == "Ultralisk" || u == "BroodLord");
}

bool MB_IsZergMissilePick (string u) {
    return (u == "Roach" || u == "Ravager" || u == "Hydralisk" || u == "LurkerMP" ||
            u == "Infestor" || u == "Queen" || u == "SwarmHostMP");
}

bool MB_IsGatewayPick (string u) {
    return (u == "Zealot" || u == "Stalker" || u == "Sentry" || u == "Adept" ||
            u == "HighTemplar" || u == "DarkTemplar");
}

void MB_AllowGenericCombatUpgrades (int player, string pick) {
    int race = MB_UnitRace(pick);
    bool air = MB_IsAir(pick);

    if (race == MB_RACE_TERRAN) {
        if (MB_IsTerranInfantryPick(pick)) {
            MB_AllowThreeLevelLine(player, "TerranInfantryWeapons");
            MB_AllowThreeLevelLine(player, "TerranInfantryArmors");
        }
        if (MB_IsTerranVehiclePick(pick)) {
            MB_AllowThreeLevelLine(player, "TerranVehicleWeapons");
            MB_AllowThreeLevelLine(player, "TerranVehicleAndShipArmors");
            MB_AllowThreeLevelLine(player, "TerranVehiclePlating");
        }
        if (MB_IsTerranAirPick(pick)) {
            MB_AllowThreeLevelLine(player, "TerranShipWeapons");
            MB_AllowThreeLevelLine(player, "TerranVehicleAndShipArmors");
            MB_AllowThreeLevelLine(player, "TerranShipPlating");
        }
    }
    else if (race == MB_RACE_ZERG) {
        if (air) {
            MB_AllowThreeLevelLine(player, "ZergFlyerWeapons");
            MB_AllowThreeLevelLine(player, "ZergFlyerArmors");
        }
        else {
            MB_AllowThreeLevelLine(player, "ZergGroundArmors");
        }
        if (MB_IsZergMeleePick(pick)) { MB_AllowThreeLevelLine(player, "ZergMeleeWeapons"); }
        if (MB_IsZergMissilePick(pick)) { MB_AllowThreeLevelLine(player, "ZergMissileWeapons"); }
        if (!air) { MB_AllowUpgradeIfValid(player, "Burrow"); }

        // Generated combat units also deserve their standard scaling.
        if (pick == "BroodLord") {
            MB_AllowThreeLevelLine(player, "ZergGroundArmors");
            MB_AllowThreeLevelLine(player, "ZergMeleeWeapons");
        }
        if (pick == "SwarmHostMP") {
            MB_AllowThreeLevelLine(player, "ZergGroundArmors");
        }
    }
    else {
        MB_AllowThreeLevelLine(player, "ProtossShields");
        if (air) {
            MB_AllowThreeLevelLine(player, "ProtossAirWeapons");
            MB_AllowThreeLevelLine(player, "ProtossAirArmors");
        }
        else {
            MB_AllowThreeLevelLine(player, "ProtossGroundWeapons");
            MB_AllowThreeLevelLine(player, "ProtossGroundArmors");
        }
        if (MB_IsGatewayPick(pick)) { MB_AllowUpgradeIfValid(player, "WarpGateResearch"); }
    }
}

void MB_ApplyUpgradeRestrictionsForPlayer (int player) {
    int i = 0;
    int count = CatalogEntryCount(c_gameCatalogUpgrade);
    string upgradeId;
    string pick = gv_mbUnit[player];

    if (!MB_PlayerActive(player) || pick == "") { return; }

    // First close every researchable upgrade entry. Existing researched levels are not removed.
    while (i < count) {
        upgradeId = CatalogEntryGet(c_gameCatalogUpgrade, i);
        if (CatalogEntryIsValid(c_gameCatalogUpgrade, upgradeId)) {
            TechTreeUpgradeAllow(player, upgradeId, false);
        }
        i += 1;
    }

    // Re-open upgrades whose own data explicitly lists the pick/shared support/generated unit.
    i = 0;
    while (i < count) {
        upgradeId = CatalogEntryGet(c_gameCatalogUpgrade, i);
        if (MB_UpgradeAffectsRelatedUnit(player, upgradeId, pick)) {
            TechTreeUpgradeAllow(player, upgradeId, true);
        }
        i += 1;
    }

    // Weapon/armor lines generally modify Weapon/Effect data instead of AffectedUnitArray.
    MB_AllowGenericCombatUpgrades(player, pick);
}

void MB_ApplyUpgradeRestrictionsAll () {
    int p = 1;
    while (p <= 8) {
        MB_ApplyUpgradeRestrictionsForPlayer(p);
        p += 1;
    }
}

'''
src = src.replace(prod_anchor, upgrade_code + prod_anchor, 1)

# Apply the upgrade whitelist at the same time as unit production restrictions.
finish_marker = '    MB_ApplyProductionRestrictionsAll();\n'
if finish_marker not in src:
    raise SystemExit('finish production restriction call missing')
src = src.replace(finish_marker,
                  finish_marker + '    MB_ApplyUpgradeRestrictionsAll();\n', 1)

# -------------------------------------------------------------------------------------------------
# 3) Replace the running-game text roster with replay-production-style icon rows.
#    Every unit icon is desaturated; a thin border and the P# below it use that player's actual color.
# -------------------------------------------------------------------------------------------------
roster_global_anchor = 'int[4] gv_mbRosterAllyIcon;\nint[4] gv_mbRosterAllyText;\nint[4] gv_mbRosterEnemyIcon;\nint[4] gv_mbRosterEnemyText;\n'
if roster_global_anchor not in src:
    raise SystemExit('old roster globals missing')
roster_globals = '''int[4] gv_mbRosterAllyIcon;
int[4] gv_mbRosterAllyText;
int[4] gv_mbRosterEnemyIcon;
int[4] gv_mbRosterEnemyText;
int[4] gv_mbRosterAllyBorder;
int[4] gv_mbRosterEnemyBorder;
'''
src = src.replace(roster_global_anchor, roster_globals, 1)

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

    DialogControlSetPropertyAsColor(borderControl, c_triggerControlPropertyColor, one, pc);
    DialogControlSetPropertyAsColor(textControl, c_triggerControlPropertyColor, one, pc);
    DialogControlSetPropertyAsText(textControl, c_triggerControlPropertyText, one,
        StringToText("P" + IntToString(targetPlayer)));

    if (icon != "") {
        DialogControlSetPropertyAsString(iconControl, c_triggerControlPropertyImage, one, icon);
        DialogControlSetPropertyAsInt(iconControl, c_triggerControlPropertyImageType, one, c_triggerImageTypeNormal);
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
    gv_mbRosterDialog = DialogCreate(650, 205, c_anchorTop, 0, 58, false);
    DialogSetTransparency(gv_mbRosterDialog, 16.0);

    gv_mbRosterTitle = DialogControlCreate(gv_mbRosterDialog, c_triggerControlTypeLabel);
    DialogControlSetSize(gv_mbRosterTitle, PlayerGroupAll(), 90, 28);
    DialogControlSetPosition(gv_mbRosterTitle, PlayerGroupAll(), c_anchorTopLeft, 12, 12);
    DialogControlSetPropertyAsText(gv_mbRosterTitle, c_triggerControlPropertyText, PlayerGroupAll(),
        TextWithColor(StringToText("ALLY"), Color(35.0, 75.0, 100.0)));

    gv_mbRosterAllyHeader = DialogControlCreate(gv_mbRosterDialog, c_triggerControlTypeLabel);
    DialogControlSetSize(gv_mbRosterAllyHeader, PlayerGroupAll(), 90, 28);
    DialogControlSetPosition(gv_mbRosterAllyHeader, PlayerGroupAll(), c_anchorTopLeft, 12, 105);
    DialogControlSetPropertyAsText(gv_mbRosterAllyHeader, c_triggerControlPropertyText, PlayerGroupAll(),
        TextWithColor(StringToText("ENEMY"), Color(100.0, 45.0, 35.0)));

    // Old enemy header is no longer needed; keep the control hidden for compatibility.
    DialogControlSetVisible(gv_mbRosterEnemyHeader, PlayerGroupAll(), false);

    while (i < 4) {
        x = 112 + (i * 126);

        gv_mbRosterAllyBorder[i] = DialogControlCreate(gv_mbRosterDialog, c_triggerControlTypePanel);
        DialogControlSetSize(gv_mbRosterAllyBorder[i], PlayerGroupAll(), 66, 66);
        DialogControlSetPosition(gv_mbRosterAllyBorder[i], PlayerGroupAll(), c_anchorTopLeft, x, 10);
        DialogControlSetPropertyAsBool(gv_mbRosterAllyBorder[i], c_triggerControlPropertyBackgroundVisible, PlayerGroupAll(), false);
        DialogControlSetPropertyAsBool(gv_mbRosterAllyBorder[i], c_triggerControlPropertyBorderVisible, PlayerGroupAll(), true);

        gv_mbRosterAllyIcon[i] = DialogControlCreate(gv_mbRosterDialog, c_triggerControlTypeImage);
        DialogControlSetSize(gv_mbRosterAllyIcon[i], PlayerGroupAll(), 58, 58);
        DialogControlSetPosition(gv_mbRosterAllyIcon[i], PlayerGroupAll(), c_anchorTopLeft, x + 4, 14);
        gv_mbRosterAllyText[i] = DialogControlCreate(gv_mbRosterDialog, c_triggerControlTypeLabel);
        DialogControlSetSize(gv_mbRosterAllyText[i], PlayerGroupAll(), 66, 20);
        DialogControlSetPosition(gv_mbRosterAllyText[i], PlayerGroupAll(), c_anchorTopLeft, x, 77);

        gv_mbRosterEnemyBorder[i] = DialogControlCreate(gv_mbRosterDialog, c_triggerControlTypePanel);
        DialogControlSetSize(gv_mbRosterEnemyBorder[i], PlayerGroupAll(), 66, 66);
        DialogControlSetPosition(gv_mbRosterEnemyBorder[i], PlayerGroupAll(), c_anchorTopLeft, x, 103);
        DialogControlSetPropertyAsBool(gv_mbRosterEnemyBorder[i], c_triggerControlPropertyBackgroundVisible, PlayerGroupAll(), false);
        DialogControlSetPropertyAsBool(gv_mbRosterEnemyBorder[i], c_triggerControlPropertyBorderVisible, PlayerGroupAll(), true);

        gv_mbRosterEnemyIcon[i] = DialogControlCreate(gv_mbRosterDialog, c_triggerControlTypeImage);
        DialogControlSetSize(gv_mbRosterEnemyIcon[i], PlayerGroupAll(), 58, 58);
        DialogControlSetPosition(gv_mbRosterEnemyIcon[i], PlayerGroupAll(), c_anchorTopLeft, x + 4, 107);
        gv_mbRosterEnemyText[i] = DialogControlCreate(gv_mbRosterDialog, c_triggerControlTypeLabel);
        DialogControlSetSize(gv_mbRosterEnemyText[i], PlayerGroupAll(), 66, 20);
        DialogControlSetPosition(gv_mbRosterEnemyText[i], PlayerGroupAll(), c_anchorTopLeft, x, 170);
        i += 1;
    }
    DialogSetVisible(gv_mbRosterDialog, PlayerGroupAll(), false);
}

//--------------------------------------------------------------------------------------------------
// Production restrictions'''
src, n = roster_pattern.subn(lambda _m: roster_replacement, src, count=1)
if n != 1:
    raise SystemExit(f'failed to replace running roster UI: {n}')

# -------------------------------------------------------------------------------------------------
# Guards
# -------------------------------------------------------------------------------------------------
for marker in (
    'DialogControlSetPropertyAsString(gv_mbSDIcon[i], c_triggerControlPropertyImage',
    'DialogControlSetVisible(gv_mbSDIcon[i], PlayerGroupAll(), true)',
    'void MB_ApplyUpgradeRestrictionsAll ()',
    'TechTreeUpgradeAllow(player, upgradeId, false)',
    '"AffectedUnitArray[" + IntToString(i) + "]"',
    'MB_IsSharedSupportUnit', 'MB_AllowGenericCombatUpgrades',
    'int[4] gv_mbRosterAllyBorder', 'int[4] gv_mbRosterEnemyBorder',
    'ColorFromIndex(PlayerGetColorIndex(targetPlayer, false), c_teamColorDiffuse)',
    'c_triggerControlPropertyDesaturated, one, true',
    'MB_ApplyUpgradeRestrictionsAll();'
):
    if marker not in src:
        raise SystemExit(f'Alpha 4.3 marker missing: {marker}')

# Galaxy string safety.
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
print('Alpha 4.3 prepared: SD icon recovery + selected-unit upgrade gating + replay-style roster')
