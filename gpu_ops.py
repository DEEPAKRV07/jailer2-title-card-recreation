"""CUDA implementations of the existing renderer's image and draw operations."""
import math
from collections import Counter
import numpy as np
import cv2
import cupy as cp
from cupyx.scipy import ndimage

COUNTS=Counter()
CODE=r'''
__device__ float pixel(const float* a,int x,int y,int w,int h,int c,int ch,int border){
 if(border){x=max(0,min(w-1,x));y=max(0,min(h-1,y));}
 else if(x<0||y<0||x>=w||y>=h)return 0;
 return a[(y*w+x)*ch+c];
}
__device__ float cubic(float x){x=fabsf(x);float A=-.75f;return x<=1?(A+2)*x*x*x-(A+3)*x*x+1:x<2?A*x*x*x-5*A*x*x+8*A*x-4*A:0;}
extern "C" __global__ void sample(const float* a,float* b,int sw,int sh,int dw,int dh,int ch,int mode,int warp,const double* m){
 int i=blockDim.x*blockIdx.x+threadIdx.x;if(i>=dw*dh*ch)return;
 int c=i%ch,x=(i/ch)%dw,y=(i/ch)/dw;
 float sx,sy;
 if(warp){sx=m[0]*x+m[1]*y+m[2];sy=m[3]*x+m[4]*y+m[5];sx=roundf(sx*32)/32;sy=roundf(sy*32)/32;}
 else {sx=(x+.5f)*sw/dw-.5f;sy=(y+.5f)*sh/dh-.5f;}
 float v=0;
 if(mode==0){int ix=warp?(int)roundf(sx):x*sw/dw,iy=warp?(int)roundf(sy):y*sh/dh;v=pixel(a,ix,iy,sw,sh,c,ch,!warp);}
 else if(mode==3&&!warp&&dw<=sw&&dh<=sh){
   float x0=(float)x*sw/dw,x1=(float)(x+1)*sw/dw,y0=(float)y*sh/dh,y1=(float)(y+1)*sh/dh;
   for(int yy=floorf(y0);yy<ceilf(y1);yy++)for(int xx=floorf(x0);xx<ceilf(x1);xx++)
    v+=pixel(a,xx,yy,sw,sh,c,ch,1)*fmaxf(0,fminf(xx+1,x1)-fmaxf(xx,x0))*fmaxf(0,fminf(yy+1,y1)-fmaxf(yy,y0));
   v/=((x1-x0)*(y1-y0));
 }else{
   int ix=floorf(sx),iy=floorf(sy);float dx=sx-ix,dy=sy-iy;
   if(mode==2){for(int j=-1;j<=2;j++)for(int k=-1;k<=2;k++)v+=pixel(a,ix+k,iy+j,sw,sh,c,ch,!warp)*cubic(k-dx)*cubic(j-dy);}
   else v=pixel(a,ix,iy,sw,sh,c,ch,!warp)*(1-dx)*(1-dy)+pixel(a,ix+1,iy,sw,sh,c,ch,!warp)*dx*(1-dy)+pixel(a,ix,iy+1,sw,sh,c,ch,!warp)*(1-dx)*dy+pixel(a,ix+1,iy+1,sw,sh,c,ch,!warp)*dx*dy;
 }
 b[i]=v;
}
// Each primitive has 32 floats: type, value, bounding x0/y0/x1/y1, then shape data.
// Resolve overlaps by last draw index, matching OpenCV's overwrite drawing semantics.
extern "C" __global__ void owners(const float* commands,int* owner,int w,int h,int n){
 int k=blockIdx.x;if(k>=n)return;const float* q=commands+32*k;
 int x0=max(0,(int)floorf(q[2])),y0=max(0,(int)floorf(q[3])),x1=min(w-1,(int)ceilf(q[4])),y1=min(h-1,(int)ceilf(q[5]));
 int bw=x1-x0+1,bh=y1-y0+1;if(bw<=0||bh<=0)return;
 for(int j=threadIdx.x;j<bw*bh;j+=blockDim.x){
  int x=x0+j%bw,y=y0+j/bw;bool hit=false;int type=q[0];
  if(type==0){float dx=q[8]-q[6],dy=q[9]-q[7],den=dx*dx+dy*dy;
    float t=den?fmaxf(0,fminf(1,((x-q[6])*dx+(y-q[7])*dy)/den)):0;
    float a=x-q[6]-t*dx,b=y-q[7]-t*dy;hit=a*a+b*b<=q[10]*q[10]+.001f;
  }else if(type==1){float a=x-q[6],b=y-q[7];hit=a*a+b*b<=q[8]*q[8]+.001f;}
  else if(type==2){float a=x-q[6],b=y-q[7],cs=cosf(q[10]),sn=sinf(q[10]);float u=(a*cs+b*sn)/q[8],v=(-a*sn+b*cs)/q[9];hit=u*u+v*v<=1.0f;}
  else {int nv=q[6];bool inside=false;
    for(int a=0,b=nv-1;a<nv;b=a++){
      float ax=q[8+2*a],ay=q[9+2*a],bx=q[8+2*b],by=q[9+2*b];
      if(((ay>y)!=(by>y))&&(x<(bx-ax)*(y-ay)/(by-ay)+ax))inside=!inside;
      float dx=bx-ax,dy=by-ay,den=dx*dx+dy*dy,t=den?fmaxf(0,fminf(1,((x-ax)*dx+(y-ay)*dy)/den)):0;
      if((x-ax-t*dx)*(x-ax-t*dx)+(y-ay-t*dy)*(y-ay-t*dy)<=.26f)hit=true;
    }hit=hit||inside;
  }
  if(hit)atomicMax(owner+y*w+x,k+1);
 }
}
extern "C" __global__ void paint(float* image,const int* owner,const float* commands,int n){int i=blockDim.x*blockIdx.x+threadIdx.x;if(i<n&&owner[i])image[i]=commands[(owner[i]-1)*32+1];}
extern "C" __global__ void nv12(const unsigned char* rgb,unsigned char* dst,int w,int h){
 int i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=w*h)return;float r=rgb[i*3],g=rgb[i*3+1],b=rgb[i*3+2];
 dst[i]=(unsigned char)max(0,min(255,(int)rintf(16+.182586f*r+.614231f*g+.062007f*b)));
 int x=i%w,y=i/w;if((x%2)==0&&(y%2)==0){float R=0,G=0,B=0;
 for(int yy=0;yy<2;yy++)for(int xx=0;xx<2;xx++){int z=((y+yy)*w+x+xx)*3;R+=rgb[z];G+=rgb[z+1];B+=rgb[z+2];}R*=.25f;G*=.25f;B*=.25f;
 int z=w*h+(y/2)*w+x;dst[z]=max(0,min(255,(int)rintf(128-.100644f*R-.338572f*G+.439216f*B)));dst[z+1]=max(0,min(255,(int)rintf(128+.439216f*R-.398942f*G-.040274f*B)));
 }
}
'''
_kernels=cp.RawModule(code=CODE,options=('--std=c++11','--fmad=false'))

def image_sample(src,size,mode,affine=None):
    COUNTS['cuda_image_sample']+=1
    src=cp.asarray(src); original=src.dtype; a=cp.ascontiguousarray(src,dtype=cp.float32)
    sh,sw=a.shape[:2]; dw,dh=size; ch=1 if a.ndim==2 else a.shape[2]
    dst=cp.empty((dh,dw) if ch==1 else (dh,dw,ch),cp.float32)
    coefficients=cp.asnumpy(affine) if isinstance(affine,cp.ndarray) else affine
    m=cp.zeros(6,cp.float64) if affine is None else cp.asarray(cv2.invertAffineTransform(np.asarray(coefficients)),dtype=cp.float64).ravel()
    _kernels.get_function('sample')(((dst.size+255)//256,),(256,),(a,dst,sw,sh,dw,dh,ch,mode,int(affine is not None),m))
    if original==cp.uint8: return cp.clip(cp.rint(dst),0,255).astype(cp.uint8)
    return dst

def draw(im,commands):
    if len(commands)==0:return
    COUNTS['cuda_primitive_raster']+=1
    commands=cp.ascontiguousarray(commands,dtype=cp.float32)
    owner=cp.zeros(im.shape,cp.int32);h,w=im.shape
    _kernels.get_function('owners')((len(commands),),(256,),(commands,owner,w,h,len(commands)))
    _kernels.get_function('paint')(((im.size+255)//256,),(256,),(im,owner,commands,im.size))

def line_radius(width):return .5 if width==1 else math.ceil(width/2)

def lines(x,y,x2,y2,r,value):
    x,y,x2,y2,r,value=cp.broadcast_arrays(*[cp.asarray(v) for v in [x,y,x2,y2,r,value]])
    out=cp.zeros((x.size,32),cp.float32);out[:,1]=value.ravel();out[:,2]=cp.minimum(x,x2).ravel()-r.ravel();out[:,3]=cp.minimum(y,y2).ravel()-r.ravel();out[:,4]=cp.maximum(x,x2).ravel()+r.ravel();out[:,5]=cp.maximum(y,y2).ravel()+r.ravel()
    for col,values in [(6,x),(7,y),(8,x2),(9,y2),(10,r)]:out[:,col]=values.ravel()
    return out

def circles(x,y,r,value):
    q=lines(x,y,x,y,r,value);q[:,0]=1;q[:,8]=q[:,10];return q

def ellipses(x,y,rx,ry,angle,value):
    q=lines(x,y,x,y,cp.maximum(rx,ry),value);q[:,0]=2;q[:,8]=rx;q[:,9]=ry;q[:,10]=angle;return q

def polygons(vertices,value):
    v=cp.asarray(vertices,dtype=cp.float32)
    if v.ndim==2:v=v[None]
    q=cp.zeros((len(v),32),cp.float32);q[:,0]=3;q[:,1]=value;q[:,2:4]=v.min(axis=1);q[:,4:6]=v.max(axis=1);q[:,6]=v.shape[1];q[:,8:8+2*v.shape[1]]=v.reshape(len(v),-1);return q

def to_nv12(rgb):
    COUNTS['cuda_rgb_to_nv12']+=1;h,w=rgb.shape[:2]; dst=cp.empty(h*w*3//2,cp.uint8)
    _kernels.get_function('nv12')(((w*h+255)//256,),(256,),(cp.ascontiguousarray(rgb),dst,w,h));return dst

class Random:
    def __init__(self,seed):self.r=np.random.default_rng(seed)
    def __getattr__(self,name):
        def call(*args,**kw):
            if 'p' in kw and isinstance(kw['p'],cp.ndarray):
                kw['p']=cp.asnumpy(kw['p']).astype(np.float64);kw['p']/=kw['p'].sum()
            return getattr(self.r,name)(*args,**kw)
        return call
class RandomFactory:
    default_rng=Random
class ArrayFacade:
    random=RandomFactory()
    def array(self,value,*args,**kw):
        if isinstance(value,(list,tuple)):
            def convert(v):return cp.stack([convert(w) for w in v]) if isinstance(v,(list,tuple)) else cp.asarray(v)
            result=convert(value);dtype=kw.get('dtype',args[0] if args else None)
            return result.astype(dtype) if dtype else result
        if not isinstance(value,(cp.ndarray,np.ndarray,list,tuple)):value=np.asarray(value)
        return cp.array(value,*args,**kw)
    def where(self,a,*args):return cp.where(cp.asarray(a),*args)
    def clip(self,a,*args,**kw):return cp.clip(a,*args,**kw) if isinstance(a,cp.ndarray) else np.clip(a,*args,**kw)
    def __getattr__(self,name):return getattr(cp,name)

class CVFacade:
    def __getattr__(self,name):return getattr(cv2,name)
    def resize(self,a,size,interpolation=cv2.INTER_LINEAR):return image_sample(a,size,interpolation)
    def warpAffine(self,a,matrix,size,flags=cv2.INTER_LINEAR):return image_sample(a,size,flags,matrix)
    def cvtColor(self,src,code):
        COUNTS['cuda_grayscale']+=1;a=cp.asarray(src)
        if code==cv2.COLOR_BGR2GRAY:r,g,b=a[:,:,2],a[:,:,1],a[:,:,0]
        elif code==cv2.COLOR_RGB2GRAY:r,g,b=a[:,:,0],a[:,:,1],a[:,:,2]
        else:raise RuntimeError(f'Unsupported CUDA color conversion {code}; refusing implicit CPU fallback')
        return ((r.astype(cp.int32)*4899+g.astype(cp.int32)*9617+b.astype(cp.int32)*1868+8192)>>14).astype(cp.uint8)
    def GaussianBlur(self,a,size,sigma):
        COUNTS['cuda_gaussian']+=1
        k=size[0] or (round(sigma*8+1)|1); weights=cp.asarray(cv2.getGaussianKernel(k,sigma).ravel(),cp.float32)
        return ndimage.correlate1d(ndimage.correlate1d(cp.asarray(a),weights,axis=1,mode='mirror'),weights,axis=0,mode='mirror')
    def Sobel(self,a,depth,dx,dy,ksize=3):
        COUNTS['cuda_sobel']+=1
        smooth=cp.asarray([1,2,1],cp.float32);deriv=cp.asarray([-1,0,1],cp.float32)
        return ndimage.correlate1d(ndimage.correlate1d(a,deriv if dx else smooth,axis=1,mode='mirror'),deriv if dy else smooth,axis=0,mode='mirror')
    def morphologyEx(self,a,op,kernel):
        COUNTS['cuda_morphology']+=1
        return ndimage.maximum_filter(a,size=kernel.shape,mode='mirror')-ndimage.minimum_filter(a,size=kernel.shape,mode='mirror')
    def fillConvexPoly(self,im,vertices,color,*args):draw(im,polygons(vertices,color))
    def fillPoly(self,im,vertices,color,*args):draw(im,cp.concatenate([polygons(v,color) for v in vertices]))
    def line(self,im,p1,p2,value,width,*args):draw(im,lines(p1[0],p1[1],p2[0],p2[1],line_radius(width),value))
