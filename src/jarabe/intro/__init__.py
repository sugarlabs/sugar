import os

from gi.repository import Gio

from sugar4 import env
from sugar4.profile import get_profile


def check_profile():
    profile = get_profile()

    path = os.path.join(env.get_profile_path(), 'config')
    if os.path.exists(path):
        profile.convert_profile()

    return profile.is_valid()


def check_group_label():
    settings = Gio.Settings.new('org.sugarlabs.user')
    if len(settings.get_string('group-label')) > 0:
        return True
    return False
