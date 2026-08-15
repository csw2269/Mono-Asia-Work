from pathlib import Path

source_path = Path('tools/prepare_alpha43.py')
script = source_path.read_text(encoding='utf-8')

# Alpha 4.3 originally inserted upgrade_code before replacing the legacy roster block.
# The roster regex ends at the Production restrictions header and therefore swallowed that insert.
# Move the insertion to AFTER the roster replacement, without duplicating the large Alpha 4.3 source.
early = "src = src.replace(prod_anchor, upgrade_code + prod_anchor, 1)\n\n# Apply the upgrade whitelist"
if early not in script:
    raise SystemExit('Alpha 4.3 early upgrade insertion anchor missing')
script = script.replace(early, "# Upgrade code is inserted after the roster replacement below.\n\n# Apply the upgrade whitelist", 1)

late_anchor = "if n != 1:\n    raise SystemExit(f'failed to replace running roster UI: {n}')\n\n# -------------------------------------------------------------------------------------------------\n# Guards"
if late_anchor not in script:
    raise SystemExit('Alpha 4.3 roster completion anchor missing')
script = script.replace(
    late_anchor,
    "if n != 1:\n    raise SystemExit(f'failed to replace running roster UI: {n}')\n\n"
    "# Insert upgrade restrictions only after the old roster block has been replaced.\n"
    "if prod_anchor not in src:\n"
    "    raise SystemExit('production restriction anchor missing after roster replacement')\n"
    "src = src.replace(prod_anchor, upgrade_code + prod_anchor, 1)\n\n"
    "# -------------------------------------------------------------------------------------------------\n# Guards",
    1,
)

compiled = compile(script, 'tools/prepare_alpha43.py[ordered]', 'exec')
exec(compiled, {'__name__': '__main__', '__file__': str(source_path)})
print('Alpha 4.3.1 preparation order fixed')
