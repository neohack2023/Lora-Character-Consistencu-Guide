import shutil, subprocess, soundfile as sf, librosa, numpy as np

def load_audio(path: str):
    # sr=None to preserve original SR; mono=False to keep channels
    y, sr = librosa.load(path, sr=None, mono=False)
    return y, int(sr)

def write_wav(path: str, y, sr: int):
    sf.write(path, y.T if getattr(y, "ndim", 1) == 2 else y, sr)

def preview_file(path: str):
    ffplay = shutil.which("ffplay")
    if ffplay:
        subprocess.Popen([ffplay, "-autoexit", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    # fallback to system default
    import utils as U
    U.open_path(path)
