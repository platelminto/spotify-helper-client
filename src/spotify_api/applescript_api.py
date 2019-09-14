# Methods to get media info through AppleScript.
import logging
import subprocess


# The AppleScript API uses macOS's AppleScript to send commandline instructions to Spotify, which natively
# supports AppleScript.
class AppleScriptApi:

    @staticmethod
    def run_command(command):
        # Pipe output to the variable
        result = subprocess.run(" ".join(['osascript', '-e',
                                          "'tell application \"Spotify\" to {}\'".format(command)]),
                                stdout=subprocess.PIPE, shell=True, stderr=subprocess.PIPE)

        if result.returncode is not 0:
            logging.warning('AppleScript API failed to run command {} with stdout: {} and '
                            'stderr: {}, used Web API instead'.format(command, result.stdout, result.stderr))
            raise AttributeError

        return result.stdout.decode('utf-8').rstrip()  # Returns command's result

    @staticmethod
    def get_track_id():
        result = AppleScriptApi.run_command('return id of current track as string')

        return result.split(':')[-1]  # Ignore other information presented

    @staticmethod
    def get_album():
        return AppleScriptApi.run_command('return album of current track')

    @staticmethod
    def get_track():
        return AppleScriptApi.run_command('return name of current track')

    @staticmethod
    def get_artist():
        return AppleScriptApi.run_command('return artist of current track')

    @staticmethod
    def get_art_url():
        return AppleScriptApi.run_command('return artwork url of current track')

    @staticmethod
    def get_current_track():
        track = dict()

        # This specific format for the track is followed by the other local APIs.

        track['name'] = AppleScriptApi.get_track()
        track['artists'] = [{'name': AppleScriptApi.get_artist()}]
        track['album'] = {'name': AppleScriptApi.get_album(), 'images': [{'url': AppleScriptApi.get_art_url()}]}

        return track

    @staticmethod
    def play_pause():
        return AppleScriptApi.run_command('playpause')

    @staticmethod
    def next():
        return AppleScriptApi.run_command('next track')

    @staticmethod
    def previous():
        return AppleScriptApi.run_command('previous track')

    @staticmethod
    def stop():
        return AppleScriptApi.run_command('pause')

    @staticmethod
    def pause():
        return AppleScriptApi.run_command('pause')

    @staticmethod
    def play():
        return AppleScriptApi.run_command('play')

    @staticmethod
    def toggle_repeat():
        return AppleScriptApi.run_command('set repeating to not repeating')  # Cannot switch to song-repeat

    @staticmethod
    def toggle_shuffle():
        return AppleScriptApi.run_command('set shuffling to not shuffling')
