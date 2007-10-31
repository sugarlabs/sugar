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
    'Afrikaans/South_Africa': ('af_ZA', 'lat0-sun16'),
    'Albanian': ('sq_AL.UTF-8', 'latarcyrheb-sun16'),
    'Arabic/Algeria': ('ar_DZ.UTF-8', 'latarcyrheb-sun16'),
    'Arabic/Bahrain': ('ar_BH.UTF-8', 'latarcyrheb-sun16'),
    'Arabic/Egypt': ('ar_EG.UTF-8', 'latarcyrheb-sun16'),
    'Arabic/India': ('ar_IN.UTF-8', 'latarcyrheb-sun16'),
    'Arabic/Iraq': ('ar_IQ.UTF-8', 'latarcyrheb-sun16'),
    'Arabic/Jordan': ('ar_JO.UTF-8', 'latarcyrheb-sun16'),
    'Arabic/Kuwait': ('ar_KW.UTF-8', 'latarcyrheb-sun16'),
    'Arabic/Lebanon': ('ar_LB.UTF-8', 'latarcyrheb-sun16'),
    'Arabic/Libyan_Arab_Jamahiriya': ('ar_LY.UTF-8', 'latarcyrheb-sun16'),
    'Arabic/Morocco': ('ar_MA.UTF-8', 'latarcyrheb-sun16'),
    'Arabic/Oman': ('ar_OM.UTF-8', 'latarcyrheb-sun16'),
    'Arabic/Qatar': ('ar_QA.UTF-8', 'latarcyrheb-sun16'),
    'Arabic/Saudi_Arabia': ('ar_SA.UTF-8', 'latarcyrheb-sun16'),
    'Arabic/Sudan': ('ar_SD.UTF-8', 'latarcyrheb-sun16'),
    'Arabic/Syrian_Arab_Republic': ('ar_SY.UTF-8', 'latarcyrheb-sun16'),
    'Arabic/Tunisia': ('ar_TN.UTF-8', 'latarcyrheb-sun16'),
    'Arabic/United_Arab_Emirates': ('ar_AE.UTF-8', 'latarcyrheb-sun16'),
    'Arabic/Yemen': ('ar_YE.UTF-8', 'latarcyrheb-sun16'),
    'Basque/Spain': ('eu_ES.UTF-8', 'latarcyrheb-sun16'),
    'Belarusian': ('be_BY.UTF-8', 'latarcyrheb-sun16'),
    'Bengali/BD': ('bn_BD.UTF-8', 'latarcyrheb-sun16'),
    'Bengali/India': ('bn_IN.UTF-8', 'latarcyrheb-sun16'),
    'Bosnian/Bosnia_and_Herzegowina': ('bs_BA', 'lat2-sun16'),
    'Breton/France': ('br_FR', 'lat0-sun16'),
    'Bulgarian': ('bg_BG.UTF-8', 'latarcyrheb-sun16'),
    'Catalan/Spain': ('ca_ES.UTF-8', 'latarcyrheb-sun16'),
    'Chinese/Hong_Kong': ('zh_HK.UTF-8', 'latarcyrheb-sun16'),
    'Chinese/P.R._of_China': ('zh_CN.UTF-8', 'lat0-sun16'),
    'Chinese/Taiwan': ('zh_TW.UTF-8', 'lat0-sun16'),
    'Cornish/Britain': ('kw_GB.UTF-8', 'latarcyrheb-sun16'),
    'Croatian': ('hr_HR.UTF-8', 'latarcyrheb-sun16'),
    'Czech': ('cs_CZ.UTF-8', 'latarcyrheb-sun16'),
    'Danish': ('da_DK.UTF-8', 'latarcyrheb-sun16'),
    'Dutch/Belgium': ('nl_BE.UTF-8', 'latarcyrheb-sun16'),
    'Dutch/Netherlands': ('nl_NL.UTF-8', 'latarcyrheb-sun16'),
    'English/Australia': ('en_AU.UTF-8', 'latarcyrheb-sun16'),
    'English/Botswana': ('en_BW.UTF-8', 'latarcyrheb-sun16'),
    'English/Canada': ('en_CA.UTF-8', 'latarcyrheb-sun16'),
    'English/Denmark': ('en_DK.UTF-8', 'latarcyrheb-sun16'),
    'English/Great_Britain': ('en_GB.UTF-8', 'latarcyrheb-sun16'),
    'English/Hong_Kong': ('en_HK.UTF-8', 'latarcyrheb-sun16'),
    'English/India': ('en_IN.UTF-8', 'latarcyrheb-sun16'),
    'English/Ireland': ('en_IE.UTF-8', 'latarcyrheb-sun16'),
    'English/New_Zealand': ('en_NZ.UTF-8', 'latarcyrheb-sun16'),
    'English/Philippines': ('en_PH.UTF-8', 'latarcyrheb-sun16'),
    'English/Singapore': ('en_SG.UTF-8', 'latarcyrheb-sun16'),
    'English/South_Africa': ('en_ZA.UTF-8', 'latarcyrheb-sun16'),
    'English/USA': ('en_US.UTF-8', 'latarcyrheb-sun16'),
    'English/Zimbabwe': ('en_ZW.UTF-8', 'latarcyrheb-sun16'),
    'Estonian': ('et_EE.UTF-8', 'latarcyrheb-sun16'),
    'Faroese/Faroe_Islands': ('fo_FO.UTF-8', 'latarcyrheb-sun16'),
    'Finnish': ('fi_FI.UTF-8', 'latarcyrheb-sun16'),
    'French/Belgium': ('fr_BE.UTF-8', 'latarcyrheb-sun16'),
    'French/Canada': ('fr_CA.UTF-8', 'latarcyrheb-sun16'),
    'French/France': ('fr_FR.UTF-8', 'latarcyrheb-sun16'),
    'French/Luxemburg': ('fr_LU.UTF-8', 'latarcyrheb-sun16'),
    'French/Switzerland': ('fr_CH.UTF-8', 'latarcyrheb-sun16'),
    'Galician/Spain': ('gl_ES.UTF-8', 'latarcyrheb-sun16'),
    'German/Austria': ('de_AT.UTF-8', 'latarcyrheb-sun16'),
    'German/Belgium': ('de_BE.UTF-8', 'latarcyrheb-sun16'),
    'German/Germany': ('de_DE.UTF-8', 'latarcyrheb-sun16'),
    'German/Luxemburg': ('de_LU.UTF-8', 'latarcyrheb-sun16'),
    'German/Switzerland': ('de_CH.UTF-8', 'latarcyrheb-sun16'),
    'Greek': ('el_GR.UTF-8', 'latarcyrheb-sun16'),
    'Greenlandic/Greenland': ('kl_GL.UTF-8', 'latarcyrheb-sun16'),
    'Gujarati/India': ('gu_IN.UTF-8', 'latarcyrheb-sun16'),
    'Hebrew/Israel': ('he_IL.UTF-8', 'latarcyrheb-sun16'),
    'Hindi/India': ('hi_IN.UTF-8', 'latarcyrheb-sun16'),
    'Hungarian': ('hu_HU.UTF-8', 'latarcyrheb-sun16'),
    'Icelandic': ('is_IS.UTF-8', 'latarcyrheb-sun16'),
    'Indonesian': ('id_ID.UTF-8', 'latarcyrheb-sun16'),
    'Irish': ('ga_IE.UTF-8', 'latarcyrheb-sun16'),
    'Italian/Italy': ('it_IT.UTF-8', 'latarcyrheb-sun16'),
    'Italian/Switzerland': ('it_CH.UTF-8', 'latarcyrheb-sun16'),
    'Japanese': ('ja_JP.UTF-8', 'lat0-sun16'),
    'Korean/Republic_of_Korea': ('ko_KR.UTF-8', 'lat0-sun16'),
    'Lao/Laos': ('lo_LA.UTF-8', 'latarcyrheb-sun16'),
    'Latvian/Latvia': ('lv_LV.UTF-8', 'latarcyrheb-sun16'),
    'Lithuanian': ('lt_LT.UTF-8', 'latarcyrheb-sun16'),
    'Macedonian': ('mk_MK.UTF-8', 'latarcyrheb-sun16'),
    'Malay/Malaysia': ('ms_MY.UTF-8', 'latarcyrheb-sun16'),
    'Maltese/malta': ('mt_MT.UTF-8', 'latarcyrheb-sun16'),
    'Manx/Britain': ('gv_GB.UTF-8', 'latarcyrheb-sun16'),
    'Marathi/India': ('mr_IN.UTF-8', 'latarcyrheb-sun16'),
    'Northern/Norway': ('se_NO', 'latarcyrheb-sun16'),
    'Norwegian': ('nb_NO.UTF-8', 'latarcyrheb-sun16'),
    'Norwegian,/Norway': ('nn_NO.UTF-8', 'latarcyrheb-sun16'),
    'Occitan/France': ('oc_FR', 'lat0-sun16'),
    'Oriya/India': ('or_IN.UTF-8', 'latarcyrheb-sun16'),
    'Persian/Iran': ('fa_IR.UTF-8', 'latarcyrheb-sun16'),
    'Polish': ('pl_PL.UTF-8', 'latarcyrheb-sun16'),
    'Portuguese/Brasil': ('pt_BR.UTF-8', 'latarcyrheb-sun16'),
    'Portuguese/Portugal': ('pt_PT.UTF-8', 'latarcyrheb-sun16'),
    'Punjabi/India': ('pa_IN.UTF-8', 'latarcyrheb-sun16'),
    'Romanian': ('ro_RO.UTF-8', 'latarcyrheb-sun16'),
    'Russian': ('ru_RU.UTF-8', 'latarcyrheb-sun16'),
    'Russian/Ukraine': ('ru_UA.UTF-8', 'latarcyrheb-sun16'),
    'Serbian': ('sr_CS.UTF-8', 'latarcyrheb-sun16'),
    'Serbian/Latin': ('sr_CS.UTF-8@Latn', 'latarcyrheb-sun16'),
    'Slovak': ('sk_SK.UTF-8', 'latarcyrheb-sun16'),
    'Slovenian/Slovenia': ('sl_SI.UTF-8', 'latarcyrheb-sun16'),
    'Spanish/Argentina': ('es_AR.UTF-8', 'latarcyrheb-sun16'),
    'Spanish/Bolivia': ('es_BO.UTF-8', 'latarcyrheb-sun16'),
    'Spanish/Chile': ('es_CL.UTF-8', 'latarcyrheb-sun16'),
    'Spanish/Colombia': ('es_CO.UTF-8', 'latarcyrheb-sun16'),
    'Spanish/Costa_Rica': ('es_CR.UTF-8', 'latarcyrheb-sun16'),
    'Spanish/Dominican_Republic': ('es_DO.UTF-8', 'latarcyrheb-sun16'),
    'Spanish/El_Salvador': ('es_SV.UTF-8', 'latarcyrheb-sun16'),
    'Spanish/Equador': ('es_EC.UTF-8', 'latarcyrheb-sun16'),
    'Spanish/Guatemala': ('es_GT.UTF-8', 'latarcyrheb-sun16'),
    'Spanish/Honduras': ('es_HN.UTF-8', 'latarcyrheb-sun16'),
    'Spanish/Mexico': ('es_MX.UTF-8', 'latarcyrheb-sun16'),
    'Spanish/Nicaragua': ('es_NI.UTF-8', 'latarcyrheb-sun16'),
    'Spanish/Panama': ('es_PA.UTF-8', 'latarcyrheb-sun16'),
    'Spanish/Paraguay': ('es_PY.UTF-8', 'latarcyrheb-sun16'),
    'Spanish/Peru': ('es_PE.UTF-8', 'latarcyrheb-sun16'),
    'Spanish/Puerto_Rico': ('es_PR.UTF-8', 'latarcyrheb-sun16'),
    'Spanish/Spain': ('es_ES.UTF-8', 'latarcyrheb-sun16'),
    'Spanish/USA': ('es_US.UTF-8', 'latarcyrheb-sun16'),
    'Spanish/Uruguay': ('es_UY.UTF-8', 'latarcyrheb-sun16'),
    'Spanish/Venezuela': ('es_VE.UTF-8', 'latarcyrheb-sun16'),
    'Swedish/Finland': ('sv_FI.UTF-8', 'latarcyrheb-sun16'),
    'Swedish/Sweden': ('sv_SE.UTF-8', 'latarcyrheb-sun16'),
    'Tagalog/Philippines': ('tl_PH', 'lat0-sun16'),
    'Tamil/India': ('ta_IN.UTF-8', 'latarcyrheb-sun16'),
    'Telugu/India': ('te_IN.UTF-8', 'latarcyrheb-sun16'),
    'Thai': ('th_TH.UTF-8', 'latarcyrheb-sun16'),
    'Turkish': ('tr_TR.UTF-8', 'latarcyrheb-sun16'),
    'Ukrainian': ('uk_UA.UTF-8', 'latarcyrheb-sun16'),
    'Urdu/Pakistan': ('ur_PK', 'latarcyrheb-sun16'),
    'Uzbek/Uzbekistan': ('uz_UZ', 'lat0-sun16'),
    'Walloon/Belgium': ('wa_BE@euro', 'lat0-sun16'),
    'Welsh/Great_Britain': ('cy_GB.UTF-8', 'latarcyrheb-sun16'),
    'Xhosa/South_Africa': ('xh_ZA.UTF-8', 'latarcyrheb-sun16'),
    'Zulu/South_Africa': ('zu_ZA.UTF-8', 'latarcyrheb-sun16')
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
    pro.save()
    _note_restart()
    
def get_color():    
    return profile.get_color()    

def print_color():
    color = get_color().to_string()
    str = color.split(',')

    for color in _COLORS:
        for hue in _COLORS[color]:
            if _COLORS[color][hue] == str[0]:
                print 'stroke: color=%s hue=%s'%(color, hue)
            if _COLORS[color][hue] == str[1]:
                print 'fill:   color=%s hue=%s'%(color, hue)

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
    state = nm.state()
    if state:
        if state == NM_ASLEEP:
            return _('off')
        else:
            return _('on')
    return _('State is unknown.')

def print_radio():
    print get_radio()
    
def set_radio(state):
    """Turn Radio 'on' or 'off'
    state : 'on/off'
    """

    # TODO: NM 0.6.x does not return a reply yet
    # so we ignore it for the moment
    
    if state == 'on':        
        dbus.SystemBus().call_async(NM_SERVICE_NAME, NM_SERVICE_PATH,
                                    NM_SERVICE_IFACE, 'wake', '', (),
                                    None, None)
    elif state == 'off':
        dbus.SystemBus().call_async(NM_SERVICE_NAME, NM_SERVICE_PATH,
                                    NM_SERVICE_IFACE, 'sleep', '', (),
                                    None, None)
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
                print (_("get_timezone: %s") % e)
    except Exception, e:
        print (_("get_timezone: %s") % e)
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
            print (_("Error copying timezone (from %s): %s")%(fromfile, msg))
            return
        try:
            os.chmod("/etc/localtime", 0644)
        except OSError, (errno, msg):
            print (_("Changing permission of timezone: %s") % (msg))
            return
                
        # Write info to the /etc/sysconfig/clock file
        fd = open(_TIMEZONE_CONFIG, "w")
        fd.write('# The ZONE parameter is only evaluated by sugarcontrol.\n')
        fd.write('# The timezone of the system ' +
                 'is defined by the contents of /etc/localtime.\n')
        fd.write('ZONE="%s"\n' % timezone)
        fd.close()                       
    else:
        print (_("Error timezone does not exist."))

def _writeI18N(lang, sysfont):
    path = '/etc/sysconfig/i18n'
    if os.access(path, os.R_OK) == 0:
        print(_("Could not access %s")%path)
    else:
        fd = open(path, 'w')
        fd.write('LANG="' + lang + '"\n')
        fd.write('SYSFONT="' + sysfont + '"\n')
        fd.close()

def get_language():
    originalFile = None
    path = '/etc/sysconfig/i18n'
    if os.access(path, os.R_OK) == 0:
        return None
    else:
        fd = open(path, "r")
        originalFile = fd.readlines()
        fd.close()

    lang = None

    for line in originalFile:
        if line[:5] == "LANG=":
            lang = line[5:].replace('"', '')
            lang = lang.strip()

    if not lang:
        lang = "en_US"            

    return lang

def print_language():
    code = get_language()

    for lang in _LANGUAGES:
        if _LANGUAGES[lang][0] == code:
            print lang
            return
    print (_("Language for code=%s could not be determined.")%code)
    
def set_language(language):
    """Set the system language.
    languages : 
    """
    if not _check_for_superuser():
        return
    if language in _LANGUAGES:
        _writeI18N(_LANGUAGES[language][0], _LANGUAGES[language][1])
        _note_restart()
    else:
        print (_("Sorry I do not speak \'%s\'.")%language)

# inilialize the docstrings for the timezone and language
_initialize()

