"""Conservative repetition checks, not a YouTube monetization eligibility verdict."""
import hashlib
import re
from collections import Counter
from difflib import SequenceMatcher


def words(text):
    return re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text.casefold())


def fingerprint(story):
    # Ignore the shared, application-owned subscribe CTA when comparing substance.
    from human_history import CTA
    text = ' '.join(scene.get('narration', '').replace(CTA, '') for scene in story['scenes'])
    tokens = words(text)
    return sorted({hashlib.sha256(' '.join(tokens[i:i+5]).encode()).hexdigest()[:16]
                   for i in range(max(0, len(tokens)-4))})[:4096]


def narration_issues(story):
    """Return chapter indexes requiring revision, retaining the first useful occurrence."""
    from human_history import CTA
    chapters = [' '.join(words(scene.get('narration', '').replace(CTA, '')))
                for scene in story['scenes']]
    issues = {}
    seen = Counter()
    for index, chapter in enumerate(chapters):
        for previous in chapters[:index]:
            if min(len(chapter), len(previous)) >= 160 and SequenceMatcher(None, chapter, previous, autojunk=False).ratio() >= .92:
                issues[index] = 'Nearly identical to an earlier chapter; explain a different assigned mechanism and example.'
        local = Counter(' '.join(words(sentence)) for sentence in re.split(r'(?<=[.!?])\s+',
                        story['scenes'][index].get('narration', '').replace(CTA, ''))
                        if len(words(sentence)) >= 8)
        if any(seen[sentence] + count >= 3 for sentence, count in local.items()):
            issues[index] = 'Repeated filler sentence; replace it with concrete new explanatory reasoning.'
        seen.update(local)
    return issues


def validate(story, history=()):
    chapters = [' '.join(words(scene.get('narration', ''))) for scene in story['scenes']]
    for index, chapter in enumerate(chapters):
        for previous in chapters[:index]:
            if min(len(chapter), len(previous)) >= 160 and SequenceMatcher(None, chapter, previous, autojunk=False).ratio() >= .92:
                raise ValueError('Quality review required: nearly identical narration chapters; revise the saved draft')
    sentences = []
    for scene in story['scenes']:
        sentences.extend(' '.join(words(sentence)) for sentence in re.split(r'(?<=[.!?])\s+', scene.get('narration', ''))
                         if len(words(sentence)) >= 8)
    counts = Counter(sentences)
    if any(count >= 3 for count in counts.values()):
        raise ValueError('Quality review required: a substantial sentence is repeated three or more times')
    current = set(fingerprint(story))
    highest = 0.0
    compared = 0
    for old in history[-30:]:
        previous = set(old.get('content_fingerprint_v1', []))
        if min(len(previous), len(current)) < 100:
            continue
        compared += 1
        overlap = len(current & previous) / min(len(current), len(previous))
        highest = max(highest, overlap)
        if overlap >= .45:
            raise ValueError('Quality review required: substantial narration overlap with an earlier upload')
    return {'repetition_checks_passed': True, 'prior_scripts_compared': compared,
            'highest_phrase_overlap': round(highest, 3), 'monetization_eligibility_verified': False}
