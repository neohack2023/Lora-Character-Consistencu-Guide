try:
    from .app_gui import App  # when run as a package: py -m mymy_looper
except ImportError:
    from app_gui import App    # when run directly:    py mymy_looper\__main__.py

if __name__ == "__main__":
    App().mainloop()
