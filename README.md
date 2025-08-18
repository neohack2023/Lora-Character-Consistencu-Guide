# MyMy Looper

A desktop tool for extracting seamless audio loops. It analyzes tracks, ranks bar-length candidates, and lets you preview and export only the loops you keep.

## Features
- Batch or single-file processing with tempo/beat tracking and downbeat alignment.
- Scores loops via seam correlation, onset flux, timbre/chroma/ZCR continuity, energy targeting, and beat alignment.
- Tkinter GUI with progress bar, results table, instant preview, CSV export, and optional online learning for confidence percentages.
- Smart naming and safe file exporting; previews are written to a temporary folder and clean loops are exported only when verified.
- Optional SQLite storage for presets and feedback to improve loop suggestions over time.

## Usage
Run the GUI:

```bash
python -m mymy_looper
```

Double-click a result to preview. Use **✔ Keep** to export a clean loop next to its preview. A CSV metadata file can be saved from the main window.

## Requirements
- Python 3.x
- NumPy, librosa, soundfile, tkinter (bundled with Python), and optional ffplay for preview.
