# Handles the keyboard listening
import logging
import sys
import os
import threading
from collections import deque
from time import sleep

import requests
from pynput import keyboard
from pynput.keyboard import Key, KeyCode


from src.spotify_api.spotify import Spotify
from src.notifications.notif_handler import send_notif
from src.errors.exceptions import AlreadyNotifiedException

bindings_file = os.path.abspath('../bindings.txt')  # TODO reload bindings after file change


class SpotifyHelper:
    def __init__(self):
        try:
            self.spotify = Spotify()
        except requests.exceptions.ConnectionError:
            send_notif('Spotify Helper closed', 'Check you have a working internet connection.')
            sys.exit(1)

        self.currently_pressed_keys = list()
        self.looking_for = {}
        self.methods_to_run = deque([])
        self.has_released_key = True

        self.load_bindings_from_file(bindings_file)

        method_handler_thread = threading.Thread(target=self.check_methods_to_run)
        method_handler_thread.daemon = True
        method_handler_thread.start()

    def load_bindings_from_file(self, file):
        with open(file) as file:
            for line in file:
                method_and_keycodes = line.split('=')

                method = method_and_keycodes[0]  # The method to run
                rest_of_line = method_and_keycodes[1]  # Includes bindings we have to parse

                # Allows comments in the bindings file
                if '#' in rest_of_line:
                    rest_of_line = rest_of_line[:rest_of_line.index('#')]

                bindings = rest_of_line.rstrip()

                if bindings is not '':
                    # Can have multiple bindings split by commas.
                    for binding in bindings.split(','):
                        keys = list()
                        for single_key in binding.split('+'):
                            keys.append(self.get_key_from_string(single_key))

                        keys_tuple = tuple(keys)

                        # looking_for is a dictionary where the keys are the bindings and the values
                        # are all the methods linked to those keys, as you can have multiple bindings
                        # per method and vice versa.

                        if keys_tuple not in self.looking_for.keys():
                            self.looking_for[keys_tuple] = []

                        self.looking_for[keys_tuple].append(method)

    # Runs as a thread, as we don't want operations that might
    # take long (such as calls to the internet) to block keyboard
    # listening.
    def check_methods_to_run(self):
        while True:
            if len(self.methods_to_run) > 0:
                self.run_method(self.methods_to_run.popleft())
            else:
                sleep(0.01)

    def run_method(self, method):
        try:
            getattr(self.spotify, method)()

        except ConnectionError:
            send_notif('Connection Error', 'Internet connection not available')
        except AlreadyNotifiedException:
            pass
        except Exception as e:
            send_notif('Error', 'Something went wrong')
            logging.error(str(e) + ':' + str(e.__traceback__))

    def on_press(self, key):
        # Keys are unique in each binding, as it makes no sense to have ctrl+ctrl+f5, for example.
        # Also prevents the same key being added more than once if held down too long, which happens
        # on some systems.
        if key not in self.currently_pressed_keys:
            self.currently_pressed_keys.append(key)

        for key_tuple, methods in self.looking_for.items():
            # has_released_key avoids running the same methods for the same keyboard
            # press - must release a key to run it again.
            if self.currently_pressed_keys == list(key_tuple) and self.has_released_key:
                for method in methods:
                    self.methods_to_run.append(method)

                self.has_released_key = False

    def on_release(self, key):
        try:
            self.has_released_key = True
            self.currently_pressed_keys.remove(key)

        except ValueError:  # Sometimes it's already empty so raises this exception, to be ignored.
            pass

    # Get pynput key from a string - modifier keys are captured in the try statement,
    # while normal letter keys are obtained from the KeyCode.from_char() method.
    @staticmethod
    def get_key_from_string(key_str):
        try:
            return getattr(Key, key_str)

        except AttributeError:
            return KeyCode.from_char(key_str)

    # Begins the keyboard listener.
    def run(self):
        listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        listener.start()