import signal
import sys
import traceback

from PyQt6.QtWidgets import QApplication

from ducktrack import AppTray


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    tray = AppTray(app)
    
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

if __name__ == "__main__":
    main()