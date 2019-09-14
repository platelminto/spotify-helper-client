# Handles the authentication and communication with the Spotify Web API.
import logging
import os
import shelve
import sys
import uuid

import requests
import time
import webbrowser
import json

from ..notifications.notif_handler import send_notif


class WebApi:

    # This follows the 'Authorization Code Flow' path set out by
    # https://developer.spotify.com/documentation/general/guides/authorization-guide/#authorization-code-flow.
    def __init__(self, scope_list, client_id, redirect_uri):
        self.api_url = 'https://api.spotify.com/v1/'
        self.authorize_access_url = 'https://accounts.spotify.com/authorize/'
        self.register_user_url = 'https://platelminto.eu.pythonanywhere.com/users/complete'
        self.refresh_token_url = 'https://platelminto.eu.pythonanywhere.com/users/refresh'

        self.scope_list = scope_list
        self.client_id = client_id
        self.redirect_uri = redirect_uri

        # Load authentication tokens, and if they do checks
        # whether they need to be refreshed.
        self.load_auth_values()
        self.check_for_refresh_token(self.expiry_time)

    # Called when registering as a new user
    def get_auth_info(self):
        # If we are new, re-do entire auth process.
        with shelve.open('../.info') as shelf:
            shelf.clear()
            new_uuid = uuid.uuid4()
            shelf['uuid'] = new_uuid
            self.uuid = shelf['uuid']

        current_time = time.time()
        self.generate_auth_code()
        info = self.get_access_info()

        self.save_auth_values(info.get('access_token'), info.get('refresh_token'),
                              current_time + info.get('expires_in'))

    # The authorization keys need to be refreshed every once in a while
    def check_for_refresh_token(self, expiry_time):
        if time.time() > expiry_time:
            self.refresh_tokens()

    # This is how the user can authenticate themselves and must follow the instructions
    # in the README.
    def generate_auth_code(self):
        params = {'client_id': self.client_id, 'response_type': 'code', 'state': self.uuid,
                  'redirect_uri': self.redirect_uri,
                  'scope': ' '.join(self.scope_list)}

        r = requests.get(self.authorize_access_url, params=params)
        webbrowser.open_new(r.url)

    def get_access_info(self):
        timeout = time.time()

        while time.time() < timeout + 120:  # We spend 2 minutes waiting for auth confirmation
            response = requests.post(self.register_user_url,
                                     json={'uuid': str(self.uuid)})
            if response.status_code == 200:
                logging.info('initial authentication done.')
                send_notif('Success', 'You are now authenticated.')
                return response.json()

            time.sleep(3)

        send_notif('Could not authenticate', 'Spotify Helper closed.')
        sys.exit('Could not authenticate')

    # Gets the new tokens after previous ones expire, following the format described by
    # the Spotify authorization guide.
    def refresh_tokens(self):
        payload = {'grant_type': 'refresh_token', 'refresh_token': self.refresh_token,
                   'uuid': str(self.uuid)}
        obtained_time = time.time()

        try:
            r = requests.post(self.refresh_token_url, json=payload, timeout=4)

        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
            raise ConnectionError

        # 403 indicates the user UUID is not registered on the server,
        if r.status_code == 403:
            send_notif('Authentication error', 'Please re-authenticate, or try restarting the app.')
            self.get_auth_info()
            logging.warning('Authentication refresh failed, info: ' + str(r.content))
            return  # Values get saved in get_auth_info()

        # If we need additional permissions and have added them to the scope, the
        # old keys will not work, and we need new authentication info.
        # 400-499 means there is a general user error, so we start anew with
        # the authentication process.
        if (400 <= r.status_code < 500) or \
                (not set(r.json().get('scope').split(' ')).issuperset(set(self.scope_list))):
            self.get_auth_info()
            return

        info = r.json()

        if 'refresh_token' in info:
            self.refresh_token = info.get('refresh_token')

        self.save_auth_values(info.get('access_token'), self.refresh_token,
                              obtained_time + info.get('expires_in'))
        self.load_auth_values()

    def save_auth_values(self, access_token, refresh_token, expiry_time):
        with shelve.open('../.info') as shelf:
            shelf['access_token'] = access_token
            shelf['refresh_token'] = refresh_token
            shelf['expiry_time'] = expiry_time

        self.load_auth_values()

    def load_auth_values(self):
        try:
            with shelve.open('../.info') as shelf:
                self.uuid = shelf['uuid']
                self.access_token = shelf['access_token']
                self.refresh_token = shelf['refresh_token']
                self.expiry_time = shelf['expiry_time']
        except KeyError:
            self.get_auth_info()

        logging.info('Authenticated from file')

    # The authorization values need to be in a specified header.
    def get_access_header(self):
        self.check_for_refresh_token(self.expiry_time)

        return {'Authorization': 'Bearer ' + self.access_token}

    @staticmethod
    def check_status_code(r):
        code = r.status_code

        # These codes are error codes.
        if code >= 300:
            logging.warning('Request failed with code ' + code)
            logging.warning('Fail message: ' + r.json().get('error').get('message'))
            if not (code == 403):
                raise Exception

        return r

    # The following functions are wrappers around requests' basic rest functions.

    def get(self, endpoint, params=None, timeout=4, retry=1):
        try:
            return self.check_status_code(requests.get(self.api_url + endpoint,
                                                       params=params, headers=self.get_access_header(),
                                                       timeout=timeout))

        except requests.exceptions.ConnectionError:
            if retry is not 0:
                return self.get(endpoint, params, timeout, retry - 1)
        except requests.exceptions.ReadTimeout:
            pass

        raise ConnectionError

    def post(self, endpoint, params=None, payload=None, timeout=4, retry=1):
        try:
            return self.check_status_code(requests.post(self.api_url + endpoint,
                                                        data=json.dumps(payload), params=params,
                                                        headers=self.get_access_header(),
                                                        timeout=timeout))

        except requests.exceptions.ConnectionError:
            if retry is not 0:
                return self.post(endpoint, params, payload, timeout, retry - 1)
        except requests.exceptions.ReadTimeout:
            pass

        raise ConnectionError

    def put(self, endpoint, params=None, payload=None, timeout=4, retry=1):
        try:
            return self.check_status_code(requests.put(self.api_url + endpoint,
                                                       data=json.dumps(payload), params=params,
                                                       headers=self.get_access_header(),
                                                       timeout=timeout))

        except requests.exceptions.ConnectionError:
            if retry is not 0:
                return self.put(endpoint, params, payload, timeout, retry - 1)
        except requests.exceptions.ReadTimeout:
            pass

        raise ConnectionError

    def delete(self, endpoint, params=None, payload=None, timeout=4, retry=1):
        try:
            return self.check_status_code(requests.delete(self.api_url + endpoint,
                                                          data=json.dumps(payload), params=params,
                                                          headers=self.get_access_header(),
                                                          timeout=timeout))

        except requests.exceptions.ConnectionError:
            if retry is not 0:
                return self.delete(endpoint, params, payload, timeout, retry - 1)
        except requests.exceptions.ReadTimeout:
            pass

        raise ConnectionError
