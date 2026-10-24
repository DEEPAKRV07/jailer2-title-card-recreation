"""Integration checks use temporary user files; never rewrite the real advanced/user configuration."""
import copy,hashlib,json,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from PIL import Image
from main import load
from user_settings import apply_user_settings,read_json
from generated_outputs import GeneratedOutputs
from gpu_renderer import GPURenderer

work=ROOT/'development/test cases';work.mkdir(exist_ok=True)
checks={};config_before=(ROOT/'config.json').read_bytes();user_before=(ROOT/'user_config.json').read_bytes()
asset_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'assets').iterdir() if p.is_file()}
final_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'output').glob('*.mp4')}
base=read_json(ROOT/'config.json');u=read_json(ROOT/'user_config.json');c=load(ROOT/'config.json')
checks['three_fields_applied']=c['opening']['letter']==u['opening_letter'] and c['titles'][0]['text']==u['display_name'] and Path(c['portrait']['image'])==(ROOT/u['portrait_image']).resolve()
checks['spaces_in_image_filename_work']=Path(c['portrait']['image']).is_file() and ' ' in Path(c['portrait']['image']).name
# Compared numerically: only identity bindings and mask-reset fields may differ.
for section in ['seed','presets','output','rain','particles','palette','effects','typography','audio','qa']:assert c[section]==base[section],section
for key in base['portrait']:
    if key not in ['image','mask','subject_polygon']:assert c['portrait'][key]==base['portrait'][key]
checks['advanced_animation_parameters_unchanged']=True
assert 'subject_polygon' in c['portrait'] and c['portrait']['subject_polygon'] is None
checks['old_polygon_not_reused']=True
g=GPURenderer(c,ROOT,640);first=g.frame(2.9);title=g.frame(14.5)
alt=dict(u,display_name='ALTERNATE TEST',opening_letter='Z');altpath=work/'alternate settings.json';altpath.write_text(json.dumps(alt))
other=load(ROOT/'config.json',altpath);g2=GPURenderer(other,ROOT,640)
checks['different_letter_changes_animation']=not np.array_equal(first,g2.frame(2.9))
checks['different_name_changes_title']=not np.array_equal(title,g2.frame(14.5))
checks['name_change_preserves_portrait']=np.array_equal(g.frame(9.6),g2.frame(9.6))
# A different real supplied person's image, copied only into a test fixture; alpha makes mask testing fast.
fixture=work/'Different Portrait With Spaces.png';img=Image.open(ROOT/'assets/portrait.jpeg').convert('RGBA');img.putalpha(255);img.save(fixture)
mask=Image.new('L',img.size,0);from PIL import ImageDraw
ImageDraw.Draw(mask).ellipse((img.width*.2,img.height*.03,img.width*.85,img.height*1.5),fill=255)
mask.save(fixture.with_name(fixture.stem+'.mask.png'))
portrait_user=work/'different portrait.json';portrait_user.write_text(json.dumps(dict(u,portrait_image=str(fixture))))
portrait_c=load(ROOT/'config.json',portrait_user);g3=GPURenderer(portrait_c,ROOT,640)
checks['different_image_changes_portrait']=not np.array_equal(g.frame(9.6),g3.frame(9.6))
checks['absolute_windows_path_and_sidecar_mask']=Path(portrait_c['portrait']['mask']).exists()
for name,payload in [('empty_name',dict(u,display_name='')),('two_letters',dict(u,opening_letter='AB')),('invalid_letter',dict(u,opening_letter='!')),('missing_image',dict(u,portrait_image='assets/does not exist.png'))]:
    path=work/(name+'.json');path.write_text(json.dumps(payload))
    try:load(ROOT/'config.json',path);checks[name+'_readable_error']=False
    except ValueError as exc:checks[name+'_readable_error']=len(str(exc))>20
invalid=work/'invalid.json';invalid.write_text('{broken json')
try:load(ROOT/'config.json',invalid);checks['invalid_json_readable_error']=False
except ValueError as exc:checks['invalid_json_readable_error']='invalid JSON' in str(exc)
# Actual preview runs twice. Unknown files in the output directories must survive.
sentinel=ROOT/'previews/user_keep_test.txt';sentinel.write_text('User-supplied content: preserve me')
qsentinel=ROOT/'qa/user_keep_test.txt';qsentinel.write_text('User-supplied QA note: preserve me')
outputs=[]
for label,user_path in [('alternate',altpath),('current',ROOT/'user_config.json')]:
    log=work/(label+'_preview.log')
    with log.open('w') as f:subprocess.run([sys.executable,str(ROOT/'main.py'),'--user-config',str(user_path),'--preview'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
    outputs.append({'name':label,'files':sorted(p.name for p in (ROOT/'previews').iterdir() if p.is_file()),'title_sha':hashlib.sha256((ROOT/'previews/current_14.50s.png').read_bytes()).hexdigest(),'configuration':json.loads((ROOT/'qa/preview_run.json').read_text())['effective_config']})
checks['preview_twice_replaces_generated_artifacts']=outputs[0]['files']==outputs[1]['files'] and outputs[0]['title_sha']!=outputs[1]['title_sha']
checks['preview_and_final_share_settings']=outputs[1]['configuration']==load(ROOT/'config.json')
checks['untracked_preview_and_qa_files_preserved']=sentinel.read_text().startswith('User-supplied') and qsentinel.read_text().startswith('User-supplied')
checks['source_assets_not_modified']=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==sha for p,sha in asset_hashes.items())
checks['existing_final_videos_preserved']=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==sha for p,sha in final_hashes.items())
checks['advanced_config_bytes_unchanged']=(ROOT/'config.json').read_bytes()==config_before
checks['user_config_bytes_unchanged']=(ROOT/'user_config.json').read_bytes()==user_before
short=copy.deepcopy(c);short['sequence_preset']='portrait_reveal';sg=GPURenderer(short,ROOT,640)
checks['both_presets_generate_frames']=sg.frame(5.8).shape==(360,640,3) and g.frame(9.6).shape==(360,640,3)
# Manifest traversal cannot delete assets, even if an inventory is corrupted.
tracker=GeneratedOutputs(ROOT,'previews','preview');tracker.entries={'../assets/portrait.jpeg':'bad'}
try:tracker.clean();checks['cleanup_path_traversal_rejected']=False
except ValueError:checks['cleanup_path_traversal_rejected']=True
from main import render
from hardware import select_backend
short['output']['preview_path']='development/test cases/short_preset_preview.mp4';short['qa']['path']='development/test cases';short['qa']['preview_path']='development/test cases'
short_run=render(short,True,select_backend())
checks['short_preset_full_preview_verified']=short_run['frames']==271
report={'checks':{k:bool(v) for k,v in checks.items()},'preview_runs':outputs,'config_sha256':hashlib.sha256(config_before).hexdigest()}
(ROOT/'development/template_test_results.json').write_text(json.dumps(report,indent=2));print(json.dumps(report['checks'],indent=2))
# Remove only the exact test-created sentinel files, after verifying their contents.
assert sentinel.read_text()=='User-supplied content: preserve me';sentinel.unlink()
assert qsentinel.read_text()=='User-supplied QA note: preserve me';qsentinel.unlink()
assert all(checks.values()),'Template integration checks failed'
