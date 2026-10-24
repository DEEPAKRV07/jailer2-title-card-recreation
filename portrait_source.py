"""Non-destructive source loading and deterministic, cached CPU GrabCut foreground extraction."""
import hashlib,json,time
from pathlib import Path
import cv2
import numpy as np

def prepare_source(path,settings,root,seed):
    path=Path(path); raw=cv2.imdecode(np.frombuffer(path.read_bytes(),np.uint8),cv2.IMREAD_UNCHANGED)
    if raw is None: raise ValueError(f'Cannot read portrait: {path}')
    if raw.ndim==2: raw=cv2.cvtColor(raw,cv2.COLOR_GRAY2BGR)
    src=raw[:,:,:3].copy(); sh,sw=src.shape[:2]
    if settings.get('mask'):
        maskpath=Path(root)/settings['mask']
        alpha=cv2.imdecode(np.frombuffer(maskpath.read_bytes(),np.uint8),0)
        if alpha is None or alpha.shape!=(sh,sw): raise ValueError('Custom portrait mask must have the same dimensions as the portrait.')
        return src,alpha
    if settings.get('subject_polygon'):
        alpha=np.zeros((sh,sw),np.uint8)
        cv2.fillPoly(alpha,[(np.asarray(settings['subject_polygon'])*[sw,sh]).astype(np.int32)],255)
        return src,alpha
    if raw.shape[2]==4 and np.any(raw[:,:,3]<255): return src,raw[:,:,3]
    key=hashlib.sha256(path.read_bytes()+f'grabcut5-{cv2.__version__}-{seed}'.encode()).hexdigest()
    cache=Path(root)/'.cache/foreground'; cache.mkdir(parents=True,exist_ok=True); file=cache/(key+'.png')
    if file.exists():
        alpha=cv2.imread(str(file),0)
        if alpha is not None and alpha.shape==(sh,sw):
            print('Foreground: cached mask reused (source unchanged).',flush=True); return src,alpha
    print('Foreground: CPU GrabCut (no compatible CUDA implementation in installed OpenCV); computing reusable mask...',flush=True)
    start=time.perf_counter(); labels=np.zeros((sh,sw),np.uint8); cv2.setRNGSeed(int(seed)%2147483647)
    try:
        cv2.grabCut(src,labels,(int(sw*.1),int(sh*.025),int(sw*.8),int(sh*.95)),np.zeros((1,65)),np.zeros((1,65)),5,cv2.GC_INIT_WITH_RECT)
        alpha=np.where((labels==1)|(labels==3),255,0).astype(np.uint8)
        if np.count_nonzero(alpha)<sh*sw*.001: raise ValueError('Empty foreground extraction')
    except (cv2.error,ValueError):
        # A conservative black-background fallback keeps actual illuminated source pixels.
        gray=cv2.cvtColor(src,cv2.COLOR_BGR2GRAY)
        if np.mean(gray<20)<.4:
            raise ValueError('Automatic extraction could not isolate this portrait. Create a same-size white-subject/black-background mask and set portrait.mask to its path in config.json.')
        alpha=np.where(gray>8,255,0).astype(np.uint8)
        print('Foreground fallback: preserving lit source pixels on the existing black background. Inspect the preview; set portrait.mask in config.json for finer isolation.',flush=True)
    cv2.imwrite(str(file),alpha)
    (cache/(key+'.json')).write_text(json.dumps({'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'backend':'CPU OpenCV GrabCut','seconds':time.perf_counter()-start},indent=2))
    return src,alpha
