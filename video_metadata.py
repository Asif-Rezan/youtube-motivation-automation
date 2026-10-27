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


def validate_metadata(data):
    title, description, tags = (data.get(k) for k in ('title', 'description', 'tags'))
    if not isinstance(title, str) or len(title) > 85 or not re.search(r'\bHumans\b', title, re.I):
        raise ValueError('Title must contain Ancient Humans or Humans and fit 85 characters')
    if not isinstance(description, str) or not 3500 <= len(description) <= 4500 or len(description) > 4500:
        raise ValueError('Description must contain 3500–4500 characters of useful episode-specific detail')
    if re.search(r'background music|music credits?|magenta|musicrnn|synthesized ambient piano', description, re.I):
        raise ValueError('Description must not include background-music or production notes')
    final_line = description.strip().splitlines()[-1]
    hashtags = final_line.split()
    if (not 3 <= len(hashtags) <= 5 or
            not all(re.fullmatch(r'#[A-Za-z][A-Za-z0-9_]*', tag) for tag in hashtags) or
            hashtags[0].lower() != '#ancienthumans' or
            len({tag.lower() for tag in hashtags}) != len(hashtags)):
        raise ValueError('Final line must contain 3–5 unique relevant hashtags starting with #AncientHumans')
    if (not isinstance(tags, list) or not 8 <= len(tags) <= 18 or
            not all(isinstance(t, str) and t.strip() and '#' not in t for t in tags) or
            len({t.strip().lower() for t in tags}) != len(tags) or len(','.join(tags)) > 400):
        raise ValueError('Use 8–18 distinct topic tags with no hashtags and total length <=400')
    return data


def generate_metadata(story, ask, pause, schema):
    text = {'type': 'string'}
    response_schema = schema({'title': {'type': 'string', 'maxLength': 85},
                              'description': {'type': 'string', 'minLength': 3500, 'maxLength': 4500},
                              'tags': {'type': 'array', 'items': text}})
    context = {'working_title': story['title'], 'topic_pillar': story.get('content_pillar'),
               'evidence_and_continuity': story.get('story_bible'),
               'completed_narration': [s['narration'] for s in story['scenes']]}
    feedback = ''
    for attempt in range(2):
        pause(60)
        result = ask(METADATA_BRIEF + '\nCompleted video context:\n' + json.dumps(context) + feedback,
                     4000, response_schema)
        try:
            return validate_metadata(result)
        except ValueError as error:
            if attempt:
                raise
            feedback = '\nRepair this rejected draft: ' + json.dumps(result) + '\nValidation issue: ' + str(error)


def public_description(description, music_credit=''):
    """Remove the old generated-Magenta footer without removing licensed-source attribution."""
    technical = re.compile(r'background music\s*:|magenta|musicrnn|synthesized ambient piano', re.I)
    body = '\n'.join(line for line in description.splitlines() if not technical.search(line)).strip()
    credit = '\n'.join(line for line in music_credit.splitlines() if not technical.search(line)).strip()
    result = body + ('\n\n'+credit if credit else '')
    if len(result) > 5000:
        raise ValueError('Final YouTube description exceeds 5000 characters')
    return result
