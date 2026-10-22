---
name: lang-python
description: Python apps, scripts, GUIs (PyQt6, CustomTkinter), packaging
domain: python
triggers: [python, py, pyqt, pyqt6, tkinter, customtkinter, pip, venv, script]
---
- Check: `python -m py_compile file.py`; run: `python file.py`; deps: `python -m pip install -r requirements.txt` inside `python -m venv .venv`.
- GUIs: PyQt6 for full apps (QMainWindow + menuBar() + QAction with shortcuts); CustomTkinter for quick themed tools.
- Menus (PyQt6): `m = self.menuBar().addMenu("&File"); a = QAction("&Open", self); a.setShortcut("Ctrl+O"); a.triggered.connect(self.open); m.addAction(a)`.
- Traps: never block the UI thread (QThread / threading + signals); paths with pathlib; `if __name__ == "__main__":`.
