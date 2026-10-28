"""Natural search metadata grounded in the completed narration, not keyword stuffing."""
import json
import re

METADATA_BRIEF = '''Write English YouTube metadata for the COMPLETED Ancient Humans explainer below.
Use only topics, mechanisms and claims actually covered in its narration. This is editorial SEO,
not verified search-volume research: never claim a keyword is trending, low competition or guaranteed to rank.

TITLE: one clear, intriguing, accurate title, preferably 50–75 characters and never over 85.
Include Ancient Humans (preferred) or Humans naturally, once, toward the beginning when readable.
Combine the central searchable topic with a concrete question, constraint or consequence.
No keyword chains, hashtags, emojis, ALL-CAPS title, invented discoveries or unsupported superlatives.

DESCRIPTION: Write a detailed, unique description targeting 4000–4400 characters, including spaces and hashtags.
The requested 1000–3000 words cannot fit YouTube's 5000-character field; prioritize useful script-grounded detail within this hard character budget. Do not return a one-sentence summary.
Open with two strong sentences: identify the specific question and viewer payoff, naturally including
Ancient Humans and the episode's primary topic within the first two lines.
Then explain the actual scope in several readable paragraphs, integrating 10–18 genuinely relevant related
terms naturally; choose them from the script rather than inserting every possible history keyword.
Add an 'In this video:' section with 3–5 short bullets describing distinct questions or mechanisms covered.
Include one concise sentence distinguishing archaeological evidence, inference and illustrative reconstructions.
End the prose with a specific comment question and a short invitation to subscribe for related explainers.
The FINAL LINE must contain 3–5 relevant hashtags separated by spaces, starting with #AncientHumans.
Other hashtags must fit this episode's actual topic, region or period. No #Viral, #Trending or irrelevant tags.
No fabricated sources, links, timestamps, statistics, historical certainty or promises not supported by the script.
No production notes, background-music information, music credits, software/model names or workflow explanations.
Do not dump comma-separated SEO tags or repeat the same keyword sentence in the description.

TAGS: 10–18 distinct, relevant English search phrases, ordered by relevance, total comma-joined length <=400.
Start with the primary topic phrase and Ancient Humans; combine specific long-tail queries with a few
broader human-history terms. No hashtags, duplicate/case-variant tags, unrelated popular topics or channel names.
Tags support relevance; do not treat them as a substitute for an accurate title and useful description.
Return only the requested title, description and tags JSON fields.'''


def _valid_hashtag_line(line):
    hashtags = line.split()
    return (3 <= len(hashtags) <= 5 and
            all(re.fullmatch(r'#[A-Za-z][A-Za-z0-9_]*', tag) for tag in hashtags) and
            hashtags[0].lower() == '#ancienthumans' and
            len({tag.lower() for tag in hashtags}) == len(hashtags))


def repair_hashtag_footer(data, story):
    """Repair footer formatting locally; preserve prose and strict validation.

    Mechanical formatting should not discard successfully generated narration.
    Specific replacement
    hashtags must occur in the completed script; broad fallbacks describe this
    channel's Ancient Humans subject without inventing facts or trend claims.
    """
    description = data.get('description')
    if not isinstance(description, str) or not description.strip():
        return data
    if _valid_hashtag_line(description.strip().splitlines()[-1]):
        return data

    lines = description.rstrip().splitlines()
    footer = []
    while lines:
        line = lines[-1].strip()
        if not line:
            lines.pop()
            continue
        unlabelled = re.sub(r'^hashtags?\s*:\s*', '', line, flags=re.I)
        # Accept malformed hashtag-only lines so duplicates, comma-separated
        # tags and extra footer lines are replaced rather than left in prose.
        remainder = re.sub(r'#[^\s#]+', '', unlabelled)
        if '#' in unlabelled and not remainder.strip(' ,;|'):
            footer.insert(0, lines.pop())
            continue
        inline = re.search(r'(?<!\S)#[^\s#]+(?:\s+#[^\s#]+)*\s*$', lines[-1])
        if inline:
            footer.insert(0, inline.group())
            lines[-1] = lines[-1][:inline.start()].rstrip()
        break

    context = ' '.join([story.get('title', '')] +
                       [scene.get('narration', '') for scene in story.get('scenes', [])])
    compact_context = re.sub(r'[^a-z0-9]', '', context.casefold())
    candidates = re.findall(r'#[A-Za-z][A-Za-z0-9_]*', ' '.join(footer))
    tags = data.get('tags')
    if isinstance(tags, list):
        candidates.extend('#' + ''.join(word.capitalize() for word in
                          re.findall(r'[A-Za-z0-9]+', tag))
                          for tag in tags if isinstance(tag, str))
    hashtags = ['#AncientHumans']
    seen = {'#ancienthumans'}
    for tag in candidates:
        if (not re.fullmatch(r'#[A-Za-z][A-Za-z0-9_]{0,39}', tag) or
                tag.casefold() in seen or
                tag.casefold() in {'#viral', '#trending', '#shorts', '#youtube'}):
            continue
        if re.sub(r'[^a-z0-9]', '', tag[1:].casefold()) not in compact_context:
            continue
        hashtags.append(tag)
        seen.add(tag.casefold())
        if len(hashtags) == 5:
            break
    for tag in ('#HumanHistory', '#AncientHistory'):
        if len(hashtags) >= 3:
            break
        if tag.casefold() not in seen:
            hashtags.append(tag)
            seen.add(tag.casefold())
    return {**data, 'description': '\n'.join(lines).rstrip() + '\n\n' + ' '.join(hashtags)}


def _valid_tags(tags):
    return (isinstance(tags, list) and 8 <= len(tags) <= 18 and
            all(isinstance(tag, str) and tag.strip() and '#' not in tag for tag in tags) and
            len({tag.strip().casefold() for tag in tags}) == len(tags) and
            len(','.join(tags)) <= 400)


def repair_topic_tags(data, story):
    """Repair recoverable model formatting without regenerating completed narration.

    Preserve a valid list exactly. Otherwise keep relevant generated phrases in
    order, remove hashtags/duplicates and bound the list and character budget.
    Supplement sparse lists with phrases present in the script, then broad terms
    describing this Ancient Humans channel; never invent specific episode claims.
    """
    raw = data.get('tags')
    if _valid_tags(raw):
        return data
    candidates = []
    for tag in raw if isinstance(raw, list) else []:
        if isinstance(tag, str):
            candidates.extend(re.split(r'[,;|\n]+', tag))
    # Both titles concern the actual episode, not unrelated popular searches.
    candidates.extend([data.get('title', ''), story.get('title', ''), 'Ancient Humans'])
    context = ' '.join([story.get('title', '')] +
                       [scene.get('narration', '') for scene in story.get('scenes', [])])
    context = ' '.join(context.casefold().split())
    for phrase in ('fire maintenance', 'camp fire', 'glowing embers', 'dry fuel',
                   'food storage', 'preserving food', 'water sources', 'dry landscapes',
                   'stone tools', 'making tools', 'sharing food', 'sheltered camp',
                   'survival skills', 'passing knowledge', 'teaching children'):
        if phrase in context:
            candidates.append(phrase)
    candidates.extend(['human history', 'prehistoric life', 'early humans',
                       'ancient human survival', 'prehistoric daily life',
                       'ancient human life', 'prehistoric humans'])
    tags, seen = [], set()
    for candidate in candidates:
        if not isinstance(candidate, str):
            continue
        tag = ' '.join(candidate.replace('#', '').split()).strip(' ,;|.!?')
        tag = re.sub(r'\bAncientHumans\b', 'Ancient Humans', tag, flags=re.I)
        if len(tag) > 42:
            # Keep complete words, leaving room for at least eight useful tags.
            tag = tag[:43].rsplit(' ', 1)[0] if ' ' in tag[:43] else ''
        key = tag.casefold()
        if not tag or key in seen or key in {'viral', 'trending', 'shorts', 'youtube'}:
            continue
        if len(','.join([*tags, tag])) > 400:
            continue
        tags.append(tag)
        seen.add(key)
        if len(tags) == 18:
            break
    return {**data, 'tags': tags}


def build_metadata_schema(schema):
    return schema({'title': {'type': 'string', 'maxLength': 85},
                   'description': {'type': 'string', 'minLength': 3500, 'maxLength': 4500},
                   'tags': {'type': 'array', 'minItems': 8, 'maxItems': 18,
                            'items': {'type': 'string', 'minLength': 1, 'maxLength': 48}}})


def build_metadata_request_schema(schema):
    """Let complete drafts reach the editorial repair loop before length validation.

    The native decoder deliberately omits large string lengths. Enforcing them
    in request_story instead would exhaust blind transport retries before the
    metadata layer can repair a short/long description. Final validation stays strict.
    """
    properties = build_metadata_schema(lambda properties: properties)
    properties['description'] = {'type': 'string'}
    return schema(properties)


def validate_metadata(data):
    title, description, tags = (data.get(k) for k in ('title', 'description', 'tags'))
    if not isinstance(title, str) or len(title) > 85 or not re.search(r'\bHumans\b', title, re.I):
        raise ValueError('Title must contain Ancient Humans or Humans and fit 85 characters')
    if not isinstance(description, str) or not 3500 <= len(description) <= 4500 or len(description) > 4500:
        raise ValueError('Description must contain 3500–4500 characters of useful episode-specific detail')
    if re.search(r'background music|music credits?|magenta|musicrnn|synthesized ambient piano', description, re.I):
        raise ValueError('Description must not include background-music or production notes')
    final_line = description.strip().splitlines()[-1]
    if not _valid_hashtag_line(final_line):
        raise ValueError('Final line must contain 3–5 unique relevant hashtags starting with #AncientHumans')
    if not _valid_tags(tags):
        raise ValueError('Use 8–18 distinct topic tags with no hashtags and total length <=400')
    return data


def generate_metadata(story, ask, pause, schema):
    response_schema = build_metadata_request_schema(schema)
    context = {'working_title': story['title'], 'topic_pillar': story.get('content_pillar'),
               'evidence_and_continuity': story.get('story_bible'),
               'completed_narration': [s['narration'] for s in story['scenes']]}
    feedback = ''
    for attempt in range(2):
        pause(60)
        result = ask(METADATA_BRIEF + '\nCompleted video context:\n' + json.dumps(context) + feedback,
                     4000, response_schema)
        result = repair_topic_tags(result, story)
        result = repair_hashtag_footer(result, story)
        try:
            return validate_metadata(result)
        except ValueError as error:
            print(json.dumps({'check': 'Metadata editorial validation', 'passed': False,
                              'attempt': attempt + 1,
                              'description_characters': len(result['description']),
                              'reason': str(error)}), flush=True)
            if attempt:
                raise
            feedback = ('\nRepair this rejected draft: ' + json.dumps(result) +
                        '\nValidation issue: ' + str(error) +
                        f'\nThe description currently contains {len(result["description"])} characters. '
                        'Rewrite it to 4000–4400 characters including the hashtag footer. '
                        'Expand with distinct mechanisms and evidence limits from the completed narration if short; '
                        'remove repetition if long. Preserve valid title and tags. Do not pad with repeated text.')


def public_description(description, music_credit=''):
    """Remove the old generated-Magenta footer without removing licensed-source attribution."""
    technical = re.compile(r'background music\s*:|magenta|musicrnn|synthesized ambient piano', re.I)
    body = '\n'.join(line for line in description.splitlines() if not technical.search(line)).strip()
    credit = '\n'.join(line for line in music_credit.splitlines() if not technical.search(line)).strip()
    result = body + ('\n\n'+credit if credit else '')
    if len(result) > 5000:
        raise ValueError('Final YouTube description exceeds 5000 characters')
    return result
