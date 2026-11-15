"""Original scripts for illustrative island simulations."""
from dataclasses import dataclass

from .metadata import Packaging


@dataclass(frozen=True)
class Beat:
    label: str
    narration: str
    population: int
    forage: float
    camera: str
    action: str = 'graze'


GOATS = (
    Beat('Arrival', 'Two goats. One island. No predators. It looks like the easiest place in the world to survive. But the island has an edge, and sooner or later every goat will run into it.', 2, 1, 'shore', 'walk'),
    Beat('The starting conditions', 'This is a thought experiment. Our island is small, there is a spring inland, and the two goats can breed. There is no bridge, no second herd, and no boat coming back with feed. The numbers on screen belong to this simulation. Change the starting conditions and the ending could look very different.', 2, 1, 'aerial', 'walk'),
    Beat('Fresh pasture', 'From the beach the goats can reach grass, herbs, and low shrubs. A patch that has just been grazed can start to grow again while the pair moves on. In the early years that is an enormous advantage. Two animals can use a fraction of the island at a time. Notice how much green is still available uphill.', 2, .98, 'pasture'),
    Beat('First generations', 'The first young goats turn a pair into a group. The important change happens when the offspring themselves start to breed. From then on, the original pair is only a small part of the story. A generation that has more breeding adults can produce more young even when each adult produces the same number as before.', 11, .91, 'pasture', 'walk'),
    Beat('The herd spreads', 'Follow the paths up the slope. The herd reaches patches the founding pair rarely visited. At first the map looks healthier than the new population count suggests. There is still green on the ridge and around the spring. But every additional animal makes it harder for the herd to leave a patch alone long enough for it to recover.', 31, .79, 'aerial', 'walk'),
    Beat('A crowded spring', 'The spring is a useful place to watch the change. Early on, an animal could drink and leave before another arrived. Now the same route carries a succession of groups. A water source can still be running and the surrounding pasture can still be under stress. Water and food are different limits, and the tighter one can change with the season.', 67, .65, 'shore', 'walk'),
    Beat('The green starts to break up', 'Look at the ground between the surviving bushes. The island has not run out of all vegetation at once. Some spots were easier to reach, some plants grew back faster, and some patches escaped grazing for longer. That is why the map changes unevenly. A green ridge in the distance can hide a large loss of feeding area below it.', 112, .44, 'pasture'),
    Beat('The dry season', 'Then the rain slows. Grass grows back less quickly, but the herd still needs to eat each day. A large population can make a change in weather matter more because there is little spare forage to fall back on. In the simulation the annual growth of the herd begins to flatten just as the supply of fresh plants drops.', 116, .23, 'aerial'),
    Beat('The limit catches up', 'To see why the numbers fall, imagine each route as a loop. A goat leaves a patch, feeds somewhere else, and eventually returns. In the early years fresh growth was often ready by the time the loop came back around. Now the return can happen before the patch has recovered. The same movement gets the herd less food each time.', 82, .14, 'pasture', 'walk'),
    Beat('After the crash', 'When there are fewer animals, the pressure on some patches eases. That does not instantly put the island back in the condition it started in. Recovery depends on which plants survived, how much seed is available, and what the next rainy season is like. In our model, the first places to get greener are the areas the smaller herd visits less.', 45, .28, 'shore'),
    Beat('A different future', 'Run the story with a larger island and the crowded years may arrive later. Give it less rain and the first dry season could matter much earlier. Change the amount of forage that grows back each year and the same starting pair can lead to a very different result. The point is the feedback between animals and their food supply.', 31, .49, 'aerial'),
    Beat('What the island tells us', 'Seen from above again, this is still the same island. The coastline never moved. What changed was how much of the island could feed the herd, and how quickly those patches could recover. Two goats made the opening scene. The competition between growth and recovery wrote the rest of the story.', 34, .61, 'aerial'),
)

PREVIEW = (
    Beat('Arrival', 'Two goats land on an empty island. With fresh grass and no predators, the first years look easy.', 2, 1, 'shore', 'walk'),
    Beat('The herd grows', 'Then their offspring start breeding. Soon the herd is grazing the same ground faster than plants can grow back.', 31, .73, 'aerial', 'walk'),
    Beat('The dry season', 'When the rain slows, the green patches shrink. Now the island has to feed a herd that grew during the good years.', 116, .23, 'pasture'),
)
GOAT_PACKAGING = Packaging(
    title='2 Goats, 1 Island: What Happens When the Food Runs Out?',
    subject='goats',
    opening='What happens when two goats arrive on a small island with no predators? '
            'Follow the growing herd as the island runs low on food.',
    description='Watch the goats spread across the island, see how their grazing changes the landscape, '
                'and follow the population through a dry season. The changing herd and pasture show '
                'how limited food can shape an island ecosystem.',
    tags=('goats on an island', 'two goats one island', 'goat population', 'feral goats',
          'wildlife simulation', 'island ecosystem', 'population growth', 'carrying capacity',
          'overgrazing', 'animated ecology'),
)
EPISODES = {'goat-island': (GOAT_PACKAGING, GOATS)}
