import sys
import time
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import subprocess


class RestartOnChangeHandler(PatternMatchingEventHandler):
    def __init__(self, command, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.command = command
        self.process = None
        self.start_process()

    def start_process(self):
        if self.process:
            self.process.terminate()
        self.process = subprocess.Popen(self.command, shell=True)

    def on_any_event(self, event):
        print(f"File changed: {event.src_path}")
        self.start_process()


if __name__ == "__main__":

    path = "."
    command = "python -m kasa_exporter.main"
    event_handler = RestartOnChangeHandler(command, patterns=["*.py"])
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    print(f"Watching {path} for changes...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
