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
    Beat('Finding water', 'The spring changes how the goats use the island. Imagine drawing a circle around it. Inside that circle, the animals can feed and return to water without a long detour. Farther away, the same patch of grass costs more time and effort to reach. That creates a pattern before numbers grow very much. Some areas get visited almost every day while others wait weeks between visits. The island may look like one uniform green surface from a distance. On the ground it already contains feeding areas that differ in how often they are used and how much time the plants have to recover.', 2, 0.97, 'shore', 'walk'),
    Beat('First generations', 'The first young goats turn a pair into a group. The important change happens when the offspring themselves start to breed. From then on, the original pair is only a small part of the story. A generation that has more breeding adults can produce more young even when each adult produces the same number as before.', 11, .91, 'pasture', 'walk'),
    Beat('Making room for the young', 'Watch what a new generation changes beyond the head count. Young animals need food while they grow, and their mothers need enough food to raise them. A head count does not tell us how much forage every animal needs. An older animal and a newborn do not use exactly the same resources. Those details matter if we were trying to make a forecast for a real island. Here we keep them simple so the main effect stays visible. More mouths are drawing on the same area, and the vegetation does not increase automatically just because the herd now has more young.', 15, 0.87, 'pasture', 'graze'),
    Beat('Why growth speeds up', 'Suppose several of the young goats survive long enough to breed. In the next generation there are several families producing young at once. We no longer need the original pair to explain most of the births. Now imagine making it harder for young goats to survive their first dry season. That would delay the moment when these separate families begin to multiply. The difference need not show up immediately. It can become obvious only after several generations, when the surviving young have young of their own. That is one reason early head counts can give such a misleading picture of what comes next.', 22, 0.84, 'aerial', 'walk'),
    Beat('The herd spreads', 'Follow the paths up the slope. The herd reaches patches the founding pair rarely visited. At first the map looks healthier than the new population count suggests. There is still green on the ridge and around the spring. But every additional animal makes it harder for the herd to leave a patch alone long enough for it to recover.', 31, .79, 'aerial', 'walk'),
    Beat('Paths through the grass', 'When a herd feeds, its movement leaves a map. Watch the stretches between the places with water and the slopes with fresh growth. Animals can pass repeatedly through the same narrow routes. The ground beside a route might still look green, even as the route itself becomes bare. A distant overhead view makes it easy to miss how much use is concentrated in those strips. Think of them as the first places that show a loss of recovery time. As the herd gets larger, more paths cross each other and fewer places have a long interval without being disturbed.', 49, 0.72, 'shore', 'walk'),
    Beat('A crowded spring', 'The spring is a useful place to watch the change. Early on, an animal could drink and leave before another arrived. Now the same route carries a succession of groups. A water source can still be running and the surrounding pasture can still be under stress. Water and food are different limits, and the tighter one can change with the season.', 67, .65, 'shore', 'walk'),
    Beat('The patch that gets a break', 'For a closer look, compare two patches with similar plants. One sits beside a popular route, the other on a rough slope that fewer goats visit. Both get the same rain in our example. The patch on the slope may keep more leaves simply because it has more time between visits. That matters when we talk about the island running short of food. There can still be plenty to eat in one corner and very little along the main route. For the animals, the useful question is how much they can reach and eat before their usual feeding areas need another break.', 91, 0.54, 'pasture', 'graze'),
    Beat('The green starts to break up', 'Look at the ground between the surviving bushes. The island has not run out of all vegetation at once. Some spots were easier to reach, some plants grew back faster, and some patches escaped grazing for longer. That is why the map changes unevenly. A green ridge in the distance can hide a large loss of feeding area below it.', 112, .44, 'pasture'),
    Beat('The dry season', 'Then the rain slows. Grass grows back less quickly, but the herd still needs to eat each day. A large population can make a change in weather matter more because there is little spare forage to fall back on. In the simulation the annual growth of the herd begins to flatten just as the supply of fresh plants drops.', 116, .23, 'aerial'),
    Beat('When rain comes late', 'On a wet year, some of the patches we have been following can green up almost together. That creates a wide choice of places to feed. Now imagine the first rains arriving late. The same herd must keep moving while fewer patches are ready. A plant that looks green in the distance may offer a small bite instead of a full feeding stop. When many animals have that experience at once, their routes start to overlap even more. The effect can build before the herd count changes. By the time the shortage is visible from overhead, many feeding areas have already been used several times.', 101, 0.19, 'aerial', 'graze'),
    Beat('The limit catches up', 'To see why the numbers fall, imagine each route as a loop. A goat leaves a patch, feeds somewhere else, and eventually returns. In the early years fresh growth was often ready by the time the loop came back around. Now the return can happen before the patch has recovered. The same movement gets the herd less food each time.', 82, .14, 'pasture', 'walk'),
    Beat('After the crash', 'When there are fewer animals, the pressure on some patches eases. That does not instantly put the island back in the condition it started in. Recovery depends on which plants survived, how much seed is available, and what the next rainy season is like. In our model, the first places to get greener are the areas the smaller herd visits less.', 45, .28, 'shore'),
    Beat('The return of green', 'Early recovery is easy to misread. The first patches to turn green are visible from above, but a bright patch can still be small. If every animal heads for it, it may be grazed again before spreading. If several patches recover at different times, the herd has more options and can leave some patches alone longer. That difference changes what the next season looks like. Our model makes the return gradual, with enough green for a smaller herd to move among patches. Recovery means rebuilding a supply of usable food over time, as much as it means seeing green on the map again.', 38, 0.39, 'pasture', 'graze'),
    Beat('A different future', 'Run the story with a larger island and the crowded years may arrive later. Give it less rain and the first dry season could matter much earlier. Change the amount of forage that grows back each year and the same starting pair can lead to a very different result. The point is the feedback between animals and their food supply.', 31, .49, 'aerial'),
    Beat('Replay the first year', 'Rewind to the first year and consider what the original pair could see. The ground nearby was green, the spring was available, and there were no other goats competing for the same plants. Those observations were accurate, but they described the island at that moment. They could tell us very little about the same island after years of growth. If we ran the scenario again and paused at each generation, we would pay as much attention to the time each patch had to regrow as to the number of animals. Those two measurements together show how the good early years can set up the shortage later.', 32, 0.55, 'aerial', 'walk'),
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
