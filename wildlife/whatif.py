"""Story seeds for what-if videos about nature and ecosystems."""

TOPICS = {
    'space': (
        ('rings', 'Earth', 'What if Earth suddenly had visible rings? Explore changes in the sky and daylight.'),
        ('moon', 'Moon', 'What if the Moon appeared twice as large? Compare apparent size with a closer orbit.'),
        ('daylight', 'Earth', 'What if daylight lasted much longer across the globe? Explore a slower rotation.'),
        ('shadows', 'Moon', 'What if a permanent lunar settlement had to follow sunlight?'),
    ),
    'ocean': (
        ('tides', 'Tides', 'What if a tidal marsh stayed underwater several hours longer every day? Follow the effects on feeding birds and marsh plants.'),
        ('currents', 'Ocean', 'What if a nutrient-rich ocean current shifted away from a kelp forest? Follow the effects through its food web.'),
        ('sea ice', 'Sea Ice', 'What if seasonal sea ice formed weeks later every year? Explore how the change travels through the marine food web.'),
        ('reefs', 'Coral Reefs', 'What if a coral reef stopped sheltering its lagoon from waves? Follow what changes for seagrass and juvenile fish.'),
    ),
    'earth': (
        ('clouds', 'Clouds', 'What if a cloud forest lost its morning fog for a month? Follow the effects on moisture, moss and small animals.'),
        ('rivers', 'Rivers', 'What if a river suddenly changed course and cut a wetland off from its water supply?'),
        ('albedo', 'Snow', 'What if mountain snow melted early each spring? Follow what happens to the downstream meadow as runoff shifts.'),
        ('wind', 'Wind', 'What if wind reversed for one growing season across a woodland? Explore what happens to seed dispersal and regrowth.'),
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


# Older saved plans still use the full topic registry for validation and rendering.
ACTIVE_DOMAINS = ('wildlife','ocean','earth')


def select_topic(history, seed):
    """Rotate through categories before revisiting one and prefer unused prompts."""
    domains = ACTIVE_DOMAINS
    recent = [row.get('domain', 'wildlife') for row in history]
    last_seen = {domain:index for index,domain in enumerate(recent)}
    domain = min(domains, key=lambda name: (last_seen.get(name,-1), (domains.index(name)-seed)%len(domains)))
    used = {row.get('topic') for row in history if row.get('domain') == domain}
    choices = [value for value in TOPICS[domain] if value[0] not in used]
    prompts = choices or TOPICS[domain]
    key, subject, prompt = prompts[seed % len(prompts)]
    return domain, key, subject, prompt, not bool(choices)
