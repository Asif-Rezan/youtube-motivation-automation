"""Exercise the real English tokenizer and Kokoro audio before generating a story."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import soundfile as sf

from voice_cpu import generate


def main():
    with TemporaryDirectory() as directory:
        audio = Path(directory) / 'narration.wav'
        generate("You review your budget and set aside twenty dollars for tomorrow.", audio)
        samples, rate = sf.read(audio)
        if rate != 24000 or samples.size < rate or not np.isfinite(samples).all():
            raise RuntimeError('Narration must contain at least one second of valid 24 kHz audio')
        if np.max(np.abs(samples)) < 0.001:
            raise RuntimeError('Narration is silent')
        print(json.dumps({'check': 'Real CPU narration', 'passed': True,
                          'seconds': round(len(samples) / rate, 2)}))


if __name__ == '__main__':
    main()
