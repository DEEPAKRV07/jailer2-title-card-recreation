"""Reapply configured audio to already-rendered project outputs without re-encoding video."""
import json,subprocess
from pathlib import Path
from analyze import ffmpeg
from main import load,validate
ROOT=Path(__file__).resolve().parent
c=load(ROOT/'config.json')
commands=[]
o=c['output'];pw=o['preview_width'];ph=round(pw*o['height']/o['width']/2)*2;sp=Path(o['preview_path'])
targets=[(ROOT/o['path'],c['sequence_preset'],o['width'],o['height']),(ROOT/o['preview_path'],c['sequence_preset'],pw,ph),(ROOT/sp.with_name(sp.stem+'_portrait_reveal'+sp.suffix),'portrait_reveal',pw,ph)]
for path,preset,w,h in targets:
    if not path.exists(): continue
    duration=c['presets'][preset]['duration']; source=ROOT/(c['audio']['source'] or c['presets'][preset]['audio'])
    tmp=path.with_name(path.stem+'_audio_corrected.mp4')
    a=c['audio']; filters=[f"volume={a['volume']}"]
    if a['offset']>0: filters.insert(0,f"adelay={round(a['offset']*1000)}:all=1")
    if a['offset']<0: filters[:0]=[f"atrim=start={-a['offset']}",'asetpts=PTS-STARTPTS']
    if a['fade_in']>0: filters.append(f"afade=t=in:d={a['fade_in']}")
    if a['fade_out']>0: filters.append(f"afade=t=out:st={duration-a['fade_out']}:d={a['fade_out']}")
    cmd=[ffmpeg(),'-y','-v','warning','-i',str(path),'-i',str(source),'-map','0:v:0','-map','1:a:0','-c:v','copy','-af',','.join(filters),'-c:a',a['codec'],'-b:a',a['bitrate'],'-ar',str(a['sample_rate']),'-ac',str(a['channels']),'-t',str(duration),'-movflags','+faststart',str(tmp)]
    subprocess.run(cmd,check=True); tmp.replace(path); commands.append(cmd)
    validate(path,c,w,h,round(duration*30))
(ROOT/'qa/audio_correction_commands.json').write_text(json.dumps(commands,indent=2))
