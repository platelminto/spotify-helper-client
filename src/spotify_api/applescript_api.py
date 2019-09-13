# Methods to get media info through AppleScript.

import subprocess


# The AppleScript API uses macOS's AppleScript to send commandline instructions to Spotify, which natively
# supports AppleScript.
class AppleScriptApi:

    @staticmethod
    def run_command(command):
        result = subprocess.run(['osascript', '-e',
                                'tell application "Spotify" to ' + command],
                                stdout=subprocess.PIPE)  # Pipe output to the variable

        if result.returncode is not 0:
            raise NameError

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
        return AppleScriptApi.run_command('set repeating to not repeating')  # TODO check this on mac

    @staticmethod
    def toggle_shuffle():
        return AppleScriptApi.run_command('set shuffling to not shuffling')
