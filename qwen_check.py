"""Exercise the real local Qwen runtime before unattended script generation."""
import json
import workflow as w
from story_cpu import MODEL_ID, decoder_schema
from human_history import THUMBNAIL_SCHEMA, build_outline_schema
from video_metadata import build_metadata_schema


def check_production_grammar():
    from llama_cpp import LlamaGrammar
    def object_schema(properties):
        return {'type': 'object', 'properties': properties, 'required': list(properties),
                'additionalProperties': False}
    # Same twenty-chapter outline used by stage-story, including thumbnail constraints.
    schema = build_outline_schema(object_schema)
    LlamaGrammar.from_json_schema(json.dumps(decoder_schema(schema)), verbose=False)
    print(json.dumps({'check': 'Production outline grammar conversion', 'passed': True}))
    LlamaGrammar.from_json_schema(json.dumps(decoder_schema(build_metadata_schema(object_schema))), verbose=False)
    print(json.dumps({'check': 'Production metadata grammar conversion', 'passed': True}))


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--schemas-only', action='store_true')
    args = parser.parse_args()
    check_production_grammar()
    if args.schemas_only:
        return
    schema = {'type': 'object', 'properties': {'ready': {'type': 'boolean'},
        'image_prompt': {'type': 'string'}, 'thumbnail_text': THUMBNAIL_SCHEMA}, 'required': ['ready', 'image_prompt', 'thumbnail_text'],
        'additionalProperties': False}
    result = w.request_text('chat/completions', {'model': MODEL_ID,
        'messages': [{'role': 'user', 'content': 'Set ready to true. Write one 12-22 word realistic historical image prompt showing an adult tending embers in a prehistoric rock shelter. Set thumbnail_text to FIRE GONE?.'}],
        'response_format': {'type': 'json_schema', 'json_schema': {'schema': schema}},
        'max_completion_tokens': 256, 'temperature': .3})
    data = json.loads(result['choices'][0]['message']['content'])
    if data['ready'] is not True or not data['image_prompt'].strip():
        raise RuntimeError('Local Qwen readiness failed')
    print(json.dumps({'check': 'Local Qwen structured text', 'passed': True, 'model': MODEL_ID}))


if __name__ == '__main__':
    main()
