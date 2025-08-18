# app_gui.py — ONLY export on Keep; previews go to temp; ML Conf% + Verify bar
import os, threading, traceback, tkinter as tk
from tkinter import ttk, filedialog, messagebox
import glob, csv, shutil, tempfile
import numpy as np

# Dual imports so it works with:  py -m mymy_looper   OR   py mymy_looper\__main__.py
try:
    from .utils import unique_path, build_loop_stem, open_path
    from .audio_io import load_audio, write_wav, preview_file
    from .dsp_core import find_top_loops, trim_fade_loop
except ImportError:
    from utils import unique_path, build_loop_stem, open_path
    from audio_io import load_audio, write_wav, preview_file
    from dsp_core import find_top_loops, trim_fade_loop

# Try to enable ML. If missing, we degrade gracefully.
ML_AVAILABLE = True
try:
    try:
        from .storage import DB
        from . import models
    except ImportError:
        from storage import DB
        import models
    FEATURE_DIM = len(models.FEATURE_ORDER)
except Exception:
    ML_AVAILABLE = False
    DB = None
    models = None
    FEATURE_DIM = 0

AUDIO_EXTS = (".mp3",".wav",".m4a",".flac",".ogg",".aac",".aif",".aiff")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("My My Loop Extractor")
        self.geometry("980x740")
        self.resizable(False, False)

        # Cancellation + ML state
        self.cancel_evt = threading.Event()
        self.row_meta = {}  # Treeview iid -> {"file","idx","x","conf","seg","sr","stem","out_dir","preview_tmp"}

        if ML_AVAILABLE:
            self.db = DB()
            self.preset_name = "Default"
            self.w, self.b, self.norm = self.db.load_ml(self.preset_name, d=FEATURE_DIM)
        else:
            self.db = None
            self.preset_name = "Default"
            self.w = self.b = self.norm = None

        # Temp session dir for previews (cleaned on exit)
        self.session_tmp = tempfile.mkdtemp(prefix="mymy_previews_")

        # ----- UI -----
        frm = ttk.Frame(self); frm.pack(fill="both", expand=True, padx=8, pady=6)

        # row 0: file
        self.in_path = tk.StringVar(); self.out_dir = tk.StringVar()
        ttk.Label(frm, text="Input audio:").grid(row=0, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.in_path, width=72).grid(row=0, column=1, columnspan=5, sticky="we")
        ttk.Button(frm, text="Browse…", command=self.browse).grid(row=0, column=6, sticky="we")

        # row 1: status
        self.status = ttk.Label(frm, text="Ready."); self.status.grid(row=1, column=0, columnspan=7, sticky="w")

        # row 2–4: params
        self.bpm = tk.StringVar()
        self.min_bars, self.max_bars = tk.IntVar(value=4), tk.IntVar(value=16)
        self.prefer_bars = tk.StringVar()
        self.beats_per_bar = tk.IntVar(value=4)
        self.top_n = tk.IntVar(value=3)
        self.diverse_sec = tk.DoubleVar(value=8.0)
        self.xfade_ms = tk.IntVar(value=16)
        self.energy = tk.StringVar(value="auto")
        self.avoid_vocals = tk.BooleanVar(value=False)

        r=2
        ttk.Label(frm, text="BPM:").grid(row=r, column=0, sticky="e")
        ttk.Entry(frm, textvariable=self.bpm, width=8).grid(row=r, column=1, sticky="w")
        ttk.Label(frm, text="Min/Max bars:").grid(row=r, column=2, sticky="e")
        ttk.Spinbox(frm, from_=1, to=64, textvariable=self.min_bars, width=5).grid(row=r, column=3, sticky="w")
        ttk.Spinbox(frm, from_=1, to=128, textvariable=self.max_bars, width=5).grid(row=r, column=4, sticky="w")
        ttk.Label(frm, text="Beats/bar:").grid(row=r, column=5, sticky="e")
        ttk.Spinbox(frm, from_=2, to=7, textvariable=self.beats_per_bar, width=5).grid(row=r, column=6, sticky="w")

        r+=1
        ttk.Label(frm, text="Prefer bars:").grid(row=r, column=0, sticky="e")
        ttk.Entry(frm, textvariable=self.prefer_bars, width=8).grid(row=r, column=1, sticky="w")
        ttk.Label(frm, text="Top N:").grid(row=r, column=2, sticky="e")
        ttk.Spinbox(frm, from_=1, to=20, textvariable=self.top_n, width=5).grid(row=r, column=3, sticky="w")
        ttk.Label(frm, text="Spacing(s):").grid(row=r, column=4, sticky="e")
        ttk.Spinbox(frm, from_=0, to=60, increment=1, textvariable=self.diverse_sec, width=6).grid(row=r, column=5, sticky="w")
        ttk.Checkbutton(frm, text="Avoid vocals", variable=self.avoid_vocals).grid(row=r, column=6, sticky="w")

        r+=1
        ttk.Label(frm, text="Energy:").grid(row=r, column=0, sticky="e")
        ttk.Combobox(frm, textvariable=self.energy, values=["auto","low","mid","high"], state="readonly", width=8).grid(row=r, column=1, sticky="w")
        ttk.Label(frm, text="Crossfade(ms):").grid(row=r, column=2, sticky="e")
        ttk.Spinbox(frm, from_=0, to=200, textvariable=self.xfade_ms, width=6).grid(row=r, column=3, sticky="w")
        ttk.Label(frm, text="Output folder:").grid(row=r, column=4, sticky="e")
        ttk.Entry(frm, textvariable=self.out_dir, width=28).grid(row=r, column=5, sticky="we")
        ttk.Button(frm, text="Choose…", command=self.choose_outdir).grid(row=r, column=6, sticky="we")

        # row buttons
        r+=1
        self.run_btn = ttk.Button(frm, text="Extract (Single File)", command=self.run_single)
        self.batch_btn = ttk.Button(frm, text="Batch Folder…", command=self.batch_folder)
        self.cancel_btn = ttk.Button(frm, text="Cancel", command=self.cancel, state="disabled")
        self.csv_btn = ttk.Button(frm, text="Export CSV…", command=self.export_csv, state="disabled")
        self.open_btn = ttk.Button(frm, text="Open Output Folder", command=self.open_out, state="disabled")
        self.preview_btn = ttk.Button(frm, text="Preview Selected", command=self.preview_selected, state="disabled")
        self.run_btn.grid(row=r, column=0, columnspan=2, sticky="we", pady=(8,6))
        self.batch_btn.grid(row=r, column=2, sticky="we", pady=(8,6))
        self.cancel_btn.grid(row=r, column=3, sticky="we", pady=(8,6))
        self.csv_btn.grid(row=r, column=4, sticky="we", pady=(8,6))
        self.open_btn.grid(row=r, column=5, sticky="we", pady=(8,6))
        self.preview_btn.grid(row=r, column=6, sticky="we", pady=(8,6))

        # progress
        r+=1
        self.pb = ttk.Progressbar(frm, mode="determinate", maximum=100)
        self.pb.grid(row=r, column=0, columnspan=7, sticky="we", pady=(0,6))

        # table
        r+=1
        ttk.Label(frm, text="Results (double-click to preview):").grid(row=r, column=0, columnspan=7, sticky="w")
        cols = ("#", "File", "Bars", "Start", "End", "Dur", "Score", "Conf%", "BPM", "Beats/Bar", "Clean Path", "Preview Path")
        self.tree = ttk.Treeview(frm, columns=cols, show="headings", height=14)
        for c, w in zip(cols, (40,160,60,80,80,80,80,70,60,80,220,220)):
            self.tree.heading(c, text=c); self.tree.column(c, width=w, anchor="w")
        self.tree.grid(row=r+1, column=0, columnspan=7, sticky="nsew")
        self.tree.bind("<Double-1>", lambda e: self.preview_selected())
        ttk.Scrollbar(frm, orient="vertical", command=self.tree.yview).grid(row=r+1, column=7, sticky="ns")
        self.tree.configure(yscrollcommand=lambda *a: None)

        # verify bar
        r += 2
        vf = ttk.Frame(frm)
        vf.grid(row=r, column=0, columnspan=7, sticky="we", pady=(6, 0))
        ttk.Label(vf, text="Verify selection:").grid(row=0, column=0, padx=(0,6))
        self.btn_keep = ttk.Button(vf, text="✔ Keep", command=lambda: self.verify_action(1, None))
        self.btn_skip = ttk.Button(vf, text="✖ Skip", command=lambda: self.verify_action(0, None))
        self.btn_keep.grid(row=0, column=1, padx=2)
        self.btn_skip.grid(row=0, column=2, padx=2)
        self.star_btns = []
        for k in range(1, 6):
            b = ttk.Button(vf, text=f"{k}★", command=lambda k=k: self.verify_action(1 if k >= 4 else 0, k))
            b.grid(row=0, column=2+k, padx=2)
            self.star_btns.append(b)
        if not ML_AVAILABLE:
            for b in [self.btn_keep, self.btn_skip, *self.star_btns]:
                b.config(state="disabled")
            ttk.Label(vf, text="(ML disabled—add models.py & storage.py to enable Conf% learning)").grid(row=0, column=8, padx=10)

        # log
        r+=1
        ttk.Label(frm, text="Log:").grid(row=r, column=0, sticky="w")
        self.log = tk.Text(frm, height=8, width=120, state="disabled")
        self.log.grid(row=r+1, column=0, columnspan=7, sticky="nsew")

        self.results = []
        self.last_out_dir = None
        frm.grid_columnconfigure(1, weight=1)

        # Ensure cleanup
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------- helpers ----------
    def set_status(self, text): self.status.config(text=text)
    def logln(self, text):
        self.log.configure(state="normal"); self.log.insert("end", text + "\n")
        self.log.see("end"); self.log.configure(state="disabled")

    def browse(self):
        f = filedialog.askopenfilename(title="Select audio file",
              filetypes=[("Audio", "*.mp3 *.wav *.m4a *.flac *.ogg *.aac *.aif *.aiff"), ("All files", "*.*")])
        if f: self.in_path.set(f); self.out_dir.set(self.out_dir.get() or os.path.dirname(f))

    def choose_outdir(self):
        d = filedialog.askdirectory(title="Choose output folder")
        if d: self.out_dir.set(d)

    def cancel(self): self.cancel_evt.set(); self.cancel_btn.config(state="disabled")

    def open_out(self):
        d = self.out_dir.get().strip() or self.last_out_dir
        if d and os.path.isdir(d): open_path(d)

    def preview_selected(self):
        sel = self.tree.selection()
        if not sel: messagebox.showinfo("Preview", "Select a row first."); return
        prev_path = self.tree.set(sel[0], "Preview Path")
        if not os.path.exists(prev_path): messagebox.showerror("Preview", "Not found:\n"+prev_path); return
        preview_file(prev_path)

    def export_csv(self):
        if not self.results: messagebox.showinfo("Export CSV", "No results yet."); return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV","*.csv")], initialfile="loops_metadata.csv")
        if not path: return
        headers = ["file","index","t0","t1","duration","bars","score","bpm","beats_per_bar","clean_path","preview_path"]
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=headers); w.writeheader()
                for r in self.results: w.writerow(r)
            messagebox.showinfo("Export CSV", f"Saved: {path}")
        except Exception as e:
            messagebox.showerror("Export CSV error", str(e))

    # ---------- runs ----------
    def run_single(self):
        path = self.in_path.get().strip()
        if not path or not os.path.isfile(path): messagebox.showerror("Missing file","Pick an input audio file."); return
        out_dir = self.out_dir.get().strip() or os.path.dirname(path); os.makedirs(out_dir, exist_ok=True)
        self._start_worker([path], out_dir)

    def batch_folder(self):
        folder = filedialog.askdirectory(title="Select folder to batch")
        if not folder: return
        files = []
        for ext in AUDIO_EXTS: files.extend(glob.glob(os.path.join(folder, f"*{ext}")))
        files.sort()
        if not files: messagebox.showinfo("Batch","No audio files found."); return
        out_dir = self.out_dir.get().strip() or folder; os.makedirs(out_dir, exist_ok=True)
        self._start_worker(files, out_dir)

    def _start_worker(self, files, out_dir):
        # parse params
        try:
            bpm = float(self.bpm.get().strip()) if self.bpm.get().strip() else None
            min_b, max_b = int(self.min_bars.get()), int(self.max_bars.get())
            pref_b = int(self.prefer_bars.get().strip()) if self.prefer_bars.get().strip() else None
            bpb = int(self.beats_per_bar.get()); topn = int(self.top_n.get())
            divs = float(self.diverse_sec.get()); xfms = int(self.xfade_ms.get())
        except Exception:
            messagebox.showerror("Params","Check inputs."); return
        if max_b < min_b: messagebox.showerror("Bars","Max bars must be >= Min bars."); return

        # UI state
        self.cancel_evt.clear()
        self.run_btn.config(state="disabled"); self.batch_btn.config(state="disabled")
        self.cancel_btn.config(state="normal"); self.csv_btn.config(state="disabled")
        self.open_btn.config(state="disabled"); self.preview_btn.config(state="disabled")
        self.pb["value"] = 0; self.pb["maximum"] = max(1, len(files))
        self.set_status("🔍 Loading…")
        self.logln(f"Scanning {len(files)} file(s)…")
        for iid in self.tree.get_children(): self.tree.delete(iid)
        self.results, self.last_out_dir = [], out_dir
        self.row_meta.clear()

        t = threading.Thread(target=self._worker,
                             args=(files, out_dir, bpm, min_b, max_b, pref_b, bpb, topn, divs, xfms,
                                   self.avoid_vocals.get(), self.energy.get().strip().lower()),
                             daemon=True)
        t.start()

    def _worker(self, files, out_dir, bpm, min_b, max_b, pref_b, bpb, topn, divs, xfms, avoid_v, energy):
        try:
            total_previewed = 0
            for i, path in enumerate(files, start=1):
                if self.cancel_evt.is_set(): break
                base = os.path.splitext(os.path.basename(path))[0]
                self.after(0, self.set_status, f"🔍 Loading… {base}")
                try:
                    y, sr = load_audio(path)
                except Exception as e:
                    self.after(0, self.logln, f"Load error: {base} -> {e}"); continue

                def stage(msg): self.after(0, self.set_status, msg)
                tempo, cands = find_top_loops(y, sr, bpm_hint=bpm, min_bars=min_b, max_bars=max_b,
                                              prefer_bars=pref_b, beats_per_bar=bpb, avoid_vocals=avoid_v,
                                              top_n=topn, min_spacing_sec=divs, energy_target=energy,
                                              status_cb=stage, cancel_evt=self.cancel_evt)
                if not cands:
                    self.after(0, self.logln, f"No loops: {base}")

                for idx, (score, t0, t1, bars, extras) in enumerate(cands, start=1):
                    if self.cancel_evt.is_set(): break
                    # Build segment + preview (preview only to temp; DO NOT export clean yet)
                    seg, prev = trim_fade_loop(y, sr, t0, t1, xfade_ms=xfms)
                    stem = build_loop_stem(base, idx, tempo, bars, extras)

                    # temp preview path
                    prev_tmp = os.path.join(self.session_tmp, f"{stem}_preview.wav")
                    n = 2
                    while os.path.exists(prev_tmp):
                        prev_tmp = os.path.join(self.session_tmp, f"{stem}_preview_{n}.wav"); n += 1

                    try:
                        # write preview to temp folder
                        write_wav(prev_tmp, prev, sr)
                    except Exception as e:
                        self.after(0, self.logln, f"Preview write error: {prev_tmp} -> {e}")
                        continue

                    total_previewed += 1

                    # features → Conf%
                    if ML_AVAILABLE and models is not None:
                        try:
                            x = models.pack_features(extras, bars, t0, t1)
                            xn = self.norm.apply(x) if self.norm is not None else x
                            conf = models.predict(self.w, self.b, xn)
                        except Exception:
                            x, conf = None, float("nan")
                    else:
                        x, conf = None, float("nan")

                    # table + results
                    conf_str = f"{conf*100:.0f}%" if np.isfinite(conf) else "—"
                    row = (idx, os.path.basename(path), bars,
                           f"{t0:.3f}", f"{t1:.3f}", f"{(t1-t0):.3f}",
                           f"{score:.3f}", conf_str, f"{tempo:.1f}", bpb,
                           "—",  # Clean Path (not exported yet)
                           prev_tmp)  # Preview Path (temp)
                    iid = self.tree.insert("", "end", values=row)
                    # store per-row data for later Keep export
                    self.row_meta[iid] = {
                        "file": path, "idx": idx, "x": x, "conf": conf,
                        "seg": seg, "sr": sr, "stem": stem, "out_dir": out_dir,
                        "preview_tmp": prev_tmp
                    }
                    self.results.append({"file": path, "index": idx, "t0": f"{t0:.6f}", "t1": f"{t1:.6f}",
                                         "duration": f"{(t1-t0):.6f}", "bars": bars, "score": f"{score:.6f}",
                                         "bpm": f"{tempo:.3f}", "beats_per_bar": bpb,
                                         "clean_path": "", "preview_path": prev_tmp})

                self.after(0, self.pb.step, 1)

            done_txt = "✅ Ready for review. Use ✔ Keep to export." if not self.cancel_evt.is_set() else "⛔ Canceled."
            self.after(0, self.set_status, done_txt)
            self.after(0, lambda: (self.open_btn.config(state="normal"),
                                   self.preview_btn.config(state="normal" if self.results else "disabled"),
                                   self.csv_btn.config(state="normal" if self.results else "disabled")))
            self.after(0, self.logln, f"Prepared {total_previewed} preview file(s). No exports yet.")
        except Exception as e:
            tb = traceback.format_exc(limit=6)
            self.after(0, self.logln, f"Error: {e}\n{tb}")
            messagebox.showerror("Loop Extractor Error", str(e))
        finally:
            self.after(0, lambda: (self.pb.stop(), self.run_btn.config(state="normal"),
                                   self.batch_btn.config(state="normal"),
                                   self.cancel_btn.config(state="disabled")))

    # ---------- verify ----------
    def verify_action(self, y: int, rating):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Verify", "Select a row first.")
            return
        iid = sel[0]
        meta = self.row_meta.get(iid)
        if not meta:
            messagebox.showerror("Verify", "Internal mapping missing for selected row.")
            return

        # If ML present, learn from the click
        if ML_AVAILABLE and self.db is not None and models is not None and meta.get("x") is not None:
            try:
                self.norm.update(meta["x"])
                xn = self.norm.apply(meta["x"])
                self.w, self.b = models.update(self.w, self.b, xn, int(y), lr=0.05)
                self.db.save_ml(self.preset_name, self.w, self.b, self.norm)
                self.db.log_feedback(self.preset_name, meta["file"], int(meta["idx"]),
                                     meta["x"], int(y), rating=rating, conf=meta.get("conf"))
                # refresh Conf% on the row
                new_conf = models.predict(self.w, self.b, self.norm.apply(meta["x"]))
                meta["conf"] = new_conf
                self.tree.set(iid, "Conf%", f"{new_conf*100:.0f}%")
            except Exception as e:
                self.logln(f"ML update error: {e}")

        # Export only on Keep (y==1). Skip does nothing (no export).
        if int(y) == 1:
            seg = meta.get("seg"); sr = meta.get("sr"); out_dir = meta.get("out_dir")
            stem = meta.get("stem"); prev_tmp = meta.get("preview_tmp")
            if seg is None or sr is None or not out_dir:
                messagebox.showerror("Export", "Missing audio data for export.")
                return
            try:
                os.makedirs(out_dir, exist_ok=True)
                out_clean = unique_path(out_dir, stem, ".wav")
                write_wav(out_clean, seg, sr)
                # also copy preview next to it for convenience
                out_prev = unique_path(out_dir, stem + "_preview", ".wav")
                try:
                    shutil.copyfile(prev_tmp, out_prev)
                except Exception:
                    out_prev = prev_tmp  # if copy fails, at least keep temp for preview
                # update table + results
                self.tree.set(iid, "Clean Path", out_clean)
                # update results entry
                f, idx = meta["file"], meta["idx"]
                for r in self.results:
                    if r.get("file")==f and int(r.get("index", -1))==int(idx):
                        r["clean_path"] = out_clean
                        r["preview_path"] = out_prev
                        break
                self.logln(f"✔ Exported: {out_clean}")
            except Exception as e:
                messagebox.showerror("Export error", str(e))
        else:
            # Optional: mark skipped in log
            self.logln("✖ Skipped (no export).")

    # ---------- lifecycle ----------
    def on_close(self):
        # best-effort cleanup of temp previews
        try:
            shutil.rmtree(self.session_tmp, ignore_errors=True)
        except Exception:
            pass
        try:
            if self.db: self.db.close()
        finally:
            self.destroy()
