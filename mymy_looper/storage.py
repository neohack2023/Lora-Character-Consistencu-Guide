# storage.py — presets (optional), ML state, and feedback log
import os, sqlite3, json
from models import Norm
import numpy as np

class DB:
    def __init__(self, app_name="MyMyLooper"):
        home = os.path.expanduser("~")
        self.dir = os.path.join(home, ".mymy_looper")
        os.makedirs(self.dir, exist_ok=True)
        self.path = os.path.join(self.dir, "loops.db")
        self.conn = sqlite3.connect(self.path)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self._init_schema()

    def _init_schema(self):
        c = self.conn.cursor()
        # minimal presets (optional; safe to ignore if you don't use them yet)
        c.execute("""
          CREATE TABLE IF NOT EXISTS presets(
            name TEXT PRIMARY KEY,
            bpm REAL,
            beats_per_bar INTEGER,
            prefer_bars INTEGER,
            xfade_ms INTEGER,
            avoid_vocals INTEGER,
            min_bars INTEGER,
            max_bars INTEGER,
            top_n INTEGER,
            diverse_sec REAL,
            energy TEXT,
            weights_json TEXT,
            usage_count INTEGER DEFAULT 0,
            last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
          )
        """)
        # ML state
        c.execute("""
          CREATE TABLE IF NOT EXISTS ml_state(
            preset TEXT PRIMARY KEY,
            w_json TEXT,
            b REAL,
            norm_json TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
          )
        """)
        # Feedback log (for your analytics / future training)
        c.execute("""
          CREATE TABLE IF NOT EXISTS feedback(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            preset TEXT,
            file TEXT,
            idx INTEGER,
            x_json TEXT,
            y INTEGER,
            rating INTEGER,
            conf REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
          )
        """)
        self.conn.commit()

    # ---- ML state API ----
    def load_ml(self, preset: str, d: int):
        row = self.conn.execute(
            "SELECT w_json, b, norm_json FROM ml_state WHERE preset=?",
            [preset]
        ).fetchone()
        if not row:
            return np.zeros(d, float), 0.0, Norm()
        w_json, b, norm_json = row
        w = np.array(json.loads(w_json), float) if w_json else np.zeros(d, float)
        norm = Norm.from_json(norm_json)
        return w, float(b or 0.0), norm

    def save_ml(self, preset: str, w, b, norm: Norm):
        self.conn.execute(
            "INSERT INTO ml_state(preset, w_json, b, norm_json) VALUES(?,?,?,?) "
            "ON CONFLICT(preset) DO UPDATE SET "
            "w_json=excluded.w_json, b=excluded.b, norm_json=excluded.norm_json, updated_at=CURRENT_TIMESTAMP",
            [preset, json.dumps([float(v) for v in w]), float(b), norm.to_json()]
        )
        self.conn.commit()

    def log_feedback(self, preset: str, file: str, idx: int, x, y: int, rating=None, conf=None):
        self.conn.execute(
            "INSERT INTO feedback(preset, file, idx, x_json, y, rating, conf) VALUES(?,?,?,?,?,?,?)",
            [preset, file, idx, json.dumps([float(v) for v in x]), int(y),
             None if rating is None else int(rating),
             None if conf is None else float(conf)]
        )
        self.conn.commit()

    # (Presets helpers are optional; left minimal so DB is shared)
    def ensure_default(self, defaults: dict):
        row = self.conn.execute("SELECT 1 FROM presets WHERE name='Default'").fetchone()
        if not row:
            self.conn.execute(
                "INSERT INTO presets(name, beats_per_bar, min_bars, max_bars, top_n, diverse_sec, energy) "
                "VALUES('Default', ?, ?, ?, ?, ?, ?)",
                [defaults.get("beats_per_bar", 4), defaults.get("min_bars", 4),
                 defaults.get("max_bars", 16), defaults.get("top_n", 3),
                 defaults.get("diverse_sec", 8.0), defaults.get("energy", "auto")]
            )
            self.conn.commit()

    def close(self):
        try: self.conn.close()
        except: pass
