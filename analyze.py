"""Reference-only analysis. Reference pixels are never passed to the renderer."""
import csv, json, subprocess
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
INPUT = ROOT.parent / 'title_card_reference_upload_pack'

def ffmpeg():
    local = ROOT / 'tools/ffmpeg.exe'
    if local.exists(): return str(local)
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()

def probe(path):
    if not (ROOT/'tools/ffprobe.exe').exists():
        cap=cv2.VideoCapture(str(path))
        report={'pending_ffprobe':True,'opencv':{'width':cap.get(3),'height':cap.get(4),'fps':cap.get(5),'frames':cap.get(7)}}
        cap.release()
        return report
    return json.loads(subprocess.check_output([str(ROOT/'tools/ffprobe.exe'), '-v','error','-show_streams','-show_format','-of','json',str(path)]))

def contact(frames, path, columns=4, cell=(480,270)):
    w,h = cell
    sheet=Image.new('RGB',(columns*(w+12)+12, ((len(frames)+columns-1)//columns)*(h+34)+12),(15,15,15))
    d=ImageDraw.Draw(sheet)
    for i,(label,arr) in enumerate(frames):
        x=12+(i%columns)*(w+12); y=12+(i//columns)*(h+34)
        im=Image.fromarray(arr).convert('RGB'); im.thumbnail(cell,Image.Resampling.LANCZOS)
        sheet.paste(im,(x,y)); d.text((x,y+h+4),label,fill='white')
    sheet.save(path)

def main():
    reports={}
    for name,key in [('reference video.mp4','short'),('lv_0_20261021030852.mp4','extended')]:
        path=INPUT/name
        print('Analyzing',name,flush=True)
        reports[key]=probe(path)
        p=subprocess.Popen([ffmpeg(),'-v','error','-i',str(path),'-vf','scale=480:270','-pix_fmt','rgb24','-f','rawvideo','-'],stdout=subprocess.PIPE)
        rows=[]; frames=[]; prev=None; i=0
        while True:
            data=p.stdout.read(480*270*3)
            if not data: break
            rgb=np.frombuffer(data,np.uint8).reshape(270,480,3)
            gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
            ys,xs=np.where(gray>40)
            rows.append([i,i/30,float(gray.mean()),float(np.mean(gray>40)),float(np.abs(gray.astype(float)-prev).mean()) if prev is not None else 0, float(xs.mean()) if len(xs) else 0,float(ys.mean()) if len(ys) else 0])
            if i%15==0 or (key=='extended' and 450<=i<=540 and i%3==0):
                frames.append((f'{key} {i/30:.3f}s | frame {i}',rgb.copy()))
            prev=gray.astype(float); i+=1
        assert p.wait()==0
        with (ROOT/f'analysis/{key}_every_frame.csv').open('w',newline='') as f:
            cw=csv.writer(f); cw.writerow(['frame','time','mean_luma','bright_fraction','mean_abs_frame_change','bright_centroid_x_480','bright_centroid_y_270']); cw.writerows(rows)
        for j in range(0,len(frames),24): contact(frames[j:j+24],ROOT/f'analysis/{key}_dense_{j//24+1}.jpg')
        raw=subprocess.check_output([ffmpeg(),'-v','error','-i',str(path),'-vn','-ac','1','-ar','8000','-f','f32le','-'])
        a=np.frombuffer(raw,np.float32)
        blocks=[{'time':j/8000,'rms':float(np.sqrt(np.mean(a[j:j+800]**2))),'peak':float(np.max(np.abs(a[j:j+800])))} for j in range(0,len(a),800)]
        (ROOT/f'analysis/{key}_audio_envelope.json').write_text(json.dumps(blocks,indent=2))
        print(key, i, 'frames examined',flush=True)
    (ROOT/'analysis/input_metadata.json').write_text(json.dumps(reports,indent=2))
    for key,name in [('extended','lv_0_20261021030852.mp4'),('short','reference video.mp4')]:
        subprocess.run([ffmpeg(),'-y','-v','error','-i',str(INPUT/name),'-vn','-c:a','copy',str(ROOT/f'assets/{key}_original_audio.m4a')],check=True)

if __name__=='__main__': main()
