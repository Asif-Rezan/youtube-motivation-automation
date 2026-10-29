"""Exercise the real local Qwen runtime before unattended script generation."""
import json
import workflow as w
from story_cpu import MODEL_ID, decoder_schema
from human_history import THUMBNAIL_SCHEMA, build_outline_schema
from video_metadata import build_metadata_schema, build_metadata_request_schema, generate_metadata


def check_metadata():
    """Exercise the production repair/validation stack using public synthetic context.

    No credentials, private stories or uploads are involved. Grammar compilation
    alone cannot reveal a model's failure to meet an editorial character target.
    """
    story = {'title': 'How Ancient Humans Kept a Camp Fire Useful', 'scenes': [
        {'narration': text} for text in (
            'A camp fire is a practical problem rather than a permanent convenience. '
            'This illustrative reconstruction asks how people could keep useful heat available '
            'when fuel and shelter varied. It does not claim that every prehistoric community '
            'followed one routine. A sheltered hearth, a fading ember and nearby fuel help '
            'explain the choices, but they cannot reveal every detail of past behavior.',
            'Fuel has to be found, carried and prepared. Damp material behaves differently '
            'from dry material. Small pieces and larger pieces serve different purposes. '
            'Keeping a fire useful therefore involves attention to both the available materials '
            'and the immediate conditions. Gathering fuel takes time that might otherwise be '
            'spent gathering food, making tools or maintaining a shelter.',
            'Glowing embers can retain heat after visible flames subside. Shelter can change '
            'exposure to wind and rain, while airflow affects combustion. These relationships '
            'help explain why the location of a hearth matters. The reconstruction illustrates '
            'physical mechanisms, without claiming a particular undocumented ancient technique '
            'or offering modern instructions for using fire indoors.',
            'Cooperation is another possible part of the explanation. Someone gathering fuel '
            'and someone attending a hearth could contribute different work to a shared need. '
            'That possibility should not be mistaken for proof of a fixed division of labor. '
            'A single archaeological trace cannot tell us exactly who performed each task '
            'or how responsibilities changed across communities.',
            'Ash, charcoal and altered material can inform archaeological interpretation, '
            'but preservation is uneven and traces require context. Archaeological evidence, '
            'plausible inference and illustrative reconstructions are different kinds of claims. '
            'The episode invents no studies, dates or eyewitnesses. Its central answer is that '
            'useful fire depended on materials, conditions and repeated human effort, with '
            'variation and uncertainty remaining part of the story.') ]}
    def schema(properties):
        return {'type': 'object', 'properties': properties, 'required': list(properties),
                'additionalProperties': False}
    def ask(prompt, limit, response_schema):
        response = w.request_text('chat/completions', {'model': MODEL_ID,
            'messages': [{'role': 'user', 'content': prompt}],
            'response_format': {'json_schema': {'schema': response_schema}},
            'max_completion_tokens': limit, 'temperature': .8})
        return json.loads(response['choices'][0]['message']['content'])
    metadata = generate_metadata(story, ask, lambda _: None, schema)
    print(json.dumps({'check': 'Production metadata generation and validation', 'passed': True,
                      'description_characters': len(metadata['description']),
                      'tag_count': len(metadata['tags'])}), flush=True)


def check_production_grammar():
    from llama_cpp import LlamaGrammar
    def object_schema(properties):
        return {'type': 'object', 'properties': properties, 'required': list(properties),
                'additionalProperties': False}
    from human_history import narration_schema
    LlamaGrammar.from_json_schema(json.dumps(decoder_schema(
        object_schema({'narration': narration_schema()}))), verbose=False)
    print(json.dumps({'check': 'Narration repair grammar conversion', 'passed': True}))
    # Same twenty-chapter outline used by stage-story, including thumbnail constraints.
    schema = build_outline_schema(object_schema)
    LlamaGrammar.from_json_schema(json.dumps(decoder_schema(schema)), verbose=False)
    print(json.dumps({'check': 'Production outline grammar conversion', 'passed': True}))
    LlamaGrammar.from_json_schema(json.dumps(decoder_schema(build_metadata_schema(object_schema))), verbose=False)
    LlamaGrammar.from_json_schema(json.dumps(decoder_schema(build_metadata_request_schema(object_schema))), verbose=False)
    print(json.dumps({'check': 'Production metadata grammar conversion', 'passed': True}))


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--schemas-only', action='store_true')
    parser.add_argument('--metadata', action='store_true')
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
    if args.metadata:
        check_metadata()


if __name__ == '__main__':
    main()
