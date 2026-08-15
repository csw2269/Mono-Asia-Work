from pathlib import Path
import runpy
import re

runpy.run_path('tools/prepare_alpha33.py', run_name='__main__')
path = Path('build/MapScript.galaxy')
src = path.read_text(encoding='utf-8')

# Known Void-era button-id exceptions: use the actual unit textures directly so these never fall
# back to empty blue buttons when a train-button catalog id differs from the unit id.
icon_old = '''string MB_UnitIcon (string unitId) {
    string buttonId = MB_UnitButtonId(unitId);
    if (!CatalogEntryIsValid(c_gameCatalogButton, buttonId)) {
        return "";
    }
    return CatalogFieldValueGet(c_gameCatalogButton, buttonId, "Icon", c_playerAny);
}'''
icon_new = '''string MB_UnitIcon (string unitId) {
    string buttonId;
    if (unitId == "Adept") { return "Assets\\Textures\\btn-unit-protoss-adept.dds"; }
    if (unitId == "Disruptor") { return "Assets\\Textures\\btn-unit-protoss-disruptor.dds"; }
    buttonId = MB_UnitButtonId(unitId);
    if (!CatalogEntryIsValid(c_gameCatalogButton, buttonId)) {
        return "";
    }
    return CatalogFieldValueGet(c_gameCatalogButton, buttonId, "Icon", c_playerAny);
}'''
if icon_old not in src:
    raise SystemExit('Alpha 3.3 icon helper not found')
src = src.replace(icon_old, icon_new, 1)

# Compact roster label: the user primarily needs to know which player slot owns which Monobattle
# unit. Removing the full Battle.net name prevents truncation on Korean UI / long names.
old_label = 'text label = StringToText("P" + IntToString(targetPlayer) + "  " + TextToString(PlayerName(targetPlayer)) + "  ·  " + MB_DisplayName(gv_mbUnit[targetPlayer]));'
new_label = 'text label = StringToText("P" + IntToString(targetPlayer) + "  ·  " + MB_DisplayName(gv_mbUnit[targetPlayer]));'
if old_label not in src:
    raise SystemExit('roster label anchor not found')
src = src.replace(old_label, new_label, 1)

# Make the roster slightly less intrusive while preserving room for four rows on both sides.
src = src.replace('DialogCreate(570, 235, c_anchorTop, 0, 72, false)', 'DialogCreate(540, 225, c_anchorTop, 0, 62, false)', 1)
src = src.replace('DialogControlSetSize(gv_mbRosterTitle, PlayerGroupAll(), 530, 28);', 'DialogControlSetSize(gv_mbRosterTitle, PlayerGroupAll(), 500, 28);', 1)
src = src.replace('DialogControlSetSize(gv_mbRosterAllyHeader, PlayerGroupAll(), 245, 24);', 'DialogControlSetSize(gv_mbRosterAllyHeader, PlayerGroupAll(), 230, 24);', 1)
src = src.replace('DialogControlSetSize(gv_mbRosterEnemyHeader, PlayerGroupAll(), 245, 24);', 'DialogControlSetSize(gv_mbRosterEnemyHeader, PlayerGroupAll(), 230, 24);', 1)
src = src.replace('c_anchorTopLeft, 302, 42', 'c_anchorTopLeft, 284, 42', 1)
src = src.replace('c_anchorTopLeft, 302, y', 'c_anchorTopLeft, 284, y')
src = src.replace('c_anchorTopLeft, 340, y', 'c_anchorTopLeft, 322, y')
src = src.replace('DialogControlSetSize(gv_mbRosterAllyText[i], PlayerGroupAll(), 220, 32);', 'DialogControlSetSize(gv_mbRosterAllyText[i], PlayerGroupAll(), 205, 32);', 1)
src = src.replace('DialogControlSetSize(gv_mbRosterEnemyText[i], PlayerGroupAll(), 220, 32);', 'DialogControlSetSize(gv_mbRosterEnemyText[i], PlayerGroupAll(), 205, 32);', 1)

# Transport-only Medivac support. The support unit itself remains buildable, but combat-support
# abilities are disabled per player; load/unload transport abilities remain untouched.
support_anchor = '//--------------------------------------------------------------------------------------------------\n// Production restrictions\n'
if support_anchor not in src:
    raise SystemExit('production section anchor missing')
support_code = r'''//--------------------------------------------------------------------------------------------------
// Shared support-unit rules
//--------------------------------------------------------------------------------------------------
void MB_ApplySupportRulesFor (int p) {
    // Medivac is a transport support unit in Monobattle. Healing and Ignite Afterburners are off;
    // Load/Unload are intentionally left available.
    if (CatalogEntryIsValid(c_gameCatalogAbil, "MedivacHeal")) {
        TechTreeAbilityAllow(p, AbilityCommand("MedivacHeal", 0), false);
    }
    if (CatalogEntryIsValid(c_gameCatalogAbil, "MedivacSpeedBoost")) {
        TechTreeAbilityAllow(p, AbilityCommand("MedivacSpeedBoost", 0), false);
    }
}

void MB_ApplySupportRulesAll () {
    int p = 1;
    while (p <= 8) {
        if (MB_PlayerActive(p)) { MB_ApplySupportRulesFor(p); }
        p += 1;
    }
}

'''
src = src.replace(support_anchor, support_code + support_anchor, 1)

finish_anchor = '    MB_ApplyProductionRestrictionsAll();\n    MB_UpdateRosterAll();\n'
if finish_anchor not in src:
    raise SystemExit('finish-selection rules anchor missing')
src = src.replace(finish_anchor, '    MB_ApplyProductionRestrictionsAll();\n    MB_ApplySupportRulesAll();\n    MB_UpdateRosterAll();\n', 1)

for marker in (
    'btn-unit-protoss-adept.dds', 'btn-unit-protoss-disruptor.dds',
    'MB_ApplySupportRulesAll', 'MedivacHeal', 'MedivacSpeedBoost',
    'P" + IntToString(targetPlayer) + "  ·  " + MB_DisplayName'
):
    if marker not in src:
        raise SystemExit(f'Alpha 3.4 marker missing: {marker}')

# Keep the no-raw-newline Galaxy-string guard.
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
print('Alpha 3.4 prepared: Adept/Disruptor icons + compact roster + transport-only Medivac')
