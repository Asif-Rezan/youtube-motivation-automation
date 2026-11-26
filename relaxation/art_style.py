"""Shared natural photographic direction; historical checkpoints retain their style."""
STYLE_ID='natural-photorealistic-v1'
ART_DIRECTION=('Ultra-realistic professional nature photography, lifelike foliage and rocks, '
 'natural botanical detail, physically plausible water and rain, realistic soft daylight, '
 'subtle atmospheric depth, authentic camera perspective and fine photographic textures. '
 'Balanced exposure, true-to-life greens, believable reflections and gentle natural colour variation. '
 'Looks like a real location photographed with a high-quality camera, not rendered artwork. '
 'Tranquil outdoor scenery, no people, no text; avoid neon colours and excessive HDR.')

def negative_prompt(style_id):
 base='text, typography, watermark, logo, person, people, human, blurry, low quality, collage, border'
 if style_id=='bright-3d-storybook-v1':
  return base+', photograph, photorealistic, flat 2D art, sketch, dull desaturated colours, gloomy, underexposed, harsh neon, oversaturated highlights'
 return base+', cartoon, illustration, 3D render, CGI, storybook, painting, plastic foliage, artificial textures, neon, oversaturated, excessive HDR'
