"""Persist the manually inspected scene findings alongside the measured frame/audio data."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def scene(a,b,name,composition,motion,particles,transition,palette='black / silver white'):
    return dict(start=a,end=b,duration=round(b-a,6),name=name,composition=composition,motion=motion,particles=particles,transition=transition,palette=palette)

short=[
scene(0,1.8,'Star field / flying fragments','Full frame, most brightness below center','Swirling/tumbling fragments, drifting laterally and into depth; no recoverable exact velocity','Hundreds of varied-size stars and fragments, high contrast','Field thins; individual trails appear'),
scene(1.8,3.0,'Vertical rain','Mostly central columns spanning the frame','Predominantly vertical streaks, downward trails; apparent speed varies with depth','Sparse bright heads, dotted tails, narrow elongated lights','Overlap from fragments into rain'),
scene(3.0,5.7,'Portrait assembly','Head near x=.55, y=.28; shoulders widen through lower half','Streaks coalesce into face/hair/shoulders; motion settles smoothly','Scattered high-luma contour samples and long vertical strands','Gradual spatial accumulation, not a full photograph fade'),
scene(5.7,9.033333,'Portrait hold','Approx. bounds x=.22–.73, y=.04–1; source pose is asymmetric','Near-static face; small particles continue near bottom','Black facial/clothing areas, white brows/edges, sparse vertical shirt trails','Stable hold to clip end')]
extended=[
scene(0,1.9,'Faceted metallic star','Initially oversized, centered; contracts to central luminous point','Rotation and rapid recession / scale decrease; eased settling','No dense particle field yet; concentrated glow','Starts black at frame 0, bright star at frame 1, shrinks into black'),
scene(1.9,3.766667,'Jeweled S','Centered letter, approx. width .33 and height .62','Fragmented/partial emergence, then stable letter with glints','Close regular crystal grid, cool highlights','Bright expansion/flash around frames 110–112; cut to field at frame 113','black / silver / cool blue white'),
scene(3.766667,5.7,'Stars and flying fragments','Low sparkling horizon then scattered across full frame','Upward/lateral scattering, tumbling, depth variation','Hundreds of stars, several larger foreground stars','Fragments turn into rain'),
scene(5.7,7.0,'Digital rain onset','Central columns; emerging subject volume','Vertical elongated lights, fast local streaking','Sparse bright lights with dotted/continuous tails','Progressive overlap with subject'),
scene(7.0,9.6,'Portrait assembly','Head approx x=.55, y=.27; torso approx x=.22–.72','Contours consolidate; long strands settle, small apparent framing change','Fine silver points and vertical lines; strong rim highlights','Spatial reveal becomes stable portrait'),
scene(9.6,12.7,'Portrait hold','Head and torso fill most of image height; deep surrounding black','Very limited portrait motion; ambient particles below','Dense hair/face texture, sparse shirt lines; black negative space','Title begins overlapping near end'),
scene(12.7,13.5,'Portrait to first title','Centered two-line title over fading portrait','Portrait dims while dots form title','Dispersing floor particles and jewel assembly','Soft overlapping dissolve'),
scene(13.5,15.9,'THARAN / CREATIONS reference card','Centered stacked serif lines; safe margins','Slow enlargement; glints travel over letters','Regular gemstones with small blooms','Rapid smooth fade near 15.6–15.9','black / silver / pale blue'),
scene(15.9,17.8,'SURYA / THARAN reference card','Centered narrow two-line dotted lettering','Dots appear sequentially; stable short hold','Sparse blue points, little bloom','Fades around 17.4–17.7','black / saturated blue'),
scene(17.8,19.7,'EDITOR reference card','Centered single bold serif word','Particle assembly then slight expansion','Silver jewels and localized glints','Fade before next card','black / silver / pale blue'),
scene(19.7,21.8,'VISUAL / NINJA reference card','Centered two-line serif text','Particle formation then slow enlargement','Silver gemstones; glints above letters','Fade to black by end','black / silver / pale blue')]
data={'method':'All 925 video frames decoded to 480x270 RGB; per-frame luma, bright coverage, centroid and absolute frame change saved. Visually inspected 0.5-second contact sheets plus 0.1-second samples from 15–18 seconds. Original timestamp-matched larger frames inspected in comparison sheets. No reference pixels used in renderer.',
'timing_precision':'Stage boundaries are visual estimates, generally +/-0.1–0.3 seconds, not recovered authoring keyframes. The 3.766667-second field cut is detected at frame 113 in the every-frame difference trace. Rates/easing/depth descriptions are qualitative observations, not measured optical flow.',
'short':short,'extended':extended,
'adaptation':{'opening':'K instead of S','main_name':'KARTHIKEYAN','later_credits':'Empty configurable credit slots; main name held through them. The original blue credit card and subsequent copy are not reproduced.','portrait':'Supplied 1600x899 stylized JPEG. Uniform-scale masked composition preserves pose and features, so shoulder breadth and head inclination differ.','flash':'Reference full-screen flash is replaced with a softened transition.'}}
for key in ['short','extended']:
    blocks=json.loads((ROOT/f'analysis/{key}_audio_envelope.json').read_text())
    data[key+'_audio_landmarks']={'measurement':'0.1s RMS blocks after 8 kHz mono analysis resampling; no semantic listening claims. Stereo original peak measured separately for output headroom.','highest_energy_blocks':sorted(blocks,key=lambda x:x['rms'],reverse=True)[:8]}
(ROOT/'analysis/scene_breakdown.json').write_text(json.dumps(data,indent=2))
lines=['# Reference scene analysis','',data['method'],'',data['timing_precision'],'','## Shared visual language','',
'Deep black environment, white/silver luminous points and trails, high-contrast portrait, locally blooming glints. Text uses a jewel grid with cool highlights. Rain predominantly travels vertically; fragments swirl laterally and through apparent depth. Portrait motion settles rather than freezing abruptly. Exact camera transforms and particle velocities cannot be recovered from these flattened references.','']
for key,scenes in [('Short portrait clip',short),('Extended edit',extended)]:
    lines+=['## '+key,'','| Start–end (s) | Duration | Stage | Composition | Motion and particles | Transition / palette |','|---|---:|---|---|---|---|']
    for s in scenes: lines.append(f"| {s['start']:.3f}–{s['end']:.3f} | {s['duration']:.3f} | {s['name']} | {s['composition']} | {s['motion']}; {s['particles']} | {s['transition']}; {s['palette']} |")
    lines+=['']
lines+=['## Audio landmarks','','The strongest 0.1-second RMS blocks in the extended analysis occur around 2.9, 9.3–9.4, 14.7 and 8.4 seconds. These are measured energy landmarks, not asserted musical beats. The original stereo AAC is extracted without changing timestamps; the output applies 0.65 gain to leave headroom. The short preset uses the short clip audio. No music is synthesized or substituted.','','## Adaptation and limitations','']
lines += ['- '+v for v in data['adaptation'].values()]
lines+=['','No pixelwise similarity score is used. The new person, letter and longer name must differ. Visual review documents the differences instead of claiming an exact match.']
(ROOT/'analysis/scene_breakdown.md').write_text('\n'.join(lines),encoding='utf-8')
print('Scene breakdown written')
