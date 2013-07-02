# -*- encoding: utf-8 -*-
# Copyright (C) 2009 Paraguay Educa, Martin Abente
# Copyright (C) 2013 Miguel González
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
import locale
import os.path
from xml.etree.cElementTree import ElementTree
from gettext import gettext as _

import dbus
from gi.repository import GLib
from gi.repository import GConf

from .config import (COUNTRY_CODES_PATH,
                     PROVIDERS_PATH,
                     PROVIDERS_FORMAT_SUPPORTED,
                     GCONF_SP_COUNTRY,
                     GCONF_SP_PROVIDER,
                     GCONF_SP_PLAN)

from jarabe.model import network


def get_connection():
    return network.find_gsm_connection()


def get_modem_settings(callback):
    modem_settings = {}
    connection = get_connection()
    if not connection:
        GLib.idle_add(callback, modem_settings)
        return

    settings = connection.get_settings('gsm')
    for setting in ('username', 'number', 'apn'):
        modem_settings[setting] = settings.get(setting, '')

    # use mutable container for nested function control variable
    secrets_call_done = [False]

    def _secrets_cb(secrets):
        secrets_call_done[0] = True
        if secrets and 'gsm' in secrets:
            gsm_secrets = secrets['gsm']
            modem_settings['password'] = gsm_secrets.get('password', '')
            modem_settings['pin'] = gsm_secrets.get('pin', '')

        callback(modem_settings)

    def _secrets_err_cb(err):
        secrets_call_done[0] = True
        if isinstance(err, dbus.exceptions.DBusException) and \
                err.get_dbus_name() == network.NM_AGENT_MANAGER_ERR_NO_SECRETS:
            logging.error('No GSM secrets present')
        else:
            logging.error('Error retrieving GSM secrets: %s', err)

        callback(modem_settings)

    connection.get_secrets('gsm', _secrets_cb, _secrets_err_cb)


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


class ServiceProviderDatabaseError(Exception):
    pass


def _get_localized_or_default_name(el):
    language_code = locale.getdefaultlocale()[0]
    LANG = language_code[0:2]
    LANG_NS_ATTR = '{http://www.w3.org/XML/1998/namespace}lang'
    tag = el.find('name[@%s="%s"]' % (LANG_NS_ATTR, LANG))
    if tag is None:
        tag = el.find('name')
    if tag is not None:
        name = tag.text
    else:
        name = _('Default')
    return name


class Country(object):
    def __init__(self, idx, code, name):
        self.idx = idx
        self.code = code
        self.name = name


class Provider(object):
    @classmethod
    def from_xml(cls, idx, el):
        name = _get_localized_or_default_name(el)
        return Provider(idx, name)

    def __init__(self, idx, name):
        self.idx = idx
        self.name = name


class Plan(object):
    DEFAULT_NUMBER = '*99#'

    @classmethod
    def from_xml(cls, idx, el):
        name = _get_localized_or_default_name(el)
        username_el = el.find('username')
        password_el = el.find('password')
        kwargs = {
            'apn': el.get('value'),
            'name': name,
            'username': username_el.text if username_el is not None else None,
            'password': password_el.text if password_el is not None else None,
        }
        return Plan(idx, **kwargs)

    def __init__(self, idx, name, apn, username=None, password=None,
                 number=None):
        self.idx = idx
        self.name = name
        self.apn = apn
        self.username = username or ''
        self.password = password or ''
        self.number = number or self.DEFAULT_NUMBER


class ServiceProvidersDatabase(object):
    def __init__(self):
        # Check ISO 3166 alpha-2 country code file exists
        if not os.path.isfile(COUNTRY_CODES_PATH):
            msg = ("Mobile broadband provider database: Country "
                   "codes path %s not found.") % COUNTRY_CODES_PATH
            logging.warning(msg)
            raise ServiceProviderDatabaseError(msg)

        # Check service provider database file exists
        try:
            tree = ElementTree(file=PROVIDERS_PATH)
        except (IOError, SyntaxError), e:
            msg = ("Mobile broadband provider database: Could not read "
                   "provider information %s error=%s") % (PROVIDERS_PATH, e)
            logging.warning(msg)
            raise ServiceProviderDatabaseError(msg)

        # Check service provider da
        self.root = tree.getroot()
        if self.root.get('format') != PROVIDERS_FORMAT_SUPPORTED:
            msg = ("Mobile broadband provider database: Could not "
                   "read provider information. Wrong format.")
            logging.warning(msg)
            raise ServiceProviderDatabaseError(msg)

        language_code = locale.getdefaultlocale()[0]
        self.COUNTRY_CODE = language_code[3:5].lower()
        self.LANG = language_code[0:2]
        self.LANG_NS_ATTR = '{http://www.w3.org/XML/1998/namespace}lang'

        # Load country code label mapping
        codes = {}
        with open(COUNTRY_CODES_PATH) as codes_file:
            for line in codes_file:
                if line.startswith('#'):
                    continue
                code, name = line.split('\t')[:2]
                codes[code.lower()] = name.strip()

        # Populate countries list
        self._countries = self.root.findall('country')
        self._countries.sort(key=lambda x: codes[x.attrib['code']])
        country_codes = [c_el.attrib['code'] for c_el in self._countries]
        self._country_names = [codes[code] for code in country_codes]

        country_code, provider_name, plan_name = self._get_initials()
        country_idx = country_codes.index(country_code)
        self.set_country(country_idx)
        for idx, provider_el in enumerate(self._providers):
            name = _get_localized_or_default_name(provider_el)
            if provider_name == name:
                self.set_provider(idx)
                break
        for idx, plan_el in enumerate(self._plans):
            name = _get_localized_or_default_name(plan_el)
            if plan_name == name:
                self.set_plan(idx)
                break

    def _get_initials(self):
        client = GConf.Client.get_default()
        country_code = client.get_string(GCONF_SP_COUNTRY) or self.COUNTRY_CODE
        provider_name = client.get_string(GCONF_SP_PROVIDER) or ''
        plan_name = client.get_string(GCONF_SP_PLAN)
        return country_code, provider_name, plan_name

    def save(self):
        country_code = self.get_country().code
        provider_name = self.get_provider().name
        plan_name = self.get_plan().name
        client = GConf.Client.get_default()
        client.set_string(GCONF_SP_COUNTRY, country_code)
        client.set_string(GCONF_SP_PROVIDER, provider_name)
        client.set_string(GCONF_SP_PLAN, plan_name)

    def set_country(self, idx):
        self._current_country = idx
        self._update_providers()
        self.set_provider(0)

    def set_provider(self, idx):
        self._current_provider = idx
        self._update_plans()
        self.set_plan(0)

    def set_plan(self, idx):
        self._current_plan = idx

    def _get_country_element(self):
        return self._countries[self._current_country]

    def _update_providers(self):
        self._providers = [
            provider
            for provider in self._get_country_element().findall('provider')
            if provider.find('.//gsm')]
        return self._providers

    def _get_provider_element(self):
        if self._providers == []:
            return None
        else:
            return self._providers[self._current_provider]

    def _update_plans(self):
        self._plans = []
        provider_el = self._get_provider_element()
        if provider_el is None:
            self._plans = []
        else:
            self._plans = provider_el.findall('.//apn')
        return self._plans

    def get_countries(self):
        countries = []
        for idx, country_el in enumerate(self._countries):
            country = Country(idx, country_el.attrib['code'],
                              self._country_names[idx])
            countries.append(country)
        return countries

    def get_providers(self):
        providers = []
        for idx, provider_el in enumerate(self._providers):
            provider = Provider.from_xml(idx, provider_el)
            providers.append(provider)
        return providers

    def get_plans(self):
        plans = []
        for idx, apn_el in enumerate(self._plans):
            plan = Plan.from_xml(idx, apn_el)
            plans.append(plan)
        return plans

    def get_country(self):
        country_el = self._countries[self._current_country]
        return Country(self._current_country, country_el.attrib['code'],
                       self._country_names[self._current_country])

    def get_provider(self):
        if self._providers == []:
            return None
        else:
            return Provider.from_xml(self._current_provider,
                                     self._providers[self._current_provider])

    def get_plan(self):
        if self._plans == []:
            return None
        else:
            return Plan.from_xml(self._current_plan,
                                 self._plans[self._current_plan])
