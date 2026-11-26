"""Gentle 2.5D nature editing on CPU; masks approximate surfaces, not full 3D.

A scene renderer caches depth/foliage/water masks. Motion stays small so the
original still is not stretched into implausible geometry. Masks need review.
"""
import math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter,ImageChops,ImageEnhance
SIZE=(1280,720)
FEATURES=['slow_depth_parallax','moving_distant_mist','masked_foliage_sway','masked_water_ripples_and_reflections','layered_wind_rain','slow_soft_light','varied_safe_camera_framing','smooth_scene_and_audio_transitions','consistent_bright_colour_grade','minimal_intro_and_chapter_labels']

def smooth(x):x=max(0,min(1,x));return x*x*(3-2*x)
def font(size):
 for p in ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/System/Library/Fonts/Supplemental/Arial.ttf']:
  if Path(p).exists():return ImageFont.truetype(p,size)
 raise FileNotFoundError('A TrueType font is required for minimal labels')
def title_overlay(im,text,age,duration=4):
 opacity=smooth(age/.7)*smooth((duration-age)/.9)
 if opacity<=0:return im
 layer=Image.new('RGBA',SIZE);d=ImageDraw.Draw(layer);f=font(27)
 text=' '.join(text.split())
 while d.textbbox((0,0),text,font=f)[2]>1120:f=font(f.size-1)
 x=64;y=642
 d.text((x+1,y+2),text,font=f,fill=(5,23,22,round(155*opacity)),stroke_width=2)
 d.text((x,y),text,font=f,fill=(245,248,239,round(235*opacity)))
 result=im.convert('RGBA');result.alpha_composite(layer);return result.convert('RGB')

class SceneRenderer:
 def __init__(self,source,depth,scene,seed=0,water_mask=None):
  self.scene=scene;self.seed=seed;self.width,self.height=SIZE
  im=source.convert('RGB').resize(SIZE,Image.Resampling.LANCZOS)
  im=ImageEnhance.Color(im).enhance(1.13);im=ImageEnhance.Brightness(im).enhance(1.07);im=ImageEnhance.Contrast(im).enhance(1.025)
  self.base=im;self.depth=depth.convert('L').resize(SIZE,Image.Resampling.BILINEAR)
  a=np.asarray(im.resize((320,180)),dtype=float);dep=np.asarray(self.depth.resize((320,180)),dtype=float)/255
  # Green foliage, excluding distant/sky regions; not a semantic tree detector.
  green=(a[:,:,1]>a[:,:,0]*1.055)&(a[:,:,1]>a[:,:,2]*.93)&(dep>.35)
  green[:35]=False
  self.foliage=Image.fromarray((green*255).astype('uint8')).resize(SIZE,Image.Resampling.BILINEAR).filter(ImageFilter.GaussianBlur(5))
  self.near=self.depth.point(lambda v:round(255*smooth((v/255-.40)/.45))).filter(ImageFilter.GaussianBlur(8))
  border=Image.new('L',SIZE);ImageDraw.Draw(border).rectangle((10,10,1269,709),fill=255);border=border.filter(ImageFilter.GaussianBlur(4))
  self.near=ImageChops.multiply(self.near,border);self.foliage=ImageChops.multiply(self.foliage,border)
  self.far=ImageChops.invert(self.depth).point(lambda v:round(v*.085))
  edge=np.asarray(im.resize((320,180)).convert('L').filter(ImageFilter.FIND_EDGES),dtype=float)
  region=scene.get('water_region','none');yy,xx=np.mgrid[:180,:320]
  if water_mask is not None:self.water=water_mask.convert('L').resize(SIZE).filter(ImageFilter.GaussianBlur(4))
  elif region!='none':
   cx={'lower_left':.25,'lower_center':.5,'lower_right':.75}[region]*320
   area=((xx-cx)/(320*.22))**2+((yy-180*.78)/(180*.18))**2<1
   quiet=(edge<17)&(a[:,:,2]>a[:,:,0]*.9)&(a.mean(2)>30)
   self.water=Image.fromarray((area*quiet*255).astype('uint8')).resize(SIZE,Image.Resampling.BILINEAR).filter(ImageFilter.GaussianBlur(5))
  else:self.water=Image.new('L',SIZE)
  random=np.random.default_rng(seed)
  self.mist=Image.new('L',(320,180));md=ImageDraw.Draw(self.mist)
  for _ in range(12):
   x=float(random.uniform(-100,320));y=float(random.uniform(45,145));rx=float(random.uniform(40,120))
   md.ellipse((x-rx,y-13,x+rx,y+13),fill=int(random.integers(10,40)))
  self.mist=self.mist.filter(ImageFilter.GaussianBlur(15)).resize(SIZE,Image.Resampling.BILINEAR)
  self.rain=[]
  for count,speed,length,alpha,width in [(280,(150,270),(5,11),(15,34),1),(180,(350,600),(12,22),(30,65),1),(45,(750,1050),(22,36),(50,90),2)]:
   self.rain.append([(float(random.uniform(0,1280)),float(random.uniform(0,720)),float(random.uniform(*speed)),float(random.uniform(*length)),int(random.integers(*alpha)),width) for _ in range(count)])
  self.rings=[(float(random.uniform(110,1170)),float(random.uniform(400,690)),float(random.uniform(0,1))) for _ in range(26)]

 def frame(self,t,camera=None):
  kind=camera or self.scene.get('camera','zoom_in');u=max(0,min(1,t/10));ease=smooth(u)
  # Crop margin keeps the camera/foreground shifts away from image borders.
  z=1.045+.022*(1-ease if kind=='zoom_out' else ease);cw=1280/z;ch=720/z
  x=(1280-cw)*({'pan_left':1-ease,'pan_right':ease}.get(kind,.5));y=(720-ch)*.5
  affine=(cw/1280,0,x,0,ch/720,y)
  def camera_view(im):return im.transform(SIZE,Image.Transform.AFFINE,affine,Image.Resampling.BICUBIC)
  base=camera_view(self.base);near=camera_view(self.near);foliage=camera_view(self.foliage);water=camera_view(self.water);far=camera_view(self.far)
  # Depth foreground is feathered over the background with <=3-pixel relative motion.
  dx=2.4*math.sin(t*.17+self.seed%7);dy=.65*math.sin(t*.21)
  foreground=base.transform(SIZE,Image.Transform.AFFINE,(1,0,dx,0,1,dy),Image.Resampling.BICUBIC)
  im=Image.composite(foreground,base,near)
  # Tiny row-dependent bends, strongest at leaf tips; base remains under soft mask.
  sway=1.25*math.sin(t*.85+self.seed%5)
  moving=im.transform(SIZE,Image.Transform.AFFINE,(1,sway/720,-sway,0,1,0),Image.Resampling.BICUBIC)
  im=Image.composite(moving,im,foliage)
  # Water texture motion stays inside a conservative still-water mask.
  shifted=im.transform(SIZE,Image.Transform.AFFINE,(1,0,.65*math.sin(t*1.4),0,1,.25*math.sin(t*1.8)),Image.Resampling.BICUBIC)
  im=Image.composite(Image.blend(im,shifted,.35),im,water)
  # Very slow light drift (<1%); no strobe or lightning.
  im=ImageEnhance.Brightness(im).enhance(1+.009*math.sin(t*.19+self.seed%9))
  result=im.convert('RGBA');layer=Image.new('RGBA',SIZE)
  mist=self.mist.transform(SIZE,Image.Transform.AFFINE,(1,0,-t*3,0,1,0),Image.Resampling.BILINEAR)
  mist=ImageChops.multiply(mist,far);mist=mist.point(lambda v:min(22,v*3))
  fog=Image.new('RGBA',SIZE,(214,232,226,0));fog.putalpha(mist);result.alpha_composite(fog)
  draw=ImageDraw.Draw(layer);wind=38+9*math.sin(t*.3)
  for group in self.rain:
   for px,py,speed,length,alpha,width in group:
    xx=(px+wind*t)%(1280+80)-40;yy=(py+speed*t)%(720+80)-40
    draw.line((xx,yy,xx+length*wind/speed,yy+length),fill=(209,229,235,alpha),width=width)
  ripples=Image.new('RGBA',SIZE);rd=ImageDraw.Draw(ripples)
  for cx,cy,phase in self.rings:
   age=(t*.7+phase)%1;r=3+age*19;opacity=round(65*(1-age)**1.5)
   rd.ellipse((cx-r,cy-r*.2,cx+r,cy+r*.2),outline=(208,229,230,opacity),width=1)
   if age<.12:rd.line((cx-2,cy,cx,cy-4,cx+2,cy),fill=(218,234,237,int(65*(1-age/.12))),width=1)
  ripples.putalpha(ImageChops.multiply(ripples.getchannel('A'),water));layer.alpha_composite(ripples)
  result.alpha_composite(layer);return result.convert('RGB')

def render_sequence(renderers,scenes,t):
 i=min(len(renderers)-1,int(t//10));local=t%10;im=renderers[i].frame(local)
 if local>8 and i+1<len(renderers):im=Image.blend(im,renderers[i+1].frame(0),smooth((local-8)/2))
 return im
