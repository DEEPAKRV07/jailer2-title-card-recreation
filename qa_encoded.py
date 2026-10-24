"""Decode the delivered master, measure continuity/audio and extract review frames."""
import csv,json,subprocess
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from analyze import ffmpeg,contact
from main import load
from generated_outputs import GeneratedOutputs

ROOT=Path(__file__).resolve().parent
c=load(ROOT/'config.json'); path=ROOT/c['output']['path']
pt=GeneratedOutputs(ROOT,c['qa']['preview_path'],'preview');qt=GeneratedOutputs(ROOT,c['qa']['path'],'qa')
cmd=[ffmpeg(),'-v','error','-i',str(path),'-vf','scale=640:360','-pix_fmt','rgb24','-f','rawvideo','-']
p=subprocess.Popen(cmd,stdout=subprocess.PIPE)
frames=[]; metrics=[]; old=None; i=0
selected={round(t*30):t for t in c['qa']['timestamps']}
while True:
    raw=p.stdout.read(640*360*3)
    if not raw: break
    rgb=np.frombuffer(raw,np.uint8).reshape(360,640,3)
    gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY).astype(np.float32)
    delta=float(np.abs(gray-old).mean()) if old is not None else 0
    metrics.append([i,i/30,float(gray.mean()),float(np.mean(gray>245)),delta])
    if i in selected:
        frames.append((f'ENCODED MASTER {i/30:.3f}s',rgb.copy()))
        dest=ROOT/c['qa']['preview_path']/f'encoded_{i/30:05.2f}s.png';pt.reserve([dest]);Image.fromarray(rgb).save(dest);pt.register(dest)
    old=gray; i+=1
assert p.wait()==0
dest=ROOT/c['qa']['preview_path']/'encoded_master_contact_sheet.jpg';pt.reserve([dest]);contact(frames,dest,3,(640,360));pt.register(dest)
qt.reserve([ROOT/'qa/encoded_frame_metrics.csv',ROOT/'qa/encoded_review.json'])
with (ROOT/'qa/encoded_frame_metrics.csv').open('w',newline='') as f:
    cw=csv.writer(f);cw.writerow(['frame','time','mean_luma','over_245_fraction','adjacent_mean_abs_difference']);cw.writerows(metrics)
raw=subprocess.check_output([ffmpeg(),'-v','error','-i',str(path),'-vn','-f','f32le','-'])
audio=np.frombuffer(raw,np.float32).reshape(-1,2)
source=ROOT/(c['audio']['source'] or c['presets'][c['sequence_preset']]['audio'])
raw_source=subprocess.check_output([ffmpeg(),'-v','error','-i',str(source),'-vn','-f','f32le','-'])
original=np.frombuffer(raw_source,np.float32).reshape(-1,2)
n=min(len(audio),len(original))
correlations=[float(np.corrcoef(audio[:n,k],original[:n,k])[0,1]) for k in range(2)]
result={'decoded_frames':i,'audio_peak':float(np.max(np.abs(audio))),'audio_samples_exceeding_full_scale':int(np.sum(np.abs(audio)>1)),'audio_seconds':len(audio)/44100,'original_audio_seconds':len(original)/44100,'audio_correlation_at_zero_offset_by_channel':correlations,'dark_frame_times_mean_luma_under_0_02':[round(row[1],3) for row in metrics if row[2]<.02],'largest_adjacent_frame_changes':sorted(metrics,key=lambda r:r[4],reverse=True)[:12],'max_highlight_coverage':max(row[3] for row in metrics),'interpretation':'Frame-difference values identify review candidates, not a reference similarity score. Black intervals at opening/closing and star-to-letter pause are intentional. Audio correlations test content/time alignment, not loudness or a perceptual quality grade.'}
(ROOT/'qa/encoded_review.json').write_text(json.dumps(result,indent=2))
qt.register(ROOT/'qa/encoded_frame_metrics.csv');qt.register(ROOT/'qa/encoded_review.json')
print(json.dumps(result,indent=2))
assert result['audio_samples_exceeding_full_scale']==0,'Audio clipping detected'
assert min(correlations)>.98,'Audio content/time alignment requires investigation'
