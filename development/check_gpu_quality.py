from pathlib import Path
import sys,time,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from main import load
from renderer import Renderer
from gpu_renderer import GPURenderer
from analyze import contact
from PIL import Image
c=load(ROOT/'config.json');cpu=Renderer(c,ROOT,1280);gpu=GPURenderer(c,ROOT,1280)
rows=[];frames=[]
for t in [.5,2.5,2.9,4.35,6.25,7.8,9.6,13.05,14.5,17.4]:
    a=cpu.frame(t);b=gpu.frame(t);d=a.astype(float)-b.astype(float)
    rows.append({'time':t,'mean_absolute_channel_error':float(np.abs(d).mean()),'psnr':float(10*np.log10(255**2/max(.0000001,np.mean(d*d))))})
    if t in [.5,2.9,7.8,9.6,14.5,17.4]:frames.extend([(f'CPU {t:.2f}s',a),(f'CUDA {t:.2f}s',b)])
    Image.fromarray(b).save(ROOT/f'development/benchmarks/gpu_{t:.2f}.png')
contact(frames,ROOT/'development/benchmarks/cpu_gpu_comparison.jpg',2,(640,360))
(ROOT/'development/benchmarks/gpu_pixel_comparison.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
