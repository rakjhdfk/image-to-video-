"""Install the pinned official CPU MeloTTS English model without disabling TLS.

Requires Python 3.12+, the project's pip requirements, and FFmpeg with rubberband.
The archive pin records the official GitHub release bytes obtained through
verified HTTPS during implementation; it is not a claim of a publisher signature.
Existing files are validated or preserved, never silently replaced.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, shutil, ssl, subprocess, tarfile, tempfile, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent
URL='https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-melo-tts-en.tar.bz2'
ARCHIVE_SHA256='f87bc5752ea3ec34273a2cc0c5086854c18b6b89dfd0534b5248e86a14cedb5d'
MODEL_SHA256='5f72fbbc4105b008de8141049c0535b7a99a527ddb80fcbc0c0ac8a046997544'
FOLDER='vits-melo-tts-en'

def digest(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def runtime_check():
 for package in ['sherpa_onnx','numpy','scipy','soundfile']:
  if importlib.util.find_spec(package) is None:raise RuntimeError(f'Missing {package}; install requirements.txt in this Python first.')
 ffmpeg=shutil.which('ffmpeg')
 if not ffmpeg:raise RuntimeError('FFmpeg is missing from PATH. Install a build that includes the rubberband audio filter.')
 result=subprocess.run([ffmpeg,'-hide_banner','-filters'],check=True,capture_output=True,text=True)
 if 'rubberband' not in result.stdout:raise RuntimeError('This FFmpeg build lacks rubberband; install a full build with librubberband for the disclosed voice treatments.')

def verify_model(directory):
 for name in ['model.onnx','tokens.txt','lexicon.txt','LICENSE']:
  if not (directory/name).is_file():raise RuntimeError(f'Existing model directory is incomplete ({name} missing); it has been preserved. Choose a new --destination.')
 if digest(directory/'model.onnx')!=MODEL_SHA256:raise RuntimeError('Existing model does not match the supported model checksum; it has been preserved. Choose a new --destination.')

def install(destination=None,archive=None):
 runtime_check()
 destination=Path(destination or ROOT/'models'/FOLDER).resolve()
 if destination.exists():
  verify_model(destination);print('Verified existing model:',destination);return destination
 destination.parent.mkdir(parents=True,exist_ok=True)
 # A temporary sibling makes the final rename atomic on Windows and Linux.
 with tempfile.TemporaryDirectory(prefix='.melo-install-',dir=destination.parent) as work:
  work=Path(work);package=Path(archive).resolve() if archive else work/'model.tar.bz2'
  if not archive:
   print('Downloading official CPU model:',URL,flush=True)
   request=urllib.request.Request(URL,headers={'User-Agent':'MagicalWorld-LocalProducer/1.0'})
   with urllib.request.urlopen(request,context=ssl.create_default_context(),timeout=120) as response,package.open('wb') as f:
    shutil.copyfileobj(response,f,length=1024*1024)
  if digest(package)!=ARCHIVE_SHA256:raise RuntimeError('Official model archive checksum mismatch. No artifacts were installed; investigate release changes instead of disabling verification.')
  extracted=work/'extracted';extracted.mkdir()
  with tarfile.open(package,'r:bz2') as tar:
   members=tar.getmembers()
   for member in members:
    p=Path(member.name)
    if p.is_absolute() or '..' in p.parts or (not member.isfile() and not member.isdir()):raise RuntimeError('Unsafe archive member; extraction refused.')
    if not p.parts or p.parts[0]!=FOLDER:raise RuntimeError('Unexpected archive root; extraction refused.')
   tar.extractall(extracted,members=members,filter='data')
  installed=extracted/FOLDER;verify_model(installed)
  (installed/'installation_manifest.json').write_text(json.dumps({'source':URL,'archive_sha256':ARCHIVE_SHA256,'model_sha256':MODEL_SHA256,'license':'MIT','speaker':'EN_INDIA, SID2','note':'Character identities are processed profiles of this same female neural speaker.'},indent=2),encoding='utf8')
  installed.rename(destination)
 print('Installed and verified:',destination)
 return destination

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--destination',type=Path);p.add_argument('--archive',type=Path,help='Optional existing official archive, still checksum verified')
 a=p.parse_args();install(a.destination,a.archive)
