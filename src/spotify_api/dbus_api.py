# Methods to get media info through DBus.
import logging
import platform
from src.notifications.notif_handler import send_notif

import dbus


# Many of the methods just parse the DBus media output into a standard format.
class DBusApi:
    def __init__(self):
        self.current_os = platform.system()
        self.player = 'org.mpris.MediaPlayer2.Player'

        self.set_dbus_connections()

    def set_dbus_connections(self):
        self.session_bus = dbus.SessionBus()
        self.dbus_connected = False

        try:
            self.spotify_bus = self.session_bus.get_object('org.mpris.MediaPlayer2.spotify',
                                                           '/org/mpris/MediaPlayer2')

            self.interface = dbus.Interface(self.spotify_bus, self.player)
            self.spotify_properties = dbus.Interface(self.spotify_bus,
                                                     'org.freedesktop.DBus.Properties')
            self.metadata = self.spotify_properties.Get(self.player, 'Metadata')

            self.dbus_connected = True

        except dbus.DBusException:
            self.dbus_disconnect()

    # Spotify doesn't support the majority of available properties
    def get_property(self, player_propety):
        return self.spotify_properties.Get(self.player, player_propety)

    # Same as above
    def set_property(self, player_propety, value):
        return self.spotify_properties.Set('org.mpris.MediaPlayer2.Player', player_propety, value)

    def run_method(self, method_str, *args):
        if not self.dbus_connected:
            self.set_dbus_connections()
        if self.dbus_connected:
            try:
                response = getattr(self.interface, method_str)(*args)
                logging.info('Dbus connected with info ' + str(response))
                return response
            except dbus.DBusException:
                logging.info('Dbus disconnected')
                self.dbus_disconnect()

    # def get_info(self, info_str):
    #     return self.ensure_dbus_connection(self.metadata.get, info_str)

    def dbus_disconnect(self):
        self.dbus_connected = False
        send_notif('Spotify closed', 'Open Spotify and try again.')

    # DBus seems to stay behind on songs when changing Spotify contexts, so for now
    # we defalt to using the Web API

    # def get_track_id(self):
    #     return self.get_info('mpris:trackid').split(':')[-1]
    #
    # def get_album(self):
    #     return self.get_info('xesam:album')
    #
    # def get_track(self):
    #     return self.get_info('xesam:title')
    #
    # def get_artist(self):
    #     return str(self.get_info('xesam:artist')[0])
    #
    # def get_art_url(self):
    #     return self.get_info('mpris:artUrl')
    #
    # def get_current_track(self):  # Tries to (partly) emulate a Spotify track object
    #     track = dict()
    #
    #     track['name'] = self.get_track()
    #     track['artists'] = [{'name': self.get_artist()}]
    #     track['album'] = {'name': self.get_album(), 'images': [{'url': self.get_art_url()}]}
    #
    #     return track

    def play_pause(self):
        return self.run_method('PlayPause')

    def next(self):
        return self.run_method('Next')

    def previous(self):
        return self.run_method('Previous')

    # Is the same as pause()
    def stop(self):
        return self.run_method('Stop')

    def pause(self):
        return self.run_method('Pause')

    def play(self):
        return self.run_method('Play')

    # Does nothing
    def seek(self, offset):
        return self.run_method('Seek', offset)

    def open(self, uri):
        return self.run_method('OpenUri', uri)
