"""Story seeds for several kinds of hypothetical science and technology videos."""

TOPICS = {
    'space': (
        ('rings', 'Earth', 'What if Earth suddenly had visible rings? Explore changes in the sky and daylight.'),
        ('moon', 'Moon', 'What if the Moon appeared twice as large? Compare apparent size with a closer orbit.'),
        ('daylight', 'Earth', 'What if daylight lasted much longer across the globe? Explore a slower rotation.'),
        ('shadows', 'Moon', 'What if a permanent lunar settlement had to follow sunlight?'),
    ),
    'ocean': (
        ('tides', 'Tides', 'What if a coastal city had to live through an unusually large daily tidal range?'),
        ('currents', 'Ocean', 'What if an ocean current shifted away from a fishing coast? Follow the changes across seasons.'),
        ('sea ice', 'Sea Ice', 'What if seasonal sea ice formed weeks later every year?'),
        ('reefs', 'Coral Reefs', 'What if a reef lost the shelter it gives to nearby coasts?'),
    ),
    'earth': (
        ('clouds', 'Clouds', 'What if low clouds disappeared over one region for a month?'),
        ('rivers', 'Rivers', 'What if a river suddenly changed course beside a town?'),
        ('albedo', 'Snow', 'What if mountain snow melted early and exposed darker rock?'),
        ('wind', 'Wind', 'What if the prevailing wind reversed for one growing season?'),
    ),
    'technology': (
        ('navigation', 'Navigation', 'What if satellite navigation signals vanished for a full day?'),
        ('storage', 'Power Grid', 'What if a city could store a whole week of electricity?'),
        ('network', 'Internet', 'What if a city lost its long-distance internet links?'),
        ('power', 'Power Grid', 'What if a neighborhood had to run on local electricity alone?'),
    ),
    'wildlife': (
        ('bridge', 'Deer', 'What if an isolated deer population found a temporary route to the mainland?'),
        ('seed', 'Rabbits', 'What if a short burst of food changed where rabbits lived for an entire season?'),
        ('flood', 'Goats', 'What if floodwater split grazing grounds into separate patches?'),
        ('shelter', 'Deer', 'What if the only winter shelter for a herd moved to the other side of a valley?'),
    ),
}


def select_topic(history, seed):
    """Rotate through categories before revisiting one and prefer unused prompts."""
    domains = tuple(TOPICS)
    recent = [row.get('domain', 'wildlife') for row in history]
    last_seen = {domain:index for index,domain in enumerate(recent)}
    domain = min(domains, key=lambda name: (last_seen.get(name,-1), (domains.index(name)-seed)%len(domains)))
    used = {row.get('topic') for row in history if row.get('domain') == domain}
    choices = [value for value in TOPICS[domain] if value[0] not in used]
    prompts = choices or TOPICS[domain]
    key, subject, prompt = prompts[seed % len(prompts)]
    return domain, key, subject, prompt, not bool(choices)
