from pathlib import Path
import runpy

runpy.run_path('tools/prepare_alpha35.py', run_name='__main__')
path = Path('build/MapScript.galaxy')
src = path.read_text(encoding='utf-8')

# Temporary QA-only acceleration. Keep all values isolated so the entire block can be removed
# before balancing/release.
anchor = '//--------------------------------------------------------------------------------------------------\n// Production restrictions\n'
if anchor not in src:
    raise SystemExit('production section anchor missing')

test_boost = r'''//--------------------------------------------------------------------------------------------------
// TEST BOOST - QA ONLY, REMOVE BEFORE RELEASE
//--------------------------------------------------------------------------------------------------
void MB_TestSpeedAbility (int p, string abilId) {
    int i;
    int count;
    string field;
    string oldValue;
    fixed oldTime;
    fixed newTime;

    if (!CatalogEntryIsValid(c_gameCatalogAbil, abilId)) { return; }
    count = CatalogFieldValueCount(c_gameCatalogAbil, abilId, "InfoArray", p);
    i = 0;
    while (i < count) {
        field = "InfoArray[" + IntToString(i) + "].Time";
        oldValue = CatalogFieldValueGet(c_gameCatalogAbil, abilId, field, p);
        if (oldValue != "") {
            oldTime = StringToFixed(oldValue);
            if (oldTime > 0.0) {
                newTime = oldTime * 0.20;
                if (newTime < 1.0) { newTime = 1.0; }
                CatalogFieldValueSet(c_gameCatalogAbil, abilId, field, p, FixedToString(newTime, 3));
            }
        }
        i += 1;
    }
}

void MB_ApplyTestBoostFor (int p) {
    if (!MB_PlayerActive(p)) { return; }

    // Huge temporary economy and no practical supply bottleneck.
    PlayerModifyPropertyInt(p, c_playerPropMinerals, c_playerPropOperSetTo, 10000);
    PlayerModifyPropertyInt(p, c_playerPropVespene, c_playerPropOperSetTo, 10000);
    PlayerModifyPropertyInt(p, c_playerPropSuppliesLimit, c_playerPropOperSetTo, 200);
    PlayerModifyPropertyInt(p, c_playerPropSuppliesMade, c_playerPropOperSetTo, 200);

    // Main melee train queues.
    MB_TestSpeedAbility(p, "BarracksTrain");
    MB_TestSpeedAbility(p, "FactoryTrain");
    MB_TestSpeedAbility(p, "StarportTrain");
    MB_TestSpeedAbility(p, "LarvaTrain");
    MB_TestSpeedAbility(p, "QueenTrain");
    MB_TestSpeedAbility(p, "GatewayTrain");
    MB_TestSpeedAbility(p, "WarpGateTrain");
    MB_TestSpeedAbility(p, "RoboticsFacilityTrain");
    MB_TestSpeedAbility(p, "StargateTrain");

    // Selected-unit morph/merge paths. Invalid ids are ignored safely.
    MB_TestSpeedAbility(p, "MorphToBaneling");
    MB_TestSpeedAbility(p, "MorphToRavager");
    MB_TestSpeedAbility(p, "MorphToLurker");
    MB_TestSpeedAbility(p, "MorphToBroodLord");
    MB_TestSpeedAbility(p, "MorphToHellionTank");
    MB_TestSpeedAbility(p, "ArchonWarp");
    MB_TestSpeedAbility(p, "HighTemplarArchon");
    MB_TestSpeedAbility(p, "DarkTemplarArchon");
}

void MB_ApplyTestBoostAll () {
    int p = 1;
    while (p <= 8) {
        MB_ApplyTestBoostFor(p);
        p += 1;
    }
    UIDisplayMessage(PlayerGroupAll(), c_messageAreaSubtitle,
        StringToText("TEST BOOST · 광물/가스 10000 · 보급 200 · 생산/변태 시간 20%"));
}

'''
src = src.replace(anchor, test_boost + anchor, 1)

finish_anchor = '    MB_ApplySupportRulesAll();\n    MB_UpdateRosterAll();\n'
if finish_anchor not in src:
    raise SystemExit('finish selection anchor missing')
src = src.replace(finish_anchor,
    '    MB_ApplySupportRulesAll();\n    MB_ApplyTestBoostAll();\n    MB_UpdateRosterAll();\n', 1)

for marker in (
    'MB_ApplyTestBoostAll', 'PlayerModifyPropertyInt', 'c_playerPropMinerals',
    'c_playerPropVespene', 'c_playerPropSuppliesLimit', 'CatalogFieldValueCount',
    'CatalogFieldValueGet', 'CatalogFieldValueSet', 'oldTime * 0.20', 'BarracksTrain',
    'LarvaTrain', 'GatewayTrain', 'RoboticsFacilityTrain', 'StargateTrain'
):
    if marker not in src:
        raise SystemExit(f'Alpha 3.6 test marker missing: {marker}')

path.write_text(src, encoding='utf-8', newline='\n')
print('Alpha 3.6 prepared: QA resources/supply and 20% train-morph times')
