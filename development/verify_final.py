"""Inspect actual encoded frames, compare to CUDA source frames, and verify run identity."""
import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import cv2,numpy as np,cupy as cp
from main import load
from gpu_renderer import GPURenderer
from analyze import contact

c=load(ROOT/'config.json');final=json.loads((ROOT/'qa/final_run.json').read_text());preview=json.loads((ROOT/'qa/preview_run.json').read_text())
assert final['effective_config_sha256']==preview['effective_config_sha256']
assert all(json.loads((ROOT/'qa/PK_4K_validation.json').read_text())['checks'].values())
out=ROOT/'development/verification';out.mkdir(exist_ok=True)
r=GPURenderer(c,ROOT,c['output']['width']);cap=cv2.VideoCapture(final['output']);rows=[];frames=[]
for t in [.5,2.9,6.25,7.8,9.6,13.05,14.5]:
    i=round(t*c['output']['fps']);t=i/c['output']['fps'];cap.set(cv2.CAP_PROP_POS_FRAMES,i);ok,bgr=cap.read();assert ok
    encoded=cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)
    previous=r.frame_device((i-1)/c['output']['fps']) if i else None
    source,_,_=r.finish_frame(r.frame_device(t),previous,c['output']['width'],float(np.clip(c['effects']['motion_blur_shutter'],0,1))*.25)
    source=cp.asnumpy(source);diff=source.astype(np.float32)-encoded.astype(np.float32)
    rows.append({'time':t,'mean_absolute_channel_error':float(np.abs(diff).mean()),'psnr_db':float(10*np.log10(255**2/max(1e-10,float((diff*diff).mean()))))})
    cv2.imwrite(str(out/f'final_{t:05.2f}s.jpg'),bgr,[cv2.IMWRITE_JPEG_QUALITY,95]);frames.append((f'ENCODED 4K {t:.2f}s',encoded))
cap.release();contact(frames,out/'final_contact_sheet.jpg',3,(640,360))
report={'same_effective_preview_final_settings':True,'advanced_config_sha256':hashlib.sha256((ROOT/'config.json').read_bytes()).hexdigest(),'encoded_frame_comparison':rows,'final_runtime_seconds':final['seconds_including_init_mux_validation'],'backend':final['hardware']['compute'],'encoder':final['hardware']['encoder']}
(out/'final_verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
