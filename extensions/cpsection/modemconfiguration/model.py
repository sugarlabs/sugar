# Copyright (C) 2009 Paraguay Educa, Martin Abente
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  US

import logging

import dbus
import gtk

from jarabe.model import network


def get_connection():
    return network.find_gsm_connection()


def get_modem_settings():
    modem_settings = {}
    connection = get_connection()
    if not connection:
        return modem_settings

    settings = connection.get_settings('gsm')
    for setting in ('username', 'number', 'apn'):
        modem_settings[setting] = settings.get(setting, '')

    # use mutable container for nested function control variable
    secrets_call_done = [False]

    def _secrets_cb(secrets):
        secrets_call_done[0] = True
        if not secrets or not 'gsm' in secrets:
            return

        gsm_secrets = secrets['gsm']
        modem_settings['password'] = gsm_secrets.get('password', '')
        modem_settings['pin'] = gsm_secrets.get('pin', '')

    def _secrets_err_cb(err):
        secrets_call_done[0] = True
        if isinstance(err, dbus.exceptions.DBusException) and \
                err.get_dbus_name() == network.NM_AGENT_MANAGER_ERR_NO_SECRETS:
            logging.debug('No GSM secrets present')
        else:
            logging.error('Error retrieving GSM secrets: %s', err)

    # must be called asynchronously as this re-enters the GTK main loop
    connection.get_secrets('gsm', _secrets_cb, _secrets_err_cb)

    # wait til asynchronous execution completes
    while not secrets_call_done[0]:
        gtk.main_iteration()

    return modem_settings


def _set_or_clear(_dict, key, value):
    """Update a dictionary value for a specific key. If value is None or
    zero-length, but the key is present in the dictionary, delete that
    dictionary entry."""
    if value:
        _dict[key] = value
        return

    if key in _dict:
        del _dict[key]


def set_modem_settings(modem_settings):
    username = modem_settings.get('username', '')
    password = modem_settings.get('password', '')
    number = modem_settings.get('number', '')
    apn = modem_settings.get('apn', '')
    pin = modem_settings.get('pin', '')

    connection = get_connection()
    if not connection:
        network.create_gsm_connection(username, password, number, apn, pin)
        return

    settings = connection.get_settings()
    gsm_settings = settings['gsm']
    _set_or_clear(gsm_settings, 'username', username)
    _set_or_clear(gsm_settings, 'password', password)
    _set_or_clear(gsm_settings, 'number', number)
    _set_or_clear(gsm_settings, 'apn', apn)
    _set_or_clear(gsm_settings, 'pin', pin)
    connection.update_settings(settings)
