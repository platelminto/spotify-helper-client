# Handles the keyboard listening
import ast
import configparser
import logging
import sys
import os
import threading
import traceback
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
        self.has_released_key = True

        self.load_bindings_from_file(bindings_file)
        self.atomic_method_groups = SpotifyHelper.get_atomic_method_groups()
        self.method_group_thread_queues = self.get_method_group_thread_queues()

    def load_bindings_from_file(self, file):
        with open(file) as file:
            for line in file:
                method_and_keycodes = line.split('=')

                method = method_and_keycodes[0]  # The method to run
                rest_of_line = method_and_keycodes[1]  # Includes bindings we have to parse

                # Allows inline comments in the bindings file
                if '#' in rest_of_line:
                    rest_of_line = rest_of_line[:rest_of_line.index('#')]

                bindings = rest_of_line.rstrip()

                if bindings != '':
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

    # Some methods can run at the same time, others cannot: we group
    # them as 'independent', which can be run in any order, 'self_dependent',
    # which have to be run sequentially from themselves, and any amount of
    # other groups, whose methods have to run sequentially from each other.
    def get_method_group_thread_queues(self):
        method_group_thread_queues = dict()
        for group in self.atomic_method_groups:
            # If it's self dependent, make a new thread group for each method
            if group == 'self_dependent':
                for method in self.atomic_method_groups[group]:
                    method_group_thread_queues[method] = deque([])
                    self.start_queue_listening_thread(method_group_thread_queues[method])
            # If it's a custom group, set a single queue for that entire group
            elif group != 'independent':
                method_group_thread_queues[group] = deque([])
                self.start_queue_listening_thread(method_group_thread_queues[group])

        return method_group_thread_queues

    # Return a dict with each atomic_group (independent, self_dependent, etc.)
    # connected to a list of the methods assigned to it.
    @staticmethod
    def get_atomic_method_groups():
        thread_groups = dict()

        config = configparser.ConfigParser()
        config.read('../config.ini')
        for group in config['method_groups']:
            thread_groups[group] = ast.literal_eval(config['method_groups'][group])

        return thread_groups

    def start_queue_listening_thread(self, queue):
        threading.Thread(target=self.check_methods_to_run,
                         args=(queue,),  # A singleton tuple
                         daemon=True).start()

    def queue_method(self, method):
        def get_method_group(method):
            for group in self.atomic_method_groups:
                if method in self.atomic_method_groups[group]:
                    return group

        # Independent groups send just that method to a thread to be run
        if method in self.get_atomic_method_groups()['independent']:
            self.start_queue_listening_thread(deque([method]))
        # Self-dependent & custom groups add their method to the appropriate queue
        elif method in self.get_atomic_method_groups()['self_dependent']:
            self.method_group_thread_queues[method].append(method)
        else:
            self.method_group_thread_queues[get_method_group(method)].append(method)

    # Given a queue, keep checking it, running methods in the order
    # they show up.
    def check_methods_to_run(self, method_queue):
        while True:
            if len(method_queue) > 0:
                self.run_method(method_queue.popleft())
            else:
                # If there are no operations, we don't want to be checking too often
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
            logging.error('{}:{}'.format(e, traceback.format_exc()))

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
                    self.queue_method(method)

                self.has_released_key = False

    def on_release(self, key):
        self.has_released_key = True

        # We ignore the key argument as dead/modified keys (e.g. shift+letter) can
        # pollute the currently_pressed_keys list.
        try:
            self.currently_pressed_keys.pop()

        except IndexError:  # Sometimes it's already empty so raises this exception, to be ignored.
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
        self.listener = keyboard.Listener(
                on_press=self.on_press,
                on_release=self.on_release)
        self.listener.start()

    def stop(self):
        self.listener.stop()


if __name__ == '__main__':
    SpotifyHelper().run()
