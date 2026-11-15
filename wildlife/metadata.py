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
POWER_WORDS = {'SURVIVE','CRISIS','VANISH','RECOVER','COLLAPSE','BOOM'}
_POWER_WORD = re.compile(r'\b(' + '|'.join(sorted(POWER_WORDS)) + r')\b', re.IGNORECASE)


def emphasize_title(title, subject, pressure):
    """Keep the model's hook when possible and use a pressure-specific fallback."""
    match = _POWER_WORD.search(title)
    if match:
        return title[:match.start()] + match.group().upper() + title[match.end():]
    question = PRESSURE_HOOKS[pressure]
    return f'{subject.title()} on an Island: {question}'


@dataclass(frozen=True)
class Packaging:
    title: str
    subject: str
    opening: str
    description: str
    tags: tuple[str, ...]

    def validate(self):
        subject = self.subject.casefold()
        if not 35 <= len(self.title) <= 70 or not self.title.endswith('?'):
            raise ValueError('Wildlife title must be a concise question of 35–70 characters')
        if not any(match.group() in POWER_WORDS for match in _POWER_WORD.finditer(self.title)):
            raise ValueError('Wildlife title requires an uppercase power word')
        if not subject or not re.search(r'\b' + re.escape(subject) + r'\b', self.title[:32].casefold()):
            raise ValueError('Put the episode subject near the start of the title')
        if not 40 <= len(self.opening) <= 160 or subject not in self.opening.casefold():
            raise ValueError('Write a concise, subject-specific opening for the description')
        if not self.description.strip():
            raise ValueError('The episode description needs an original synopsis')
        tags = [tag.casefold().strip() for tag in self.tags]
        if not 4 <= len(tags) <= 12 or len(set(tags)) != len(tags) or not all(tags):
            raise ValueError('Use four to twelve distinct, relevant tags')
        if len(','.join(f'"{tag}"' if ' ' in tag else tag for tag in tags)) > 500:
            raise ValueError('Tags exceed the YouTube tag budget')
        if not any(subject in tag for tag in tags):
            raise ValueError('Include at least one subject-specific tag')

    def build(self, timeline, *, preview=False):
        self.validate()
        title = self.title + ' (30-Second Preview)' if preview else self.title
        paragraphs = [self.opening, self.description,
                      'This is an illustrative wildlife simulation. Population counts represent the hypothetical scenario.']
        if not preview:
            starts = [int(chapter['start']) for chapter in timeline]
            if len(starts) < 3 or starts[0] != 0 or any(b-a < 10 for a, b in zip(starts, starts[1:])):
                raise ValueError('YouTube chapters require a zero start and at least three entries, ten seconds apart')
            chapters = [f"{start//60}:{start%60:02d} {chapter['chapter']}"
                        for start, chapter in zip(starts, timeline)]
            paragraphs.append('Chapters\n' + '\n'.join(chapters))
        description = '\n\n'.join(paragraphs)
        if len(description.encode('utf-8')) > 5000 or any(c in title + description for c in '<>'):
            raise ValueError('Wildlife metadata contains invalid characters or exceeds the description limit')
        return {'title': title, 'description': description, 'tags': list(self.tags)}
