"""Three simple overrides. Advanced settings are never rewritten."""
import copy
import hashlib
import json
from pathlib import Path
import unicodedata

FIELDS={'portrait_image','display_name','opening_letter'}

def read_json(path):
    try: return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except json.JSONDecodeError as exc: raise ValueError(f'{Path(path).name}: invalid JSON near line {exc.lineno}. Check commas, quotes and Windows path backslashes.') from exc
    except OSError as exc: raise ValueError(f'Cannot open {path}. Restore this configuration file before rendering.') from exc

def apply_user_settings(advanced,root,user_path=None):
    root=Path(root).resolve(); path=Path(user_path) if user_path else root/'user_config.json'
    u=read_json(path)
    if not isinstance(u,dict) or set(u)!=FIELDS:
        raise ValueError('user_config.json must contain only portrait_image, display_name and opening_letter.')
    for key in FIELDS:
        if not isinstance(u[key],str) or not u[key].strip(): raise ValueError(f'user_config.json: {key} must be non-empty text.')
    letter=u['opening_letter'].strip()
    if len(letter)!=1 or unicodedata.category(letter)[0] not in ('L','N'):
        raise ValueError('user_config.json: opening_letter must be exactly one letter or digit, for example D.')
    source=Path(u['portrait_image']).expanduser()
    if not source.is_absolute(): source=root/source
    source=source.resolve()
    if not source.is_file(): raise ValueError(f'Portrait image not found: {source}. Put the image in assets and correct portrait_image in user_config.json.')
    from PIL import Image
    try:
        with Image.open(source) as im: im.verify()
    except Exception as exc: raise ValueError(f'Cannot read portrait image {source.name}. Use a valid PNG, JPG or JPEG image.') from exc
    c=copy.deepcopy(advanced)
    old_image=(root/advanced['portrait']['image']).resolve()
    c['portrait']['image']=str(source)
    if source!=old_image:
        c['portrait']['subject_polygon']=None
        c['portrait']['mask']=None
    sidecar=source.with_name(source.stem+'.mask.png')
    if sidecar.exists(): c['portrait']['mask']=str(sidecar); c['portrait']['subject_polygon']=None
    old_name=c['titles'][0]['text']
    c['titles'][0]['text']=u['display_name'].strip()
    # Existing cards repeating the main person's name are name bindings, not independent credits.
    for card in c['titles'][1:]:
        if old_name and card['text']==old_name: card['text']=u['display_name'].strip()
    c['opening']['letter']=letter
    return c

def fingerprint(c):
    return hashlib.sha256(json.dumps(c,sort_keys=True).encode()).hexdigest()
