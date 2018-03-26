import os

from gi.repository import Gio

from sugar3 import env
from sugar3.profile import get_profile


def check_profile():
    profile = get_profile()

    path = os.path.join(env.get_profile_path(), 'config')
    if os.path.exists(path):
        profile.convert_profile()

    return profile.is_valid()


def check_group_label():
    settings = Gio.Settings('org.sugarlabs.user')
    if len(settings.get_string('group-label')) > 0:
        return True
    return False
