"""Separate spoken story copy from production directions in wildlife plans."""

import re


PRODUCTION_LINE = re.compile(
    r'^(?:(?:visual|camera|action|shot|scene|narration|on-screen text|caption|sound effect)\s*:'
    r'|(?:aerial|overhead|wide|close-up|ground-level) (?:shot|view) (?:shows?|reveals?|of)\b'
    r'|forage(?:[_ ]percent)? (?:drops?|falls?|rises?|climbs?|stays?|is|remains?) (?:to |at )?'
    r'(?:\d+|zero\b|one\b|two\b|three\b|four\b|five\b|ten\b|twenty\b|thirty\b|forty\b|fifty\b)'
    r'|population(?:[_ ]count)?\s*(?::|zero\b|(?:drops?|falls?|fades?|rises?|stays?|is) (?:to |at )?(?:\d+|zero\b)))',
    re.IGNORECASE,
)


def spoken_text(text):
    """Remove standalone production cues while keeping ordinary story references."""
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])|\n+', text.strip())
    return ' '.join(line for line in sentences if not PRODUCTION_LINE.match(line))
