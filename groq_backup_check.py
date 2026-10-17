"""Verify one real backup-key call after a simulated primary rate limit."""
import json
from types import SimpleNamespace
from unittest.mock import patch
import requests
import workflow as w


def main():
    original=requests.post
    calls=[]
    def post(url,**kwargs):
        calls.append(url)
        assert url.startswith('https://api.groq.com/')
        if len(calls)==1:
            return SimpleNamespace(ok=False,status_code=429,headers={},json=lambda:{'error':{'code':'rate_limit_exceeded'}})
        return original(url,**kwargs)
    w._groq_backup_active=False
    payload={'model':'openai/gpt-oss-120b','messages':[{'role':'user','content':'Return JSON with status equal to ok.'}],
             'reasoning_effort':'low','max_completion_tokens':256,'response_format':{'type':'json_object'}}
    with patch.object(requests,'post',side_effect=post):
        result=w.request_groq('chat/completions',payload)
    assert json.loads(result['choices'][0]['message']['content'])['status']=='ok'
    assert w._groq_backup_active and len(calls)==2
    print(json.dumps({'check':'Live primary 429 to backup Groq key','passed':True}))


if __name__=='__main__':main()
