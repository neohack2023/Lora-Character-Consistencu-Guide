# models.py — stabilized online LR (regularized, clipped, temp-scaled)
import numpy as np, json, math

# Keep this order stable (also used by server if you add one)
FEATURE_ORDER = ["bars", "log_dur", "seam_corr", "beat_err_norm", "loud_mean", "energy_iqr"]

# Tunables to prevent whiplash
LR = 0.01              # smaller step
WEIGHT_DECAY = 1e-3    # L2 shrink
Z_CLIP = 6.0           # clamp logit to avoid 0/1 saturation
TEMP = 1.8             # soften sigmoid
X_CLIP = 5.0           # clamp standardized features
NORM_WARMUP = 25       # show ~50% until we’ve seen enough data

def pack_features(extras: dict, bars: int, t0: float, t1: float) -> np.ndarray:
    dur = float(t1 - t0)
    bars_f = float(bars)
    sc = float(extras.get("seam_corr", 0.0))
    be = float(extras.get("beat_err_s", 0.0))
    mu = float(extras.get("mu_ld", 0.0))
    q25 = float(extras.get("q25", mu))
    q75 = float(extras.get("q75", mu + 1e-6))
    iqr = max(1e-6, q75 - q25)
    energy_iqr = np.clip((mu - 0.5*(q25+q75))/iqr, -3.0, 3.0)

    # normalize beat error by seconds-per-bar estimated from loop
    spb = dur / max(1.0, bars_f)
    beat_err_norm = np.clip(be / max(1e-3, spb), 0.0, 1.0)

    log_dur = math.log(max(1e-3, dur))
    return np.array([bars_f, log_dur, sc, beat_err_norm, mu, energy_iqr], float)

def init(d):  # zeros = neutral
    return np.zeros(d, float), 0.0

def _sigmoid(z):  # temperatured & clipped
    z = np.clip(z, -Z_CLIP, Z_CLIP)
    return 1.0 / (1.0 + np.exp(-z / TEMP))

def predict(w, b, xn):
    z = float(np.dot(w, xn) + b)
    return _sigmoid(z)

def update(w, b, xn, y, lr=LR):
    p = predict(w, b, xn)
    g = (y - p)
    # L2 regularization + small step
    w = (1.0 - lr*WEIGHT_DECAY) * w + lr * g * xn
    b = b + lr * g
    return w, b

class Norm:
    """Running mean/std. Apply only after warmup; clip standardized values."""
    def __init__(self, mean=None, std=None, n=0):
        self.mean = np.array(mean, float) if mean is not None else None
        self.std  = np.array(std, float)  if std  is not None else None
        self.n = int(n)
        self._M2 = np.zeros_like(self.mean) if self.mean is not None else None

    def apply(self, x):
        x = np.asarray(x, float)
        if self.mean is None or self.std is None or self.n < NORM_WARMUP:
            return np.clip(x, -X_CLIP, X_CLIP)
        s = np.where(self.std < 1e-8, 1.0, self.std)
        xn = (x - self.mean) / s
        return np.clip(xn, -X_CLIP, X_CLIP)

    def update(self, x):
        x = np.asarray(x, float)
        if self.mean is None:
            self.mean = x.copy()
            self._M2  = np.zeros_like(x)
            self.std  = np.ones_like(x)
            self.n = 1
            return
        self.n += 1
        d = x - self.mean
        self.mean += d / self.n
        self._M2 += d * (x - self.mean)
        var = self._M2 / max(1, self.n - 1)
        self.std = np.sqrt(np.maximum(var, 1e-8))

    def to_json(self):
        return json.dumps({
            "mean": self.mean.tolist() if self.mean is not None else None,
            "std":  self.std .tolist() if self.std  is not None else None,
            "n":    self.n
        })

    @staticmethod
    def from_json(s):
        if not s: return Norm()
        d = json.loads(s)
        return Norm(d.get("mean"), d.get("std"), d.get("n", 0))
