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

import gconf

from jarabe.model.network import GSM_USERNAME_PATH, GSM_PASSWORD_PATH, \
                                 GSM_NUMBER_PATH, GSM_APN_PATH, GSM_PIN_PATH, \
                                 GSM_PUK_PATH


def get_username():
    client = gconf.client_get_default()
    return client.get_string(GSM_USERNAME_PATH) or ''


def get_password():
    client = gconf.client_get_default()
    return client.get_string(GSM_PASSWORD_PATH) or ''


def get_number():
    client = gconf.client_get_default()
    return client.get_string(GSM_NUMBER_PATH) or ''


def get_apn():
    client = gconf.client_get_default()
    return client.get_string(GSM_APN_PATH) or ''


def get_pin():
    client = gconf.client_get_default()
    return client.get_string(GSM_PIN_PATH) or ''


def get_puk():
    client = gconf.client_get_default()
    return client.get_string(GSM_PUK_PATH) or ''


def set_username(username):
    client = gconf.client_get_default()
    client.set_string(GSM_USERNAME_PATH, username)


def set_password(password):
    client = gconf.client_get_default()
    client.set_string(GSM_PASSWORD_PATH, password)


def set_number(number):
    client = gconf.client_get_default()
    client.set_string(GSM_NUMBER_PATH, number)


def set_apn(apn):
    client = gconf.client_get_default()
    client.set_string(GSM_APN_PATH, apn)


def set_pin(pin):
    client = gconf.client_get_default()
    client.set_string(GSM_PIN_PATH, pin)


def set_puk(puk):
    client = gconf.client_get_default()
    client.set_string(GSM_PUK_PATH, puk)
