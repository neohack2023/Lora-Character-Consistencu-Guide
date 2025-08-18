import os, re, numpy as np, sys, subprocess, shutil

INVALID_CHARS = set('<>:"/\\|?*')

def scalar(x) -> float:
    return float(np.asarray(x).reshape(-1)[0])

def slug(s: str) -> str:
    s = (s or "").encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"\s+", "_", s.strip())
    s = "".join(ch if (32 <= ord(ch) < 127) and (ch not in INVALID_CHARS) else "_" for ch in s)
    return re.sub(r"_+", "_", s).strip("_") or "audio"

def unique_path(folder: str, stem: str, ext: str) -> str:
    path = os.path.join(folder, f"{stem}{ext}")
    n = 2
    while os.path.exists(path):
        path = os.path.join(folder, f"{stem}_{n}{ext}"); n += 1
    return path

def open_path(path: str):
    if sys.platform.startswith("win"): os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin": subprocess.Popen(["open", path])
    else: subprocess.Popen(["xdg-open", path])

def build_loop_stem(track_stem: str, idx: int, bpm: float, bars: int, extras: dict) -> str:
    stem = slug(track_stem)
    seam = int(round(float(extras.get("seam_corr", 0.0)) * 100))
    beat_ms = int(round(float(extras.get("beat_err_s", 0.0)) * 1000.0))
    mood = extras.get("mood", None)
    parts = [stem, f"L{idx:02d}", (mood or ""), f"B{bars}", f"BPM{int(round(bpm))}", f"SEAM{seam}", f"BEAT{beat_ms}ms"]
    name = "_".join(p for p in parts if p)
    return name[:140] or "loop"
