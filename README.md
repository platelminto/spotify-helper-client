## spotify-helper
Provides various utility methods to interact with Spotify, mostly through the ability to assign keyboard shortcuts to most Spotify functions. These are editable in the `bindings.txt` file. Run `taskbar_icon.py` with python 3 to start the script (has to be run as sudo on macOS for keyboard access), which should then create an icon in your taskbar.

The program first tries to directly interact with the Spotify client, and then falls back on using the Web API; some methods are only available using the Web API.


### Dependencies

To install all the dependencies needed, find the appropriate requirements text file for your OS in `requirements/`, and run:

`pip install -r requirements.txt`


#### General dependencies

- [Requests](http://docs.python-requests.org/en/master/) - to make RESTful requests easily.
- [pynput](https://pythonhosted.org/pynput/) - for multiplatform keyboard-input parsing.
- [pystray](https://pypi.org/project/pystray/) - for multiplatform tray-icon creation.

#### Windows-specific dependencies

- [pywin32](https://pypi.python.org/pypi/pywin32) - to be able to send notifications on Windows.

#### Linux-specific dependencies

- gi - needed for the tray icon. This dependency should already be installed on most Linux systems, but if you are using a virtual environment, make sure to run this command if you find certain python requirements failing to install via pip, then try again:

```$ sudo apt install libgirepository1.0-dev python3-cairo python-cairo```
