## spotify-helper
Provides various utility methods to interact with Spotify, mostly through the ability to assign keyboard shortcuts to most Spotify functions. These are editable in the `bindings.txt` file. Run `taskbar_icon.py` with python 3 from `src/main` to start the script (has to be run as sudo on macOS for keyboard access).

The program first tries to directly interact with the Spotify client (unavailable on Windows), and then falls back on using the Web API; some methods are only available using the Web API.


### Dependencies

To install all the dependencies needed, find the appropriate requirements text file for your OS in `requirements/`, and run:

`pip install -r requirements.txt`


#### General dependencies

- [Requests](http://docs.python-requests.org/en/master/) - to communicate easily with the Spotify API service.
- [pynput](https://pythonhosted.org/pynput/) - to read keyboard input regardless of platform.

#### Windows-specific dependencies

- [pywin32](https://pypi.python.org/pypi/pywin32) - to be able to send notifications on Windows.

#### Linux-specific dependencies

- [dbus-python](https://pypi.org/project/dbus-python) - to be able to interact with the Spotify client. **This dependency should already be installed on most Linux systems**, but if it isn't available, either install it from PyPI (`pip install dbus-python`) or, if you are using a virtual environment, copy the dbus python files from your system into the virtual environment's lib folder (as described [here](https://stackoverflow.com/a/23237728)).

- gi - needed for the tray icon. **This dependency should also be installed on most Linux systems, as it is very integrated with each Linux setup**; because of this, you cannot get it off of PyPI, so if you are using a virtual environment, follow the steps for copying dbus pyhton files (you only have to copy the `gi` folder, there are no `.so` files).
