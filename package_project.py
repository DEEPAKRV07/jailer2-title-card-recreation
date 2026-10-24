"""Package the current reusable template and verified output; omit environments and old renders."""
import hashlib,json,zipfile
from pathlib import Path
from main import load
ROOT=Path(__file__).resolve().parent
c=load(ROOT/'config.json')
destination=ROOT.parent/'portrait_title_project_gpu.zip'
selected=set()
for pattern in ['*.py','*.json','*.bat','*.md','requirements*.txt']:
    selected.update(ROOT.glob(pattern))
for folder in ['assets','analysis']:
    selected.update(p for p in (ROOT/folder).rglob('*') if p.is_file())
for folder,kind in [('previews','preview'),('qa','qa')]:
    manifest=ROOT/folder/f'.generated_{kind}.json'
    if manifest.exists():
        selected.add(manifest)
        for name,sha in json.loads(manifest.read_text())['files'].items():
            p=(ROOT/folder/name).resolve()
            if p.is_relative_to(ROOT/folder) and p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==sha:selected.add(p)
for name in ['final_run.json','final_commands.json','final_encode.log','final_frame_metrics.csv',Path(c['output']['path']).stem+'_validation.json']:
    selected.add(ROOT/'qa'/name)
selected.add(ROOT/c['output']['path'])
for name in ['template_test_results.json','template_tests.log','backend_selection_tests.json','test_backend_selection.py','hardware_detection.json','hardware_test.log','current_final_render.log','test_template.py','check_gpu_quality.py','measure_baseline.py','measure_gpu.py','verify_final.py']:
    selected.add(ROOT/'development'/name)
for name in ['cpu_times.json','gpu_times.json','cpu_profile.txt','gpu_pixel_comparison.json','cpu_gpu_comparison.jpg','baseline_effective_config.json']:
    selected.add(ROOT/'development/benchmarks'/name)
selected.update(p for p in (ROOT/'development/baseline').glob('*') if p.is_file())
selected.update(p for p in (ROOT/'development/verification').glob('*') if p.is_file())
files=sorted(p for p in selected if p.is_file() and p.resolve().is_relative_to(ROOT))
with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in files:z.write(p,Path('portrait_title_project')/p.relative_to(ROOT))
with zipfile.ZipFile(destination) as z:
    assert z.testzip() is None
    required=['main.py','renderer.py','gpu_renderer.py','gpu_ops.py','hardware.py','user_config.json','config.json','requirements-gpu.txt','README.md',c['output']['path']]
    assert all('portrait_title_project/'+name.replace('\\','/') in z.namelist() for name in required)
report={'zip':str(destination),'bytes':destination.stat().st_size,'files':len(files),'crc_validation':'passed','sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),'excluded':'Virtual environments, tools, caches, original reference footage, old final videos, benchmark MP4s and unrelated preview files.'}
(ROOT.parent/'portrait_title_project_gpu_verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))

