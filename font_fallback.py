"""Per-character Unicode fallback for the existing monochrome title masks."""
from functools import lru_cache
from pathlib import Path
from fontTools.ttLib import TTFont
from PIL import ImageFont

DEFAULT_FALLBACKS = ('C:/Windows/Fonts/seguisym.ttf', 'C:/Windows/Fonts/seguiemj.ttf')

@lru_cache(maxsize=64)
def coverage(path, index=0):
    with TTFont(path, fontNumber=index, lazy=True) as font:
        return frozenset((font.getBestCmap() or {}).keys())

@lru_cache(maxsize=128)
def load_font(path, size):
    return ImageFont.truetype(path, size)

def normalize_text(text):
    # The title material is monochrome; presentation selectors do not get spacing.
    if '\u200d' in text:
        raise ValueError('Joined emoji sequences are not supported by the title layout. Use a single symbol/emoji instead.')
    return text.replace('\ufe0e', '').replace('\ufe0f', '')

@lru_cache(maxsize=1024)
def fallback_path(primary, index, paths, ch):
    if ord(ch) in coverage(primary, index):
        return primary
    for path in paths:
        if Path(path).is_file() and ord(ch) in coverage(path):
            print(f'Font fallback: U+{ord(ch):04X} -> {Path(path).name}', flush=True)
            return path
    raise ValueError(f'No configured font contains U+{ord(ch):04X}. Add a supporting font to typography.fallback_fonts.')

def line_fonts(line, primary, typography, root, size):
    paths = [typography.get('fallback_font', '')] + list(typography.get('fallback_fonts', DEFAULT_FALLBACKS))
    paths = tuple(str((Path(root) / p).resolve()) for p in paths if p)
    primary_path = str(Path(primary.path).resolve())
    fonts = []
    for ch in line:
        selected = fallback_path(primary_path, primary.index, paths, ch)
        fonts.append(primary if selected == primary_path else load_font(selected, size))
    return fonts
