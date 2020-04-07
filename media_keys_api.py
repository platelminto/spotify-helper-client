from pynput.keyboard import Controller, KeyCode

# Just uses the virtual keys for media control, applies to Windows
# (available at https://docs.microsoft.com/en-us/windows/win32/inputdev/virtual-key-codes).
class MediaKeysApi:

    def __init__(self):
        self.keyboard = Controller()

    def send_key(self, keycode):
        self.keyboard.press(KeyCode.from_vk(keycode))
        self.keyboard.release(KeyCode.from_vk(keycode))

    def play_pause(self):
        self.send_key(173)

    def next(self):
        self.send_key(176)

    def previous(self):
        self.send_key(177)
