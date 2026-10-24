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
from user_settings import read_json, apply_user_settings, fingerprint
from generated_outputs import GeneratedOutputs, migrate_known_outputs
from hardware import select_backend, encoder_args

ROOT=Path(__file__).resolve().parent

def load(path,user_path=None):
    c=apply_user_settings(read_json(path),ROOT,user_path)
    if c['sequence_preset'] not in c['presets']: raise ValueError('Unknown sequence_preset')
    o=c['output']
    if any(o[k]<=0 for k in ['width','height','fps','supersampling']): raise ValueError('Output dimensions/fps/supersampling must be positive')
    if o['width']%2 or o['height']%2: raise ValueError('H.264 dimensions must be even')
    if o['encoder'] not in ['libx264','h264_nvenc','h264_qsv','h264_amf']: raise ValueError('Use an H.264 encoder in advanced config.json.')
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

def make_renderer(c,width,hardware):
    if hardware['compute']['backend']=='cupy_cuda':
        from gpu_renderer import GPURenderer
        return GPURenderer(c,ROOT,width)
    print('CPU rendering reason: '+hardware['compute']['reason'],flush=True)
    return Renderer(c,ROOT,width)

def previews(c,tag='current',hardware=None,rendered_video=None):
    hardware=hardware or select_backend()
    r=None if rendered_video else make_renderer(c,c['output']['preview_width'],hardware)
    out=ROOT/c['qa']['preview_path']; frames=[]; compare=[]
    if c['sequence_preset']=='extended_credits':
        times=c['qa']['timestamps']; ref=ROOT.parent/'title_card_reference_upload_pack/lv_0_20261021030852.mp4'
    else:
        times=[0,1.5,2.45,4,5.8,7.5,9]; ref=ROOT.parent/'title_card_reference_upload_pack/reference video.mp4'
    cap=cv2.VideoCapture(str(ref)) if ref.exists() else None
    actual=cv2.VideoCapture(str(rendered_video)) if rendered_video else None
    for t in times:
        if actual:
            actual.set(cv2.CAP_PROP_POS_FRAMES,round(t*c['output']['fps']));ok,bgr=actual.read()
            if not ok:raise RuntimeError(f'Cannot extract current preview frame at {t}s')
            frame=cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)
        else:frame=r.frame(t)
        Image.fromarray(frame).save(out/f'{tag}_{t:05.2f}s.png')
        frames.append((f'GENERATED {t:.2f}s',frame))
        if cap:
            cap.set(cv2.CAP_PROP_POS_MSEC,t*1000); ok,rf=cap.read()
            if ok:
                rf=cv2.cvtColor(cv2.resize(rf,(frame.shape[1],frame.shape[0])),cv2.COLOR_BGR2RGB)
                compare.extend([(f'REFERENCE {t:.2f}s',rf),(f'GENERATED {t:.2f}s',frame)])
    if cap: cap.release()
    if actual:actual.release()
    contact(frames,out/f'{tag}_contact_sheet.jpg',3,(640,360))
    if compare: contact(compare,out/f'{tag}_comparison.jpg',2,(640,360))
    if r is not None:
        alpha=r.alpha.get() if hasattr(r.alpha,'get') else r.alpha
        cv2.imwrite(str(out/f'{tag}_subject_mask.png'),np.uint8(np.clip(alpha,0,1)*255))
    print('Preview frames written:',out,flush=True)

def render(c,preview=False,hardware=None):
    wall_start=time.perf_counter();hardware=hardware or select_backend()
    o=c['output']; fps=o['fps']; duration=o['duration'] or c['presets'][c['sequence_preset']]['duration']; count=round(duration*fps)
    width=o['preview_width'] if preview else o['width']; height=round(width*o['height']/o['width']/2)*2
    internal=round(width*o['supersampling']/2)*2
    r=make_renderer(c,internal,hardware)
    is_gpu=hardware['compute']['backend']=='cupy_cuda'
    target=ROOT/(o['preview_path'] if preview else o['path']); target.parent.mkdir(parents=True,exist_ok=True)
    if target.resolve()==(ROOT/c['portrait']['image']).resolve(): raise ValueError('Output must not overwrite input')
    temp=target.with_name(target.stem+'_video_only.mp4')
    pending=target.with_name(target.stem+'_pending.mp4')
    logpath=ROOT/c['qa']['path']/('preview_encode.log' if preview else 'final_encode.log')
    cmd=[ffmpeg(),'-y','-v','info','-f','rawvideo','-pix_fmt','nv12' if is_gpu else 'rgb24','-s',f'{width}x{height}','-r',str(fps),'-i','-','-an']
    cmd+=encoder_args(c,preview,hardware)
    cmd+=['-pix_fmt','nv12' if is_gpu else 'yuv420p','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-movflags','+faststart']
    cmd+=[str(temp)]
    commands=[cmd]; begun=time.time(); metrics=[]; previous=None
    with logpath.open('w') as log:
        p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=log)
        try:
            for i in range(count):
                shutter=float(np.clip(c['effects']['motion_blur_shutter'],0,1))*.25
                if is_gpu:
                    import cupy as cp
                    from gpu_ops import to_nv12
                    blurred,previous,measure=r.finish_frame(r.frame_device(i/fps),previous,width,shutter)
                    payload=cp.asnumpy(to_nv12(blurred)).tobytes()
                else:
                    arr=r.frame(i/fps)
                    if internal!=width: arr=cv2.resize(arr,(width,height),interpolation=cv2.INTER_AREA)
                    blurred=cv2.addWeighted(arr,1-shutter,previous,shutter,0) if previous is not None and shutter else arr
                    small=cv2.resize(blurred,(320,180)); gray=cv2.cvtColor(small,cv2.COLOR_RGB2GRAY)
                    measure=[float(gray.mean()),float(np.mean(gray>245))];previous=arr;payload=blurred.tobytes()
                metrics.append([i,i/fps,*measure]);p.stdin.write(payload)
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
        cmd+=['-t',str(count/fps),'-movflags','+faststart',str(pending)]; commands.append(cmd)
        with logpath.open('a') as log: subprocess.run(cmd,stderr=log,check=True)
        temp.unlink()
    else: shutil.move(temp,pending)
    with (ROOT/c['qa']['path']/('preview_frame_metrics.csv' if preview else 'final_frame_metrics.csv')).open('w',newline='') as f:
        writer=csv.writer(f); writer.writerow(['frame','time','mean_luma','over_245_fraction']); writer.writerows(metrics)
    (ROOT/c['qa']['path']/('preview_commands.json' if preview else 'final_commands.json')).write_text(json.dumps(commands,indent=2))
    validate(pending,c,width,height,count,report_name=target.stem)
    pending.replace(target)
    report_path=ROOT/c['qa']['path']/(target.stem+'_validation.json')
    verified=json.loads(report_path.read_text());verified['file']=str(target);report_path.write_text(json.dumps(verified,indent=2))
    if preview:
        alpha=r.alpha.get() if hasattr(r.alpha,'get') else r.alpha
        cv2.imwrite(str(ROOT/c['qa']['preview_path']/'current_subject_mask.png'),np.uint8(np.clip(alpha,0,1)*255))
    elapsed=time.perf_counter()-wall_start
    run={'effective_config':c,'effective_config_sha256':fingerprint(c),'hardware':hardware,'telemetry':r.telemetry() if is_gpu else {'backend':'CPU'},'seconds_including_init_mux_validation':elapsed,'seconds_after_renderer_init':time.time()-begun,'frames':count,'output':str(target),'width':width,'height':height}
    (ROOT/c['qa']['path']/('preview_run.json' if preview else 'final_run.json')).write_text(json.dumps(run,indent=2))
    print(f'Render verified: {target}; total {elapsed:.1f}s; backend {hardware["compute"]["backend"]}; encoder {hardware["encoder"]}',flush=True)
    return run

def validate(path,c,width=None,height=None,count=None,report_name=None):
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
    (ROOT/c['qa']['path']/f'{report_name or path.stem}_validation.json').write_text(json.dumps(result,indent=2))
    print('Validation:',checks,flush=True)
    if not all(checks.values()): raise RuntimeError('Validation failed; consult qa report')

def main():
    parser=argparse.ArgumentParser(description='Reusable GPU portrait title sequence')
    parser.add_argument('--config',default=str(ROOT/'config.json'))
    parser.add_argument('--render',action='store_true'); parser.add_argument('--preview',action='store_true'); parser.add_argument('--frames',action='store_true')
    parser.add_argument('--preset',choices=['extended_credits','portrait_reveal']); parser.add_argument('--tag',default='current',help=argparse.SUPPRESS); parser.add_argument('--validate')
    parser.add_argument('--user-config',default=str(ROOT/'user_config.json'))
    args=parser.parse_args(); c=load(args.config,args.user_config)
    if args.preset:
        c['sequence_preset']=args.preset
        if args.preset=='portrait_reveal':
            for key in ['path','preview_path']:
                p=Path(c['output'][key]);c['output'][key]=str(p.with_name(p.stem+'_portrait_reveal'+p.suffix))
    if args.frames or args.preview or args.render:
        hardware=select_backend()
        print(f'Current person: {c["titles"][0]["text"]} | Opening: {c["opening"]["letter"]} | Image: {c["portrait"]["image"]}',flush=True)
    if args.frames or args.preview:
        migrate_known_outputs(ROOT)
        pt=GeneratedOutputs(ROOT,c['qa']['preview_path'],'preview');qt=GeneratedOutputs(ROOT,c['qa']['path'],'qa')
        pt.clean();qt.clean()
        out=ROOT/c['qa']['preview_path'];target=ROOT/c['output']['preview_path']
        times=c['qa']['timestamps'] if c['sequence_preset']=='extended_credits' else [0,1.5,2.45,4,5.8,7.5,9]
        generated=[out/f'current_{t:05.2f}s.png' for t in times]+[out/'current_contact_sheet.jpg',out/'current_comparison.jpg',out/'current_subject_mask.png',target,target.with_name(target.stem+'_video_only.mp4'),target.with_name(target.stem+'_pending.mp4')]
        qa=[ROOT/c['qa']['path']/name for name in ['preview_run.json','preview_encode.log','preview_commands.json','preview_frame_metrics.csv',target.stem+'_validation.json','current_settings.json']]
        pt.reserve(generated);qt.reserve(qa)
        try:
            if args.preview: render(c,True,hardware)
            if args.frames or args.preview:previews(c,'current',hardware,target if args.preview else None)
            (ROOT/c['qa']['path']/'current_settings.json').write_text(json.dumps({'effective_config_sha256':fingerprint(c),'effective_config':c,'hardware':hardware},indent=2))
        finally:
            for path in generated:
                if path.exists():pt.register(path)
            for path in qa:
                if path.exists():qt.register(path)
    if args.render: render(c,False,hardware)
    if args.validate: validate(args.validate,c)
    if not any([args.frames,args.preview,args.render,args.validate]): parser.print_help()

if __name__=='__main__':
    try: main()
    except Exception as exc:
        print(f'ERROR: {exc}',file=sys.stderr); sys.exit(1)
