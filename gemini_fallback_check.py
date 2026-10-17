"""One live structured Gemini request through a simulated Groq rate-limit response."""
import json
import os
import datetime
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
    # Capture the exact production outline request, without generating narration.
    captured = []
    class OutlineCaptured(Exception):
        pass
    def capture(endpoint, payload):
        captured.append(payload)
        raise OutlineCaptured()
    with patch.dict(os.environ, {'CONTENT_TYPE':'financial-storytelling'}), \
         patch.object(w, 'request_groq', side_effect=capture):
        try:
            w.make_story(datetime.date.today().isoformat(), [])
        except OutlineCaptured:
            pass
    payload = captured[0]
    w._gemini_fallback_active=False
    with patch.object(requests,'post',side_effect=post):
        result = w.request_groq('chat/completions',payload)
    data=json.loads(result['choices'][0]['message']['content'])
    assert len(data['scenes'])==20
    assert set(data['scenes'])=={f'chapter_{i:02}' for i in range(1,21)}
    assert data['title'].startswith('POV: You')
    assert data['story_bible']
    assert all(s['summary'] and s['continuity_note'] for s in data['scenes'].values())
    assert len(calls)==2 and w._gemini_fallback_active
    print(json.dumps({'check':'Live Groq 429 to Gemini fallback','passed':True,'structured_json':True,'production_outline_chapters':20}))


if __name__ == '__main__':
    main()
