"""Archive the reviewed private preview and audit temporary Drive objects."""
import argparse,json,hashlib
from pathlib import Path
from storage import Store,drive_retry

def archive(out,run_id):
    store=Store();prefix=f'fitness/previews/{run_id}/';files=[]
    report=json.loads((out/'quality-report.json').read_text())
    if report.get('published') or report.get('frames')!=1440:raise ValueError('Preview quality gate failed')
    for name in ['fitness-preview.mp4','thumbnail.jpg','plan.json','metadata.json','quality-report.json']:
        path=out/name;key=prefix+name;store.upload(path,key)
        files.append(dict(key=key,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size))
    receipt=dict(run_id=run_id,published=False,private_preview_archived=True,files=files)
    store.save(prefix+'archive.json',receipt)
    (out/'archive-receipt.json').write_text(json.dumps(receipt,indent=2))

def cleanup(out,run_id):
    store=Store();prefix=f'fitness/previews/{run_id}/';receipt=store.load(prefix+'archive.json',None)
    if not receipt or not receipt.get('private_preview_archived'):raise RuntimeError('No verified archive; retain all intermediates')
    # All inter-job media uses short-lived GitHub artifacts, not Drive. Audit the
    # exact current-run namespace; do not sweep other previews or public episodes.
    prefix_name=(prefix+'tmp/').replace('/','__');token=None;trashed=[];checked=0
    while True:
        page=drive_retry(lambda:store.client.files().list(q=f"'{store.folder}' in parents and trashed=false",pageSize=1000,
            pageToken=token,fields='nextPageToken,files(id,name,parents,appProperties)').execute())
        for item in page.get('files',[]):
            if not item.get('name','').startswith(prefix_name):continue
            key=item['name'].replace('__','/')
            if item.get('appProperties',{}).get('workflow_key')!=hashlib.sha256(key.encode()).hexdigest():continue
            checked+=1;store.check_private(item['id'])
            drive_retry(lambda item=item:store.client.files().update(fileId=item['id'],body=dict(trashed=True),fields='id,trashed').execute())
            trashed.append(item['id'])
        token=page.get('nextPageToken')
        if not token:break
    report=dict(run_id=run_id,temporary_drive_files_checked=checked,temporary_drive_files_trashed=len(trashed),
        final_preview_preserved=True,intermediates='GitHub artifacts expire after one day',published=False)
    store.save(prefix+'cleanup.json',report)
    (out/'cleanup-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['archive','cleanup']);p.add_argument('--out',type=Path,required=True);p.add_argument('--run-id',required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);globals()[a.stage](a.out,a.run_id)
