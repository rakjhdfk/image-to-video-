"""Resumable local 2D anime production. Native 720p independent character rigs.

Run `python pipeline.py all`. No video model or GPU is required by hybrid mode.
"""
from __future__ import annotations
import argparse, hashlib, importlib, json, math, os, random, shutil, subprocess, sys, time, wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
from contextlib import contextmanager

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output';OUT.mkdir(exist_ok=True)
W,H,FPS=1280,720,24
FONT_CANDIDATES=['C:/Windows/Fonts/arial.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']
FONTS={}
def font(size):
 if size not in FONTS:
  path=next((p for p in FONT_CANDIDATES if Path(p).exists()),None)
  FONTS[size]=ImageFont.truetype(path,size) if path else ImageFont.load_default(size=size)
 return FONTS[size]
def save_json(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 tmp=path.with_suffix(f'.{os.getpid()}.writing');tmp.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8');tmp.replace(path)
def log(message):
 print(message,flush=True)
 with (OUT/'generation_log.txt').open('a',encoding='utf-8') as f:f.write(time.strftime('%Y-%m-%dT%H:%M:%S')+' '+message+'\n')
def progress(stage,status='running',**kw):
 save_json(OUT/'progress.json',{'stage':stage,'status':status,'total_shots':60,**kw})
def ffmpeg():
 p=shutil.which('ffmpeg')
 if not p:raise RuntimeError('FFmpeg is required. Install a verified official FFmpeg build and add it to PATH.')
 return p
def probe(path):
 p=shutil.which('ffprobe')
 if not p:raise RuntimeError('ffprobe is required alongside FFmpeg.')
 return json.loads(subprocess.check_output([p,'-v','error','-show_streams','-show_format','-of','json',str(path)],text=True))
def plan():
 p=OUT/'episode01_screenplay.json'
 if not p.exists():
  from story import generate
  generate(OUT)
 screenplay=json.loads(p.read_text(encoding='utf-8'))
 manifest=OUT/'voices'/'dialogue_manifest.json'
 if manifest.exists():
  lines=json.loads(manifest.read_text())
  for shot in screenplay['shots']:
   for line in shot['dialogue']:
    match=next((a for a in lines if a['shot']==shot['id'] and a['speaker']==line['speaker'] and a['text']==line['text']),None)
    if match:
     line['offset']=match['start']-shot['start'];line['duration']=match['end']-match['start'];line['voice_file']=match['file']
 return screenplay
def wait_if_paused():
 notified=False
 while (OUT/'PAUSE').exists():
  if not notified:progress('animation','paused',message='Paused at a frame boundary. Resume continues this shot.');notified=True
  time.sleep(.2)
def completed_shots():
 return sum((OUT/'renders'/f'shot_{i:03d}.mp4').exists() for i in range(60))
@contextmanager
def production_lock():
 handle=(OUT/'.production.lock').open('a+b');acquired=False
 try:
  handle.seek(0,2)
  if handle.tell()==0:handle.write(b'0');handle.flush()
  handle.seek(0)
  try:
   if os.name=='nt':
    import msvcrt
    msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
   else:
    import fcntl
    fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
   acquired=True
  except (BlockingIOError,OSError):pass
  yield acquired
 finally:
  if acquired:
   handle.seek(0)
   if os.name=='nt':
    import msvcrt
    msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
   else:
    import fcntl
    fcntl.flock(handle.fileno(),fcntl.LOCK_UN)
  handle.close()

def prepare():
 progress('preparation');ffmpeg();screenplay=plan()
 for folder in ['characters','backgrounds','animation','voices','music','sound_effects','renders','episode01_storyboard']:(OUT/folder).mkdir(exist_ok=True)
 from characters import generate_references
 generate_references(OUT/'characters')
 missing=[n for n in ['city','street','academy','courtyard','ruins','tower','seal'] if not (OUT/'backgrounds'/f'{n}.png').exists()]
 if missing:raise RuntimeError('Missing original environment assets: '+', '.join(missing)+'. Render does not substitute blank or unrelated images.')
 settings=json.loads((OUT/'user_settings.json').read_text()) if (OUT/'user_settings.json').exists() else {}
 save_json(OUT/'project_manifest.json',{'title':screenplay['title'],'production_mode':'2D skeletal hybrid animation','resolution':[W,H],'fps':FPS,'duration':600,'required_frames':14400,'gpu_required':False,'settings':settings,'notes':'Original painted environment plates plus independently posed human rigs, face animation, choreographed motion paths, tracked spell layers. Not diffusion video or hand-drawn frame-by-frame animation.'})
 progress('preparation','completed',message='Story, character references, original painted locations and tools available.');log('Preparation complete')

BG_CACHE={}
COLOR_STYLE=None
ENVELOPES={}
def speech_envelope(shot,name,t):
 for line in shot['dialogue']:
  if line['speaker']!=name or not line['offset']<=t<line['offset']+line.get('duration',4):continue
  file=line.get('voice_file')
  if not file:return True,.5+.4*math.sin(t*14)
  if file not in ENVELOPES:
   with wave.open(str(OUT/file),'rb') as w:
    data=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(np.float32)/32768;sr=w.getframerate()
   block=sr//100;data=np.pad(data,(0,(-len(data))%block));rms=np.sqrt(np.mean(data.reshape(-1,block)**2,axis=1));ENVELOPES[file]=np.clip(rms*9,0,1)
  env=ENVELOPES[file];j=min(len(env)-1,max(0,int((t-line['offset'])*100)));amp=float(env[j]);return amp>.035,amp
 return False,0.
def background(location):
 if location not in BG_CACHE:
  p=OUT/'backgrounds'/f'{location}.png'
  if not p.exists():raise FileNotFoundError(p)
  BG_CACHE[location]=Image.open(p).convert('RGB').resize((W,H),Image.Resampling.LANCZOS)
 return BG_CACHE[location]
def ease(u):u=max(0,min(1,u));return u*u*(3-2*u)
def bezier(points,steps=40):
 p0,p1,p2,p3=points
 return [tuple((1-u)**3*p0[k]+3*(1-u)**2*u*p1[k]+3*(1-u)*u*u*p2[k]+u**3*p3[k] for k in range(2)) for u in np.linspace(0,1,steps)]
def camera(shot,u):
 typ=shot.get('camera','medium');idx=shot['id']
 if typ=='close':return (1.36+u*.05,math.sin(idx)*48,-30)
 if typ=='wide':return (1.0+u*.025,0,0)
 if typ=='track':return (1.04,math.sin(u*1.4)*55-20,0)
 return (1.08+u*.025,math.sin(idx)*25+u*18,0)
def actor_motion(shot,name,idx,u,t):
 cast=shot.get('characters',[]);n=len(cast)
 x=([640] if n==1 else [405,875] if n==2 else [315,650,1010] if n==3 else [230,505,790,1060])[min(idx,3)]
 y=660;scale=.98 if n<3 else .90
 if name=='elder':scale=1.01
 action=shot['action'];pose='talk';expression=shot.get('expression','determined')
 if action in ['walk','run']:
  pose=action;x+=(-120+240*ease(u))*(1 if shot['id']%2==0 else -1)
 elif action in ['battle','rescue','rift','weave','seal','fall']:
  pose=action
  # Different motivated attack, dodge and recovery paths for consecutive shots.
  if action=='battle':
   if name=='mira':pose='weave';x+=24*math.sin(u*math.pi)
   elif name=='riven':x+=110*math.sin(u*math.pi*2)*(1 if shot['id']%2 else -1)
   else:x+=75*math.sin(u*math.pi);pose='battle' if u<.68 else 'weave'
  if action=='rescue':x+=190*ease(min(1,u*1.5));pose='run' if u<.45 else 'rescue'
  if action=='fall':y+=75*ease(u);pose='fall'
  if action=='rift':x-=45*ease(u);pose='battle'
 elif action=='ceremony':pose='weave' if name=='elder' else 'talk'
 elif action=='listen':pose='listen';expression='surprised'
 if shot.get('magic') in ['origin','silver','crimson'] and name=='kael' and action=='weave':pose='weave'
 phase=t*2.4+idx*.8+shot['id']*.15
 facing=1 if idx<n/2 else -1
 speaking=any(d['speaker']==name and d['offset']<=t<d['offset']+d.get('duration',max(1,len(d['text'].split())/2.4)) for d in shot.get('dialogue',[]))
 return x,y,scale,pose,phase,expression,speaking,facing

def atmosphere(frame,shot,t):
 d=ImageDraw.Draw(frame,'RGBA');s=shot['start']+t;loc=shot['location']
 # Wind-blown magical dust and drifting leaves are independent scene layers.
 for i in range(24):
  x=(i*137+s*(9+i%4))%W;y=85+(i*79)%530+8*math.sin(s*.4+i)
  if loc in ['seal','ruins','tower']:col=(135,192,255,75)
  else:col=(255,238,174,105)
  d.ellipse((x,y,x+2.2,y+2.2),fill=col)
 if loc in ['city','street','academy','courtyard']:
  for i in range(3):
   x=(s*21+i*370)%1450-80;y=80+i*40+7*math.sin(s+i);wing=5+5*math.sin(s*4+i)
   d.line([(x-10,y-wing),(x,y),(x+10,y-wing)],fill=(41,60,91,180),width=2)
 if loc=='street':
  # Small pedestrians supply living city depth; main characters are separate rigs.
  for i in range(4):
   x=(s*13+i*310)%1450-80;y=430+i%2*16
   d.ellipse((x-5,y-30,x+5,y-19),fill=(47,52,79,150));d.polygon([(x-5,y-19),(x+5,y-19),(x+9,y+3),(x-8,y+3)],fill=(53,68,101,145))
   k=math.sin(s*5+i)*5;d.line([(x-3,y),(x-4+k,y+17)],fill=(40,46,68,160),width=3);d.line([(x+3,y),(x+4-k,y+17)],fill=(40,46,68,160),width=3)

def beast(frame,t,shot,zoom,cx,cy):
 d=ImageDraw.Draw(frame,'RGBA');u=t/10;bx=980+45*math.sin(t*1.3);by=495+14*math.sin(t*2)
 if shot['id']>=47:bx+=180*ease(u)
 def p(x,y):return ((x-cx-640)*zoom+640,(y-cy-360)*zoom+360)
 # An original smoke-winged guardian of the Rift: cel-shaded, articulated silhouette.
 wing=math.sin(t*3)*35
 for side in [-1,1]:
  poly=[p(bx,by-80),p(bx+side*190,by-200-wing),p(bx+side*140,by-65),p(bx+side*85,by-90),p(bx+side*75,by+30)]
  d.polygon(poly,fill=(31,20,62,240),outline=(163,81,223,255),width=3)
 d.ellipse((*p(bx-65,by-65),*p(bx+65,by+75)),fill=(24,19,48,245),outline=(128,70,176,255),width=3)
 d.polygon([p(bx-55,by-120),p(bx-40,by-175),p(bx-8,by-130),p(bx+30,by-165),p(bx+58,by-113),p(bx+44,by-48),p(bx-30,by-48)],fill=(39,24,68,255),outline=(173,97,224,255),width=3)
 for side in [-1,1]:
  x=bx+side*20;d.line([p(x-side*10,by-105),p(x+side*10,by-99)],fill=(211,118,255,255),width=5)
  ax=bx+side*90;ay=by+40+math.sin(t*2+side)*25
  d.line([p(bx+side*40,by-10),p(ax,ay)],fill=(55,32,83,255),width=max(3,int(18*zoom)))
  for j in range(3):d.line([p(ax,ay),p(ax+side*(18+j*4),ay+25+j*4)],fill=(175,132,199,255),width=3)

def magic_layer(frame,shot,t,anchors):
 typ=shot.get('magic','none');action=shot['action'];s=shot['start']+t
 if typ=='none':return
 layer=Image.new('RGBA',(W,H));d=ImageDraw.Draw(layer,'RGBA')
 colors={'silver':(210,225,255),'crimson':(255,75,111),'origin':(82,249,219),'rift':(176,75,255),'seal':(255,206,104),'none':(90,225,220)}
 col=colors.get(typ,colors['origin'])
 def glowline(pts,width=3,c=col):
  d.line(pts,fill=(*c,45),width=width*5,joint='curve');d.line(pts,fill=(*c,200),width=width+2,joint='curve');d.line(pts,fill=(245,254,255,245),width=width,joint='curve')
 if typ=='rift' or 180<=s<480:
  x=985;y=90;sz=1 if s<480 else .7
  pinch=1-ease((s-473)/7) if s>473 else 1
  pts=[(x+math.sin(k*1.4+s*.7)*20*pinch,y+k*7*pinch) for k in range(24)]
  glowline(pts,7,(156,74,238))
  for j in range(5):
   a=j*1.1+s*.13;glowline([(x,y+80),(x+math.cos(a)*55,y+110+math.sin(a)*75),(x+math.cos(a)*110,y+160+math.sin(a)*90)],2,(151,85,239))
 if typ=='seal' or shot['location']=='seal':
  for r in [110,145,175]:
   d.ellipse((640-r,565-r*.27,640+r,565+r*.27),outline=(*col,195),width=3)
  for i in range(12):
   a=i*math.tau/12+s*.12;px=640+math.cos(a)*145;py=565+math.sin(a)*40
   d.line([(px-4,py-10),(px+4,py+10),(px+8,py-5)],fill=(*col,225),width=2)
 if typ in ['origin','silver','crimson'] or action in ['battle','weave','rescue']:
  names=list(anchors)
  from blocking import active_casters
  names=[n for n in names if n in active_casters(shot,t)]
  for n in names:
   if n=='elder':continue
   if n=='kael' and (shot['id']<35 or typ not in ['origin','seal']):continue
   if n=='mira' and not (typ=='silver' or 380<=s<475):continue
   if n=='riven' and not (typ=='crimson' or 380<=s<475):continue
   a=anchors[n];hand=a.get('right_hand',a.get('hands',[(640,400)])[-1])
   if isinstance(hand,dict):hand=hand.get('right',(640,400))
   try:hx,hy=float(hand[0]),float(hand[1])
   except (TypeError,KeyError,IndexError):hx,hy=640,400
   color=(215,226,255) if n=='mira' else (255,65,112) if n=='riven' else (90,246,218)
   tx=930+30*math.sin(s);ty=390+15*math.sin(s*.7)
   if action=='weave' and n=='kael':tx,ty=740,330
   for j in range(3 if n!='mira' else 6):
    off=(j-1)*18
    pts=bezier([(hx,hy),(hx+85,hy-65+off+10*math.sin(s*2+j)),(tx-100,ty+65+off),(tx,ty+off)])
    if n=='riven':
     rng=random.Random(int(s*12)+j*31);pts=[(px+rng.uniform(-8,8),py+rng.uniform(-8,8)) for px,py in pts[::3]]
    glowline(pts,2,color)
   for i in range(13):
    a1=i*2.4+s*2;r=18+12*math.sin(s+i)
    px=hx+math.cos(a1)*r;py=hy+math.sin(a1)*r
    d.ellipse((px-2,py-2,px+2,py+2),fill=(*color,240))
 if action in ['battle','rift','rescue']:
  for i in range(28):
   px=(i*159+s*(50+i%5*13))%W;py=380+(i*41)%280+12*math.sin(s*2+i)
   d.polygon([(px,py),(px+5,py-4),(px+9,py+6)],fill=(173,148,140,170))
 frame.alpha_composite(layer)

def subtitles(frame,shot,t):
 d=ImageDraw.Draw(frame,'RGBA')
 active=[line for line in shot.get('dialogue',[]) if line['offset']<=t<line['offset']+line.get('duration',max(1,len(line['text'].split())/2.35))]
 if not active:return
 line=active[-1];text=line['text'];words=text.split();rows=[];row=''
 for word in words:
  candidate=(row+' '+word).strip()
  if d.textlength(candidate,font=font(24))>1110 and row:rows.append(row);row=word
  else:row=candidate
 if row:rows.append(row)
 rows=rows[:3];y=H-36-len(rows)*30
 d.rounded_rectangle((58,y-9,W-58,H-20),radius=10,fill=(7,12,30,174))
 for i,row in enumerate(rows):
  tw=d.textlength(row,font=font(24));d.text(((W-tw)/2,y+i*30),row,font=font(24),fill='white',stroke_width=1,stroke_fill=(10,14,30,255))

def render_frame(shot,frame_index,previous=None):
 global COLOR_STYLE
 from characters import draw_character
 t=frame_index/FPS;u=t/10;z,cx,cy=camera(shot,u)
 bg=background(shot['location'])
 frame=bg.transform((W,H),Image.Transform.AFFINE,(1/z,0,640-(640+cx*.25)/z,0,1/z,360-(360+cy*.3)/z),Image.Resampling.BILINEAR).convert('RGBA')
 atmosphere(frame,shot,t)
 if 210<=shot['start']+t<475 and shot['location'] in ['ruins','courtyard']:beast(frame,shot['start']+t,shot,z,cx,cy)
 try:
  from blocking import override_motion,draw_props
 except ImportError:override_motion=draw_props=None
 if draw_props:draw_props(frame,shot,t,anchors=None,before=True,camera=(z,cx,cy))
 anchors={};stats={}
 for idx,name in enumerate(shot.get('characters',[])):
  if name not in ['kael','mira','riven','elder']:continue
  x,y,sc,pose,phase,expr,speaking,facing=actor_motion(shot,name,idx,u,t)
  if override_motion:
   mo=override_motion(shot,name,dict(x=x,y=y,scale=sc,pose=pose,phase=phase,expression=expr,speaking=speaking,facing=facing),t)
   x,y,sc,pose,phase,expr,speaking,facing=[mo[k] for k in ['x','y','scale','pose','phase','expression','speaking','facing']]
  # Position continuity for same location/cast; motivated movement settles into the new blocking.
  if previous and name in previous.get('characters',[]) and previous['location']==shot['location'] and frame_index<24:
   pi=previous['characters'].index(name);last_t=239/FPS
   pv=actor_motion(previous,name,pi,last_t/10,last_t)
   prior=dict(zip(['x','y','scale','pose','phase','expression','speaking','facing'],pv))
   if override_motion:prior=override_motion(previous,name,prior,last_t)
   blend=ease(frame_index/24);x=prior['x']*(1-blend)+x*blend;y=prior['y']*(1-blend)+y*blend;sc=prior['scale']*(1-blend)+sc*blend
   if frame_index<8:pose=prior['pose'];phase=prior['phase']+t;facing=prior['facing']
  x=(x-cx-640)*z+640;y=(y-cy-360)*z+360
  speaking,amp=speech_envelope(shot,name,t)
  a=draw_character(frame,name,x,y,scale=sc*z,pose=pose,phase=phase,expression=expr,speaking=speaking,facing=facing,magic=shot.get('magic','none'),face_phase=shot['start']+t,mouth_open=amp)
  anchors[name]=a or {'right_hand':(x+60,y-235)};stats[name]=[round(x,3),round(y,3),round(phase,3),pose,speaking]
 if draw_props:draw_props(frame,shot,t,anchors=anchors,before=False,camera=(z,cx,cy))
 magic_layer(frame,shot,t,anchors)
 if COLOR_STYLE is None:
  settings_file=OUT/'user_settings.json'
  COLOR_STYLE=json.loads(settings_file.read_text()).get('anime_style','default') if settings_file.exists() else 'default'
 if COLOR_STYLE in ['moonlit','dawn']:
  tint=(14,35,86,35) if COLOR_STYLE=='moonlit' else (255,171,81,24)
  frame=Image.alpha_composite(frame,Image.new('RGBA',(W,H),tint))
 # Doors, drifting foreground shadow and a magical veil motivate location transitions.
 if previous and previous['location']!=shot['location'] and frame_index<15:
  opacity=int(180*(1-ease(frame_index/15)));veil=Image.new('RGBA',(W,H),(8,16,35,opacity));frame=Image.alpha_composite(frame,veil)
 if shot['id']==0 and t<7:
  d=ImageDraw.Draw(frame,'RGBA');d.rectangle((55,65,770,185),fill=(6,18,42,150));d.text((78,79),'THE MAGICAL WORLD',font=font(43),fill=(238,228,185,255));d.text((82,139),'EPISODE 1  /  THE BOY WITHOUT A MAGIC SIGNATURE',font=font(17),fill='white')
 if shot['id']==59 and t>6:
  d=ImageDraw.Draw(frame,'RGBA');d.text((60,38),'THE FIRST SEAL',font=font(25),fill=(245,226,167,255));d.text((62,73),'The story has only begun.',font=font(18),fill='white')
 subtitles(frame,shot,t)
 return frame.convert('RGB'),stats

def shot_fingerprint(shot):
 h=hashlib.sha256(json.dumps(shot,sort_keys=True).encode())
 for file in [ROOT/'pipeline.py',ROOT/'characters.py',OUT/'backgrounds'/f"{shot['location']}.png"]:
  h.update(file.read_bytes())
 if (ROOT/'blocking.py').exists():h.update((ROOT/'blocking.py').read_bytes())
 if (OUT/'user_settings.json').exists():h.update((OUT/'user_settings.json').read_bytes())
 return h.hexdigest()
def render_shot(shot,previous=None,force=False):
 i=shot['id'];dest=OUT/'renders'/f'shot_{i:03d}.mp4';state=OUT/'animation'/f'shot_{i:03d}.json';sig=shot_fingerprint(shot)
 if not force and dest.exists() and state.exists():
  st=json.loads(state.read_text())
  if st.get('fingerprint')==sig and st.get('frames')==240:log(f'Reusing validated shot {i:02d}');return dest
 temp=dest.with_name(dest.stem+'.partial.mp4');log(f'Rendering shot {i+1}/60: {shot["description"]}')
 err=(OUT/'renders'/f'shot_{i:03d}.log').open('w')
 cmd=[ffmpeg(),'-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r','24','-i','pipe:0','-an','-c:v','libx264','-preset','veryfast','-threads','2','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(temp)]
 proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=err);digests=[];motion=[];start=time.monotonic()
 try:
  for f in range(240):
   wait_if_paused();im,st=render_frame(shot,f,previous);proc.stdin.write(im.tobytes())
   if f%24==0:
    digests.append(hashlib.sha256(im.tobytes()).hexdigest());motion.append(st)
    progress('animation',completed_shots=completed_shots(),current_shot=i,shot_frame=f,message=f'Shot {i+1}/60, frame {f+1}/240')
    if f==120:im.save(OUT/'episode01_storyboard'/f'shot_{i:03d}.jpg',quality=92)
  proc.stdin.close();code=proc.wait()
  if code:raise RuntimeError(f'FFmpeg shot {i} failed ({code}); see shot log')
 finally:
  if proc.poll() is None:proc.kill();proc.wait()
  err.close()
 result=probe(temp);video=next(s for s in result['streams'] if s['codec_type']=='video')
 if int(video.get('nb_frames',0))!=240:raise RuntimeError(f'Incomplete shot {i}')
 temp.replace(dest)
 save_json(state,{'fingerprint':sig,'frames':240,'duration':10,'render_seconds':round(time.monotonic()-start,2),'sample_frame_hashes':digests,'character_motion_samples':motion,'description':shot['description']})
 progress('animation',completed_shots=completed_shots(),current_shot=i,message=f'Completed shot {i+1}/60');return dest
def _render_job(item):return render_shot(*item)
def render(selected=None,force=False,workers=2):
 sc=plan();shots=sc['shots']
 jobs=[(s,shots[i-1] if i else None,force) for i,s in enumerate(shots) if selected is None or s['id']==selected]
 # Preserve stale versions outside the active output list; progress counts current assets.
 for s,_,_ in jobs:
  dest=OUT/'renders'/f"shot_{s['id']:03d}.mp4";state=OUT/'animation'/f"shot_{s['id']:03d}.json"
  if dest.exists() and (force or not state.exists() or json.loads(state.read_text()).get('fingerprint')!=shot_fingerprint(s)):
   stale=OUT/'renders'/'stale';stale.mkdir(exist_ok=True)
   dest.replace(stale/f"{dest.stem}_{time.time_ns()}.mp4")
 if workers<=1 or len(jobs)==1:
  for job in jobs:_render_job(job)
 else:
  # Two workers balance native drawing and two-thread encoders on six-core laptops.
  it=iter(jobs)
  with ProcessPoolExecutor(max_workers=min(2,workers)) as pool:
   pending={pool.submit(_render_job,next(it)) for _ in range(min(2,len(jobs)))}
   while pending:
    done,pending=wait(pending,return_when=FIRST_COMPLETED)
    for future in done:
     future.result()
     try:job=next(it)
     except StopIteration:continue
     pending.add(pool.submit(_render_job,job))
 progress('animation','completed',completed_shots=completed_shots())

def audio(sample_shot=None):
 if sample_shot is not None and (OUT/'audio.wav').exists():
  shot=next(s for s in plan()['shots'] if s['id']==sample_shot)
  with wave.open(str(OUT/'audio.wav'),'rb') as source:
   source.setpos(int(shot['start']*source.getframerate()));params=source.getparams();data=source.readframes(int(shot['duration']*source.getframerate()))
  with wave.open(str(OUT/'sample_audio.wav'),'wb') as dest:dest.setparams(params);dest.writeframes(data)
  return {'sample_shot':sample_shot,'source':'Validated full episode soundtrack'}
 from audio import generate_audio
 return generate_audio(plan(),OUT,sample_shot=sample_shot)
def sample():
 prepare();audio(8);sc=plan();p=render_shot(sc['shots'][8],sc['shots'][7]);dest=OUT/'sample.mp4'
 subprocess.run([ffmpeg(),'-v','error','-y','-i',str(p),'-i',str(OUT/'sample_audio.wav'),'-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-t','10','-movflags','+faststart',str(dest)],check=True)
 report=validate(dest,expected_seconds=10,expected_frames=240,full=False);save_json(OUT/'sample_quality_report.json',report)
 if not report['technical_pass']:raise RuntimeError('Sample failed technical validation')
 log('End-to-end animated sample completed and validated')
def export():
 files=[OUT/'renders'/f'shot_{i:03d}.mp4' for i in range(60)];missing=[str(p) for p in files if not p.exists()]
 if missing:raise RuntimeError(f'{len(missing)} shots are not rendered')
 if not (OUT/'audio.wav').exists():raise RuntimeError('Missing generated soundtrack')
 concat=OUT/'renders'/'concat.txt';concat.write_text('\n'.join("file '"+p.name+"'" for p in files),encoding='utf-8')
 dest=OUT/'THE_MAGICAL_WORLD_EP01_720P.mp4';progress('export')
 subprocess.run([ffmpeg(),'-v','error','-y','-f','concat','-safe','0','-i',str(concat),'-i',str(OUT/'audio.wav'),'-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-t','600','-movflags','+faststart','-metadata','title=THE MAGICAL WORLD - Episode 1: The Boy Without a Magic Signature',str(dest)],check=True)
 progress('export','completed',completed_shots=60,message='600-second MP4 exported');return dest
def validate(path=None,expected_seconds=600,expected_frames=14400,full=True):
 path=Path(path or OUT/'THE_MAGICAL_WORLD_EP01_720P.mp4');info=probe(path)
 v=next((s for s in info['streams'] if s['codec_type']=='video'),{});a=next((s for s in info['streams'] if s['codec_type']=='audio'),{})
 checks={'duration':abs(float(info['format']['duration'])-expected_seconds)<.05,'video_frames':int(v.get('nb_frames',0))==expected_frames,'resolution':(v.get('width'),v.get('height'))==(1280,720),'fps':v.get('avg_frame_rate')=='24/1','h264':v.get('codec_name')=='h264','aac':a.get('codec_name')=='aac','audio_48k':a.get('sample_rate')=='48000'}
 subprocess.run([ffmpeg(),'-v','error','-xerror','-i',str(path),'-f','null','-'],check=True);checks['full_decode']=True
 qc=OUT/('qc_full.log' if full else 'qc_sample.log')
 with qc.open('w') as f:subprocess.run([ffmpeg(),'-hide_banner','-i',str(path),'-vf','blackdetect=d=0.1:pix_th=0.03,freezedetect=n=-55dB:d=2','-an','-f','null','-'],stdout=subprocess.DEVNULL,stderr=f,check=True)
 text=qc.read_text();checks['no_black_segments']='black_start:' not in text;checks['no_frozen_segments_over_2s']='freeze_start:' not in text
 report={'file':str(path),'technical_pass':all(checks.values()),'checks':checks,'actual':{'seconds':float(info['format']['duration']),'frames':v.get('nb_frames'),'dimensions':[v.get('width'),v.get('height')],'fps':v.get('avg_frame_rate'),'bytes':int(info['format']['size'])},'production_mode':'independent 2D character rigs with painted plates and animated tracked effects','visual_review':'Representative sample and story beats must be reviewed; automated stream checks do not certify premium anime quality or anatomical correctness.','voice_review':'See audio_report.json and voices/dialogue_manifest.json for actual backend, timing and transformed voice identities; emotion and natural male voice quality are limited by the source model.'}
 if full:
  report['shots_completed']=completed_shots();report['timeline_seconds']=len(json.loads((OUT/'episode01_timeline.json').read_text()))
  report['continuity_limitations']='Motivated location cuts and keyed screen blocking; hand-drawn in-between frames and diffusion temporal conditioning are not used.'
  save_json(OUT/'quality_report.json',report)
 return report

def dispatch(args):
 if args.command=='prepare':prepare()
 elif args.command=='sample':sample()
 elif args.command=='render':render(args.shot,args.force,args.workers)
 elif args.command=='audio':audio()
 elif args.command=='export':export()
 elif args.command=='validate':print(json.dumps(validate(),indent=2))
 elif args.command=='all':
  prepare()
  if not (OUT/'sample_quality_report.json').exists():sample()
  audio();render(workers=args.workers);dest=export();report=validate(dest)
  if not report['technical_pass']:raise RuntimeError('Final video requires QC correction; inspect quality_report.json')
  progress('complete','completed',completed_shots=60,message='Episode generated; inspect quality report for artistic/voice limitations.');log('Production and technical QC complete')
def main():
 p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','sample','render','audio','export','validate','all','pause','resume']);p.add_argument('--shot',type=int);p.add_argument('--force',action='store_true');p.add_argument('--workers',type=int,choices=[1,2],default=2);args=p.parse_args()
 try:
  if args.command=='pause':(OUT/'PAUSE').touch();return
  resumed=args.command=='resume'
  if resumed:(OUT/'PAUSE').unlink(missing_ok=True);args.command='all'
  if args.command=='validate':dispatch(args);return
  with production_lock() as acquired:
   if not acquired:
    if resumed:log('Active production resumed; no duplicate worker launched.');return
    raise RuntimeError('Another production process is active. Use Resume to release its PAUSE checkpoint.')
   dispatch(args)
 except Exception as e:
  progress('error','failed',message=str(e));log(f'ERROR {type(e).__name__}: {e}');raise
if __name__=='__main__':main()
