# Is the main app, and needs to be the main thread for pystray to work correctly.
import os
import subprocess
import platform
import logging
import traceback

from PIL import Image
from pystray import Icon, Menu, MenuItem
from spotify_helper import SpotifyHelper, bindings_file
from notif_handler import send_notif

logging.basicConfig(filename='spotify-helper.log', level=logging.INFO,
                    format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')


# Opens the bindings file in the default text editor
def open_bindings_file():
    send_notif('Changing bindings', 'Please restart the Spotify Helper app after '
                                    'saving your changes')
    current_os = platform.system()
    if current_os == 'Darwin':  # macOS
        subprocess.call(('open', bindings_file))
    elif current_os == 'Windows':  # Windows
        os.startfile(bindings_file)
    else:  # Linux
        subprocess.call(('xdg-open', bindings_file))


if __name__ == "__main__":
    # Called after icon is set up due to threading issues.
    spotify_helper = SpotifyHelper()

    def run_spotify_helper(icon_callback):
        try:
            icon_callback.visible = True
            spotify_helper.run()
        except Exception as e:
            logging.error('{}:{}'.format(e, traceback.format_exc()))
            traceback.print_exc()

    def stop_program(icon_callback):
        icon_callback.stop()
        spotify_helper.stop()

    icon_image = Image.open(os.path.join(os.path.dirname(__file__), 'resources/spo.png'))
    icon = Icon('spotify-helper', icon_image, menu=Menu(
        MenuItem(
            text='Edit bindings',
            action=open_bindings_file),
        Menu.SEPARATOR,
        MenuItem(
            text='Quit',
            action=lambda: stop_program(icon)
        ),
    ))

    # After icon starts running, we start the keyboard listener thread (together with the main
    # Spotify Helper code), since on macOS pystray won't work if pynput runs first, as the latter seems
    # to call a Mac _MainThread function which pystray then tries to call again but is not allowed - running
    # pystray first seems to be ok though.
    icon.run(setup=run_spotify_helper)
