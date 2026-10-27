"""Exercise the real local Qwen runtime before unattended script generation."""
import json
import workflow as w
from story_cpu import MODEL_ID


def main():
    schema = {'type': 'object', 'properties': {'ready': {'type': 'boolean'},
        'image_prompt': {'type': 'string'}}, 'required': ['ready', 'image_prompt'],
        'additionalProperties': False}
    result = w.request_text('chat/completions', {'model': MODEL_ID,
        'messages': [{'role': 'user', 'content': 'Set ready to true. Write one 12-22 word realistic historical image prompt showing an adult tending embers in a prehistoric rock shelter.'}],
        'response_format': {'type': 'json_schema', 'json_schema': {'schema': schema}},
        'max_completion_tokens': 256, 'temperature': .3})
    data = json.loads(result['choices'][0]['message']['content'])
    if data['ready'] is not True or not data['image_prompt'].strip():
        raise RuntimeError('Local Qwen readiness failed')
    print(json.dumps({'check': 'Local Qwen structured text', 'passed': True, 'model': MODEL_ID}))


if __name__ == '__main__':
    main()
