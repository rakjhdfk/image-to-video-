"""Resumable CPU neural dialogue, original score and synchronized sound design.

MeloTTS English-Indian is a female neural speaker (SID 2). Character profiles
below are deliberately disclosed pitch/rate treatments of that shared speaker,
not claims of six separately trained actors. Models/runtime are MIT/Apache-2.0.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, re, subprocess, sys, time, wave
from pathlib import Path

ROOT=Path(__file__).resolve().parent
MODEL_URL='https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-melo-tts-en.tar.bz2'
DEFAULT_MODEL=Path('/workspace/anime-models/vits-melo-tts-en')
DEFAULT_PYTHON=Path('/workspace/anime-audio-venv/bin/python')
SR=48000
PROFILES={
 'kael':{'pitch':.82,'speed':1.06,'gain':.93},
 'mira':{'pitch':1.00,'speed':1.04,'gain':.92},
 'riven':{'pitch':.91,'speed':1.12,'gain':.98},
 'elder':{'pitch':.69,'speed':.98,'gain':.97},
 'ancient':{'pitch':.64,'speed':.95,'gain':.93},
 'narrator':{'pitch':.77,'speed':1.03,'gain':.96},
}

def model_directory():
 configured=os.environ.get('ANIME_TTS_MODEL')
 if configured:return Path(configured).expanduser()
 local=ROOT/'models'/'vits-melo-tts-en'
 return local if (local/'model.onnx').exists() else DEFAULT_MODEL

def _wait_pause(out):
 paused=False
 while (out/'PAUSE').exists() or (out.parent/'PAUSE').exists():
  if not paused:_log(out,'Paused between dialogue clips; remove PAUSE to resume');paused=True
  time.sleep(.2)
 if paused:_log(out,'Resuming dialogue generation')

def _log(out,message):
 line=time.strftime('%Y-%m-%d %H:%M:%S')+' AUDIO '+message
 print(line,flush=True)
 with (out/'generation_log.txt').open('a',encoding='utf8') as f:f.write(line+'\n')

def _load_wav(path):
 import numpy as np
 import soundfile as sf
 from scipy.signal import resample_poly
 a,sr=sf.read(str(path),dtype='float32',always_2d=True)
 if sr!=SR:a=resample_poly(a,SR,sr,axis=0).astype(np.float32)
 return a

def _write(path,a):
 import soundfile as sf
 path.parent.mkdir(parents=True,exist_ok=True)
 sf.write(str(path),a,SR,subtype='PCM_16')

def _tts(model):
 import sherpa_onnx
 lex=model/'lexicon_episode.txt'
 base=(model/'lexicon.txt').read_text()
 extra='\naetheria ey th ih r iy ah 9 7 9 7 8 8\nardyn aa r d ih n 9 7 7 8 7\nveyne v ey n 7 9 7\naether ey th er 9 7 8\n'
 added='\n'.join(line for line in extra.splitlines() if line and not re.search('^'+re.escape(line.split()[0])+' ',base,re.M))
 lex.write_text(base+'\n'+added+'\n',encoding='utf8')
 cfg=sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
  vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=str(model/'model.onnx'),lexicon=str(lex),tokens=str(model/'tokens.txt')),
  num_threads=2,provider='cpu'),max_num_sentences=1)
 if not cfg.validate():raise RuntimeError('Invalid neural TTS configuration')
 return sherpa_onnx.OfflineTts(cfg)

def _normal_text(text):
 return text.replace('’',"'").replace('—',', ').replace('…','...').replace('“','').replace('”','')

def generate_voices(screenplay,out,duration=600):
 import numpy as np
 import soundfile as sf
 model=model_directory()
 if not (model/'model.onnx').exists():
  raise RuntimeError('MeloTTS model missing. Run setup_audio.py or set ANIME_TTS_MODEL. Required trusted model: '+MODEL_URL)
 engine=None
 folder=out/'voices';folder.mkdir(parents=True,exist_ok=True)
 if (model/'LICENSE').exists():(folder/'MeloTTS_LICENSE.txt').write_text((model/'LICENSE').read_text(),encoding='utf8')
 stems=np.zeros((round(duration*SR),2),np.float32)
 activity=np.zeros(round(duration*SR),np.float32)
 clips=[]
 for shot in screenplay['shots']:
  if shot['start']>=duration:continue
  lines=shot.get('dialogue',[])
  for j,line in enumerate(lines):
   _wait_pause(out)
   speaker=line['speaker'].lower();profile=PROFILES.get(speaker,PROFILES['narrator'])
   start=shot['start']+float(line.get('offset',0))
   if start>=duration:continue
   next_offset=float(lines[j+1].get('offset',shot['duration'])) if j+1<len(lines) else float(shot['duration'])
   available=min(next_offset-.12,float(shot['duration'])-.07,duration-shot['start'])-float(line.get('offset',0))
   if available<=.2:raise ValueError(f'No dialogue slot available for shot {shot["id"]} line {j}')
   text=_normal_text(line['text'])
   signature=hashlib.sha256(json.dumps([text,speaker,profile,available,'melo-sid2-v1']).encode()).hexdigest()[:16]
   clip=folder/f'{shot["id"]:03d}_{j:02d}_{speaker}_{signature}.wav'
   if not clip.exists():
    if engine is None:engine=_tts(model)
    _log(out,f'Generating shot {shot["id"]+1}/60 {speaker}: {text}')
    audio=engine.generate(text,sid=2,speed=profile['speed'])
    a=np.asarray(audio.samples,dtype=np.float32)
    # Trim only leading/trailing digital silence, retaining natural inner pauses.
    nz=np.flatnonzero(np.abs(a)>.006)
    if len(nz):a=a[max(0,nz[0]-int(.04*audio.sample_rate)):min(len(a),nz[-1]+int(.09*audio.sample_rate))]
    raw=folder/(clip.stem+'_raw.wav');sf.write(raw,a,audio.sample_rate,subtype='PCM_16')
    seconds=len(a)/audio.sample_rate
    tempo=max(1.0,seconds/available)
    if tempo>1.7:raise ValueError(f'Dialogue too long in shot {shot["id"]} line {j}: {seconds:.2f}s for {available:.2f}s slot. Edit text; no truncation performed.')
    filters=[f'rubberband=pitch={profile["pitch"]}:tempo={tempo}:formant=shifted:pitchq=quality',
             'highpass=f=70','lowpass=f=12500',f'volume={profile["gain"]}', 'alimiter=limit=0.9:level=false']
    if speaker=='ancient':filters+=['aecho=0.8:0.55:85|170|290:0.22|0.13|0.08']
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(raw),'-af',','.join(filters),'-ar',str(SR),'-ac','1','-t',str(available),str(clip)],check=True)
    raw.unlink()
   a=_load_wav(clip)[:,0]
   rms=float(np.sqrt(np.mean(a*a))) if len(a) else 0
   peak=float(np.max(np.abs(a))) if len(a) else 0
   if peak>0:
    a*=min(.115/max(rms,1e-8),.80/peak)
    _write(clip,a)
   # Hard slot limit is metadata after controlled time-stretch, not dialogue truncation.
   if len(a)>int(available*SR)+1200:raise ValueError('Clip exceeds its scene boundary')
   left=max(0,int(start*SR));right=min(len(stems),left+len(a));a=a[:right-left]
   pan={'kael':-.13,'mira':.17,'riven':.28,'elder':-.2}.get(speaker,0)
   stems[left:right,0]+=a*math.sqrt((1-pan)/2)
   stems[left:right,1]+=a*math.sqrt((1+pan)/2)
   activity[left:right]=1
   clips.append({'shot':shot['id'],'speaker':speaker,'text':line['text'],'start':start,'end':start+len(a)/SR,'file':str(clip.relative_to(out)),'source_voice':'MeloTTS EN_INDIA SID2','profile':profile})
 _write(folder/'dialogue_stem.wav',stems)
 (folder/'dialogue_manifest.json').write_text(json.dumps(clips,indent=2),encoding='utf8')
 return stems,activity,clips

def _add(stem,start,data,pan=0,gain=1):
 import numpy as np
 at=round(start*SR)
 if at>=len(stem) or at+len(data)<=0:return
 if at<0:data=data[-at:];at=0
 n=min(len(data),len(stem)-at)
 stem[at:at+n,0]+=data[:n]*gain*math.sqrt((1-pan)/2)
 stem[at:at+n,1]+=data[:n]*gain*math.sqrt((1+pan)/2)

def _note(freq,duration,kind='bell',seed=1):
 import numpy as np
 n=round(duration*SR);t=np.arange(n,dtype=np.float32)/SR
 if kind=='pad':
  y=(np.sin(2*np.pi*freq*t)+.32*np.sin(2*np.pi*freq*2.002*t)+.12*np.sin(2*np.pi*freq*3*t))
  env=np.minimum(t/.25,1)*np.minimum((duration-t)/.35,1)
 elif kind=='bass':
  y=np.sin(2*np.pi*freq*t)+.2*np.sin(2*np.pi*2*freq*t);env=np.minimum(t/.012,1)*np.exp(-t*3)
 elif kind=='pluck':
  y=(np.sin(2*np.pi*freq*t)+.22*np.sin(2*np.pi*freq*2*t)+.1*np.sin(2*np.pi*freq*3*t));env=np.minimum(t/.005,1)*np.exp(-t*5)
 else:
  y=np.sin(2*np.pi*freq*t)+.23*np.sin(2*np.pi*freq*2.76*t)+.12*np.sin(2*np.pi*freq*4.07*t);env=np.minimum(t/.006,1)*np.exp(-t*4)
 return (y*env).astype(np.float32)

def generate_music(out,duration):
 import numpy as np
 music=np.zeros((round(duration*SR),2),np.float32);beat=.60
 roots=[50,46,53,48,50,43,46,45]
 intensity=[.60,.38,.52,.95,.80,.25,.72,1,.45,.60]
 motif=[0,7,12,10,7,3,5,7]
 def hz(m):return 440*2**((m-69)/12)
 for bar,start in enumerate(np.arange(0,duration,beat*4)):
  section=min(9,int(start//60));e=intensity[section];root=roots[(bar+section)%len(roots)]
  minor=section not in [0,2,9]
  for ni,interval in enumerate([0,3 if minor else 4,7]):
   _add(music,float(start),_note(hz(root+12+interval),2.7,'pad'),pan=(ni-1)*.45,gain=.017*e)
  for b in range(4):
   st=float(start+b*beat)
   _add(music,st,_note(hz(root-12),.48,'bass'),gain=.035*e)
   _add(music,st,_note(hz(root+24+motif[(bar*4+b)%8]),.65,'bell'),pan=.35*math.sin(bar+b),gain=.032*e)
   if section in [3,4,6,7]:
    t=np.arange(round(.17*SR),dtype=np.float32)/SR
    kick=np.sin(2*np.pi*(70*t-65*t*t))*np.exp(-t*24)
    _add(music,st,kick,gain=.08*e)
    rng=np.random.default_rng(bar*7+b);h=rng.normal(0,1,round(.08*SR)).astype(np.float32);h[1:]-=.9*h[:-1];h*=np.exp(-np.arange(len(h))/SR*70)
    _add(music,st+.3,h,pan=(-1 if b%2 else 1)*.4,gain=.012*e)
   else:
    _add(music,st+beat/2,_note(hz(root+19),.4,'pluck'),pan=-.35,gain=.017*e)
 # Original recurring four-note theme resolves in final section.
 for st in np.arange(4,duration,12):
  sec=min(9,int(st//60));root=62 if sec in [0,6,9] else 60
  for j,iv in enumerate([0,3,7,12]):_add(music,float(st+j*.45),_note(hz(root+iv),1.0,'bell'),pan=.12,gain=.025*intensity[sec])
 fade=np.minimum(np.arange(len(music),dtype=np.float32)/SR/2,1)*np.minimum((len(music)-np.arange(len(music),dtype=np.float32))/SR/3,1)
 music*=fade[:,None]
 _write(out/'music'/'original_score.wav',music)
 return music

def _effect(kind,duration=1,seed=1):
 import numpy as np
 from scipy.signal import butter,sosfilt
 rng=np.random.default_rng(seed);n=round(duration*SR);t=np.arange(n,dtype=np.float32)/SR
 noise=rng.normal(0,1,n).astype(np.float32)
 env=np.minimum(t/.02,1)*np.minimum((duration-t)/.15,1)
 if kind=='step':return noise*np.exp(-t*45)*.13+np.sin(2*np.pi*90*t)*np.exp(-t*42)*.25
 if kind in ['lightning','explosion','debris','shatter','impact']:
  y=sosfilt(butter(2,3500 if kind=='shatter' else 1800,fs=SR,output='sos'),noise)
  y+=.45*np.sin(2*np.pi*(55*t-15*t*t))
  return (y*np.exp(-t*(3 if kind=='explosion' else 5))*env).astype(np.float32)
 if kind in ['wind','crowd']:
  return (sosfilt(butter(2,600,fs=SR,output='sos'),noise)*env*.2).astype(np.float32)
 if kind=='rift':
  return ((np.sin(2*np.pi*(110*t+13*t*t))+.5*np.sin(2*np.pi*113*t)+noise*.08)*env*.24).astype(np.float32)
 if kind in ['silver','origin','seal','pulse','magic']:
  base={'silver':880,'origin':440,'seal':220,'pulse':165,'magic':660}[kind]
  y=sum(np.sin(2*np.pi*(base*ratio*t+25*t*t))*amp for ratio,amp in [(1,.36),(1.5,.2),(2,.10),(2.5,.06)])
  return (y*env*np.exp(-t*.8)).astype(np.float32)
 if kind=='whoosh':return (sosfilt(butter(2,[300,4000],btype='bandpass',fs=SR,output='sos'),noise)*np.sin(np.pi*t/duration)**2*.36).astype(np.float32)
 return (noise*env*np.exp(-t*5)*.1).astype(np.float32)

def generate_effects(screenplay,out,duration):
 import numpy as np
 fx=np.zeros((round(duration*SR),2),np.float32);events=[]
 # A low garden/city breeze persists; it is actual generated ambience, not silence.
 for start in np.arange(0,duration,5):_add(fx,float(start),_effect('wind',5,round(start)+41),pan=math.sin(start)*.5,gain=.09)
 kinds={'wind'}
 for shot in screenplay['shots']:
  start=float(shot['start'])
  if start>=duration:continue
  action=shot.get('action','talk').lower();magic=shot.get('magic','none').lower()
  scheduled=[]
  if action in ['walk','run','rescue']:
   interval=.32 if action in ['run','rescue'] else .56
   scheduled += [(t,'step',.14,.21) for t in np.arange(.3,9.8,interval)]
  if magic!='none':scheduled +=[(.7,magic if magic in ['silver','origin','seal','rift'] else 'lightning' if magic=='crimson' else 'magic',2.5,.32)]
  if action in ['battle','attack','dodge']:scheduled +=[(1.8,'whoosh',.6,.37),(3.3,'impact',.7,.40),(6.4,'lightning',.8,.32),(8.0,'whoosh',.7,.3)]
  if action in ['rift','rescue']:scheduled +=[(2,'rift',3,.28),(5.5,'debris',.7,.3)]
  if action in ['ceremony','weave','seal']:scheduled +=[(2.5,'pulse',1.7,.28),(7.3,'silver',1.6,.24)]
  if action=='fall':scheduled +=[(4.7,'impact',.7,.35)]
  for j,event in enumerate(shot.get('sfx',[])[:4]):
   name=(event.get('name','') if isinstance(event,dict) else str(event)).lower()
   kind='shatter' if any(w in name for w in ['glass','crystal','shatter']) else 'lightning' if 'lightning' in name else 'explosion' if 'explosion' in name else 'whoosh' if 'whoosh' in name else None
   if kind:scheduled.append((1.2+j*2.2,kind,.9,.25))
  for j,(offset,kind,length,gain) in enumerate(scheduled):
   kinds.add(kind);_add(fx,start+float(offset),_effect(kind,length,shot['id']*100+j),pan=.45*math.sin(j*2),gain=gain)
   events.append({'shot':shot['id'],'time':start+float(offset),'kind':kind,'duration':length})
 for kind in kinds:_write(out/'sound_effects'/(kind+'.wav'),_effect(kind,1.5,12))
 _write(out/'sound_effects'/'effects_stem.wav',fx)
 (out/'sound_effects'/'events.json').write_text(json.dumps(events,indent=2))
 return fx,events

def generate_audio(screenplay,outdir,duration=600,sample_shot=None):
 out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
 if sample_shot is not None:
  import copy,shutil
  selected=next((s for s in screenplay['shots'] if s['id']==sample_shot),None)
  if selected is None:raise ValueError(f'Shot {sample_shot} missing')
  selected=copy.deepcopy(selected);selected['start']=0
  part=copy.deepcopy(screenplay);part['shots']=[selected]
  report=generate_audio(part,out/'sample_audio',duration=float(selected['duration']))
  shutil.copy2(out/'sample_audio'/'audio.wav',out/'sample_audio.wav')
  return report
 try:import sherpa_onnx,soundfile
 except ImportError:
  python=Path(os.environ.get('ANIME_AUDIO_PYTHON',DEFAULT_PYTHON))
  if not python.exists():raise RuntimeError('Audio dependencies missing in this Python. Run: python -m pip install -r requirements.txt; then python setup_audio.py. ANIME_AUDIO_PYTHON can select an existing compatible environment.')
  source=out/'audio_screenplay_input.json';source.write_text(json.dumps(screenplay),encoding='utf8')
  subprocess.run([str(python),str(Path(__file__).resolve()),'--screenplay',str(source),'--out',str(out),'--duration',str(duration)],check=True)
  return json.loads((out/'audio_report.json').read_text())
 import numpy as np
 from scipy.ndimage import maximum_filter1d,gaussian_filter1d
 _log(out,f'Start audio production: {duration}s / CPU neural English-Indian')
 voice,activity,clips=generate_voices(screenplay,out,duration)
 music=generate_music(out,duration)
 effects,events=generate_effects(screenplay,out,duration)
 # Duck with smooth 60ms attack and 180ms release, using coarse 100Hz control.
 n=len(activity);control=np.array([activity[i:min(n,i+480)].max(initial=0) for i in range(0,n,480)],dtype=np.float32)
 control=maximum_filter1d(control,size=19);control=gaussian_filter1d(control,4)
 duck=np.interp(np.arange(n)/480,np.arange(len(control)),control).astype(np.float32)
 mix=voice+music*(1-.72*duck[:,None])+effects*(1-.25*duck[:,None])
 peak=float(np.max(np.abs(mix)))
 if peak>0:mix*=.92/peak
 fade=np.minimum(np.arange(n,dtype=np.float32)/SR/.2,1)*np.minimum((n-np.arange(n,dtype=np.float32))/SR/.6,1)
 mix*=fade[:,None]
 _write(out/'audio.wav',mix)
 report={'duration_seconds':duration,'sample_rate':SR,'channels':2,'peak':float(np.max(np.abs(mix))),
  'dialogue_clips':len(clips),'effects':len(events),'backend':'MeloTTS EN_INDIA via sherpa-onnx CPU',
  'voice_limitations':['All six identities derive from the same female Indian-English neural speaker using consistent pitch/rate/formant treatments. They are not six independent natural voice actors.','Emotional direction is approximated through timing and processing; human listening and accent quality review remain required.'],
  'licenses':{'MeloTTS':'MIT (LICENSE bundled with official model archive)','sherpa-onnx':'Apache-2.0','music':'Original synthesized composition','sound_effects':'Original synthesized effects'},
  'model_source':MODEL_URL,'model_sha256':hashlib.file_digest((model_directory()/'model.onnx').open('rb'),'sha256').hexdigest()}
 (out/'audio_report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 if duration==600 and (out/'episode01_timeline.json').is_file():
  from timeline_sync import sync_timeline
  sync_timeline(out)
 _log(out,'Audio complete: '+json.dumps({'clips':len(clips),'seconds':duration,'peak':report['peak']}))
 return report

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--screenplay',required=True);p.add_argument('--out',required=True);p.add_argument('--duration',type=float,default=600);p.add_argument('--sample-shot',type=int)
 a=p.parse_args();generate_audio(json.loads(Path(a.screenplay).read_text()),Path(a.out),a.duration,a.sample_shot)
