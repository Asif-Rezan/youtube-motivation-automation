"""Wait for complete source inputs, without rerunning expensive AI generation."""
import json,os,time,urllib.request,sys
from pathlib import Path

def main():
 request=json.loads(Path('.generation/relaxation-production-recovery.json').read_text())
 source=str(request['source_run'])
 if not source.isdigit():raise ValueError('Invalid source Actions run')
 repo=os.environ['GITHUB_REPOSITORY'];token=os.environ['GH_TOKEN']
 needed={'long-plan','long-music','long-rain'}|{f'long-image-{i}' for i in range(20)}
 deadline=time.monotonic()+95*60
 while time.monotonic()<deadline:
  url=f'https://api.github.com/repos/{repo}/actions/runs/{source}/artifacts?per_page=100'
  req=urllib.request.Request(url,headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json'})
  with urllib.request.urlopen(req,timeout=60) as response:data=json.load(response)
  found={a['name'] for a in data['artifacts'] if not a.get('expired')}
  missing=needed-found
  if not missing:
   with open(os.environ['GITHUB_OUTPUT'],'a') as output:output.write('source_run='+source+'\n')
   print('All 100 generated images, AI piano, recorded rain and original plan available',flush=True);return
  print(json.dumps(dict(stage='waiting_for_source_inputs',missing=sorted(missing))),flush=True)
  time.sleep(30)
 raise RuntimeError('Source assets incomplete; retain source run and retry recovery without regenerating')
def verify_inputs():
 root=Path('output/relaxation-production')
 request=json.loads(Path('.generation/relaxation-production-recovery.json').read_text())
 plan=json.loads((root/'plan.json').read_text())
 if str(plan['run_id'])!=str(request['source_run']) or plan['seconds']!=10800:
  raise ValueError('Recovery source plan identity mismatch')
 required=['music-original.wav','rain-original.wav','metadata.json']+[f'{kind}-{i:02d}.png' for kind in ('scene','depth') for i in range(100)]
 missing=[name for name in required if not (root/name).is_file() or (root/name).stat().st_size==0]
 if missing:raise ValueError('Incomplete source artifacts: '+', '.join(missing))
 print('Verified original plan and all required generated inputs',flush=True)

def stop_source():
 source=str(json.loads(Path('.generation/relaxation-production-recovery.json').read_text())['source_run'])
 if not source.isdigit() or source==os.environ['GITHUB_RUN_ID']:raise ValueError('Invalid source cancellation target')
 url=f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{source}"
 headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json'}
 with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=60) as response:status=json.load(response)['status']
 if status!='completed':
  with urllib.request.urlopen(urllib.request.Request(url+'/cancel',headers=headers,method='POST'),timeout=60):pass
 print('Source inputs secured; superseded source rendering stopped',flush=True)

if __name__=='__main__':
 if '--stop-source' in sys.argv:stop_source()
 elif '--verify'  in sys.argv:verify_inputs()
 else:main()
