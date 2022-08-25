# Copyright (C) 2007, 2008 One Laptop Per Child
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
#
#
# The language config is based on the system-config-language
# (http://fedoraproject.org/wiki/SystemConfig/language) tool
# Parts of the code were reused.
#

import os
import locale
from gettext import gettext as _
import subprocess

_default_lang = '%s.%s' % locale.getdefaultlocale()
_standard_msg = _('Could not access ~/.i18n. Create standard settings.')

LANGUAGES = {
    "Afar": "Afar",
    "Afrikaans": "Afrikaans",
    "Aguaruna": "Agr",
    "Akan": "Akan",
    "Albanian": "Shqip",
    "American English": "English",
    "Amharic": "\u12a0\u121b\u122d\u129b",
    "Angika": "Angika",
    "Arabic": "\u0627\u0644\u0639\u0631\u0628\u064a\u0629",
    "Aragonese": "Aragonese",
    "Armenian": "\u0540\u0561\u0575\u0565\u0580\u0565\u0576",
    "Assamese": "\u0985\u09b8\u09ae\u09c0\u09af\u09bc\u09be",
    "Asturian": "Asturianu",
    "Australian English": "English",
    "Austrian German": "Deutsch",
    "Aymara": "Ayc",
    "Azerbaijani": "Az\u0259rbaycan",
    "Bangla": "\u09ac\u09be\u0982\u09b2\u09be",
    "Basque": "Euskara",
    "Belarusian": "\u0411\u0435\u043b\u0430\u0440\u0443\u0441\u043a\u0430\u044f",
    "Bemba": "Ichibemba",
    "Berber": "Ber",
    "Bhili": "Bhb",
    "Bhojpuri": "Bhojpuri",
    "Bislama": "Bislama",
    "Blin": "Blin",
    "Bodo": "\u092c\u0921\u093c\u094b",
    "Bosnian": "Bosanski",
    "Brazilian Portuguese": "Portugu\u00eas",
    "Breton": "Brezhoneg",
    "British English": "English",
    "Bulgarian": "\u0411\u044a\u043b\u0433\u0430\u0440\u0441\u043a\u0438",
    "Burmese": "\u1019\u103c\u1014\u103a\u1019\u102c",
    "Canadian English": "English",
    "Canadian French": "Fran\u00e7ais",
    "Cantonese": "\u7cb5\u8a9e",
    "Catalan": "Catal\u00e0",
    "Central Kurdish": "\u06a9\u0648\u0631\u062f\u06cc\u06cc",
    "Central Nahuatl": "Nhn",
    "Chechen": "\u041d\u043e\u0445\u0447\u0438\u0439\u043d",
    "Cherokee": "\u13e3\uab83\uab79",
    "Chhattisgarhi": "Hne",
    "Chinese": "\u4e2d\u6587\uff08\u4e2d\u56fd\uff09",
    "Chitwania Tharu": "The",
    "Chuvash": "Chuvash",
    "Cornish": "Kernewek",
    "Crimean Tatar": "Crimean",
    "Croatian": "Hrvatski",
    "Cusco Quechua": "Quz",
    "Czech": "\u010ce\u0161tina",
    "Danish": "Dansk",
    "Divehi": "Divehi",
    "Dogri": "\u0921\u094b\u0917\u0930\u0940",
    "Dutch": "Nederlands",
    "Dzongkha": "\u0f62\u0fab\u0f7c\u0f44\u0f0b\u0f41\u0f0d",
    "English": "English",
    "Estonian": "Eesti",
    "European Portuguese": "Portugu\u00eas",
    "European Spanish": "Espa\u00f1ol",
    "Faroese": "F\u00f8royskt",
    "Fiji Hindi": "Fiji",
    "Filipino": "Filipino",
    "Finnish": "Suomi",
    "Flemish": "Nederlands",
    "French": "Fran\u00e7ais",
    "Friulian": "Furlan",
    "Fulah": "Pulaar",
    "Galician": "Galego",
    "Ganda": "Luganda",
    "Geez": "Geez",
    "Georgian": "\u10e5\u10d0\u10e0\u10d7\u10e3\u10da\u10d8",
    "German": "Deutsch",
    "Greek": "\u0395\u03bb\u03bb\u03b7\u03bd\u03b9\u03ba\u03ac",
    "Gujarati": "\u0a97\u0ac1\u0a9c\u0ab0\u0abe\u0aa4\u0ac0",
    "Haitian Creole": "Haitian",
    "Hakka Chinese": "Hakka",
    "Hausa": "Hausa",
    "Hebrew": "\u05e2\u05d1\u05e8\u05d9\u05ea",
    "Hindi": "\u0939\u093f\u0928\u094d\u0926\u0940",
    "Hungarian": "Magyar",
    "Icelandic": "\u00cdslenska",
    "Igbo": "Igbo",
    "Indonesian": "Indonesia",
    "Interlingua": "Interlingua",
    "Inuktitut": "Inuktitut",
    "Inupiaq": "Inupiaq",
    "Irish": "Gaeilge",
    "Italian": "Italiano",
    "Japanese": "\u65e5\u672c\u8a9e",
    "Kabyle": "Taqbaylit",
    "Kalaallisut": "Kalaallisut",
    "Kannada": "\u0c95\u0ca8\u0ccd\u0ca8\u0ca1",
    "Karbi": "Mjw",
    "Kashmiri": "\u06a9\u0672\u0634\u064f\u0631",
    "Kashubian": "Kashubian",
    "Kazakh": "\u049a\u0430\u0437\u0430\u049b",
    "Khmer": "\u1781\u17d2\u1798\u17c2\u179a",
    "Kinyarwanda": "Kinyarwanda",
    "Konkani": "\u0915\u094b\u0902\u0915\u0923\u0940",
    "Korean": "\ud55c\uad6d\uc5b4(\ub300\ud55c\ubbfc\uad6d)",
    "Kurdish": "Kurd\u00ee",
    "Kyrgyz": "\u041a\u044b\u0440\u0433\u044b\u0437\u0447\u0430",
    "Lao": "\u0ea5\u0eb2\u0ea7",
    "Latvian": "Latvie\u0161u",
    "Ligurian": "Ligurian",
    "Limburgish": "Limburgish",
    "Lingala": "Ling\u00e1la",
    "Literary Chinese": "Literary",
    "Lithuanian": "Lietuvi\u0173",
    "Low German": "Low",
    "Low Saxon": "Low",
    "Lower Sorbian": "Dolnoserb\u0161\u0107ina",
    "Luxembourgish": "L\u00ebtzebuergesch",
    "Macedonian": "\u041c\u0430\u043a\u0435\u0434\u043e\u043d\u0441\u043a\u0438",
    "Magahi": "Magahi",
    "Maithili": "\u092e\u0948\u0925\u093f\u0932\u0940",
    "Malagasy": "Malagasy",
    "Malay": "Melayu",
    "Malayalam": "\u0d2e\u0d32\u0d2f\u0d3e\u0d33\u0d02",
    "Maltese": "Malti",
    "Mandarin Chinese": "Cmn",
    "Manipuri": "\u09ae\u09c8\u09a4\u09c8\u09b2\u09cb\u09a8\u09cd",
    "Manx": "Gaelg",
    "Maori": "Te",
    "Marathi": "\u092e\u0930\u093e\u0920\u0940",
    "Meadow Mari": "Mhr",
    "Mexican Spanish": "Espa\u00f1ol",
    "Min Nan Chinese": "Min",
    "Miskito": "Miq",
    "Mon": "Mnw",
    "Mongolian": "\u041c\u043e\u043d\u0433\u043e\u043b",
    "Morisyen": "Kreol",
    "Nepali": "\u0928\u0947\u092a\u093e\u0932\u0940",
    "Niuean": "Niuean",
    "Northern Sami": "Davvis\u00e1megiella",
    "Northern Sotho": "Northern",
    "Norwegian Bokm\u00e5l": "Norsk",
    "Norwegian Nynorsk": "Norsk",
    "Occitan": "Occitan",
    "Odia": "\u0b13\u0b21\u0b3c\u0b3f\u0b06",
    "Oromo": "Oromoo",
    "Ossetic": "\u0418\u0440\u043e\u043d",
    "Papiamento": "Papiamento",
    "Pashto": "\u067e\u069a\u062a\u0648",
    "Persian": "\u0641\u0627\u0631\u0633\u06cc",
    "Polish": "Polski",
    "Punjabi": "\u0a2a\u0a70\u0a1c\u0a3e\u0a2c\u0a40",
    "Rajasthani": "Rajasthani",
    "Romanian": "Rom\u00e2n\u0103",
    "Russian": "\u0420\u0443\u0441\u0441\u043a\u0438\u0439",
    "Sakha": "\u0421\u0430\u0445\u0430",
    "Samoan": "Samoan",
    "Samogitian": "Samogitian",
    "Sanskrit": "\u0938\u0902\u0938\u094d\u0915\u0943\u0924",
    "Santali": "\u1c65\u1c5f\u1c71\u1c5b\u1c5f\u1c72\u1c64",
    "Sardinian": "Sardinian",
    "Scottish Gaelic": "G\u00e0idhlig",
    "Serbian": "\u0421\u0440\u043f\u0441\u043a\u0438",
    "Shan": "Shan",
    "Shuswap": "Shs",
    "Sidamo": "Sidamo",
    "Silesian": "Silesian",
    "Sindhi": "\u0633\u0646\u068c\u064a",
    "Sinhala": "\u0dc3\u0dd2\u0d82\u0dc4\u0dbd",
    "Slovak": "Sloven\u010dina",
    "Slovenian": "Sloven\u0161\u010dina",
    "Somali": "Soomaali",
    "South Azerbaijani": "Az\u0259rbaycan",
    "South Ndebele": "South",
    "Southern Sotho": "Southern",
    "Spanish": "Espa\u00f1ol",
    "Swahili": "Kiswahili",
    "Swati": "Swati",
    "Swedish": "Svenska",
    "Swiss French": "Fran\u00e7ais",
    "Swiss High German": "Deutsch",
    "Tagalog": "Tagalog",
    "Tajik": "\u0422\u043e\u04b7\u0438\u043a\u04e3",
    "Tamil": "\u0ba4\u0bae\u0bbf\u0bb4\u0bcd",
    "Tatar": "\u0422\u0430\u0442\u0430\u0440",
    "Telugu": "\u0c24\u0c46\u0c32\u0c41\u0c17\u0c41",
    "Thai": "\u0e44\u0e17\u0e22",
    "Tibetan": "\u0f56\u0f7c\u0f51\u0f0b\u0f66\u0f90\u0f51\u0f0b",
    "Tigre": "Tigre",
    "Tigrinya": "\u1275\u130d\u122d",
    "Tok Pisin": "Tok",
    "Tongan": "Lea",
    "Tsonga": "Tsonga",
    "Tswana": "Tswana",
    "Tulu": "Tulu",
    "Turkish": "T\u00fcrk\u00e7e",
    "Turkmen": "T\u00fcrkmen",
    "Ukrainian": "\u0423\u043a\u0440\u0430\u0457\u043d\u0441\u044c\u043a\u0430",
    "Unami Delaware": "Unm",
    "Upper Sorbian": "Hornjoserb\u0161\u0107ina",
    "Urdu": "\u0627\u0631\u062f\u0648",
    "Uyghur": "\u0626\u06c7\u064a\u063a\u06c7\u0631\u0686\u06d5",
    "Uzbek": "O\u2018Zbek",
    "Venda": "Venda",
    "Vietnamese": "Ti\u1ebfng",
    "Walloon": "Walloon",
    "Walser": "Walser",
    "Welsh": "Cymraeg",
    "Western Frisian": "Frysk",
    "Wolaytta": "Wolaytta",
    "Wolof": "Wolof",
    "Xhosa": "Isixhosa",
    "YauNungon": "Yuw",
    "Yiddish": "\u05d9\u05d9\u05b4\u05d3\u05d9\u05e9",
    "Yoruba": "\u00c8d\u00e8",
    "Zulu": "Isizulu"
}



def read_all_languages():
    fdp = subprocess.Popen(['locale', '-av'], stdout=subprocess.PIPE)
    lines = fdp.stdout.read().decode('utf-8', 'ignore').split('\n')
    locales = []

    for line in lines:
        if line.find('locale:') != -1:
            locale_str = line.split()[1]
        elif line.find('title |') != -1:
            title = line.lstrip('title |')
        elif line.find('language |') != -1:
            lang = line.lstrip('language |')
            # Sometimes language is a language code, not the language name
            if len(lang) <= 3:
                lang = title.split()[0]
        elif line.find('territory |') != -1:
            territory = line.lstrip('territory |')
            # Sometimes territory is a territory code, not the territory name
            if len(territory) <= 3 and territory != 'USA':
                if ' locale for ' in title:
                    territory = title.split(' locale for ')[-1]
                    # Aesthetic cleanup up for titles with trailing .
                    if territory[-1] == '.':
                        territory = territory[:-1]
                else:
                    territory = title.split()[-1]
            if locale_str.endswith('utf8') and len(lang):
                locales.append((LANGUAGES[lang], territory, locale_str))

    locales.sort()
    return locales


def _initialize():
    if set_languages.__doc__ is None:
        # when running under 'python -OO', all __doc__ fields are None,
        # so += would fail -- and this function would be unnecessary anyway.
        return
    languages = read_all_languages()
    set_languages.__doc__ += '\n'
    for lang in languages:
        set_languages.__doc__ += '%s \n' % (lang[0].replace(' ', '_') + '/' +
                                            lang[1].replace(' ', '_'))


def _write_i18n(lang_env, language_env):
    path = os.path.join(os.environ.get('HOME', ''), '.i18n')
    # try avoid writing the file if the values didn't changed
    lang_line = None
    language_line = None
    other_lines = []
    try:
        with open(path) as fd:
            for line in fd:
                if line.startswith('LANG='):
                    lang_line = line
                elif line.startswith('LANGUAGE='):
                    language_line = line
                else:
                    other_lines.append(line)
    except:
        pass

    new_lang_line = 'LANG="%s"\n' % lang_env
    new_language_line = 'LANGUAGE="%s"\n' % language_env

    if lang_line == new_lang_line and language_line == new_language_line:
        return

    with open(path, 'w') as fd:
        fd.write(new_lang_line)
        fd.write(new_language_line)
        for line in other_lines:
            fd.write(line)
        fd.flush()
        # be sure all is flushed
        os.fsync(fd)


def _get_from_env(name):
    lang = os.environ[name]
    lang = lang.strip()
    if lang.endswith('UTF-8'):
        lang = lang.replace('UTF-8', 'utf8')
    return lang


def get_languages():
    # read the env variables set in bin/sugar
    langlist = None
    lang = _default_lang

    if 'LANGUAGE' in os.environ:
        lang = _get_from_env('LANGUAGE')
        langlist = lang.split(':')

    if 'LANG' in os.environ:
        lang = _get_from_env('LANG')

    # There might be cases where .i18n may not contain a LANGUAGE field
    if langlist is None:
        return [lang]
    return langlist


def print_languages():
    codes = get_languages()

    languages = read_all_languages()
    for code in codes:
        found_lang = False
        for lang in languages:
            if lang[2].split('.')[0] == code.split('.')[0]:
                print(lang[0].replace(' ', '_') + '/' +
                      lang[1].replace(' ', '_'))
                found_lang = True
                break
        if not found_lang:
            print((_('Language for code=%s could not be determined.') % code))


def set_languages(languages):
    """Set the system language.
    languages :
    """

    if isinstance(languages, list):
        set_languages_list(languages)
        return

    if languages.endswith('utf8'):
        set_languages_list([languages])
        return 1
    langs = read_all_languages()
    for lang, territory, locale_str in langs:
        code = lang.replace(' ', '_') + '/' \
                    + territory.replace(' ', '_')
        if code == languages:
            set_languages_list([locale_str])
            return 1
    print((_("Sorry I do not speak \'%s\'.") % languages))


def set_languages_list(languages):
    """Set the system language using a list of preferred languages"""
    colon = ':'
    language_env = colon.join(languages)
    lang_env = languages[0].strip('\n')
    _write_i18n(lang_env, language_env)


# inilialize the docstrings for the language
_initialize()
