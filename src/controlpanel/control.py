# Copyright (C) 2007, One Laptop Per Child
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
#
#
# The language config is based on the system-config-language
# (http://fedoraproject.org/wiki/SystemConfig/language) tool
# and the timezone config on the system-config-date
# (http://fedoraproject.org/wiki/SystemConfig/date) tool.
# Parts of the code were reused.
#

import os
import string
import shutil
from gettext import gettext as _
import dbus

from sugar import profile
from sugar.graphics.xocolor import XoColor

NM_SERVICE_NAME = 'org.freedesktop.NetworkManager'
NM_SERVICE_PATH = '/org/freedesktop/NetworkManager'
NM_SERVICE_IFACE = 'org.freedesktop.NetworkManager'
NM_ASLEEP = 1

_COLORS = {'red': {'dark':'#b20008', 'medium':'#e6000a', 'light':'#ffadce'},
           'orange': {'dark':'#9a5200', 'medium':'#c97e00', 'light':'#ffc169'},
           'yellow': {'dark':'#807500', 'medium':'#be9e00', 'light':'#fffa00'},
           'green': {'dark':'#008009', 'medium':'#00b20d', 'light':'#8bff7a'},
           'blue': {'dark':'#00588c', 'medium':'#005fe4', 'light':'#bccdff'},
           'purple': {'dark':'#5e008c', 'medium':'#7f00bf', 'light':'#d1a3ff'}
           }

_MODIFIERS = ('dark', 'medium', 'light')

_TIMEZONE_CONFIG = '/etc/sysconfig/clock'

_LANGUAGES = {
    'Afrikaans/South_Africa': 'af_ZA',
    'Albanian': 'sq_AL.UTF-8',
    'Amharic/Ethiopian': 'am_ET.UTF-8',
    'Arabic/Algeria': 'ar_DZ.UTF-8',
    'Arabic/Bahrain': 'ar_BH.UTF-8',
    'Arabic/Egypt': 'ar_EG.UTF-8',
    'Arabic/India': 'ar_IN.UTF-8',
    'Arabic/Iraq': 'ar_IQ.UTF-8',
    'Arabic/Jordan': 'ar_JO.UTF-8',  
    'Arabic/Kuwait': 'ar_KW.UTF-8',  
    'Arabic/Lebanon': 'ar_LB.UTF-8',  
    'Arabic/Libyan_Arab_Jamahiriya': 'ar_LY.UTF-8',  
    'Arabic/Morocco': 'ar_MA.UTF-8',  
    'Arabic/Oman': 'ar_OM.UTF-8',  
    'Arabic/Qatar': 'ar_QA.UTF-8',  
    'Arabic/Saudi_Arabia': 'ar_SA.UTF-8',  
    'Arabic/Sudan': 'ar_SD.UTF-8',  
    'Arabic/Syrian_Arab_Republic': 'ar_SY.UTF-8',  
    'Arabic/Tunisia': 'ar_TN.UTF-8',  
    'Arabic/United_Arab_Emirates': 'ar_AE.UTF-8',  
    'Arabic/Yemen': 'ar_YE.UTF-8',  
    'Basque/Spain': 'eu_ES.UTF-8',  
    'Belarusian': 'be_BY.UTF-8',  
    'Bengali/BD': 'bn_BD.UTF-8',  
    'Bengali/India': 'bn_IN.UTF-8',  
    'Bosnian/Bosnia_and_Herzegowina': 'bs_BA',
    'Breton/France': 'br_FR',
    'Bulgarian': 'bg_BG.UTF-8',  
    'Catalan/Spain': 'ca_ES.UTF-8',  
    'Chinese/Hong_Kong': 'zh_HK.UTF-8',  
    'Chinese/P.R._of_China': 'zh_CN.UTF-8',
    'Chinese/Taiwan': 'zh_TW.UTF-8',
    'Cornish/Britain': 'kw_GB.UTF-8',  
    'Croatian': 'hr_HR.UTF-8',  
    'Czech': 'cs_CZ.UTF-8',  
    'Danish': 'da_DK.UTF-8',  
    'Dutch/Belgium': 'nl_BE.UTF-8',  
    'Dutch/Netherlands': 'nl_NL.UTF-8',  
    'English/Australia': 'en_AU.UTF-8',  
    'English/Botswana': 'en_BW.UTF-8',  
    'English/Canada': 'en_CA.UTF-8',  
    'English/Denmark': 'en_DK.UTF-8',  
    'English/Great_Britain': 'en_GB.UTF-8',  
    'English/Hong_Kong': 'en_HK.UTF-8',  
    'English/India': 'en_IN.UTF-8',  
    'English/Ireland': 'en_IE.UTF-8',  
    'English/New_Zealand': 'en_NZ.UTF-8',  
    'English/Philippines': 'en_PH.UTF-8',  
    'English/Singapore': 'en_SG.UTF-8',  
    'English/South_Africa': 'en_ZA.UTF-8',  
    'English/USA': 'en_US.UTF-8',  
    'English/Zimbabwe': 'en_ZW.UTF-8',  
    'Estonian': 'et_EE.UTF-8',  
    'Faroese/Faroe_Islands': 'fo_FO.UTF-8',  
    'Finnish': 'fi_FI.UTF-8',  
    'French/Belgium': 'fr_BE.UTF-8',  
    'French/Canada': 'fr_CA.UTF-8',  
    'French/France': 'fr_FR.UTF-8',  
    'French/Luxemburg': 'fr_LU.UTF-8',  
    'French/Switzerland': 'fr_CH.UTF-8',  
    'Galician/Spain': 'gl_ES.UTF-8',  
    'German/Austria': 'de_AT.UTF-8',  
    'German/Belgium': 'de_BE.UTF-8',  
    'German/Germany': 'de_DE.UTF-8',  
    'German/Luxemburg': 'de_LU.UTF-8',  
    'German/Switzerland': 'de_CH.UTF-8',  
    'Greek': 'el_GR.UTF-8',  
    'Greenlandic/Greenland': 'kl_GL.UTF-8',  
    'Gujarati/India': 'gu_IN.UTF-8',  
    'Hausa/Nigeria': 'ha_NG.UTF-8',
    'Hebrew/Israel': 'he_IL.UTF-8',  
    'Hindi/India': 'hi_IN.UTF-8',  
    'Hungarian': 'hu_HU.UTF-8',  
    'Icelandic': 'is_IS.UTF-8',  
    'Igbo/Nigeria': 'ig_NG.UTF-8',
    'Indonesian': 'id_ID.UTF-8',  
    'Irish': 'ga_IE.UTF-8',  
    'Italian/Italy': 'it_IT.UTF-8',  
    'Italian/Switzerland': 'it_CH.UTF-8',  
    'Japanese': 'ja_JP.UTF-8',
    'Korean/Republic_of_Korea': 'ko_KR.UTF-8',
    'Lao/Laos': 'lo_LA.UTF-8',  
    'Latvian/Latvia': 'lv_LV.UTF-8',  
    'Lithuanian': 'lt_LT.UTF-8',  
    'Macedonian': 'mk_MK.UTF-8',  
    'Malay/Malaysia': 'ms_MY.UTF-8',  
    'Maltese/malta': 'mt_MT.UTF-8',  
    'Manx/Britain': 'gv_GB.UTF-8',  
    'Marathi/India': 'mr_IN.UTF-8',
    'Mongolian': 'mn_MN.UTF-8',
    'Nepali': 'ne_NP.UTF-8',
    'Northern/Norway': 'se_NO',  
    'Norwegian': 'nb_NO.UTF-8',  
    'Norwegian,/Norway': 'nn_NO.UTF-8',  
    'Occitan/France': 'oc_FR',
    'Oriya/India': 'or_IN.UTF-8',  
    'Persian/Iran': 'fa_IR.UTF-8',  
    'Polish': 'pl_PL.UTF-8',  
    'Portuguese/Brasil': 'pt_BR.UTF-8',  
    'Portuguese/Portugal': 'pt_PT.UTF-8',  
    'Punjabi/India': 'pa_IN.UTF-8',  
    'Romanian': 'ro_RO.UTF-8',  
    'Russian': 'ru_RU.UTF-8',  
    'Russian/Ukraine': 'ru_UA.UTF-8',  
    'Serbian': 'sr_CS.UTF-8',  
    'Serbian/Latin': 'sr_CS.UTF-8@Latn',  
    'Slovak': 'sk_SK.UTF-8',  
    'Slovenian/Slovenia': 'sl_SI.UTF-8',  
    'Spanish/Argentina': 'es_AR.UTF-8',  
    'Spanish/Bolivia': 'es_BO.UTF-8',  
    'Spanish/Chile': 'es_CL.UTF-8',  
    'Spanish/Colombia': 'es_CO.UTF-8',  
    'Spanish/Costa_Rica': 'es_CR.UTF-8',  
    'Spanish/Dominican_Republic': 'es_DO.UTF-8',  
    'Spanish/El_Salvador': 'es_SV.UTF-8',  
    'Spanish/Equador': 'es_EC.UTF-8',  
    'Spanish/Guatemala': 'es_GT.UTF-8',  
    'Spanish/Honduras': 'es_HN.UTF-8',  
    'Spanish/Mexico': 'es_MX.UTF-8',  
    'Spanish/Nicaragua': 'es_NI.UTF-8',  
    'Spanish/Panama': 'es_PA.UTF-8',  
    'Spanish/Paraguay': 'es_PY.UTF-8',  
    'Spanish/Peru': 'es_PE.UTF-8',  
    'Spanish/Puerto_Rico': 'es_PR.UTF-8',  
    'Spanish/Spain': 'es_ES.UTF-8',  
    'Spanish/USA': 'es_US.UTF-8',  
    'Spanish/Uruguay': 'es_UY.UTF-8',  
    'Spanish/Venezuela': 'es_VE.UTF-8',  
    'Swedish/Finland': 'sv_FI.UTF-8',  
    'Swedish/Sweden': 'sv_SE.UTF-8',  
    'Tagalog/Philippines': 'tl_PH',
    'Tamil/India': 'ta_IN.UTF-8',  
    'Telugu/India': 'te_IN.UTF-8',  
    'Thai': 'th_TH.UTF-8',  
    'Turkish': 'tr_TR.UTF-8',  
    'Ukrainian': 'uk_UA.UTF-8',  
    'Urdu/Pakistan': 'ur_PK',  
    'Uzbek/Uzbekistan': 'uz_UZ',
    'Walloon/Belgium': 'wa_BE@euro',
    'Welsh/Great_Britain': 'cy_GB.UTF-8',  
    'Xhosa/South_Africa': 'xh_ZA.UTF-8',
    'Yoruba/Nigeria': 'yo_NG.UTF-8',
    'Zulu/South_Africa': 'zu_ZA.UTF-8'
    }


def _initialize():
    timezones = _read_zonetab()

    j=0
    for timezone in timezones:
        set_timezone.__doc__ += timezone+', '
        j+=1
        if j%3 == 0:
            set_timezone.__doc__ += '\n'
                        
    keys =  _LANGUAGES.keys()
    keys.sort()
    i = 0
    for key in keys:
        set_language.__doc__ += key+', '
        i+=1
        if i%3 == 0:
            set_language.__doc__ += '\n'

def _note_restart():
    print _('To apply your changes you have to restart sugar.\n' +
            'Hit at the same time ctrl+alt+erase on the keyboard to do this.')
    
def get_jabber():
    pro = profile.get_profile()    
    return pro.jabber_server

def print_jabber():
    print get_jabber()

def set_jabber(server):
    """Set the jabber server
    server : e.g. 'olpc.collabora.co.uk'
    """
    pro = profile.get_profile()
    pro.jabber_server = server
    pro.jabber_registered = False
    pro.save()
    _note_restart()
    
def get_color():    
    return profile.get_color()    

def print_color():
    color = get_color().to_string()
    str = color.split(',')

    stroke = None
    fill = None
    for color in _COLORS:
        for hue in _COLORS[color]:
            if _COLORS[color][hue] == str[0]:
                stroke = (color, hue)
            if _COLORS[color][hue] == str[1]:
                fill = (color, hue)

    if stroke is not None:            
        print 'stroke:   color=%s hue=%s'%(stroke[0], stroke[1])
    else:
        print 'stroke:   %s'%(str[0])        
    if fill is not None:    
        print 'fill:     color=%s hue=%s'%(fill[0], fill[1])
    else:
        print 'fill:     %s'%(str[1])
        
def set_color(stroke, fill, modstroke='medium', modfill='medium'):
    """Set the system color by setting a fill and stroke color.
    fill : [red, orange, yellow, blue, purple]
    stroke : [red, orange, yellow, blue, purple]
    hue stroke : [dark, medium, light] (optional)
    hue fill : [dark, medium, light] (optional)
    """
    
    if modstroke not in _MODIFIERS or modfill not in _MODIFIERS:
        print (_("Error in specified color modifiers."))
        return
    if stroke not in _COLORS or fill not in _COLORS:
        print (_("Error in specified colors."))
        return
    
    if modstroke == modfill:
        if modfill == 'medium':
            modfill = 'light'
        else:
            modfill = 'medium'
            
    color = _COLORS[stroke][modstroke] + ',' + _COLORS[fill][modfill]
    pro = profile.get_profile()
    pro.color = XoColor(color)   
    pro.save()
    _note_restart()
        
def get_nick():
    return profile.get_nick_name()

def print_nick():
    print get_nick()
    
def set_nick(nick):
    """Set the nickname.
    nick : e.g. 'walter'
    """
    pro = profile.get_profile()
    pro.nick_name = nick    
    pro.save()
    _note_restart()
            
def get_radio():    
    bus = dbus.SystemBus()
    proxy = bus.get_object(NM_SERVICE_NAME, NM_SERVICE_PATH)
    nm = dbus.Interface(proxy, NM_SERVICE_IFACE)
    state = nm.getWirelessEnabled()	
    if state == 0:
        return _('off')
    elif state == 1:
        return _('on')
    else:
        return _('State is unknown.')
	
def print_radio():
    print get_radio()
    
def set_radio(state):
    """Turn Radio 'on' or 'off'
    state : 'on/off'
    """    
    if state == 'on':
        bus = dbus.SystemBus()
        proxy = bus.get_object(NM_SERVICE_NAME, NM_SERVICE_PATH)
        nm = dbus.Interface(proxy, NM_SERVICE_IFACE)
        nm.setWirelessEnabled(True)        
    elif state == 'off':
        bus = dbus.SystemBus()
        proxy = bus.get_object(NM_SERVICE_NAME, NM_SERVICE_PATH)
        nm = dbus.Interface(proxy, NM_SERVICE_IFACE)
        nm.setWirelessEnabled(False)
    else:        
        print (_("Error in specified radio argument use on/off."))

def _check_for_superuser():
    if os.getuid():
        print _("Permission denied. You need to be root to run this method.")
        return False
    return True

def get_timezone():
    if not os.access(_TIMEZONE_CONFIG, os.R_OK):
        # this is what the default is for the /etc/localtime
        return "America/New_York"    
    fd = open(_TIMEZONE_CONFIG, "r")
    lines = fd.readlines()
    fd.close()
    try:
        for line in lines:
            line = string.strip(line)
            if len (line) and line[0] == '#':
                continue
            try:
                tokens = string.split(line, "=")
                if tokens[0] == "ZONE":
                    timezone = string.replace(tokens[1], '"', '')
                    return timezone        
            except Exception, e:
                print "get_timezone: %s" % e
    except Exception, e:
        print "get_timezone: %s" % e
    return None
        
def print_timezone():
    timezone = get_timezone()
    if timezone is None:
        print (_("Error in reading timezone"))
    else:
        print timezone 
                
def _read_zonetab(fn='/usr/share/zoneinfo/zone.tab'):
    fd = open (fn, 'r')
    lines = fd.readlines()
    fd.close()
    timezones = []
    for line in lines:
        if line.startswith('#'):
            continue
        line = line.split()
        if len(line) > 1:
            timezones.append(line[2])
    timezones.sort()
    return timezones

def set_timezone(timezone):
    """Set the system timezone
    timezone : 
    """
    if not _check_for_superuser():
        return

    timezones = _read_zonetab()
    if timezone in timezones:
        fromfile = os.path.join("/usr/share/zoneinfo/", timezone)        
        try:
            shutil.copyfile(fromfile, "/etc/localtime")
        except OSError, (errno, msg):
            print (_("Error copying timezone (from %s): %s") % (fromfile, msg))
            return
        try:
            os.chmod("/etc/localtime", 0644)
        except OSError, (errno, msg):
            print (_("Changing permission of timezone: %s") % (msg))
            return
                
        # Write info to the /etc/sysconfig/clock file
        fd = open(_TIMEZONE_CONFIG, "w")
        fd.write('# use sugar-control-panel to change this\n')
        fd.write('ZONE="%s"\n' % timezone)
        fd.write('UTC=true\n')
        fd.close()                       
    else:
        print (_("Error timezone does not exist."))

def _writeI18N(lang):
    path = os.path.join(os.environ.get("HOME"), '.i18n')
    if os.access(path, os.W_OK) == 0:
        print(_("Could not access %s. Create standard settings.") % path)
        fd = open(path, 'w')
        fd.write('LANG="en_US.UTF-8"\n')
        fd.close()
    else:
        fd = open(path, 'r')
        lines = fd.readlines()
        fd.close()
        for i in range(len(lines)):
            if lines[i][:5] == "LANG=":                
                lines[i] = 'LANG="' + lang + '"\n'
                fd = open(path, 'w')
                fd.writelines(lines)
                fd.close()

def get_language():
    originalFile = None
    path = os.path.join(os.environ.get("HOME"), '.i18n')
    if os.access(path, os.R_OK) == 0:
        print(_("Could not access %s. Create standard settings.") % path)
        fd = open(path, 'w')
        default = 'en_US.UTF-8'
        fd.write('LANG="%s"\n'%default)
        fd.close()
        return default
    
    fd = open(path, "r")
    lines = fd.readlines()
    fd.close()

    lang = None

    for line in lines:
        if line[:5] == "LANG=":
            lang = line[5:].replace('"', '')
            lang = lang.strip()

    return lang

def print_language():
    code = get_language()

    for lang in _LANGUAGES:
        if _LANGUAGES[lang] == code:
            print lang
            return
    print (_("Language for code=%s could not be determined.") % code)
    
def set_language(language):
    """Set the system language.
    languages : 
    """
    if language in _LANGUAGES:
        _writeI18N(_LANGUAGES[language])
        _note_restart()
    else:
        print (_("Sorry I do not speak \'%s\'.") % language)

# inilialize the docstrings for the timezone and language
_initialize()

