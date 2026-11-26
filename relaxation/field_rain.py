"""Verified licensed field recording, selected conservatively for soft rain ambience."""
import hashlib,json,math,subprocess
from pathlib import Path
import numpy as np
ASSETS=Path(__file__).with_name('assets')

def prepare(out,run_id):
 import soundfile as sf
 from scipy.signal import butter,sosfiltfilt
 info=json.loads((ASSETS/'rain-source.json').read_text());source=ASSETS/'rain-alex36917-blanket.ogg'
 if hashlib.sha256(source.read_bytes()).hexdigest()!=info['sha256']:raise ValueError('Recorded rain checksum mismatch')
 raw=out/'recorded-rain-decoded.wav'
 subprocess.run(['ffmpeg','-v','error','-y','-i',str(source),'-ar','48000','-ac','2',str(raw)],check=True)
 pcm,rate=sf.read(raw,dtype='float32',always_2d=True);length=len(pcm)/rate;seconds=60
 # Avoid the end of the source (the original recording describes a distant horn).
 # A numerical quiet-window check is not a guarantee that no external sound remains.
 candidates=[]
 for start in range(5,max(6,int(length-30-seconds)),3):
  clip=pcm[start*rate:(start+seconds)*rate];levels=np.array([np.sqrt(np.mean(c.astype(float)**2)) for c in np.array_split(clip,30)])
  rms=max(float(levels.mean()),1e-8);peak=float(np.abs(clip).max())
  candidates.append((float(levels.std())/rms+peak/(rms*80),start))
 if not candidates:raise ValueError('Rain recording too short for the reviewed selection rule')
 candidates.sort();start=candidates[0][1];clip=pcm[start*rate:(start+seconds)*rate]
 clip=sosfiltfilt(butter(2,[55,7600],btype='bandpass',fs=rate,output='sos'),clip,axis=0).astype('float32')
 if not np.isfinite(clip).all() or np.sqrt(np.mean(clip**2))<1e-5:raise ValueError('Recorded rain decode is silent or invalid')
 sf.write(out/'rain-original.wav',clip,rate,subtype='PCM_16');raw.unlink()
 (out/'rain-provenance.json').write_text(json.dumps(dict(**info,selection_start_seconds=start,selection_duration_seconds=seconds,backend='licensed-field-recording',processing='Quiet-window selection, gentle 55–7600 Hz filtering; crossfades/gain applied during mixing'),indent=2))
 (out/'nature-license.txt').write_text(info['credit']+'\n'+info['source']+'\n'+info['license_url']+'\n')
 print('LICENSED_RECORDED_RAIN_READY',seconds,start,flush=True)
 return info
