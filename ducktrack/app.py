import os
import signal
import sys
import traceback

from obs_client import close_obs, is_obs_running, open_obs
from playback import Player, get_latest_recording
from PyQt6.QtCore import QObject, QTimer, pyqtSlot
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (QApplication, QDialog, QFileDialog, QFormLayout,
                             QLabel, QLineEdit, QMenu, QMessageBox,
                             QPushButton, QSystemTrayIcon, QTextEdit,
                             QVBoxLayout)
from recorder import Recorder
from util import get_recordings_dir, open_file


class TitleDescriptionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Recording Details")

        self.layout = QVBoxLayout(self)

        self.form_layout = QFormLayout()

        self.title_label = QLabel("Title:")
        self.title_input = QLineEdit(self)
        self.form_layout.addRow(self.title_label, self.title_input)

        self.description_label = QLabel("Description:")
        self.description_input = QTextEdit(self)
        self.form_layout.addRow(self.description_label, self.description_input)

        self.layout.addLayout(self.form_layout)

        self.submit_button = QPushButton("Save", self)
        self.submit_button.clicked.connect(self.accept)
        self.layout.addWidget(self.submit_button)

    def get_values(self):
        return self.title_input.text(), self.description_input.toPlainText()

class AppTray(QObject):
    def __init__(self):
        super().__init__()
        self.tray = QSystemTrayIcon(QIcon(self.resource_path("../assets/hal9000.png")))
        self.tray.show()

        self.menu = QMenu()
        self.tray.setContextMenu(self.menu)

        self.start_record_action = QAction("Start Recording")
        self.start_record_action.triggered.connect(self.start_recording)
        self.menu.addAction(self.start_record_action)

        self.stop_record_action = QAction("Stop Recording")
        self.stop_record_action.triggered.connect(self.stop_recording)
        self.stop_record_action.setVisible(False)
        self.menu.addAction(self.stop_record_action)

        self.toggle_pause_action = QAction("Pause Recording")
        self.toggle_pause_action.triggered.connect(self.toggle_pause)
        self.toggle_pause_action.setVisible(False)
        self.menu.addAction(self.toggle_pause_action)
        
        self.show_recordings_action = QAction("Show Recordings")
        self.show_recordings_action.triggered.connect(lambda: open_file(get_recordings_dir()))
        self.menu.addAction(self.show_recordings_action)
        
        self.play_latest_action = QAction("Play Latest Recording")
        self.play_latest_action.triggered.connect(self.play_latest_recording)
        self.menu.addAction(self.play_latest_action)

        self.play_custom_action = QAction("Play Custom Recording")
        self.play_custom_action.triggered.connect(self.play_custom_recording)
        self.menu.addAction(self.play_custom_action)
        
        self.replay_recording_action = QAction("Replay Recording")
        self.replay_recording_action.triggered.connect(self.replay_recording)
        self.menu.addAction(self.replay_recording_action)
        self.replay_recording_action.setVisible(False)

        self.quit_action = QAction("Quit")
        self.quit_action.triggered.connect(self.quit)
        self.menu.addAction(self.quit_action)
        
        if not is_obs_running():
            self.obs_process = open_obs()

    @pyqtSlot()
    def replay_recording(self):
        player = Player()
        if hasattr(self, "last_played_recording_path"):
            player.play(self.last_played_recording_path)
        else:
            self.display_error_message("No recording has been played yet!")

    @pyqtSlot()
    def play_latest_recording(self):
        player = Player()
        recording_path = get_latest_recording()
        self.last_played_recording_path = recording_path
        self.replay_recording_action.setVisible(True)
        player.play(recording_path)

    @pyqtSlot()
    def play_custom_recording(self):
        player = Player()
        directory = QFileDialog.getExistingDirectory(None, "Select Recording", get_recordings_dir())
        if directory:
            self.last_played_recording_path = directory
            self.replay_recording_action.setVisible(True)
            player.play(directory)

    @pyqtSlot()
    def quit(self):
        self.stop_recording()
        if hasattr(self, "obs_process"):
            close_obs(self.obs_process)
        app.quit()

    @pyqtSlot()
    def toggle_pause(self):
        if tray.recorder_thread._is_paused:
            tray.recorder_thread.resume_recording()
            self.toggle_pause_action.setText("Pause Recording")
        else:
            tray.recorder_thread.pause_recording()
            self.toggle_pause_action.setText("Resume Recording")

    @pyqtSlot()
    def start_recording(self):
        self.recorder_thread = Recorder()
        self.recorder_thread.recording_stopped.connect(self.on_recording_stopped)
        self.recorder_thread.start()
        self.update_menu(True)

    @pyqtSlot()
    def stop_recording(self):
        if hasattr(self, "recorder_thread"):
            self.recorder_thread.stop_recording()
            self.recorder_thread.terminate()

            recording_dir = self.recorder_thread.recording_path

            del self.recorder_thread
            
            dialog = TitleDescriptionDialog()
            QTimer.singleShot(0, dialog.raise_)
            result = dialog.exec()

            if result == QDialog.DialogCode.Accepted:
                title, description = dialog.get_values()

                if title:
                    renamed_dir = os.path.join(os.path.dirname(recording_dir), title)
                    os.rename(recording_dir, renamed_dir)

                    with open(os.path.join(renamed_dir, 'README.md'), 'w') as f:
                        f.write(description)
                    
                self.on_recording_stopped()

    @pyqtSlot()
    def on_recording_stopped(self):
        self.update_menu(False)

    def update_menu(self, is_recording: bool):
        self.start_record_action.setVisible(not is_recording)
        self.stop_record_action.setVisible(is_recording)
        self.toggle_pause_action.setVisible(is_recording)

    def display_error_message(self, message):
        QMessageBox.critical(None, "Error", message)
        
    def resource_path(self, relative_path):
        base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    tray = AppTray()
    
    original_excepthook = sys.excepthook

    def handle_exception(exc_type, exc_value, exc_traceback):
        print("Exception type:", exc_type)
        print("Exception value:", exc_value)
        
        trace_details = traceback.format_exception(exc_type, exc_value, exc_traceback)
        trace_string = "".join(trace_details)

        print("Exception traceback:", trace_string)

        message = f"An error occurred!\n\n{exc_value}\n\n{trace_string}"
        tray.display_error_message(message)
        
        original_excepthook(exc_type, exc_value, exc_traceback)

    sys.excepthook = handle_exception

    sys.exit(app.exec())
