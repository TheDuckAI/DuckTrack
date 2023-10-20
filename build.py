import os

os.system("pyinstaller --onefile --windowed --add-data \"assets/:assets/\" --name DuckTrack --icon=assets/hal9000.png main.py")
