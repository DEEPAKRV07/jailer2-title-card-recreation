"""Exercise fail-closed CUDA errors and explicitly unsupported-hardware paths."""
import sys,json
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from hardware import select_backend,encoder_args
from main import load
checks={}
with patch.dict(sys.modules,{'cupy':None}):
    try:select_backend({'cuda_driver':{'devices':1}})
    except RuntimeError as exc:checks['cuda_present_runtime_broken_stops_without_cpu_fallback']='CPU fallback is disabled' in str(exc)
cpu=select_backend({'cuda_driver':{'devices':0},'hardware_encoders':{'h264_nvenc':{'usable':False},'h264_qsv':{'usable':False},'h264_amf':{'usable':False}}})
checks['no_supported_device_explicit_cpu_reason']=cpu['compute']['backend']=='cpu' and bool(cpu['compute']['reason']) and cpu['encoder']=='libx264'
c=load(ROOT/'config.json');c['output']['encoder']='h264_nvenc'
checks['unavailable_hardware_encoder_uses_detected_cpu_encoder']=encoder_args(c,False,cpu)[1]=='libx264'
amf=select_backend({'cuda_driver':{'devices':0},'hardware_encoders':{'h264_nvenc':{'usable':False},'h264_qsv':{'usable':False},'h264_amf':{'usable':True}}})
checks['hardware_encoding_selected_without_cuda_compute']=amf['encoder']=='h264_amf'
(ROOT/'development/backend_selection_tests.json').write_text(json.dumps({'simulated_error_and_absence_paths':checks},indent=2))
print(json.dumps(checks,indent=2));assert all(checks.values())
