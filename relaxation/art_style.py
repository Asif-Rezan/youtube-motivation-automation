"""One shared bright storybook direction for episode plans and image inference."""
STYLE_ID='bright-3d-storybook-v1'
ART_DIRECTION=('Bright polished 3D storybook nature illustration, dimensional sculpted foliage and rocks, '
 'rich luminous greens, clear turquoise water where present, colourful flowers, soft warm highlights, '
 'gentle volumetric light, layered foreground and distant depth, refined detailed textures, '
 'cheerful balanced colour contrast, softly rounded natural forms. '
 'Keep the scene tranquil and spacious; avoid harsh neon, gloom, flat grey lighting and washed-out colours. '
 'Nature scenery only, no people, no text.')
def negative_prompt(style_id):
 base='text, typography, watermark, logo, person, people, human, blurry, low quality, collage, border'
 if style_id==STYLE_ID:
  return base+', photograph, photorealistic, flat 2D art, sketch, dull desaturated colours, gloomy, underexposed, harsh neon, oversaturated highlights'
 return base+', cartoon, illustration'
