from pathlib import Path
import runpy

# Start from Alpha 3.4 (icons, compact roster, Medivac support rules, team victory logic).
runpy.run_path('tools/prepare_alpha34.py', run_name='__main__')

path = Path('build/MapScript.galaxy')
src = path.read_text(encoding='utf-8')

# Alpha 3.4 generated one literal backslash in these two Galaxy strings because Python consumed
# one escaping layer first. Galaxy then reads sequences such as \T as invalid escapes.
# Replace the final packaged source with TWO backslashes per path separator.
bad_adept = r'return "Assets\Textures\btn-unit-protoss-adept.dds";'
bad_disruptor = r'return "Assets\Textures\btn-unit-protoss-disruptor.dds";'
good_adept = r'return "Assets\\Textures\\btn-unit-protoss-adept.dds";'
good_disruptor = r'return "Assets\\Textures\\btn-unit-protoss-disruptor.dds";'

if bad_adept not in src:
    raise SystemExit('Alpha 3.5 could not find the Adept path that needs escaping')
if bad_disruptor not in src:
    raise SystemExit('Alpha 3.5 could not find the Disruptor path that needs escaping')

src = src.replace(bad_adept, good_adept, 1)
src = src.replace(bad_disruptor, good_disruptor, 1)

# Verify the FINAL Galaxy source, not the Python template.
if good_adept not in src or good_disruptor not in src:
    raise SystemExit('escaped unit icon paths were not emitted into final Galaxy source')
if bad_adept in src or bad_disruptor in src:
    raise SystemExit('single-backslash unit icon path remains in final Galaxy source')

# Keep earlier string-literal structural guard.
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
print('Alpha 3.5 prepared: final Galaxy texture paths contain escaped backslashes')
