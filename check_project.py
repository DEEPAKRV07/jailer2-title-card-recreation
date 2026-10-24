"""Small behavioral checks: source identity, independent titles and deterministic rendering."""
import copy, hashlib, json
from pathlib import Path
import numpy as np
from renderer import Renderer
from main import load

ROOT=Path(__file__).resolve().parent
c=load(ROOT/'config.json'); tests={}
r=Renderer(c,ROOT,640)
a=r.frame(7.8); b=r.frame(7.8)
tests['repeat_frame_is_deterministic']=np.array_equal(a,b)
changed=copy.deepcopy(c); changed['opening']['letter']='Q'; changed['titles'][0]['text']='DIFFERENT NAME'
r2=Renderer(changed,ROOT,640)
tests['changing_text_does_not_change_portrait']=np.array_equal(r.portrait,r2.portrait) and np.array_equal(r.frame(9.6),r2.frame(9.6))
tests['no_flat_rectangular_photo_background']=float(r.portrait[:,:40].max())==0 and float(r.portrait[:,-40:].max())==0
early=r.portrait_frame(2.4); middle=r.portrait_frame(4); end=r.portrait_frame(5.8)
# Total luma can fall as bright flying particles settle. Test that recognizable source
# structure grows instead of incorrectly requiring ever-increasing global exposure.
scores=[np.corrcoef(r.portrait.ravel(),f.ravel())[0,1] for f in [early,middle,end]]
tests['reveal_accumulates_subject_structure']=scores[0]<scores[1]<scores[2]
tests['finite_image_values']=bool(np.isfinite(r.portrait).all())
tests['title_changes_visible_letter']=not np.array_equal(r.frame(2.9),r2.frame(2.9))
source=ROOT/'assets/portrait.jpeg'; original=ROOT.parent/'title_card_reference_upload_pack/karthi-jailer2.jpeg'
if original.exists(): tests['portrait_source_bytes_preserved']=hashlib.sha256(source.read_bytes()).digest()==hashlib.sha256(original.read_bytes()).digest()
tests={key:bool(value) for key,value in tests.items()}
(ROOT/'qa/project_checks.json').write_text(json.dumps(tests,indent=2))
print(tests)
assert all(tests.values()),'Project behavioral checks failed'
