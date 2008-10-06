import os

import gtk

from sugar.profile import get_profile

from jarabe.intro.window import IntroWindow
from jarabe.intro.window import create_profile

def check_profile():
    if not get_profile().is_valid():
        if 'SUGAR_PROFILE_NAME' in os.environ:
            create_profile(os.environ['SUGAR_PROFILE_NAME'])
        else:
            win = IntroWindow()
            win.show_all()
            gtk.main()

