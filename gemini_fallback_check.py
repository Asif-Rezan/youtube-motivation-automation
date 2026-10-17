"""One live structured Gemini request through a simulated Groq rate-limit response."""
import json
from types import SimpleNamespace
from unittest.mock import patch
import requests
import workflow as w


def main():
    original = requests.post
    calls = []
    def post(url, **kwargs):
        calls.append(url)
        if url.startswith('https://api.groq.com/'):
            return SimpleNamespace(ok=False,status_code=429,headers={},json=lambda:{'error':{'code':'rate_limit_exceeded'}})
        return original(url, **kwargs)
    payload = {'messages':[{'role':'user','content':'Return status ok and scene: An adult reads a bill at a kitchen table.'}],
               'max_completion_tokens':256, 'response_format':{'type':'json_schema','json_schema':{'schema':{
                   'type':'object','properties':{'status':{'type':'string','enum':['ok']},'scene':{'type':'string'}},
                   'required':['status','scene'],'additionalProperties':False}}}}
    w._gemini_fallback_active=False
    with patch.object(requests,'post',side_effect=post):
        result = w.request_groq('chat/completions',payload)
    data=json.loads(result['choices'][0]['message']['content'])
    assert data['status']=='ok' and data['scene']
    assert len(calls)==2 and w._gemini_fallback_active
    print(json.dumps({'check':'Live Groq 429 to Gemini fallback','passed':True,'structured_json':True}))


if __name__ == '__main__':
    main()
