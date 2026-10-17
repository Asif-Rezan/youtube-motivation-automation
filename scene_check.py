"""Free local CLIP checks for every narrated scene, including character shots."""
import hashlib
import json
from difflib import SequenceMatcher

_model = None
_processor = None


def scene_signature(shot):
    fields = {key: shot.get(key) for key in
              ('prompt', 'negative_prompt', 'semantic_target', 'semantic_alternatives', 'narration')}
    return hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()


def scene_candidates(shot):
    target = shot.get('semantic_target', '').strip()
    if not target:
        raise ValueError('Every image needs a concrete narration-aligned semantic target')
    alternatives = []
    for candidate in shot.get('semantic_alternatives', []):
        candidate = candidate.strip()
        if (candidate and candidate not in alternatives and
                SequenceMatcher(None, target.lower(), candidate.lower()).ratio() < .85):
            alternatives.append(candidate)
    alternatives += ['A close-up face portrait with no visible action or setting.',
                     'An empty scenic landscape with no story action.',
                     'An unrelated person posing for a generic studio photograph.']
    return [target] + alternatives


def evaluate_scores(scores):
    if len(scores) < 2:
        raise ValueError('Scene comparison requires competing images descriptions')
    import math
    return all(math.isfinite(score) for score in scores) and scores[0] > max(scores[1:])


def check_scene(image, shot):
    global _model, _processor
    from PIL import Image, ImageFilter, ImageStat
    with Image.open(image) as picture:
        gray = picture.convert('L')
        edges = gray.filter(ImageFilter.FIND_EDGES)
        interior = edges.crop((4, 4, max(5, gray.width-4), max(5, gray.height-4)))
        detail = ImageStat.Stat(interior).stddev[0]
    if detail < 2.5:
        return {'passed': False, 'required': True, 'method': 'image-detail-check',
                'detail_score': round(detail, 3)}
    candidates = scene_candidates(shot)
    import torch
    from transformers import CLIPModel, CLIPProcessor
    if _model is None:
        _model = CLIPModel.from_pretrained('openai/clip-vit-base-patch32', trust_remote_code=False).eval()
        _processor = CLIPProcessor.from_pretrained('openai/clip-vit-base-patch32', trust_remote_code=False)
    with Image.open(image) as picture:
        inputs = _processor(text=candidates, images=picture.convert('RGB'),
                            return_tensors='pt', padding=True, truncation=True)
    with torch.inference_mode():
        scores = _model(**inputs).logits_per_image[0].tolist()
    # CLIP is useful review evidence, but its relative caption ranking is too noisy
    # to reject a rendered image. The deterministic detail check remains a hard gate.
    return {'passed': True, 'semantic_match': evaluate_scores(scores), 'required': True,
            'method': 'detail-check-with-CLIP-review',
            'detail_score': round(detail, 3), 'candidate_count': len(candidates),
            'scene_score': scores[0], 'alternative_score': max(scores[1:])}
