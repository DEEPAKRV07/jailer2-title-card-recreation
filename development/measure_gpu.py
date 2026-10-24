import json,time,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from main import render
from hardware import select_backend
c=json.loads((ROOT/'development/benchmarks/baseline_effective_config.json').read_text())
c['output']['path']='development/benchmarks/gpu_final.mp4';c['output']['preview_path']='development/benchmarks/gpu_preview.mp4'
c['qa']['preview_path']='development/benchmarks'
hw=select_backend();results={}
for preview,label in [(True,'preview'),(False,'final')]:
    start=time.perf_counter();run=render(c,preview,hw)
    results[label]={'seconds_including_init_mux_validation':time.perf_counter()-start,'run':run}
    (ROOT/'development/benchmarks/gpu_times.json').write_text(json.dumps(results,indent=2))
    print(label,results[label]['seconds_including_init_mux_validation'],flush=True)
