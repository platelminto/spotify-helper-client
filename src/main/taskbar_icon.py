# Is the main app, and needs to be the main thread for pystray to work correctly.
import os
import sys
import threading
import time
import webbrowser
import subprocess
import platform

from PIL import Image
from pystray import Icon, Menu, MenuItem
from src.main.spotify_helper import SpotifyHelper, bindings_file


# Begins the keyboard listener.
class SpotifyThread(threading.Thread):
    def __init__(self):
        super(SpotifyThread, self).__init__()
        self.daemon = True

    def run(self):
        SpotifyHelper().run()


spotify_thread = SpotifyThread()
spotify_thread.start()


# Opens the bindings file in the default text editor
def open_bindings_file():
    current_os = platform.system()
    if current_os == 'Darwin':       # macOS
        subprocess.call(('open', bindings_file))
    elif current_os == 'Windows':    # Windows
        os.startfile(bindings_file)
    else:                                   # Linux
        subprocess.call(('xdg-open', bindings_file))


if __name__ == "__main__":
    icon_image = Image.open('../resources/spo.png')

    icon = Icon('spotify-helper', icon_image, menu=Menu(
        MenuItem(
            text='Edit bindings',
            action=open_bindings_file),
        Menu.SEPARATOR,
        MenuItem(
            text='Quit',
            action=lambda: icon.stop()
        ),
    ))

    # If the spotify_helper thread crashed, the program should exit completely.
    def is_helper_alive():
        while True:
            if not spotify_thread.is_alive():
                break
            time.sleep(3)
        icon.stop()

    check_helper_alive_thread = threading.Thread(target=is_helper_alive)
    check_helper_alive_thread.daemon = True
    check_helper_alive_thread.start()

    icon.run()
