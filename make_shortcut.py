"""One-time: put an Eclipse shortcut on the Desktop and in the Start menu (Windows), or
build ~/Applications/Eclipse.app (macOS). Double-click it like any app; no console window.

    python make_shortcut.py
"""
from __future__ import annotations

import os
import stat
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
ENTRY = os.path.join(ROOT, "desktop.py")


def windows() -> list[str]:
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.isfile(pyw):
        pyw = sys.executable                    # falls back to python.exe (shows a console)
    icon = os.path.join(ROOT, "assets", "icon.ico")
    # the real Desktop, even when OneDrive has moved it
    desk = subprocess.run(["powershell", "-NoProfile", "-Command", "[Environment]::GetFolderPath('Desktop')"],
                          capture_output=True, text=True).stdout.strip() or os.path.join(os.path.expanduser("~"), "Desktop")
    spots = [desk,
             os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs")]
    made = []
    for folder in spots:
        lnk = os.path.join(folder, "Eclipse.lnk")
        ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:LNK);"
              "$s.TargetPath=$env:PYW;$s.Arguments='\"'+$env:ENTRY+'\"';"
              "$s.WorkingDirectory=$env:ROOT;$s.IconLocation=$env:ICON;"
              "$s.Description='Eclipse - local AI dev workbench';$s.Save()")
        env = dict(os.environ, LNK=lnk, PYW=pyw, ENTRY=ENTRY, ROOT=ROOT, ICON=icon)
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], env=env, check=True)
        made.append(lnk)
    return made


def mac() -> list[str]:
    app = os.path.expanduser("~/Applications/Eclipse.app")
    macos = os.path.join(app, "Contents", "MacOS")
    res = os.path.join(app, "Contents", "Resources")
    os.makedirs(macos, exist_ok=True)
    os.makedirs(res, exist_ok=True)
    run = os.path.join(macos, "Eclipse")
    with open(run, "w") as f:
        f.write(f'#!/bin/sh\ncd "{ROOT}"\nexec "{sys.executable}" "{ENTRY}"\n')
    os.chmod(run, os.stat(run).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    png = os.path.join(ROOT, "assets", "icon.png")
    icns = os.path.join(res, "Eclipse.icns")
    subprocess.run(["sips", "-s", "format", "icns", png, "--out", icns], capture_output=True)
    with open(os.path.join(app, "Contents", "Info.plist"), "w") as f:
        f.write("""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleName</key><string>Eclipse</string>
<key>CFBundleIdentifier</key><string>local.eclipse.workbench</string>
<key>CFBundleExecutable</key><string>Eclipse</string>
<key>CFBundleIconFile</key><string>Eclipse</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>NSHighResolutionCapable</key><true/>
</dict></plist>
""")
    return [app]


if __name__ == "__main__":
    if sys.platform == "win32":
        out = windows()
    elif sys.platform == "darwin":
        out = mac()
    else:
        sys.exit("Shortcuts are made for Windows and macOS. On Linux run: python desktop.py")
    print("Made:\n  " + "\n  ".join(out))
