"""Composite the transparent trainer frames over the existing jungle art."""

import argparse
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageFilter, ImageOps


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("frames", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    paths = sorted(args.frames.glob("[0-9][0-9][0-9][0-9].png"))
    if [path.stem for path in paths] != [f"{index:04d}" for index in range(186)]:
        parser.error("Expected all 186 consecutive trainer frames")

    artwork = Path(__file__).resolve().parent.parent / "jungle.png"
    with Image.open(artwork) as image:
        background = ImageOps.fit(image.convert("RGBA"), (1280, 720))
    shadow = Image.new("RGBA", background.size)
    ImageDraw.Draw(shadow).ellipse((546, 600, 738, 631), fill=(11, 23, 14, 128))
    background.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(9)))

    command = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo",
        "-pixel_format", "rgb24", "-video_size", "1280x720", "-framerate", "30",
        "-i", "pipe:0", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(args.output),
    ]
    with subprocess.Popen(command, stdin=subprocess.PIPE) as encoder:
        for path in paths:
            frame = background.copy()
            with Image.open(path) as actor:
                frame.alpha_composite(actor, (416, 98))
            encoder.stdin.write(frame.convert("RGB").tobytes())
        encoder.stdin.close()
        if encoder.wait():
            raise RuntimeError("FFmpeg failed to encode the motion-capture preview")


if __name__ == "__main__":
    main()
