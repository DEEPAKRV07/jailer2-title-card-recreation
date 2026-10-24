"""Same animation equations, evaluated and rasterized on CUDA; one host transfer at output."""
import importlib.util,time
from pathlib import Path
import math
import numpy as np
import cupy as cp
import gpu_ops as ops

_spec=importlib.util.spec_from_file_location('_cuda_animation_equations',Path(__file__).with_name('renderer.py'))
_base=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_base)
_base.np=ops.ArrayFacade();_base.cv2=ops.CVFacade()
ease=_base.ease;window=_base.window

class GPURenderer(_base.Renderer):
    def __init__(self,*args,**kw):
        self.starting_ops=dict(ops.COUNTS)
        self.gpu_frame_milliseconds=0;self.gpu_frames=0
        super().__init__(*args,**kw)
        for name in ['sx','sy','sz','sp','sv','rx','ry','rv','rl','rp','phase','ttravel','tx','ty','tv','ta']:
            setattr(self,name,cp.asarray(getattr(self,name)))
        # Keep the legacy hash field once; its value is independent of text and time.
        spacing=max(3,self.c['typography']['jewel_spacing_1080']*self.scale)
        self.hashes=cp.mod(cp.sin(cp.floor(self.xx/spacing)*12.9898+cp.floor(self.yy/spacing)*78.233)*43758.5453,1)
        for data in self.texts.values():data['phase']=cp.asarray(data['phase'])
    def field_commands(self,t):
        fade=1-float(ease((t-1.1)/1.5));settle=float(ease((t-5.6)/.8))*.28
        if fade>.002:
            x=cp.mod(self.sx+cp.sin(t*.45+self.sp)*.05*t,1); y=self.sy*.50+.48-t*self.sv
            amp=fade*(.35+.65*self.sz)
        elif settle>.002:
            x=cp.mod(self.sx+t*self.sv*.1,1);y=.9+self.sy*.12+cp.sin(t*.6+self.sp)*.04;amp=settle*self.sz
        else:return cp.empty((0,32),cp.float32)
        px=(x*self.w).astype(cp.int32);py=(y*self.h).astype(cp.int32)
        idx=cp.arange(len(x));r=cp.maximum(1,(self.c['particles']['size_1080']*self.scale*(.4+self.sz*1.8)).astype(cp.int32))
        r=cp.where((idx%83==0)&(fade>.05),((12+self.sz*16)*self.scale).astype(cp.int32),r)
        q=ops.ellipses(px,py,r,cp.maximum(1,r//2),cp.sin(t+self.sp)*80*math.pi/180,amp*self.c['particles']['brightness'])
        stars=((idx%9==0)|(idx%83==0))&(fade>.05)
        a=cp.arange(10)[None,:]*math.pi/5+t*.8+self.sp[:,None]-math.pi/2
        rad=cp.where(cp.arange(10)%2==0,r[:,None]*2,r[:,None]*2*.43)
        vertices=cp.stack([px[:,None]+cp.cos(a)*rad,py[:,None]+cp.sin(a)*rad],axis=2).astype(cp.int32)
        q=cp.where(stars[:,None],ops.polygons(vertices,amp*self.c['particles']['brightness']),q)
        return q[(py>=0)&(py<self.h)]
    def rain_commands(self,t):
        c=self.c['rain'];settle=float(ease((t-5)/1.3));fade=float(ease((t-1.45)/.8))*(1-settle*(1-c['settled_density']))
        if fade<.001:return cp.empty((0,32),cp.float32)
        x=((self.rx+cp.sin(t*.3+self.rp)*.002)*self.w).astype(cp.int32)
        y=((cp.mod(self.ry+t*c['speed']*self.rv,1.5)-.2)*self.h).astype(cp.int32)
        length=(c['length']*self.h*self.rl*(1-settle*.7)).astype(cp.int32);val=fade*c['brightness']*(.3+self.rl*.7)
        ids=cp.arange(len(x));valid=(y>=0)&(y-length<=self.h)
        x,y,length,val,ids,rl=x[valid],y[valid],length[valid],val[valid],ids[valid],self.rl[valid]
        if len(x)==0:return cp.empty((0,32),cp.float32)
        parts=[ops.lines(x,y-length,x,y,ops.line_radius(max(1,round(self.scale*.9))),val*.65)]
        q=ops.ellipses(x,y,max(1,round(self.scale*1.3)),cp.maximum(2,cp.rint(self.scale*(4+rl*8))),0,val)
        q[ids%4!=0,2:6]=-100
        parts.append(q)
        for j in range(5):parts.append(ops.circles(x,y-j*max(3,int(6*self.scale)),max(1,round(self.scale*1.45)),val*(1-j*.16)))
        # Interleave per-rain-column draw calls to preserve overwrite order.
        return cp.stack(parts,axis=1).reshape(-1,32)
    def portrait_frame(self,t):
        ops.COUNTS['cuda_particle_equations']+=1
        im=cp.zeros((self.h,self.w),cp.float32)
        ops.draw(im,cp.concatenate([self.field_commands(t),self.rain_commands(t)]))
        c=self.c['portrait'];p=(t-c['reveal_start'])/(c['reveal_end']-c['reveal_start'])
        if p>0:im+=self.portrait*ease((p-self.arrival)/.13)
        u=(t-self.ta+self.ttravel)/self.ttravel
        active=cp.where((u>0)&(u<1.15))[0]
        if len(active):
            u=u[active];rem=1-ease(u)
            x=self.tx[active]+cp.sin(t*c['turbulence']+self.phase[active])*self.w*c['drift']*rem
            y=self.ty[active]-self.h*(.15+self.ttravel[active]*.2)*rem
            valid=(y>=0)&(y<self.h)
            amp=self.tv[active]*c['particle_brightness']*ease(u*5)*(1-ease((u-1)/.15))
            tail=((4+rem*65)*self.scale).astype(cp.int32)
            x,y,amp,tail=cp.rint(x[valid]),cp.rint(y[valid]),amp[valid],tail[valid]
            lines=ops.lines(x,y-tail,x,y,ops.line_radius(max(1,round(self.scale*.8))),amp*.65)
            circles=ops.circles(x,y,max(1,round(c['particle_size_1080']*self.scale)),amp)
            ops.draw(im,cp.stack([lines,circles],axis=1).reshape(-1,32))
        zoom=1+self.c['effects']['camera_zoom']*float(ease((t-2)/5))
        if zoom!=1:
            matrix=ops.cv2.getRotationMatrix2D((self.w*.5,self.h*.48),0,zoom)
            im=ops.image_sample(im,(self.w,self.h),1,matrix)
        return im
    def text_frame(self,data,t,progress=1):
        ops.COUNTS['cuda_text_reveal']+=1
        gate=ease((progress-self.hashes*.82)/.18) if progress<1 else 1
        sweep=cp.exp(-((self.xx/self.w-(t*.16%1.6-.3))/.035)**2)*.35
        return (data['tex']*(.85+sweep)*gate).astype(cp.float32)
    def glints(self,im,data,t,opacity):
        e=self.c['effects'];amp=cp.maximum(0,cp.sin(t*e['glint_frequency']*2*math.pi+data['phase']))**12*opacity*e['glint_intensity']
        valid=amp>=.02;points=data['points'][valid];amp=amp[valid]
        if not len(amp):return
        r=cp.maximum(2,cp.rint((3+11*amp)*self.scale));x=points[:,1];y=points[:,0];w=ops.line_radius(max(1,round(self.scale)))
        ops.draw(im,cp.stack([ops.lines(x-r,y,x+r,y,w,amp*.8),ops.lines(x,y-r,x,y+r,w,amp)],axis=1).reshape(-1,32))
    def opening_star(self,t):
        o=self.c['opening'];im=cp.zeros((self.h,self.w),cp.float32);local=(t-o['star_start'])/(o['star_end']-o['star_start'])
        if not 0<local<1:return im
        opacity=window(local,0,1,.12,.22);r=self.h*(.5*(1-ease(local))+.004)
        pts=_base.star_points(self.w*.5,self.h*.48,r,t*.85)
        center=cp.tile(cp.asarray([self.w*.5,self.h*.48],cp.int32),(10,1))
        tri=cp.stack([center,pts,cp.roll(pts,-1,axis=0)],axis=1)
        vals=(.23+.7*cp.maximum(0,cp.cos(cp.arange(10)*math.pi/5-t*1.4)))*opacity
        ops.draw(im,ops.polygons(tri,vals));return im
    def frame_device(self,t):
        start=cp.cuda.Event();end=cp.cuda.Event();start.record()
        frame=super().frame(t);end.record();end.synchronize()
        self.gpu_frame_milliseconds+=cp.cuda.get_elapsed_time(start,end);self.gpu_frames+=1
        ops.COUNTS['cuda_composite']+=1
        return frame
    def frame(self,t):return cp.asnumpy(self.frame_device(t))
    def finish_frame(self,arr,previous,width,shutter):
        if arr.shape[1]!=width:arr=ops.image_sample(arr,(width,round(width*self.h/self.w)),3)
        out=arr
        if previous is not None and shutter:
            ops.COUNTS['cuda_temporal_blur']+=1
            out=cp.clip(cp.rint(arr.astype(cp.float32)*(1-shutter)+previous.astype(cp.float32)*shutter),0,255).astype(cp.uint8)
        small=ops.image_sample(out,(320,180),1);gray=ops.CVFacade().cvtColor(small,ops.cv2.COLOR_RGB2GRAY)
        metrics=[float(gray.mean()),float((gray>245).mean())]
        return out,arr,metrics
    def telemetry(self):
        return {'backend':'CuPy CUDA','device':cp.cuda.runtime.getDeviceProperties(cp.cuda.Device().id)['name'].decode(),'frames_executed':self.gpu_frames,'cuda_event_frame_ms':self.gpu_frame_milliseconds,'kernel_operation_counts':{k:v-self.starting_ops.get(k,0) for k,v in ops.COUNTS.items()},'cuda_runtime':cp.cuda.runtime.runtimeGetVersion(),'cuda_driver':cp.cuda.runtime.driverGetVersion(),'device_memory_used_bytes':cp.get_default_memory_pool().used_bytes(),'cpu_exceptions':['File/image decoding and PNG/JPEG writing','Pillow/FreeType font shaping and glyph masks (no matching GPU API)','OpenCV GrabCut segmentation, cached by source content (installed OpenCV has no CUDA GrabCut)','NumPy PCG64 seeded random sampling to retain seeded sequence semantics','Small scalar timeline/control and Gaussian/affine coefficient generation','FFmpeg AAC audio encoding and MP4 muxing']}
