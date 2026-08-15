from pathlib import Path
import runpy
import re

# First generate the Alpha 3 source (pick-matched starting race + icon SD UI).
runpy.run_path('tools/prepare_alpha3.py', run_name='__main__')

path = Path('build/MapScript.galaxy')
src = path.read_text(encoding='utf-8')

# With starting units now created only AFTER selection, there is nothing to pause during
# vote/draft. Removing UnitPauseAll keeps pre-game selection independent of world units.
src = src.replace('    UnitPauseAll(true);\n', '')
src = src.replace('    UnitPauseAll(false);\n', '')

# Keep vote initialization simple for runtime QA. Personal "my selection" highlighting can be
# reintroduced once the rest of Alpha 3 is stable.
pattern = re.compile(
    r'    while \(p <= 8\) \{ gv_mbVote\[p\] = MB_MODE_NONE; MB_ResetVoteButtonTextFor\(p\); p \+= 1; \}\n'
)
replacement = '''    while (p <= 8) {
        gv_mbVote[p] = MB_MODE_NONE;
        p += 1;
    }
    DialogControlSetPropertyAsText(gv_mbVoteBlindButton, c_triggerControlPropertyText, PlayerGroupAll(),
        StringToText("BLIND RANDOM\\n종족 선택 + 즉시 추첨"));
    DialogControlSetPropertyAsText(gv_mbVoteSDButton, c_triggerControlPropertyText, PlayerGroupAll(),
        StringToText("SINGLE DRAFT\\n24개 후보 드래프트"));
'''
# Use a callable replacement so Python's regex engine does NOT reinterpret \\n as a real newline.
src, n = pattern.subn(lambda _m: replacement, src, count=1)
if n != 1:
    raise SystemExit(f'failed to replace reported vote-reset site: {n}')

src = src.replace(' MB_ResetVoteButtonTextFor(p);', '')
src = src.replace('MB_ResetVoteButtonTextFor(p); ', '')


def escape_raw_newlines_inside_strings(text: str) -> str:
    """Galaxy string literals may contain \\n escapes, but not literal source newlines.

    Some earlier re.sub replacements converted \\n to an actual newline inside quotes, which caused
    the SC2 parser to lose synchronization and report dozens of later lines as compile errors.
    """
    out = []
    in_string = False
    escaped = False
    line_comment = False
    i = 0
    while i < len(text):
        ch = text[i]

        if line_comment:
            out.append(ch)
            if ch == '\n':
                line_comment = False
            i += 1
            continue

        if not in_string and ch == '/' and i + 1 < len(text) and text[i + 1] == '/':
            out.append('//')
            line_comment = True
            i += 2
            continue

        if in_string:
            if ch == '\n':
                out.append('\\n')
                escaped = False
                i += 1
                continue
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == '\\':
                escaped = True
            elif ch == '"':
                in_string = False
            i += 1
            continue

        out.append(ch)
        if ch == '"':
            in_string = True
            escaped = False
        i += 1

    if in_string:
        raise SystemExit('unterminated Galaxy string literal after newline sanitization')
    return ''.join(out)


src = escape_raw_newlines_inside_strings(src)

# Validate that no source newline remains inside a quoted string.
def has_raw_string_newline(text: str) -> bool:
    in_string = False
    escaped = False
    line_comment = False
    i = 0
    while i < len(text):
        ch = text[i]
        if line_comment:
            if ch == '\n':
                line_comment = False
            i += 1
            continue
        if not in_string and ch == '/' and i + 1 < len(text) and text[i + 1] == '/':
            line_comment = True
            i += 2
            continue
        if in_string:
            if ch == '\n':
                return True
            if escaped:
                escaped = False
            elif ch == '\\':
                escaped = True
            elif ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
        i += 1
    return False


if has_raw_string_newline(src):
    raise SystemExit('raw newline remains inside a Galaxy string literal')
if 'UnitPauseAll(' in src:
    raise SystemExit('Alpha 3.2 must not call UnitPauseAll during pre-game selection')
if 'MB_ResetVoteButtonTextFor(p)' in src:
    raise SystemExit('Alpha 3.2 must not call the temporary vote-label helper')
for marker in ('MB_InitStartingUnitsAll', 'MeleeInitUnitsForPlayer', 'PlayerSetRace', 'MB_UnitIcon', 'gv_mbSDNameLabel'):
    if marker not in src:
        raise SystemExit(f'Alpha 3 functionality regressed: {marker}')

path.write_text(src, encoding='utf-8', newline='\n')
print('Alpha 3.2 prepared: raw Galaxy string newlines fixed and validated')
