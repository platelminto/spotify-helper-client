# Is the main app, and needs to be the main thread for pystray to work correctly.
import os
import subprocess
import platform
import logging

from PIL import Image
from pystray import Icon, Menu, MenuItem
from src.main.spotify_helper import SpotifyHelper, bindings_file
from ..notifications.notif_handler import send_notif

logging.basicConfig(filename='../spotify-helper.log', level=logging.INFO,
                    format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')


# Opens the bindings file in the default text editor
def open_bindings_file():
    send_notif('Changing bindings.', 'Please restart the Spotify Helper app after \
                                                                saving your changes')
    current_os = platform.system()
    if current_os == 'Darwin':  # macOS
        subprocess.call(('open', bindings_file))
    elif current_os == 'Windows':  # Windows
        os.startfile(bindings_file)
    else:  # Linux
        subprocess.call(('xdg-open', bindings_file))


if __name__ == "__main__":
    SpotifyHelper().run()

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

    icon.run()
