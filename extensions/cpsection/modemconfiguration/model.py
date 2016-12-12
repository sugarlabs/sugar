# -*- encoding: utf-8 -*-
# Copyright (C) 2009 Paraguay Educa, Martin Abente
# Copyright (C) 2013 Miguel González
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import locale
from xml.etree.cElementTree import ElementTree
from gettext import gettext as _

import dbus
from gi.repository import GLib
from gi.repository import Gio

from jarabe.model import network


PROVIDERS_PATH = "/usr/share/mobile-broadband-provider-info/"\
                 "serviceproviders.xml"

PROVIDERS_FORMAT_SUPPORTED = "2.0"
COUNTRY_CODES_PATH = "/usr/share/zoneinfo/iso3166.tab"

CONF_GSM_DIR = 'org.sugarlabs.network.gsm'
CONF_SP_COUNTRY = 'country'
CONF_SP_PROVIDER = 'provider'
CONF_SP_PLAN = 'plan'


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


class ServiceProvidersError(Exception):
    pass


def _get_name(el):
    language_code = locale.getdefaultlocale()[0]

    if language_code is None:
        tag = None
    else:
        lang = language_code.split('_')[0]
        lang_ns_attr = '{http://www.w3.org/XML/1998/namespace}lang'

        tag = el.find('name[@%s="%s"]' % (lang_ns_attr, lang))

    if tag is None:
        tag = el.find('name')

    name = tag.text if tag is not None else None
    return name


class Country(object):
    def __init__(self, idx, code, name):
        self.idx = idx
        self.code = code
        self.name = name


class Provider(object):
    @classmethod
    def from_xml(cls, idx, el):
        name = _get_name(el)
        return Provider(idx, name)

    def __init__(self, idx, name):
        self.idx = idx
        self.name = name


class Plan(object):
    DEFAULT_NUMBER = '*99#'

    @classmethod
    def from_xml(cls, idx, el):
        name = _get_name(el) or _('Plan #%s' % (idx + 1))
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


class CountryCodeParser(object):
    def _load_country_names():
        # Load country code label mapping
        data = {}
        try:
            with open(COUNTRY_CODES_PATH) as codes_file:
                for line in codes_file:
                    if line.startswith('#'):
                        continue
                    code, name = line.split('\t')[:2]
                    data[code.lower()] = name.strip()

        except IOError:
            # Error reading ISO 3166 alpha-2 country code file
            msg = ("Mobile broadband provider database: Country "
                   "codes path %s not found.") % COUNTRY_CODES_PATH
            logging.warning(msg)
            raise ServiceProvidersError(msg)

        return data

    _data = _load_country_names()

    def get(self, country_code):
        try:
            return self._data[country_code]
        except KeyError:
            raise KeyError('Not found country name for code "%s"'
                           % country_code)


class ServiceProvidersParser(object):
    def __init__(self):
        # Check service provider database file exists
        try:
            tree = ElementTree(file=PROVIDERS_PATH)
        except (IOError, SyntaxError), e:
            msg = ("Mobile broadband provider database: Could not read "
                   "provider information %s error=%s") % (PROVIDERS_PATH, e)
            logging.warning(msg)
            raise ServiceProvidersError(msg)

        # Check service provider database format
        self.root = tree.getroot()
        if self.root.get('format') != PROVIDERS_FORMAT_SUPPORTED:
            msg = ("Mobile broadband provider database: Could not "
                   "read provider information. Wrong format.")
            logging.warning(msg)
            raise ServiceProvidersError(msg)

        # Populate countries list
        names = CountryCodeParser()
        self._countries = self.root.findall('country')
        self._countries.sort(key=lambda x: names.get(x.attrib['code']))
        self._country_codes = [c_el.attrib['code'] for c_el in self._countries]
        self._country_names = [names.get(code) for code in self._country_codes]

    def _get_country(self, country_idx):
        return self._countries[country_idx]

    def _get_provider(self, country_idx, provider_idx):
        try:
            return self.get_providers(country_idx)[provider_idx]
        except IndexError:
            return None

    def get_country_idx_by_code(self, country_code):
        return self._country_codes.index(country_code)

    def get_country_name_by_idx(self, country_idx):
        return self._country_names[country_idx]

    def get_countries(self):
        return self._countries

    def get_providers(self, country_idx):
        return [
            provider
            for provider in self._get_country(country_idx).findall('provider')
            if provider.find('.//gsm')
        ]

    def get_plans(self, country_idx, provider_idx):
        provider_el = self._get_provider(country_idx, provider_idx)
        if provider_el is None:
            plans = []
        else:
            plans = provider_el.findall('.//apn')
        return plans


class ServiceProviders(object):
    def __init__(self):
        self._db = ServiceProvidersParser()
        self._settings = Gio.Settings(CONF_GSM_DIR)

        # Get initial values from GSettings or default ones
        country_code, provider_name, plan_idx = self._get_initial_config()

        # Update status: countries, providers and plans
        self._countries = self._db.get_countries()
        country_idx = 0
        if country_code is not None:
            country_idx = self._db.get_country_idx_by_code(country_code)
        self._current_country = country_idx
        self._providers = self._db.get_providers(self._current_country)

        provider_idx = 0
        for idx, provider_el in enumerate(self._providers):
            name = _get_name(provider_el) or _('Provider %s' % idx)
            if provider_name == name:
                provider_idx = idx
                break
        self._current_provider = provider_idx
        self._plans = self._db.get_plans(self._current_country,
                                         self._current_provider)

        self._current_plan = plan_idx

    def _guess_country_code(self):
        """Return country based on locale lang attribute."""
        language_code = locale.getdefaultlocale()[0]
        if language_code is None:
            country_code = None
        else:
            lc_list = language_code.split('_')
            country_code = lc_list[1].lower() if len(lc_list) >= 2 else None
        return country_code

    def _get_initial_config(self):
        """Retrieve values stored in GSettings or get default ones."""

        country_code = self._settings.get_string(CONF_SP_COUNTRY)
        if not country_code:
            country_code = self._guess_country_code()

        provider_name = self._settings.get_string(CONF_SP_PROVIDER)
        if not provider_name:
            provider_name = u''
        else:
            provider_name = provider_name.decode('utf-8')

        plan_idx = self._settings.get_int(CONF_SP_PLAN) or 0

        return (country_code, provider_name, plan_idx)

    def set_country(self, idx):
        self._current_country = idx
        country = self.get_country()
        self._settings.set_string(CONF_SP_COUNTRY, country.code)
        self._providers = self._db.get_providers(self._current_country)
        self.set_provider(0)
        return country

    def set_provider(self, idx):
        self._current_provider = idx
        provider = self.get_provider()
        if provider is not None:
            self._settings.set_string(CONF_SP_PROVIDER, provider.name)
        self._plans = self._db.get_plans(self._current_country,
                                         self._current_provider)
        self.set_plan(0)
        return provider

    def set_plan(self, idx):
        self._current_plan = idx
        plan = self.get_plan()
        if plan is not None:
            self._settings.set_int(CONF_SP_PLAN, idx)
        return plan

    def get_countries(self):
        countries = []
        for idx, country_el in enumerate(self._countries):
            country = Country(idx, country_el.attrib['code'],
                              self._db.get_country_name_by_idx(idx))
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
                       self._db.get_country_name_by_idx(self._current_country))

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
