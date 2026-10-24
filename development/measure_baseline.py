import cProfile, importlib.util, json, pstats, time, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
oldr=module('original_renderer',ROOT/'development/baseline/renderer.py')
old=module('original_main',ROOT/'development/baseline/main.py'); old.Renderer=oldr.Renderer; old.ROOT=ROOT
c=json.loads((ROOT/'development/baseline/config.json').read_text())
prior=c['titles'][0]['text']; c['portrait'].update(image='assets/Cyberpunk Digital Rain Portrait.png',subject_polygon=None,mask=None)
c['opening']['letter']='D'
for card in c['titles']:
    if card['text']==prior: card['text']='DEEPAK R V'
c['qa']['path']='development/benchmarks'; c['output']['path']='development/benchmarks/cpu_final.mp4'; c['output']['preview_path']='development/benchmarks/cpu_preview.mp4'
(ROOT/'development/benchmarks/baseline_effective_config.json').write_text(json.dumps(c,indent=2))
profile=cProfile.Profile(); profile.enable(); r=oldr.Renderer(c,ROOT,3840)
for t in c['qa']['timestamps']: r.frame(t)
profile.disable(); profile.dump_stats(str(ROOT/'development/benchmarks/cpu_profile.prof'))
with (ROOT/'development/benchmarks/cpu_profile.txt').open('w') as out: pstats.Stats(profile,stream=out).sort_stats('cumtime').print_stats(45)
del r
results={}
for preview,label in [(True,'preview'),(False,'final')]:
    start=time.perf_counter(); old.render(c,preview); results[label]={'seconds_including_init_mux_validation':time.perf_counter()-start,'frames':654,'width':1280 if preview else 3840}
    (ROOT/'development/benchmarks/cpu_times.json').write_text(json.dumps(results,indent=2))
print(results)
