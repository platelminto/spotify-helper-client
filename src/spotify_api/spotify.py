import datetime
import logging
import platform
import shelve
import configparser

from ..notifications.notif_handler import send_notif, send_notif_with_web_image
from ..spotify_api.web_api import WebApi
from ..errors.exceptions import AlreadyNotifiedException

current_os = platform.system()

if current_os == 'Darwin':
    from ..spotify_api.applescript_api import AppleScriptApi

elif current_os == 'Linux':
    from ..spotify_api.dbus_api import DBusApi

elif current_os == 'Windows':
    from src.spotify_api.windows_api import WindowsApi


def get_device_name():
    return platform.uname()[1]


class Spotify:

    def __init__(self):
        config = configparser.ConfigParser()
        config.read('../config.ini')
        client_id = config['authentication']['client_id']

        redirect_uri = 'https://platelminto.eu.pythonanywhere.com/users/registering'

        scope_list = ['user-library-read', 'user-library-modify', 'playlist-modify-public',
                      'user-modify-playback-state', 'user-read-playback-state', 'playlist-modify-private']

        self.web_api = WebApi(scope_list=scope_list, client_id=client_id,
                              redirect_uri=redirect_uri)
        if current_os == 'Darwin':
            self.local_api = AppleScriptApi()

        elif current_os == 'Linux':
            self.local_api = DBusApi()

        elif current_os == 'Windows':
            self.local_api = WindowsApi()

        self.repeat_states = ['track', 'context', 'off']

    def next(self):
        self.try_local_method_then_web('next', 'me/player/next', 'post')

    def previous(self):
        self.try_local_method_then_web('previous', 'me/player/previous', 'post')

    # Starting a song over means setting its current playing-time to 0.
    def restart(self):
        self.try_local_method_then_web('restart', 'me/player/seek', 'put', params={'position_ms': 0})

    def pause(self):
        self.try_local_method_then_web('pause', 'me/player/pause', 'put')

    def toggle_play(self):
        try:
            self.local_api.play_pause()

        except AttributeError:
            is_playing = self.is_playing()

            if is_playing:
                self.pause()
            else:
                self.play()

    def play(self):
        # Web API method for 'play' is currently broken, so instead we use the 'transfer playback'
        # endpoint to "transfer" playback to the already active device, which allows us to give it
        # a 'play' parameter to resume playback. This is done in call_play_method() to ensure
        # an API call is made only if a local API isn't available.
        self.try_local_method_then_web('play', 'me/player', 'put')

    # This does not toggle save, so if a song is already saved it doesn't remove it.
    def save(self):
        song = self.get_current_song_info()[0]

        if not self.is_saved(self.get_current_song_id()):
            self.add_songs_to_library(self.get_current_song_id())
            send_notif_with_web_image('Successfully saved',
                                      'Added ' + song + ' to library.',
                                      self.currently_playing_art_url())
        else:
            send_notif_with_web_image('Already saved',
                                      song + ' was already in library.',
                                      self.currently_playing_art_url())

    # This also doesn't toggle, so unsaving a song that isn't saved just does nothing.
    def unsave(self):
        song = self.get_current_song_info()[0]

        self.remove_songs_from_library(self.get_current_song_id())
        send_notif_with_web_image('Successfully unsaved',
                                  'Removed ' + song + ' from library.',
                                  self.currently_playing_art_url())

    def toggle_shuffle(self):
        def change_shuffle_with_web_api(response):
            toggled_shuffle = not response.json().get('shuffle_state')

            self.call_web_method('me/player/shuffle', 'put', params={'state': toggled_shuffle})
            send_notif('Shuffle toggled',
                       'Shuffle now {}'.format('enabled' if toggled_shuffle else 'disabled'))

        self.try_local_method_then_web('toggle_shuffle', 'me/player', 'get', change_shuffle_with_web_api)

    def toggle_repeat(self):
        # There are 3 repeat states (track, context, off), so we cannot simply toggle
        # on and off, we must switch between them.
        def change_state_with_web_api(response):
            repeat_state = response.json().get('repeat_state')
            next_state = self.repeat_states[self.repeat_states.index(repeat_state) - 1]
            self.call_web_method('me/player/repeat', 'put', params={'state': next_state})
            send_notif('Repeat changed',
                       'Repeating is now set to: {}'.format(self.get_shuffle_and_repeat_state()[1]))

        self.try_local_method_then_web('toggle_repeat', 'me/player', 'get', change_state_with_web_api)

    def play_on_current_device(self):
        self.call_web_method('me/player', 'put', payload={'device_ids': [self.get_current_device_id()]})

    def toggle_save_monthly_playlist(self):
        song_id = self.get_current_song_id()
        is_in_playlist = self.is_in_monthly_playlist(song_id, 0)

        song = self.get_current_song_info()[0]

        if is_in_playlist:
            self.remove_song_from_monthly_playlist(song_id)
            send_notif_with_web_image('Successfully removed',
                                      'Removed ' + song + ' from playlist.',
                                      self.currently_playing_art_url())
        else:
            self.add_song_to_monthly_playlist(song_id)
            send_notif_with_web_image('Successfully added',
                                      'Added ' + song + ' to playlist.',
                                      self.currently_playing_art_url())

    def show_current_song(self):
        song, artists, album = self.get_current_song_info()
        send_notif_with_web_image(song, ', '.join(artists) + ' - ' + album, self.currently_playing_art_url())

    def add_song_to_monthly_playlist(self, song_id):
        return self.call_web_method(
            'users/{}/playlists/{}/tracks'.format(self.get_user_id(), self.get_monthly_playlist_id()),
            'post',
            params={'uris': 'spotify:track:{}'.format(song_id)}
        )

    # The API is inconsistent so adding and deleting are different.
    def remove_song_from_monthly_playlist(self, song_id):
        return self.call_web_method(
            'users/{}/playlists/{}/tracks'.format(self.get_user_id(), self.get_monthly_playlist_id()),
            'delete',
            payload={'tracks': [{'uri': 'spotify:track:{}'.format(song_id)}]}
        )

    def get_current_song_info(self):
        def get_track_from_web_api(response):
            return response.json().get('item')

        track = self.try_local_method_then_web('get_current_track', 'me/player', 'get', get_track_from_web_api)

        song = track.get('name')
        artists = [x.get('name') for x in track.get('artists')]
        album = track.get('album').get('name')

        return song, artists, album

    def get_monthly_playlist_id(self):
        now = datetime.datetime.now()
        month, year = now.strftime('%B'), str(now.year)

        with shelve.open('../.info') as shelf:
            # Check if months and years are available and are correct, if not, update
            # playlist id.
            if 'month' not in shelf or shelf['month'] != month:
                shelf['month'] = month
                shelf['monthly_playlist_id'] = self.__fetch_playlist_id(month, year, 0)
            if 'year' not in shelf or shelf['year'] != year:
                shelf['year'] = year
                shelf['monthly_playlist_id'] = self.__fetch_playlist_id(month, year, 0)
            return shelf['monthly_playlist_id']

    def get_user_id(self):
        with shelve.open('../.info') as shelf:
            if 'user_id' not in shelf:
                shelf['user_id'] = self.__fetch_user_id()
            return shelf['user_id']

    def __fetch_user_id(self):
        return self.call_web_method('me', 'get').json().get('id')

    def __fetch_playlist_id(self, month, year, offset):
        response = self.call_web_method('me/playlists', 'get').json()

        playlist_id = None

        for playlist in response.get('items'):
            if str(playlist.get('name')).lower() == '{} {}'.format(month, year).lower():
                playlist_id = playlist.get('id')

        if playlist_id is not None:
            return playlist_id
        # Check through all pages to look for our playlist
        elif playlist_id is None and Spotify.is_paging(response):
            return self.__fetch_playlist_id(month, year, offset + response.get('limit'))
        else:
            return self.call_web_method(
                'users/{}/playlists'.format(self.get_user_id()),
                'post',
                payload={'name': '{} {}'.format(month.capitalize(), year)}
            ).json().get('id')

    def is_in_monthly_playlist(self, song_id, offset):  # TODO refactor into a paging-handling method
        playlist_tracks = self.call_web_method(
            'playlists/{}/tracks'.format(self.get_monthly_playlist_id()),
            'get',
            params={'offset': offset}
        ).json()

        exists = len([x for x in playlist_tracks.get('items') if x.get('track').get('id') == song_id]) > 0

        # Run this same method with the next set of results
        if not exists and Spotify.is_paging(playlist_tracks):
            return self.is_in_monthly_playlist(song_id, offset + playlist_tracks.get('limit'))
        else:
            return exists

    # If a response contains a 'next', it means there are more results that we will then have to request.
    @staticmethod
    def is_paging(json):
        return json.get('next') is not None

    def add_songs_to_library(self, *song_ids):
        return self.call_web_method('me/tracks', 'put', payload={'ids': song_ids})
        # return self.web_api.put('me/tracks', payload={'ids': song_ids})

    def get_available_devices(self):
        return self.call_web_method('me/player/devices', 'get').json().get('devices')

    # The active device is the one currently playing music, not necessarily the one currently
    # being used by the user (for example, music could be playing through a phone, but the user
    # is on their computer).
    def get_active_device(self):
        devices = self.get_available_devices()
        try:
            return next(device for device in devices if device.get('is_active'))

        except StopIteration:
            return None

    def get_current_song_id(self):
        def get_id_from_web_api(response):
            return response.json().get('item').get('id')

        return self.try_local_method_then_web('get_track_id', 'me/player', 'get', get_id_from_web_api, 'get')

    def is_saved(self, song_id):
        # Returns a list of boolean values matching each id we give it; with only one, we get the first and only value
        return self.call_web_method('me/tracks/contains', 'get', params={'ids': [song_id]}).json()[0]

    def currently_playing_art_url(self, track=None, quality=2):
        if track is None:
            try:
                track = self.try_local_method_then_web('', 'me/player', 'get').json().get('item')

            except ConnectionError:
                return None

        images = track.get('album').get('images')

        # We don't need very high quality images for notifications, so we get
        # the images at the end of the list (which is ordered by quality).
        return images[-quality if len(images) >= 2 else 0].get('url')

    def remove_songs_from_library(self, *song_ids):
        return self.call_web_method('me/tracks', 'delete', payload={'ids': song_ids})

    def is_playing(self):
        return self.try_local_method_then_web('is_playing', 'me/player', 'get').json().get('is_playing')

    def get_shuffle_and_repeat_state(self):
        response = self.call_web_method('me/player', 'get').json()
        return response.get('shuffle_state'), response.get('repeat_state')

    def get_current_device_id(self):
        return next(x.get('id') for x in self.call_web_method('me/player/devices', 'get').json().get('devices') if
                    x.get('name') == get_device_name())

    # For every method, we first try a local API, and then move onto the Web API as a fallback.
    def try_local_method_then_web(self, local_method_name, web_method_name, rest_function_name,
                                  do_with_web_result=lambda x: x, params=None, payload=None):
        try:
            return getattr(self.local_api, local_method_name)()

        except AttributeError:
            return do_with_web_result(
                self.call_web_method(web_method_name, rest_function_name, params=params, payload=payload))

    def call_web_method(self, method, rest_function_name, params=None, payload=None):
        # 'get' functions don't have payloads.
        if rest_function_name == 'get':
            response = getattr(self.web_api, rest_function_name)(method, params=params)
        # get_active_devices() is here to avoid unnecessarily calls if not using the Web API when calling play(),
        # which has no payload.
        elif method == 'me/player' and rest_function_name == 'put':
            response = getattr(self.web_api, rest_function_name)(method, params=params,
                                                                 payload={
                                                                     'device_ids': [self.get_active_device().get('id')],
                                                                     'play': True} if payload is None else payload)
        else:
            response = getattr(self.web_api, rest_function_name)(method, params=params, payload=payload)

        status_code = response.status_code

        # 'get' with no further method returns information about the user's playback.
        # 204s are usually successes, but in this case it means no active devices exist.
        if status_code == 204 and method == 'me/player' and rest_function_name == 'get':
            send_notif('Error', 'No device found')
            raise AlreadyNotifiedException
        elif 200 <= status_code <= 299:  # These responses are fine
            return response

        info = response.json()

        # Player errors also return a reason, which we use to notify with the appropriate message from config.ini,
        # though it appears nearly all reasons will always be UNKNOWN, an issue with the Spotify API.
        if 'error' in info and 'reason' in info.get('error'):
            reason = info.get('error').get('reason')
            config = configparser.ConfigParser()
            config.read('../config.ini')
            response = config['player_error_strings'][reason]
            send_notif('Player Error', response)
            raise AlreadyNotifiedException

        if status_code >= 300:
            logging.warning('Request {} failed with code {}'.format(response.text, status_code))
            logging.warning('Fail message: {}'.format(response.json().get('error').get('message')))
            raise Exception

        return response

    def toggle_save(self):
        is_saved = self.is_saved(self.get_current_song_id())

        if is_saved:
            self.unsave()
        else:
            self.save()


if __name__ == '__main__':
    spotify = Spotify()
