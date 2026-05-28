"""Build script — packages Chaos Engine into a single .exe"""
import subprocess
import sys

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--onefile",
    "--windowed",
    "--name", "ChaosEngine",
    "--add-data", "config.json;.",
    "--add-data", "commons;commons",
    "--add-data", "game;game",
    "--hidden-import", "numpy",
    "--hidden-import", "pygame",
    "main.py",
]

print("Building Chaos Engine...")
print(" ".join(cmd))
subprocess.run(cmd)
print("\nDone! Check dist/ChaosEngine.exe")
