"""Original second-person money stories, with rotation across human stakes."""
import hashlib
import re

PROFILE = 'original-financial-pov-v1'
PILLARS = {
    'career_options': 'A cash buffer changes a difficult workplace decision; show the cost of staying and leaving.',
    'lifestyle_pressure': 'An affordable-looking upgrade competes with a private goal; explore social pressure without mocking spending.',
    'family_boundaries': 'A family request tests generosity, trust and a finite budget; make both sides human.',
    'debt_recovery': 'A manageable repayment plan meets an unexpected expense; show setbacks and realistic recovery.',
    'income_fragility': 'A lost shift or client exposes dependence on one income; rebuilding takes time and has costs.',
    'quiet_progress': 'Small repeated choices create breathing room before visible wealth; make the emotional change specific.',
    'business_tradeoff': 'A small business opportunity forces a choice between revenue, cash flow and time at home.',
    'enough_and_time': 'A character reconsiders what enough means when more income costs health, time or relationships.',
}


def select_pillar(day, history):
    recent = history[-30:]
    excluded = {item.get('content_pillar') for item in recent[-3:]}
    candidates = [key for key in PILLARS if key not in excluded]
    counts = {key: sum(item.get('content_pillar') == key for item in recent) for key in candidates}
    return min(candidates, key=lambda key: (counts[key], hashlib.sha256(f'{day}:{key}'.encode()).hexdigest()))


def narration_direction(story):
    from human_history import direction
    if direction(story):
        return direction(story)
    if story.get('content_profile') != PROFILE:
        return ''
    return ('Tell the story in second person: you/your is the protagonist, while the internal '
        'protagonist_name identifies that same person for visual planning only. Preserve the story bible, '
        'timeline and all established money amounts. Describe observable decisions, costs and consequences. '
        'No generic wealth sermon, guaranteed returns, unverified current rates or invented true-story claims. '
        'Any dollar amounts are fictional scenario assumptions, not promises or general financial rules.')


def validate_pov(story):
    """Fail closed on an accidental return to third-person narration or reused packaging."""
    if story.get('content_profile') != PROFILE:
        return
    if not re.match(r'^POV:\s+You\b', story['title'], re.I):
        raise ValueError('Financial POV title must begin with POV: You')
    if 'fiction' not in story['description'].lower():
        raise ValueError('Financial POV description must disclose fiction')
    if not story.get('story_bible', '').strip():
        raise ValueError('Financial POV requires a continuity story bible')
    for scene in story['scenes']:
        # Dialogue may address other people; require the viewer to remain present in every chapter.
        if not re.search(r'\b(you|your|yours|yourself)\b', scene['narration'], re.I):
            raise ValueError('Financial POV chapter lost second-person narration')
        if not scene.get('continuity_note', '').strip():
            raise ValueError('Financial POV chapter requires a continuity note')
