"""Encrypted credential transfer; private key stays in owner-only Drive."""
import base64
import hashlib
import json
import os
from pathlib import Path
import tempfile
import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

CONTEXT = b'YoutubeAutomation/runtime/v1'

def unwrap(store, envelope):
    record = store.load('runtime-transfer-key.json', None)
    if not record:
        raise RuntimeError('Private transfer key is not configured')
    private = serialization.load_pem_private_key(record['private_pem'].encode(), password=None)
    public = private.public_key().public_bytes(serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo)
    if hashlib.sha256(public).hexdigest() != envelope['key_fingerprint']:
        raise RuntimeError('Credential transfer key does not match')
    key = private.decrypt(base64.b64decode(envelope['wrapped_key']),
        padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=CONTEXT))
    data = AESGCM(key).decrypt(base64.b64decode(envelope['nonce']),
        base64.b64decode(envelope['ciphertext']), CONTEXT)
    return json.loads(data)

def load_runtime_environment(store):
    if os.getenv('GROQ_API_KEY'):
        return
    envelope = store.load('runtime-config-envelope.json', None)
    if not envelope:
        return
    payload = unwrap(store, envelope)
    key = payload.get('groq_api_key', '')
    if key:
        if os.getenv('GITHUB_ACTIONS') == 'true':
            print('::add-mask::' + key, flush=True)
        os.environ['GROQ_API_KEY'] = key

def main():
    import sys
    from workflow import Store, duration
    from googleapiclient.http import MediaFileUpload
    store = Store()
    mode = sys.argv[1]
    if mode == 'create-key':
        record = store.load('runtime-transfer-key.json', None)
        if not record:
            key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
            record = {'private_pem': key.private_bytes(serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()}
            store.save('runtime-transfer-key.json', record)
        private = serialization.load_pem_private_key(record['private_pem'].encode(), password=None)
        public = private.public_key().public_bytes(serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo).decode()
        print(json.dumps({'public_transfer_key': public}), flush=True)
        return
    if mode != 'import':
        raise ValueError('Unsupported transfer mode')
    envelope = json.loads(Path('runtime-envelope.json').read_text())
    payload = unwrap(store, envelope)
    store.save('runtime-config-envelope.json', envelope)
    load_runtime_environment(store)
    music = payload['music']
    if not music['audioUrl'].startswith('https://'):
        raise RuntimeError('Music download requires HTTPS')
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp)/'generated-score.wav'
        response = requests.get(music['audioUrl'], timeout=180)
        if response.status_code != 200:
            raise RuntimeError('Music provider download failed')
        path.write_bytes(response.content)
        actual_duration = duration(path)
        result = store.put('music/generated-score.wav',
            MediaFileUpload(str(path), resumable=True), path.stat().st_size)
        store.save('music-manifest.json', {'source': 'AI-generated (vidIQ)',
            'title': 'Quiet Steps', 'artist': 'AI-generated with vidIQ',
            'license': 'Royalty-free original track per vidIQ music generation service',
            'provider_music_id': music['musicId'], 'duration_seconds': actual_duration,
            'attribution_required': False, 'attribution': '',
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'file_id': result['id']})
    response = requests.get('https://api.groq.com/openai/v1/models',
        headers={'Authorization': 'Bearer ' + os.environ['GROQ_API_KEY']}, timeout=30)
    if response.status_code != 200:
        print(json.dumps({'check': 'Groq API authorization', 'passed': False,
            'http_status': response.status_code}))
        raise SystemExit(1)
    ids = {model['id'] for model in response.json().get('data', [])}
    print(json.dumps({'check': 'Encrypted runtime credentials and generated music',
        'passed': True, 'groq_authorized': True,
        'story_model_available': 'llama-3.3-70b-versatile' in ids,
        'speech_model_available': 'canopylabs/orpheus-v1-english' in ids}), flush=True)

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'check': 'Encrypted cloud setup', 'passed': False,
            'error_type': type(error).__name__,
            'http_status': getattr(getattr(error, 'resp', None), 'status', None)}))
        raise SystemExit(1)
