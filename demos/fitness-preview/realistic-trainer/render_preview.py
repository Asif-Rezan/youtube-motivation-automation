"""Export the original trainer's close-up and full-body motion test."""
from pathlib import Path
import sys

import bpy

out=Path(sys.argv[sys.argv.index("--")+1])
out.mkdir(parents=True,exist_ok=True)
scene=bpy.context.scene
scene.render.resolution_x=960
scene.render.resolution_y=540
scene.eevee.taa_render_samples=12
close=bpy.data.objects["Close-up"]
wide=bpy.data.objects["Full body"]
close.data.ortho_scale=.91
wide.data.ortho_scale=3.33
for frame in range(1,193):
    scene.frame_set(frame)
    scene.camera=close if frame<139 else wide
    scene.render.filepath=str(out/f"{frame-1:04}.jpg")
    scene.render.image_settings.file_format="JPEG"
    scene.render.image_settings.quality=94
    bpy.ops.render.render(write_still=True)
