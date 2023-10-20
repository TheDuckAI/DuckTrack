import os

os.system("rm -rf dist build && pyinstaller --onefile --windowed --add-data \"assets/:assets/\" --name DuckTrack --icon=assets/hal9000.png main.py")
