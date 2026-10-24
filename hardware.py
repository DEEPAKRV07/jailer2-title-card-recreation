"""Runtime-tested GPU selection. A present compatible CUDA device may never silently use CPU."""
import ctypes,json,shutil,subprocess,sys,time
from pathlib import Path
import cv2
from analyze import ffmpeg

def cuda_inventory():
    result={'devices':0,'driver_version':None}
    try:
        driver=ctypes.WinDLL('nvcuda.dll') if sys.platform=='win32' else ctypes.CDLL('libcuda.so.1')
        status=driver.cuInit(0);count=ctypes.c_int();version=ctypes.c_int()
        result['init_status']=status
        if status==0:
            driver.cuDeviceGetCount(ctypes.byref(count));driver.cuDriverGetVersion(ctypes.byref(version))
            result.update(devices=count.value,driver_version=version.value)
    except OSError as exc:result['reason']=str(exc)
    return result

def inspect_hardware(test_encoders=True):
    result={'cuda_driver':cuda_inventory(),'opencv_cuda_devices':cv2.cuda.getCudaEnabledDeviceCount(),'opencv_opencl_available':cv2.ocl.haveOpenCL(),'opencv_opencl_enabled':cv2.ocl.useOpenCL(),'ffmpeg':ffmpeg()}
    if sys.platform=='win32':
        p=subprocess.run(['powershell','-NoProfile','-Command','Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion | ConvertTo-Json -Compress'],capture_output=True,text=True)
        result['display_adapters']=p.stdout.strip()
    if shutil.which('nvidia-smi'):
        result['nvidia_smi']=subprocess.run(['nvidia-smi','--query-gpu=name,driver_version,memory.total,compute_cap','--format=csv,noheader'],capture_output=True,text=True).stdout.strip()
    encoders=subprocess.run([ffmpeg(),'-hide_banner','-encoders'],capture_output=True,text=True,check=True).stdout
    result['hardware_encoders']={}
    for name in ['h264_nvenc','h264_qsv','h264_amf']:
        r={'compiled':name in encoders,'usable':False}
        if r['compiled'] and test_encoders:
            cmd=[ffmpeg(),'-hide_banner','-v','error','-f','lavfi','-i','color=black:s=640x360:r=30','-frames:v','2','-c:v',name,'-pix_fmt','yuv420p','-f','null','-']
            try:
                p=subprocess.run(cmd,capture_output=True,text=True,timeout=30);r.update(usable=p.returncode==0,returncode=p.returncode,log=p.stderr.strip(),test_command=cmd)
            except subprocess.TimeoutExpired:r['log']='Hardware encoder initialization timed out.'
        result['hardware_encoders'][name]=r
    return result

def select_backend(report=None):
    report=report or inspect_hardware()
    if report['cuda_driver']['devices']:
        try:
            import cupy as cp
            cp.cuda.Device(0).use();start=cp.cuda.Event();end=cp.cuda.Event();start.record()
            data=cp.arange(4096,dtype=cp.float32);value=float((data*data).sum());end.record();end.synchronize()
            if value<=0:raise RuntimeError('CUDA arithmetic self-test returned an invalid result')
            report['compute']={'backend':'cupy_cuda','device':cp.cuda.runtime.getDeviceProperties(0)['name'].decode(),'self_test_sum':value,'self_test_cuda_ms':cp.cuda.get_elapsed_time(start,end),'cupy_version':cp.__version__}
        except Exception as exc:
            raise RuntimeError('A compatible NVIDIA GPU is present, but CUDA initialization failed. Run setup.bat to install/repair GPU dependencies. CPU fallback is disabled. Details: '+str(exc)) from exc
    else:
        report['compute']={'backend':'cpu','reason':'No compatible CUDA device detected. CUDA particle/image kernels cannot execute. OpenCV OpenCL alone does not implement this renderer\'s CUDA kernels.'}
    report['encoder']=next((name for name,r in report['hardware_encoders'].items() if r['usable']),'libx264')
    report['encoding_reason']='Hardware encoder passed an actual two-frame encode' if report['encoder']!='libx264' else 'No hardware H.264 encoder passed the runtime compatibility test; using CPU H.264 encoding.'
    print('Compute backend: '+report['compute']['backend']+' | Encoder: '+report['encoder'],flush=True)
    return report

def encoder_args(c,preview,report):
    o=c['output'];quality=o['preview_crf'] if preview else o['crf'];encoder=report['encoder']
    if encoder=='h264_nvenc':
        # CRF and CQ are different encoder controls; preserve the requested quality target,
        # use the highest-quality preset and verify perceptual quality against source frames.
        args=['-c:v',encoder,'-preset','p7','-tune','hq','-rc','vbr','-cq',str(quality),'-b:v',str(o.get('bitrate') or '0'),'-multipass','fullres','-spatial-aq','1','-temporal-aq','1']
    elif encoder=='h264_qsv':args=['-c:v',encoder,'-preset','veryslow','-global_quality',str(quality)]
    elif encoder=='h264_amf':args=['-c:v',encoder,'-quality','quality','-rc','cqp','-qp_i',str(quality),'-qp_p',str(quality)]
    else:args=['-c:v','libx264','-threads','6','-preset',o['encoder_preset'],'-crf',str(quality)]
    if o.get('bitrate') and encoder!='h264_nvenc':args+=['-b:v',str(o['bitrate'])]
    return args

def ensure_gpu_dependencies():
    inventory=cuda_inventory()
    if not inventory['devices']:return
    try:
        import cupy as cp
        float(cp.arange(4,dtype=cp.float32).sum())
    except Exception:
        print('Installing project-local CUDA runtime and CuPy for the detected NVIDIA GPU...',flush=True)
        subprocess.run([sys.executable,'-m','pip','install','-r',str(Path(__file__).with_name('requirements-gpu.txt'))],check=True)
        subprocess.run([sys.executable,'-c','import cupy as cp; print("CUDA arithmetic test:",float(cp.arange(4096,dtype=cp.float32).sum()))'],check=True)

if __name__=='__main__':
    report=select_backend();Path('development/hardware_detection.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
