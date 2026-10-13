"""Free Kokoro English narration and Faster-Whisper word alignment on cloud CPUs."""
import os
import numpy as np

_pipeline = None
_whisper = None


def generate(text, path):
    global _pipeline
    import soundfile as sf
    import torch
    torch.set_num_threads(2)
    if _pipeline is None:
        from kokoro import KPipeline
        _pipeline = KPipeline(lang_code='a', device='cpu', repo_id='hexgrad/Kokoro-82M')
    parts = [audio.numpy() for _, _, audio in _pipeline(text,
        voice=os.getenv('CPU_TTS_VOICE', 'am_michael'), speed=.9, split_pattern=r'\n+')]
    if not parts:
        raise RuntimeError('Kokoro returned no narration')
    sf.write(str(path), np.concatenate(parts), 24000)


def transcribe_audio(path):
    global _whisper
    if _whisper is None:
        from faster_whisper import WhisperModel
        _whisper = WhisperModel('base.en', device='cpu', compute_type='int8', cpu_threads=2)
    segments, info = _whisper.transcribe(str(path), language='en', word_timestamps=True,
        beam_size=3, vad_filter=False)
    words = [dict(word=w.word, start=w.start, end=w.end) for segment in segments for w in segment.words or []
        if w.end > w.start]
    if not words:
        raise RuntimeError('CPU transcription returned no aligned words')
    return words
