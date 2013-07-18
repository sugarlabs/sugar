# -*- encoding: utf-8 -*-
# Copyright (C) 2013, Miguel González
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA

import sys
import unittest
from xml.etree.cElementTree import ElementTree
from mock import patch

from jarabe import config


def setUpModule():
    sys.path.append(config.ext_path)


def tearDownModule():
    sys.path.remove(config.ext_path)
    # Needed to actually get rid of imported modules
    try:
        del sys.modules['cpesection.modemconfiguration.model']
        del sys.modules['cpesection.modemconfiguration']
        del sys.modules['cpesection']
    except KeyError:
        pass


class CountryCodeParserTest(unittest.TestCase):
    def test_get_country(self):
        from cpsection.modemconfiguration.model import CountryCodeParser
        self.assertEqual(CountryCodeParser().get('ad'), 'Andorra')
        self.assertEqual(CountryCodeParser().get('es'), 'Spain')
        self.assertEqual(CountryCodeParser().get('zw'), 'Zimbabwe')

    def test_raise_if_not_found(self):
        from cpsection.modemconfiguration.model import CountryCodeParser
        with self.assertRaises(KeyError):
            CountryCodeParser().get('xx')


class ServiceProvidersParserTest(unittest.TestCase):
    def setUp(self):
        from cpsection.modemconfiguration.model import ServiceProvidersParser,\
            PROVIDERS_PATH
        self.tree = ElementTree(file=PROVIDERS_PATH)
        self.countries_from_xml = self.tree.findall('country')
        self.db = ServiceProvidersParser()
        self.countries_from_class = self.db.get_countries()

    def test_get_countries(self):
        for country in self.countries_from_class:
            self.assertEqual(country.tag, 'country')

    def test_get_country_idx_by_code(self):
        for idx, country in enumerate(self.countries_from_class):
            country_code = country.attrib['code']
            country_idx = self.db.get_country_idx_by_code(country_code)
            self.assertEqual(idx, country_idx)

    def test_get_country_name_by_idx(self):
        from cpsection.modemconfiguration.model import CountryCodeParser
        for idx, country in enumerate(self.countries_from_class):
            country_code = country.attrib['code']
            self.assertEqual(
                CountryCodeParser().get(country_code),
                self.db.get_country_name_by_idx(idx)
            )

    def test_get_providers(self):
        for country_idx, country in enumerate(self.countries_from_class):
            providers = self.db.get_providers(country_idx)
            for provider in providers:
                self.assertEqual(provider.tag, 'provider')
                self.assertIsNotNone(provider.find('.//gsm'))

    def test_get_plans(self):
        for country_idx, country in enumerate(self.countries_from_class):
            providers = self.db.get_providers(country_idx)
            for provider_idx, provider in enumerate(providers):
                plans = self.db.get_plans(country_idx, provider_idx)
                for plan in plans:
                    self.assertEqual(plan.tag, 'apn')

    def get_providers(self, country_xml):
        """Given a country element find all provider with a gsm tag."""
        idx = 0
        for provider in country_xml.findall('provider'):
            if provider.find('.//gsm'):
                yield idx, provider
                idx = idx + 1

    def get_plans(self, provider_xml):
        """Given a provider element find all apn elements."""
        for idx, plan in enumerate(provider_xml.findall('.//apn')):
            yield idx, plan

    def test_get_some_specific_values(self):
        for country in self.countries_from_xml:
            country_code = country.attrib['code']
            country_idx = self.db.get_country_idx_by_code(country_code)

            for provider_idx, provider in self.get_providers(country):
                plans_from_class = self.db.get_plans(country_idx,
                                                     provider_idx)

                for plan_idx, plan in self.get_plans(provider):
                    plan_from_class = plans_from_class[plan_idx]
                    self.assertEqual(plan.attrib['value'],
                                     plan_from_class.attrib['value'])


class ServiceProvidersTest(unittest.TestCase):
    def setUp(self):
        from cpsection.modemconfiguration.model import ServiceProviders
        self.db = ServiceProviders()
        self.countries = self.db.get_countries()

    def test_go_trough_all_combo_options(self):
        from cpsection.modemconfiguration.model import ServiceProviders
        # Traverse countries
        for country in self.countries:
            # Check if country is stored
            self.db.set_country(country.idx)
            new_country = self.db.get_country()
            self.assertEqual(country.code, new_country.code)

            # Traverse providers for country
            providers = self.db.get_providers()
            for provider in providers:
                # Check if provider is stored
                self.db.set_provider(provider.idx)
                new_provider = self.db.get_provider()
                self.assertEqual(provider.name, new_provider.name)

                # Traverse plans for provider
                plans = self.db.get_plans()
                for plan in plans:
                    # Check if plan is stored
                    self.db.set_plan(plan.idx)
                    new_plan = self.db.get_plan()
                    self.assertEqual(plan.name, new_plan.name)

                    # Check if selection is permanently stored
                    db2 = ServiceProviders()
                    country2 = db2.get_country()
                    provider2 = db2.get_provider()
                    plan2 = db2.get_plan()
                    self.assertEqual(country2.idx, country.idx)
                    self.assertEqual(provider2.idx, provider.idx)
                    self.assertEqual(plan2.idx, plan.idx)


class FakeGConfClient(object):

    def __init__(self, **kwargs):
        from cpsection.modemconfiguration.model import \
            GCONF_SP_COUNTRY, GCONF_SP_PROVIDER, GCONF_SP_PLAN
        self.store = {
            GCONF_SP_COUNTRY: None,
            GCONF_SP_PROVIDER: None,
            GCONF_SP_PLAN: None,
        }
        self.store.update(kwargs)

    def get_string(self, key):
        return self.store[key]

    def set_string(self, key, value):
        self.store[key] = value
        return

    def get_int(self, key):
        return self.store[key]

    def set_int(self, key, value):
        self.store[key] = value
        return


class ServiceProvidersGuessCountryTest(unittest.TestCase):
    def setUp(self):
        # patch GConf.Client.get_default to use a fake client
        gconf_patcher = patch('gi.repository.GConf.Client.get_default')
        gconf_mock = gconf_patcher.start()
        gconf_mock.return_value = FakeGConfClient(GCONF_SP_COUNTRY=None)
        self.addCleanup(gconf_patcher.stop)

    def test_guess_country(self):
        from cpsection.modemconfiguration.model import ServiceProviders
        LOCALE = ('hi_IN', 'UTF-8')
        default_country_code = LOCALE[0][3:5].lower()

        with patch('locale.getdefaultlocale') as locale_mock:
            locale_mock.return_value = LOCALE

            db = ServiceProviders()
            country = db.get_country()
            self.assertEqual(country.code, default_country_code)
