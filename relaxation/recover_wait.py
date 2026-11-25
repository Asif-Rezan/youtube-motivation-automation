"""Wait for saved AI assets; recover composition without regenerating any models."""
import json,os,re,time,urllib.request
from pathlib import Path
source=str(json.loads(Path('.generation/relaxation-recovery-request.json').read_text())['source_run'])
if not re.fullmatch(r'[1-9][0-9]{0,19}',source):raise ValueError('Invalid source run')
repo=os.environ['GITHUB_REPOSITORY'];token=os.environ['GH_TOKEN']
required={'relaxation-plan','relaxation-ai-music','relaxation-ai-rain'}|{f'relaxation-scene-{i}' for i in range(6)}
def get(path):
 req=urllib.request.Request(f'https://api.github.com/repos/{repo}/{path}',headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})
 with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
for attempt in range(150):
 jobs=get(f'actions/runs/{source}/jobs?per_page=100')['jobs']
 generation=[j for j in jobs if j['name']!='Mix, dissolve every ten seconds, validate and deliver sample']
 failed=[j['name'] for j in generation if j['status']=='completed' and j['conclusion']!='success']
 if failed:raise RuntimeError('Source AI generation failed; inspect: '+', '.join(failed))
 assets=get(f'actions/runs/{source}/artifacts?per_page=100')['artifacts']
 names={a['name'] for a in assets if not a['expired']}
 ready=required<=names and len(generation)==9 and all(j['status']=='completed' and j['conclusion']=='success' for j in generation)
 print(json.dumps(dict(source=source,available=len(required&names),required=len(required),ready=ready)),flush=True)
 if ready:
  with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write('source_run='+source+'\n')
  break
 time.sleep(30)
else:raise TimeoutError('AI artifacts not ready within 75 minutes; preserved source outputs')
