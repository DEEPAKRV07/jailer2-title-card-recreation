import argparse
import copy
import csv
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from renderer import Renderer
from analyze import contact, ffmpeg, probe

ROOT=Path(__file__).resolve().parent

def load(path):
    c=json.loads(Path(path).read_text(encoding='utf-8'))
    if c['sequence_preset'] not in c['presets']: raise ValueError('Unknown sequence_preset')
    o=c['output']
    if any(o[k]<=0 for k in ['width','height','fps','supersampling']): raise ValueError('Output dimensions/fps/supersampling must be positive')
    if o['width']%2 or o['height']%2: raise ValueError('H.264 dimensions must be even')
    if o['encoder']!='libx264': raise ValueError('This CPU workflow supports encoder=libx264')
    p=c['portrait']
    if p['reveal_end']<=p['reveal_start']: raise ValueError('Reveal end must follow start')
    if not (ROOT/p['image']).is_file(): raise FileNotFoundError(p['image'])
    if p['fit']!='contain': raise ValueError('Use fit=contain to preserve natural proportions')
    if len(p['crop'])!=4 or not (0<=p['crop'][0]<p['crop'][2]<=1 and 0<=p['crop'][1]<p['crop'][3]<=1): raise ValueError('crop is normalized [left,top,right,bottom]')
    if c['audio']['enabled'] and not (ROOT/(c['audio']['source'] or c['presets'][c['sequence_preset']]['audio'])).exists(): raise FileNotFoundError('Configured audio file is missing')
    for card in c['titles']:
        if card['end']<=card['start'] or min(card['fade_in'],card['fade_out'])<=0: raise ValueError('Invalid card timing')
    for directory in [c['qa']['path'],c['qa']['preview_path'],'output']:
        (ROOT/directory).mkdir(parents=True,exist_ok=True)
    return c

def previews(c,tag='v1'):
    r=Renderer(c,ROOT,c['output']['preview_width'])
    out=ROOT/c['qa']['preview_path']; frames=[]; compare=[]
    if c['sequence_preset']=='extended_credits':
        times=c['qa']['timestamps']; ref=ROOT.parent/'title_card_reference_upload_pack/lv_0_20261021030852.mp4'
    else:
        times=[0,1.5,2.45,4,5.8,7.5,9]; ref=ROOT.parent/'title_card_reference_upload_pack/reference video.mp4'
    cap=cv2.VideoCapture(str(ref)) if ref.exists() else None
    for t in times:
        frame=r.frame(t); Image.fromarray(frame).save(out/f'{tag}_{t:05.2f}s.png')
        frames.append((f'GENERATED {t:.2f}s',frame))
        if cap:
            cap.set(cv2.CAP_PROP_POS_MSEC,t*1000); ok,rf=cap.read()
            if ok:
                rf=cv2.cvtColor(cv2.resize(rf,(r.w,r.h)),cv2.COLOR_BGR2RGB)
                compare.extend([(f'REFERENCE {t:.2f}s',rf),(f'GENERATED {t:.2f}s',frame)])
    if cap: cap.release()
    contact(frames,out/f'{tag}_contact_sheet.jpg',3,(640,360))
    if compare: contact(compare,out/f'{tag}_comparison.jpg',2,(640,360))
    cv2.imwrite(str(out/f'{tag}_subject_mask.png'),np.uint8(np.clip(r.alpha,0,1)*255))
    print('Preview frames written:',out,flush=True)

def render(c,preview=False):
    o=c['output']; fps=o['fps']; duration=o['duration'] or c['presets'][c['sequence_preset']]['duration']; count=round(duration*fps)
    width=o['preview_width'] if preview else o['width']; height=round(width*o['height']/o['width']/2)*2
    internal=round(width*o['supersampling']/2)*2
    r=Renderer(c,ROOT,internal)
    target=ROOT/(o['preview_path'] if preview else o['path']); target.parent.mkdir(parents=True,exist_ok=True)
    if target.resolve()==(ROOT/c['portrait']['image']).resolve(): raise ValueError('Output must not overwrite input')
    temp=target.with_name(target.stem+'_video_only.mp4')
    logpath=ROOT/c['qa']['path']/('preview_encode.log' if preview else 'final_encode.log')
    cmd=[ffmpeg(),'-y','-v','warning','-f','rawvideo','-pix_fmt','rgb24','-s',f'{width}x{height}','-r',str(fps),'-i','-','-an','-c:v',o['encoder'],'-threads','6','-preset',o['encoder_preset'],'-crf',str(o['preview_crf'] if preview else o['crf']),'-pix_fmt','yuv420p','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-movflags','+faststart']
    if o.get('bitrate'): cmd+=['-b:v',str(o['bitrate'])]
    cmd+=[str(temp)]
    commands=[cmd]; begun=time.time(); metrics=[]; previous=None
    with logpath.open('w') as log:
        p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=log)
        try:
            for i in range(count):
                arr=r.frame(i/fps)
                if internal!=width: arr=cv2.resize(arr,(width,height),interpolation=cv2.INTER_AREA)
                # Short two-frame temporal integration, with a clear current-frame majority.
                shutter=float(np.clip(c['effects']['motion_blur_shutter'],0,1))*.25
                blurred=cv2.addWeighted(arr,1-shutter,previous,shutter,0) if previous is not None and shutter else arr
                small=cv2.resize(blurred,(320,180)); gray=cv2.cvtColor(small,cv2.COLOR_RGB2GRAY)
                metrics.append([i,i/fps,float(gray.mean()),float(np.mean(gray>245))])
                p.stdin.write(blurred.tobytes()); previous=arr
                if i%30==0: print(f'{i}/{count} frames | {time.time()-begun:.1f}s elapsed',flush=True)
        finally:
            p.stdin.close()
        if p.wait()!=0: raise RuntimeError(f'FFmpeg encoding failed; see {logpath}')
    if c['audio']['enabled']:
        a=c['audio']; source=ROOT/(a['source'] or c['presets'][c['sequence_preset']]['audio'])
        filters=[]
        if a['offset']>0: filters.append(f"adelay={round(a['offset']*1000)}:all=1")
        elif a['offset']<0: filters+= [f"atrim=start={-a['offset']}",'asetpts=PTS-STARTPTS']
        if a['volume']!=1: filters.append(f"volume={a['volume']}")
        if a['fade_in']>0: filters.append(f"afade=t=in:d={a['fade_in']}")
        if a['fade_out']>0: filters.append(f"afade=t=out:st={duration-a['fade_out']}:d={a['fade_out']}")
        cmd=[ffmpeg(),'-y','-v','warning','-i',str(temp),'-i',str(source),'-map','0:v:0','-map','1:a:0','-c:v','copy']
        if not filters and a['codec']=='aac': cmd+=['-c:a','copy']
        else:
            cmd+=['-c:a',a['codec'],'-b:a',a['bitrate'],'-ar',str(a['sample_rate']),'-ac',str(a['channels'])]
            if filters: cmd+=['-af',','.join(filters)]
        cmd+=['-t',str(count/fps),'-movflags','+faststart',str(target)]; commands.append(cmd)
        with logpath.open('a') as log: subprocess.run(cmd,stderr=log,check=True)
        temp.unlink()
    else: shutil.move(temp,target)
    with (ROOT/c['qa']['path']/('preview_frame_metrics.csv' if preview else 'final_frame_metrics.csv')).open('w',newline='') as f:
        writer=csv.writer(f); writer.writerow(['frame','time','mean_luma','over_245_fraction']); writer.writerows(metrics)
    (ROOT/c['qa']['path']/('preview_commands.json' if preview else 'final_commands.json')).write_text(json.dumps(commands,indent=2))
    print(f'Render finished: {target}; {time.time()-begun:.1f}s',flush=True)
    validate(target,c,width,height,count)

def validate(path,c,width=None,height=None,count=None):
    path=Path(path); report=probe(path)
    if report.get('pending_ffprobe'): raise RuntimeError('ffprobe unavailable: render exists but metadata verification is incomplete')
    v=next(s for s in report['streams'] if s['codec_type']=='video')
    a=[s for s in report['streams'] if s['codec_type']=='audio']
    width=width or c['output']['width']; height=height or c['output']['height']
    count=count or round((c['output']['duration'] or c['presets'][c['sequence_preset']]['duration'])*c['output']['fps'])
    checks={'dimensions':v['width']==width and v['height']==height,'fps':v['avg_frame_rate']==f"{c['output']['fps']}/1",'frames':int(v['nb_frames'])==count,'h264':v['codec_name']=='h264','pixel_format':v['pix_fmt']=='yuv420p','audio': bool(a)==c['audio']['enabled']}
    if a: checks['audio_format']=a[0]['codec_name']=='aac' and a[0]['sample_rate']=='44100' and a[0]['channels']==2
    decode=subprocess.run([ffmpeg(),'-v','error','-xerror','-i',str(path),'-f','null','-'],capture_output=True,text=True)
    checks['full_decode']=decode.returncode==0
    checks['duration']=abs(float(v['duration'])-count/c['output']['fps'])<.001
    result={'file':str(path),'checks':checks,'metadata':report,'decode_errors':decode.stderr}
    (ROOT/c['qa']['path']/f'{path.stem}_validation.json').write_text(json.dumps(result,indent=2))
    print('Validation:',checks,flush=True)
    if not all(checks.values()): raise RuntimeError('Validation failed; consult qa report')

def main():
    parser=argparse.ArgumentParser(description='Procedural KARTHIKEYAN title sequence')
    parser.add_argument('--config',default=str(ROOT/'config.json'))
    parser.add_argument('--render',action='store_true'); parser.add_argument('--preview',action='store_true'); parser.add_argument('--frames',action='store_true')
    parser.add_argument('--preset',choices=['extended_credits','portrait_reveal']); parser.add_argument('--tag',default='v1'); parser.add_argument('--validate')
    args=parser.parse_args(); c=load(args.config)
    if args.preset:
        c['sequence_preset']=args.preset
        if args.preset=='portrait_reveal':
            c['output']['path']='output/KARTHIKEYAN_portrait_reveal_4K.mp4'
            c['output']['preview_path']='previews/KARTHIKEYAN_portrait_reveal_preview.mp4'
    if args.frames: previews(c,args.tag)
    if args.preview: render(c,True)
    if args.render: render(c)
    if args.validate: validate(args.validate,c)
    if not any([args.frames,args.preview,args.render,args.validate]): parser.print_help()

if __name__=='__main__':
    try: main()
    except Exception as exc:
        print(f'ERROR: {exc}',file=sys.stderr); raise
