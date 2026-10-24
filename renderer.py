"""Deterministic, source-photo-driven procedural animation. No reference-video input."""
import math
import warnings
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from portrait_source import prepare_source

def ease(x):
    x=np.clip(x,0,1)
    return x*x*x*(x*(x*6-15)+10)

def window(t,a,b,fi=.3,fo=.3):
    return float(ease((t-a)/max(fi,.001))*(1-ease((t-(b-fo))/max(fo,.001))))

def star_points(x,y,r,angle=0):
    a=np.arange(10)*np.pi/5+angle-np.pi/2
    rad=np.where(np.arange(10)%2==0,r,r*.43)
    return np.stack([x+np.cos(a)*rad,y+np.sin(a)*rad],1).astype(np.int32)

class Renderer:
    def __init__(self, cfg, root, width=None):
        self.c=cfg; self.root=Path(root); self.preset=cfg['presets'][cfg['sequence_preset']]
        self.w=width or cfg['output']['width']; self.h=round(self.w*cfg['output']['height']/cfg['output']['width']/2)*2
        self.scale=self.h/1080; self.rng=np.random.default_rng(cfg['seed'])
        cv2.setNumThreads(4)
        self.yy,self.xx=np.mgrid[0:self.h,0:self.w].astype(np.float32)
        self.prepare_portrait(); self.prepare_particles(); self.texts={}
        if cfg['sequence_preset']=='extended_credits':
            o=cfg['opening']; self.texts['opening']=self.prepare_text(o['letter'],o['font_height'],o['position'],0)
            for i,card in enumerate(cfg['titles']):
                if card['text']:
                    self.texts[i]=self.prepare_text(card['text'],card['font_height'],card['position'],card.get('tracking',cfg['typography']['tracking']),card.get('alignment','center'))
                    if card.get('subtitle'):
                        pos=[card['position'][0],card['position'][1]+card['font_height']*.65]
                        self.texts[f'sub{i}']=self.prepare_text(card['subtitle'],card.get('subtitle_height',.07),pos,card.get('tracking',.012))

    def prepare_portrait(self):
        c=self.c['portrait']; src,alpha=prepare_source(self.root/c['image'],c,self.root,self.c['seed'])
        sh,sw=src.shape[:2]
        cr=c['crop']; x0,y0,x1,y1=[int(v*d) for v,d in zip(cr,[sw,sh,sw,sh])]
        src=src[y0:y1,x0:x1]; alpha=alpha[y0:y1,x0:x1]
        ys,xs=np.where(alpha>128)
        if not len(xs): raise ValueError('Empty portrait mask')
        top,bottom=ys.min(),ys.max(); left,right=xs.min(),xs.max()
        factor=self.h*c['height_fraction']/max(1,bottom-top)
        if c['fit']=='contain': factor=min(factor,self.w*.84/max(1,right-left))
        center=(left+right)/2
        matrix=np.array([[factor,0,self.w*c['anchor'][0]-center*factor],[0,factor,self.h*c['anchor'][1]-top*factor]],np.float32)
        g=cv2.cvtColor(src,cv2.COLOR_BGR2GRAY).astype(np.float32)/255
        g=cv2.warpAffine(g,matrix,(self.w,self.h),flags=cv2.INTER_CUBIC)
        a=cv2.warpAffine(alpha.astype(np.float32)/255,matrix,(self.w,self.h),flags=cv2.INTER_LINEAR)
        a=cv2.GaussianBlur(a,(0,0),max(.5,c['feather_px_1080']*self.scale))
        g=np.clip((g-c['black_level'])*c['contrast'],0,1)**c['gamma']*c['brightness']
        # Retain high-frequency identity-bearing detail; remove the photograph's rectangular background.
        sx=cv2.Sobel(g,cv2.CV_32F,1,0,ksize=3); sy=cv2.Sobel(g,cv2.CV_32F,0,1,ksize=3)
        edges=np.minimum(np.sqrt(sx*sx+sy*sy)*.25,1)
        spacing=max(1.7,2.5*self.scale)
        vertical=.65+.35*np.cos(self.xx*2*np.pi/spacing)**8
        dots=(.5+.5*np.cos(self.xx*2*np.pi/spacing))*(.5+.5*np.cos(self.yy*2*np.pi/spacing))
        texture=(1-c['line_strength'])+c['line_strength']*vertical
        texture*=1-c['stipple_strength']+c['stipple_strength']*dots
        self.portrait=np.clip((g*texture+edges*c['edge_strength'])*a,0,1).astype(np.float32)
        self.alpha=a
        # Fixed spatial arrival map, never fresh frame noise: scattered columns converge on the face.
        noise=cv2.resize(self.rng.random((max(8,self.h//8),max(8,self.w//5))).astype(np.float32),(self.w,self.h),interpolation=cv2.INTER_LINEAR)
        cols=cv2.resize(self.rng.random((1,max(16,self.w//7))).astype(np.float32),(self.w,self.h),interpolation=cv2.INTER_NEAREST)
        y=self.yy/self.h
        if c['reveal_direction']=='bottom_up': y=1-y
        elif c['reveal_direction']=='center_out': y=np.abs(y-.5)*2
        self.arrival=(.12+.45*noise+.25*cols+.23*y-.13*np.minimum(edges,1)).astype(np.float32)
        self.arrival=np.clip(self.arrival,.05,.97)
        weights=(self.portrait**1.3).ravel(); weights/=weights.sum()
        idx=self.rng.choice(len(weights),c['particle_count'],p=weights)
        self.tx=(idx%self.w).astype(np.float32); self.ty=(idx//self.w).astype(np.float32)
        self.tv=self.portrait.ravel()[idx]
        self.ta=self.arrival.ravel()[idx]*(c['reveal_end']-c['reveal_start'])+c['reveal_start']
        self.phase=self.rng.uniform(0,2*np.pi,len(idx))
        self.ttravel=self.rng.uniform(.65,1.3,len(idx))*c['travel_seconds']

    def prepare_particles(self):
        n=self.c['particles']['count']
        self.sx=self.rng.uniform(0,1,n); self.sy=self.rng.uniform(0,1,n); self.sz=self.rng.uniform(.15,1,n)
        self.sp=self.rng.uniform(0,2*np.pi,n); self.sv=self.rng.uniform(.03,.15,n)
        n=self.c['rain']['density']
        self.rx=self.rng.uniform(.12,.88,n); self.ry=self.rng.uniform(-1,1,n); self.rv=self.rng.uniform(.6,1.5,n)
        self.rl=self.rng.uniform(.15,1,n); self.rp=self.rng.uniform(0,2*np.pi,n)

    def font(self,size):
        for font in [self.c['typography']['font'],self.c['typography']['fallback_font']]:
            path=Path(font)
            if not path.is_absolute(): path=self.root/path
            if path.exists(): return ImageFont.truetype(str(path),size)
            warnings.warn(f'Font unavailable: {font}; trying fallback')
        raise ValueError('No configured font found. Set typography.font to an installed TTF font.')

    def prepare_text(self,text,height,position,tracking,align='center'):
        mask=Image.new('L',(self.w,self.h)); d=ImageDraw.Draw(mask)
        size=round(height*self.h*1.33); font=self.font(size); gap=tracking*self.h
        lines=text.split('\n'); widths=[sum(font.getlength(ch) for ch in line)+max(0,len(line)-1)*gap for line in lines]
        maxwidth=self.w*(1-2*self.c['typography']['safe_area'])
        if max(widths)>maxwidth:
            ratio=maxwidth/max(widths); size=max(8,round(size*ratio)); gap*=ratio; font=self.font(size)
            widths=[sum(font.getlength(ch) for ch in line)+max(0,len(line)-1)*gap for line in lines]
        lineheight=size*1.05
        for i,(line,width) in enumerate(zip(lines,widths)):
            bbox=font.getbbox(line or 'A'); actual=bbox[3]-bbox[1]
            y=position[1]*self.h+(i-(len(lines)-1)/2)*lineheight-actual/2-bbox[1]
            x=position[0]*self.w-(width/2 if align=='center' else width if align=='right' else 0)
            for ch in line:
                d.text((round(x),round(y)),ch,font=font,fill=255); x+=font.getlength(ch)+gap
        m=np.array(mask,dtype=np.float32)/255
        spacing=max(3.0,self.c['typography']['jewel_spacing_1080']*self.scale*(1.8 if len(text)==1 else 1))
        # Analytic miniature faceted gemstones, rendered within the editable font mask.
        dx=((self.xx+spacing/2)%spacing-spacing/2)/(spacing*.45)
        dy=((self.yy+spacing/2)%spacing-spacing/2)/(spacing*.45)
        r=np.sqrt(dx*dx+dy*dy); angle=np.arctan2(dy,dx)
        facet=.32+.4*np.maximum(0,np.cos(angle*6+.6))+.24*np.maximum(0,-dx-dy)
        gems=np.where(r<1,facet*(.5+.5*np.sqrt(np.maximum(0,1-r*r))),.025)
        gems+=np.exp(-((dx+.3)**2+(dy+.4)**2)/.045)*.65
        edge=cv2.morphologyEx(m,cv2.MORPH_GRADIENT,np.ones((3,3),np.uint8))*.25
        tex=(m*(.09+gems*1.9)+edge*.8).astype(np.float32)
        # Broad horizontal shimmer only; individual starbursts are placed on actual glyph pixels.
        points=np.column_stack(np.where(m>.9))
        sel=points[self.rng.integers(0,len(points),18)] if len(points) else np.zeros((0,2))
        return {'mask':m,'tex':tex,'points':sel,'phase':self.rng.uniform(0,6.28,len(sel))}

    def text_frame(self, data,t,progress=1):
        if progress<1:
            # Per-jewel sequential assembly, independent of the portrait mask and its RNG.
            spacing=max(3,self.c['typography']['jewel_spacing_1080']*self.scale)
            hashes=np.mod(np.sin(np.floor(self.xx/spacing)*12.9898+np.floor(self.yy/spacing)*78.233)*43758.5453,1)
            gate=ease((progress-hashes*.82)/.18)
        else: gate=1
        sweep=np.exp(-((self.xx/self.w-(t*.16%1.6-.3))/.035)**2)*.35
        im=data['tex']*(.85+sweep)*gate
        return im.astype(np.float32)

    def glints(self,im,data,t,opacity):
        e=self.c['effects']
        for (y,x),phase in zip(data['points'],data['phase']):
            amp=max(0,math.sin(t*e['glint_frequency']*2*np.pi+phase))**12*opacity*e['glint_intensity']
            if amp<.02: continue
            r=max(2,round((3+11*amp)*self.scale))
            cv2.line(im,(int(x)-r,int(y)),(int(x)+r,int(y)),float(amp*.8),max(1,round(self.scale)),cv2.LINE_AA)
            cv2.line(im,(int(x),int(y)-r),(int(x),int(y)+r),float(amp),max(1,round(self.scale)),cv2.LINE_AA)

    def field(self,t,im):
        # Star fragments travel continuously from a low horizon into the emerging rain.
        fade=1-float(ease((t-1.1)/1.5))
        settle=float(ease((t-5.6)/.8))*.28
        for i in range(len(self.sx)):
            z=self.sz[i]
            if fade>.002:
                x=(self.sx[i]+math.sin(t*.45+self.sp[i])*.05*t)%1
                y=(self.sy[i]*.50+.48-t*self.sv[i])
                amp=fade*(.35+.65*z)
            elif settle>.002:
                x=(self.sx[i]+t*self.sv[i]*.1)%1
                y=.9+self.sy[i]*.12+math.sin(t*.6+self.sp[i])*.04
                amp=settle*z
            else: continue
            px,py=int(x*self.w),int(y*self.h)
            if not 0<=py<self.h: continue
            r=max(1,int(self.c['particles']['size_1080']*self.scale*(.4+z*1.8)))
            if i%83==0 and fade>.05: r=int((12+z*16)*self.scale)
            val=float(amp*self.c['particles']['brightness'])
            if (i%9==0 or i%83==0) and fade>.05:
                cv2.fillPoly(im,[star_points(px,py,r*2,t*.8+self.sp[i])],val,cv2.LINE_AA)
            else: cv2.ellipse(im,(px,py),(r,max(1,r//2)),math.sin(t+self.sp[i])*80,0,360,val,-1,cv2.LINE_AA)

    def rain(self,t,im):
        c=self.c['rain']; settle=float(ease((t-5.0)/1.3))
        fade=float(ease((t-1.45)/.8))*(1-settle*(1-c['settled_density']))
        if fade<.001: return
        for i in range(len(self.rx)):
            x=int((self.rx[i]+math.sin(t*.3+self.rp[i])*.002)*self.w)
            y=int(((self.ry[i]+t*c['speed']*self.rv[i])%1.5-.2)*self.h)
            length=int(c['length']*self.h*self.rl[i]*(1-settle*.7))
            val=float(fade*c['brightness']*(.3+self.rl[i]*.7))
            if y<0 or y-length>self.h: continue
            cv2.line(im,(x,y-length),(x,y),val*.65,max(1,round(self.scale*.9)),cv2.LINE_AA)
            if i%4==0:
                cv2.ellipse(im,(x,y),(max(1,round(self.scale*1.3)),max(2,round(self.scale*(4+self.rl[i]*8)))),0,0,360,val,-1,cv2.LINE_AA)
            for j in range(5):
                yy=y-j*max(3,int(6*self.scale))
                cv2.circle(im,(x,yy),max(1,round(self.scale*1.45)),val*(1-j*.16),-1,cv2.LINE_AA)

    def portrait_frame(self,t):
        im=np.zeros((self.h,self.w),np.float32); self.field(t,im); self.rain(t,im)
        c=self.c['portrait']; p=(t-c['reveal_start'])/(c['reveal_end']-c['reveal_start'])
        if p>0:
            gate=ease((p-self.arrival)/.13)
            im+=self.portrait*gate
        # Each bright source sample has an arrival time. Its falling trail deposits into the mask.
        age=t-self.ta; u=(age+self.ttravel)/self.ttravel
        active=np.where((u>0)&(u<1.15))[0]
        for i in active:
            q=float(ease(u[i])); rem=1-q
            x=self.tx[i]+math.sin(t*c['turbulence']+self.phase[i])*self.w*c['drift']*rem
            y=self.ty[i]-self.h*(.15+self.ttravel[i]*.2)*rem
            if not 0<=y<self.h: continue
            amp=float(self.tv[i]*c['particle_brightness']*ease(u[i]*5)*(1-ease((u[i]-1)/.15)))
            tail=int((4+rem*65)*self.scale)
            cv2.line(im,(round(x),round(y)-tail),(round(x),round(y)),amp*.65,max(1,round(self.scale*.8)),cv2.LINE_AA)
            cv2.circle(im,(round(x),round(y)),max(1,round(c['particle_size_1080']*self.scale)),amp,-1,cv2.LINE_AA)
        zoom=1+self.c['effects']['camera_zoom']*float(ease((t-2)/5))
        if zoom!=1:
            matrix=cv2.getRotationMatrix2D((self.w*.5,self.h*.48),0,zoom)
            im=cv2.warpAffine(im,matrix,(self.w,self.h),flags=cv2.INTER_LINEAR)
        return im

    def opening_star(self,t):
        o=self.c['opening']; im=np.zeros((self.h,self.w),np.float32)
        local=(t-o['star_start'])/(o['star_end']-o['star_start'])
        if not 0<local<1: return im
        opacity=window(local,0,1,.12,.22)
        r=self.h*(.5*(1-ease(local))+.004)
        pts=star_points(self.w*.5,self.h*.48,r,t*.85)
        center=np.array([self.w*.5,self.h*.48],np.int32)
        for i in range(10):
            tri=np.array([center,pts[i],pts[(i+1)%10]])
            val=(.23+.7*max(0,math.cos(i*np.pi/5-t*1.4)))*opacity
            cv2.fillConvexPoly(im,tri,float(val),cv2.LINE_AA)
        return im

    def frame(self,t):
        extended=self.c['sequence_preset']=='extended_credits'
        im=np.zeros((self.h,self.w),np.float32); text=np.zeros_like(im)
        if extended:
            o=self.c['opening']
            if t<o['star_end']: im+=self.opening_star(t)
            op=window(t,o['letter_start'],o['letter_end'],o['fade_in'],o['fade_out'])
            if op>.001:
                data=self.texts['opening']; text+=self.text_frame(data,t,float(ease((t-o['letter_start'])/o['fade_in'])))*op
                self.glints(text,data,t,op)
        off=self.preset['portrait_offset']; pout=1-float(ease((t-self.preset['portrait_fade_start'])/(self.preset['portrait_fade_end']-self.preset['portrait_fade_start'])))
        if off<=t and pout>.001:
            fade=float(ease((t-off)/.2)) if extended else 1
            im+=self.portrait_frame(t-off)*pout*fade
        if extended:
            cards=self.c['titles']
            for i,card in enumerate(cards):
                if not card['text']: continue
                op=window(t,card['start'],card['end'],card['fade_in'],card['fade_out'])
                # A configured later card takes over the long main-name hold.
                if i==0:
                    for later in cards[1:]:
                        if later['text']: op*=1-window(t,later['start'],later['end'],later['fade_in'],later['fade_out'])
                if op<.001: continue
                data=self.texts[i]; progress=float(ease((t-card['start'])/card['fade_in']))
                text+=self.text_frame(data,t,progress)*op; self.glints(text,data,t,op)
                if f'sub{i}' in self.texts: text+=self.text_frame(self.texts[f'sub{i}'],t,progress)*op
        combined=im+text
        # Small-resolution bloom is deliberately restrained; fine glyph/portrait detail stays native.
        small=cv2.resize(combined,(max(1,self.w//4),max(1,self.h//4)),interpolation=cv2.INTER_AREA)
        glow=cv2.GaussianBlur(small,(0,0),max(.5,self.c['effects']['glow_radius_1080']*self.scale/4))
        glow=cv2.resize(glow,(self.w,self.h),interpolation=cv2.INTER_LINEAR)*self.c['effects']['glow_strength']
        result=np.empty((self.h,self.w,3),np.uint8)
        pal=self.c['palette']
        for ch in range(3):
            color=im*pal['particle'][ch]+text*pal['text'][ch]+glow*pal['glow'][ch]+pal['background'][ch]
            result[:,:,ch]=np.clip(color,0,255).astype(np.uint8)
        return result
