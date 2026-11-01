# Scene stories

New episodes feature children and friendly animal companions with consistent
clothing, colors and appearances in the episode outline. Each five-second shot
has ordered beats: blink, incoming object, notice, action and final reaction.
Rabbit/jumping shots contain two hop arcs. Ball, rain and bedtime scenes use
approach, sway and settling actions instead. The camera pushes closer at the end.

`scene_actions.py` selects actions from the literal scene and lyric. Substantial
disjoint silhouettes animate separately, with staggered reactions. Touching
characters remain one group; this is a CPU 2D puppet renderer, not a full 3D rig.
A conservative eye-pair detector enables blinking, a small head warp and cheek
lift only when there is one unambiguous pair. These are approximations of a head
turn and happy expression, not newly generated side-view or smiling poses.
Uncertain faces retain the source art. Clip manifests record the story plan,
actor count and detected face rigs. Invalid foreground extraction retains the
existing camera-only fallback and records the reason.

Changing `.generation/scene-story-request.json` on main explicitly starts a new
10-minute **generation-only** run. Its final video is saved as a GitHub artifact;
that push run does not publish to YouTube/Facebook or create Shorts. Normal
scheduled/manual runs retain their configured publication behavior and also use
the new scene renderer. Cache versions invalidate previous motion clips.
