import math, numpy as np, librosa
from utils import scalar

def _rms(x, frame=2048, hop=512):
    frames = max(1, (x.shape[-1]-frame)//hop+1)
    out = np.zeros(frames, dtype=np.float32)
    for i in range(frames):
        seg = x[i*hop:i*hop+frame]
        out[i] = np.sqrt(np.mean(seg**2) + 1e-12)
    return out

def _db(v): return 20*np.log10(np.maximum(1e-9, v))

def equal_power_xfade(a, b, xf_samples):
    if a.ndim == 1: a = a[None, ...]
    if b.ndim == 1: b = b[None, ...]
    # clamp crossfade <= half of each segment
    xf_samples = int(max(0, min(int(xf_samples), a.shape[-1]//2, b.shape[-1]//2)))
    if min(a.shape[-1], b.shape[-1]) < 2 or xf_samples == 0:
        return np.concatenate([a, b], axis=-1)
    t = np.linspace(0, 1, xf_samples, endpoint=False, dtype=a.dtype)
    ca, sa = np.cos(t * math.pi/2.0), np.sin(t * math.pi/2.0)
    a_tail = a[:, -xf_samples:] * ca
    b_head = b[:, :xf_samples] * sa
    mid = a_tail + b_head
    return np.concatenate([a[:, :-xf_samples], mid, b[:, xf_samples:]], axis=-1)

def trim_fade_loop(y, sr, t0, t1, xfade_ms=12):
    t0 = scalar(t0); t1 = scalar(t1); sr = int(sr)
    s0 = int(round(t0*sr)); s1 = int(round(t1*sr))
    seg = y[..., s0:s1]
    xf = int(round(sr*xfade_ms/1000.0))
    looped = equal_power_xfade(seg, seg, xf)
    return seg, looped

def find_top_loops(y, sr, *, bpm_hint=None, min_bars=4, max_bars=16,
                   prefer_bars=None, beats_per_bar=4, avoid_vocals=False,
                   top_n=3, min_spacing_sec=8.0, energy_target="auto",
                   status_cb=None, cancel_evt=None):
    """Return (tempo, [(score, t0, t1, bars, extras)...]), best-first."""
    if status_cb: status_cb("🥁 Detecting tempo…")
    y_mono = y if y.ndim == 1 else np.mean(y, axis=0)
    y_h, y_p = librosa.effects.hpss(y_mono)
    if bpm_hint is not None and np.isfinite(bpm_hint) and float(bpm_hint) > 0:
        tempo, beats = librosa.beat.beat_track(y=y_p, sr=sr, start_bpm=float(bpm_hint), units="frames")
    else:
        tempo, beats = librosa.beat.beat_track(y=y_p, sr=sr, units="frames")
    tempo = float(np.asarray(tempo).item())
    beat_times = librosa.frames_to_time(beats, sr=sr)

    if len(beat_times) < (min_bars*beats_per_bar + 1):
        return tempo, []

    if status_cb: status_cb("⏱️ Mapping downbeats…")
    chroma = librosa.feature.chroma_cqt(y=y_mono, sr=sr)
    novelty = librosa.onset.onset_strength(S=chroma, sr=sr, feature=None)
    onsets = librosa.onset.onset_detect(onset_envelope=novelty, sr=sr, units="time", backtrack=False)
    down_ix = np.arange(0, len(beat_times), beats_per_bar)
    down_times = beat_times[down_ix]
    if len(onsets):
        for i, t in enumerate(down_times):
            j = np.argmin(np.abs(onsets - t)); down_times[i] = onsets[j]
        down_times = np.sort(np.clip(down_times, 0, beat_times[-1]))

    if status_cb: status_cb("📦 Scoring loops…")
    hop = 512
    spec = np.abs(librosa.stft(y_mono, n_fft=2048, hop_length=hop))
    sc   = librosa.onset.onset_strength(S=librosa.power_to_db(spec**2), sr=sr)
    loud = _rms(y_mono, frame=2048, hop=hop)
    sc_t = librosa.frames_to_time(np.arange(len(sc)), sr=sr, hop_length=hop)
    ld_t = librosa.frames_to_time(np.arange(len(loud)), sr=sr, hop_length=hop)
    mfcc = librosa.feature.mfcc(y=y_mono, sr=sr, n_mfcc=13, hop_length=hop)
    mf_t = librosa.frames_to_time(np.arange(mfcc.shape[1]), sr=sr, hop_length=hop)

    mel_db = mel_t = vocal_band = None
    if avoid_vocals:
        mel = librosa.feature.melspectrogram(y=y_h, sr=sr, n_fft=2048, hop_length=hop, n_mels=64)
        mel_db = librosa.power_to_db(mel, ref=np.max)
        mel_t  = librosa.frames_to_time(np.arange(mel_db.shape[1]), sr=sr, hop_length=hop)
        freqs  = librosa.mel_frequencies(n_mels=64, fmin=0, fmax=sr/2)
        vbmask = (freqs >= 300) & (freqs <= 3400)
        vocal_band = mel_db[vbmask, :]

    # energy target
    q25, q50, q75 = np.quantile(loud, [0.25, 0.50, 0.75])
    target = {"low": q25, "mid": q50, "high": q75}.get(energy_target, None)

    def mean_in(arr, arr_t, t0, t1):
        mask = (arr_t >= t0) & (arr_t <= t1)
        if not mask.any(): return None
        return float(np.mean(arr[mask]))

    def vecmean_in(mat, arr_t, t0, t1):
        mask = (arr_t >= t0) & (arr_t <= t1)
        if not mask.any(): return None
        return np.mean(mat[:, mask], axis=1)

    sec_per_bar = (60.0/tempo) * float(beats_per_bar)
    edge_win = 0.12
    candidates = []

    for bars in range(min_bars, max_bars+1):
        if cancel_evt and cancel_evt.is_set(): break
        dur = bars * sec_per_bar
        for t0 in down_times:
            t1 = t0 + dur
            if t1 > librosa.get_duration(y=y_mono, sr=sr) - 0.02: continue
            # base score
            sf_mean = mean_in(sc, sc_t, t0, t1) or 1.0
            mu_ld   = mean_in(loud, ld_t, t0, t1) or 1e-3
            ld_varw = mean_in((loud - mu_ld)**2, ld_t, t0, t1) or 0.1
            score = (sf_mean*1.0 + ld_varw*0.5) - 0.2*_db(mu_ld+1e-9)

            # boundaries
            sf_start = mean_in(sc, sc_t, max(0, t0-edge_win), t0+edge_win) or 0.0
            sf_end   = mean_in(sc, sc_t, t1-edge_win, min(t1+edge_win, sc_t[-1])) or 0.0
            score += 0.6 * (sf_start + sf_end) / 2.0

            m_start = vecmean_in(mfcc, mf_t, t0, t0+edge_win)
            m_end   = vecmean_in(mfcc, mf_t, t1-edge_win, t1)
            if m_start is not None and m_end is not None:
                score += 0.10 * float(np.linalg.norm(m_start - m_end))

            z_pen = 0.0
            if avoid_vocals and mel_db is not None:
                mask_vb = (mel_t>=t0) & (mel_t<=t1)
                if mask_vb.any():
                    vm = np.mean(np.std(vocal_band[:, mask_vb], axis=1))
                    score += 0.15 * float(vm)

            if target is not None:
                score += 2.0 * abs(float(mu_ld - target))

            if prefer_bars is not None and bars != prefer_bars:
                score += 0.2

            # seam correlation + beat start error for filenames/extras
            seam_corr, beat_err_s = 0.0, 0.0
            try:
                s0 = int(round(t0*sr)); s1 = int(round(t1*sr))
                seam_len = max(64, int(0.20*sr))
                L = s1 - s0
                if L >= 2 and seam_len*2 <= L:
                    a = y_mono[s1-seam_len:s1]; b = y_mono[s0:s0+seam_len]
                    a = a - float(a.mean()); b = b - float(b.mean())
                    denom = float(np.linalg.norm(a) * np.linalg.norm(b) + 1e-12)
                    seam_corr = float(np.dot(a, b)/denom) if denom > 0 else 0.0
            except: pass
            # nearest downbeat distance
            beat_err_s = float(np.min(np.abs(down_times - t0))) if len(down_times) else 0.0

            extras = {"seam_corr":seam_corr, "beat_err_s":beat_err_s, "mu_ld":mu_ld, "q25":q25, "q75":q75}
            candidates.append((float(score), float(t0), float(t1), int(bars), extras))

    # sort & de-duplicate by spacing
    candidates.sort(key=lambda z: z[0])
    selected = []
    for c in candidates:
        _, t0, _, _, _ = c
        if all(abs(t0 - s[1]) >= min_spacing_sec for s in selected):
            selected.append(c)
        if len(selected) >= top_n: break

    return tempo, selected
