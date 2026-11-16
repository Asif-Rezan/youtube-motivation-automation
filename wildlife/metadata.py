"""Build upload-ready metadata from episode-specific copy and the rendered timeline."""
from dataclasses import dataclass
import re


PRESSURE_HOOKS = {
    'drought': 'Can They SURVIVE the Drought?',
    'winter': 'Can They SURVIVE the Winter?',
    'food competition': 'What Happens in a Food CRISIS?',
    'vegetation loss': 'What If Their Food Starts to VANISH?',
    'water shortage': 'Can They Survive a Water CRISIS?',
    'habitat recovery': 'Can Their Habitat RECOVER?',
}
TOPIC_TITLES = {
    'tides': 'Tides Rise: Can a Coastal Marsh SURVIVE?',
    'currents': 'Ocean Currents Shift: Can a Kelp Forest SURVIVE?',
    'sea ice': 'Sea Ice Arrives Late: Can the Food Web SURVIVE?',
    'reefs': 'Coral Reefs Lose Their Shelter: Can Fish SURVIVE?',
    'clouds': 'Clouds VANISH: Can a Forest SURVIVE Without Fog?',
    'rivers': 'Rivers Change Course: Can a Wetland SURVIVE?',
    'albedo': 'Snow Melts Early: Can a Mountain Meadow SURVIVE?',
    'wind': 'Wind Reverses: Can a Woodland RECOVER?',
    'rings': 'Earth Gets Rings: Can Its Seasons SURVIVE?',
    'moon': 'Moon Appears Bigger: Could Familiar Tides VANISH?',
    'daylight': 'Earth Slows Down: Can Life SURVIVE Longer Days?',
    'shadows': 'Moon Base in Darkness: Can a Settlement SURVIVE?',
    'navigation': 'Navigation Signals VANISH: How Would a City Adapt?',
    'storage': 'Power Grid Has a Week of Energy: Can It Avoid a CRISIS?',
    'network': 'Internet Links VANISH: Can a City Stay Connected?',
    'power': 'Power Grid Goes Local: Can a Neighborhood SURVIVE?',
}
# Topic-specific cover angles and search phrases. These are story cues, not predicted outcomes.
TOPIC_PACKAGING = {
    'tides': ('LESS TIME TO FEED', ('tidal marsh ecology','high tide and marsh birds')),
    'currents': ('FOOD DRIFTS AWAY', ('kelp forest food web','ocean current shift')),
    'sea ice': ('THE HUNT SHRINKS', ('seasonal sea ice','marine food web')),
    'reefs': ('NO SHIELD LEFT', ('coral reef wave protection','lagoon ecosystem')),
    'clouds': ('NOT A DROP', ('cloud forest ecology','fog and forest moisture')),
    'rivers': ('THE OLD BED DRIES', ('river changes course','wetland hydrology')),
    'albedo': ('THE MEADOW THIRSTS', ('early snowmelt','mountain meadow ecology')),
    'wind': ('SEEDS GO ELSEWHERE', ('wind seed dispersal','woodland regeneration')),
    'bridge': ('ONE WAY OUT', ('deer island simulation','wildlife migration')),
    'seed': ('THE FEAST ENDS', ('rabbit population simulation','seasonal food supply')),
    'flood': ('CUT OFF', ('goat island simulation','flooded grazing habitat')),
    'shelter': ('THE LONG WAY HOME', ('deer winter habitat','wildlife movement')),
}
BACKGROUND_READING = {
    'tides': ('NOAA Fisheries — Estuary habitat','https://www.fisheries.noaa.gov/national/habitat-conservation/estuary-habitat'),
    'currents': ('NOAA Fisheries — Kelp forest habitat','https://www.fisheries.noaa.gov/west-coast/habitat-conservation/kelp-forest-habitat-west-coast'),
    'reefs': ('USGS — Coastal ecosystems','https://www.usgs.gov/science/science-explorer/coasts/coastal-ecosystems'),
    'rivers': ('USGS — Hydrology of flooded and wetland forests','https://www.usgs.gov/publications/hydrology-flooded-and-wetland-forests'),
    'albedo': ('USDA Forest Service — Water needs of riparian and wetland vegetation','https://www.fs.usda.gov/rm/pubs/rmrs_gtr282.pdf'),
}


def thumbnail_hook(idea):
    topic = TOPIC_PACKAGING.get(idea.get('topic'))
    headline = ' '.join(idea['thumbnail_text'].upper().split())
    title_words = set(re.findall(r'[A-Z0-9]+', idea.get('title', '').upper()))
    hook_words = set(re.findall(r'[A-Z0-9]+', headline))
    generic_words = {'AFTER', 'BEFORE', 'CHANGES', 'HAPPENS', 'NEXT', 'WHAT', 'NOW', 'THEN'}
    story = idea.get('premise', '') + ' ' + idea.get('arc', '')
    counts_match = all(re.search(r'\b' + count + r'\b', story, re.IGNORECASE)
                       for count in re.findall(r'\d+', headline))
    if (re.fullmatch(r'[A-Z0-9 -]{4,22}', headline) and 2 <= len(headline.split()) <= 4
            and hook_words - title_words - generic_words and counts_match):
        return headline
    return topic[0] if topic else 'THE BALANCE SHIFTS'


POWER_WORDS = {'SURVIVE','CRISIS','VANISH','RECOVER','COLLAPSE','BOOM'}
_POWER_WORD = re.compile(r'\b(' + '|'.join(sorted(POWER_WORDS)) + r')\b', re.IGNORECASE)


def emphasize_title(title, subject, pressure=None, *, topic=None):
    """Keep the model's hook when possible and use a pressure-specific fallback."""
    if not any(match.group() in POWER_WORDS for match in _POWER_WORD.finditer(title)):
        match = _POWER_WORD.search(title)
        if match:
            title = title[:match.start()] + match.group().upper() + title[match.end():]
    try:
        validate_title(title,subject)
    except ValueError:
        if topic in TOPIC_TITLES:
            return TOPIC_TITLES[topic]
        if pressure is not None:
            return f'{subject.title()} on an Island: {PRESSURE_HOOKS[pressure]}'
    return title


TITLE_PREFIX = 'What Happens When '
TOPIC_EVENTS = {
    'tides': 'Tides Flood a Marsh for Longer',
    'currents': 'Ocean Currents Shift Away From Kelp',
    'sea ice': 'Sea Ice Forms Later',
    'reefs': 'Coral Reefs Stop Sheltering a Lagoon',
    'clouds': 'Clouds Stop Reaching a Forest',
    'rivers': 'Rivers Change Course',
    'albedo': 'Snow Melts Early',
    'wind': 'Wind Reverses Over a Woodland',
    'rings': 'Earth Gets Rings',
    'moon': 'the Moon Appears Bigger',
    'daylight': 'Earth Slows Down',
    'shadows': 'a Moon Base Loses Sunlight',
    'navigation': 'Navigation Signals Vanish',
    'storage': 'the Power Grid Can Store a Week of Energy',
    'network': 'Internet Links Vanish',
    'power': 'a Neighborhood Runs on a Local Power Grid',
}
ANIMAL_EVENTS = {
    'drought': 'Face a Drought',
    'winter': 'Face a Harsh Winter',
    'food competition': 'Compete for Food',
    'vegetation loss': 'Run Out of Plants to Eat',
    'water shortage': 'Run Out of Water',
    'habitat recovery': 'Get a Chance to Recover',
}


def episode_title(title, subject, topic='', pressure=None):
    if title.startswith(TITLE_PREFIX):
        return title
    if topic in TOPIC_EVENTS:
        return TITLE_PREFIX + TOPIC_EVENTS[topic] + '?'
    if pressure:
        event = ANIMAL_EVENTS[pressure]
    elif 'food runs out' in title.casefold():
        event = 'Run Out of Food'
    else:
        event = 'Face a Changing Island'
    return f'{TITLE_PREFIX}{subject.title()} {event} on an Island?'


def validate_title(title,subject):
    subject = subject.casefold()
    if title.startswith(TITLE_PREFIX):
        if not 35 <= len(title) <= 84 or not title.endswith('?'):
            raise ValueError('Story title must be a question of 35–84 characters')
        if not re.search(r'\b' + re.escape(subject) + r'\b',title[len(TITLE_PREFIX):].casefold()):
            raise ValueError('Put the episode subject in the story title')
        return
    if not 35 <= len(title) <= 70 or not title.endswith('?'):
        raise ValueError('Wildlife title must be a concise question of 35–70 characters')
    if not any(match.group() in POWER_WORDS for match in _POWER_WORD.finditer(title)):
        raise ValueError('Wildlife title requires an uppercase power word')
    if not subject or not re.search(r'\b' + re.escape(subject) + r'\b',title[:32].casefold()):
        raise ValueError('Put the episode subject near the start of the title')


def tag_cost(tag):
    return len(tag) + (2 if ' ' in tag else 0)


def fit_tags(candidates, *, limit):
    """Deduplicate search phrases and keep them within YouTube's tag budget."""
    tags = []
    used = set()
    budget = 0
    for candidate in candidates:
        tag = ' '.join(candidate.split())
        cost = tag_cost(tag) + bool(tags)
        if not tag or tag.casefold() in used or budget + cost > 500:
            continue
        tags.append(tag)
        used.add(tag.casefold())
        budget += cost
        if len(tags) == limit:
            break
    return tags


def normalize_generated_tags(tags, subject):
    tags = fit_tags(tags, limit=12)
    if not any(subject.casefold() in tag.casefold() for tag in tags):
        tags = fit_tags([f'{subject} what if', *tags], limit=12)
    return tags


@dataclass(frozen=True)
class Packaging:
    title: str
    subject: str
    opening: str
    description: str
    tags: tuple[str, ...]
    topic: str = ''
    premise: str = ''
    pressure: str | None = None

    def validate(self):
        subject = self.subject.casefold()
        validate_title(self.title,self.subject)
        if not 40 <= len(self.opening) <= 160 or subject not in self.opening.casefold():
            raise ValueError('Write a concise, subject-specific opening for the description')
        if not self.description.strip():
            raise ValueError('The episode description needs an original synopsis')
        tags = [tag.casefold().strip() for tag in self.tags]
        if not 4 <= len(tags) <= 12 or len(set(tags)) != len(tags) or not all(tags):
            raise ValueError('Use four to twelve distinct, relevant tags')
        if sum(map(tag_cost, tags)) + len(tags) - 1 > 500:
            raise ValueError('Tags exceed the YouTube tag budget')
        if not any(subject in tag for tag in tags):
            raise ValueError('Include at least one subject-specific tag')

    def build(self, timeline, *, preview=False):
        self.validate()
        title = episode_title(self.title, self.subject, self.topic, self.pressure)
        if preview:
            title += ' (30-Second Preview)'
        paragraphs = [self.premise or self.opening]
        if self.description.strip().casefold() != paragraphs[0].strip().casefold():
            paragraphs.append(self.description)
        paragraphs.append('This is a hypothetical ecosystem scenario. Events and any on-screen counts illustrate the story.')
        if not preview:
            starts = [int(chapter['start']) for chapter in timeline]
            if len(starts) < 3 or starts[0] != 0 or any(b-a < 10 for a, b in zip(starts, starts[1:])):
                raise ValueError('YouTube chapters require a zero start and at least three entries, ten seconds apart')
            chapters = [f"{start//60}:{start%60:02d} {chapter['chapter']}"
                        for start, chapter in zip(starts, timeline)]
            paragraphs.append('Chapters\n' + '\n'.join(chapters))
        if self.topic in BACKGROUND_READING:
            name,url = BACKGROUND_READING[self.topic]
            paragraphs.append(f'Background reading\n{name} — {url}')
        subject_hashtag = re.sub(r'[^A-Za-z0-9]', '', self.subject).lower()
        hashtags = dict.fromkeys(('#simulation', '#'+subject_hashtag, '#ecology', '#whatif', '#animation'))
        paragraphs.append(' '.join(hashtags))
        description = '\n\n'.join(paragraphs)
        if len(description.encode('utf-8')) > 5000 or any(c in title + description for c in '<>'):
            raise ValueError('Wildlife metadata contains invalid characters or exceeds the description limit')
        from_topic = TOPIC_PACKAGING.get(self.topic)
        candidates = [*(from_topic[1] if from_topic else ()), *self.tags,
                      f'{self.subject} what if', 'ecosystem what if', 'ecology simulation',
                      'low poly animation', 'nature simulation']
        tags = fit_tags(candidates, limit=18)
        return {'title': title, 'description': description, 'tags': tags}
