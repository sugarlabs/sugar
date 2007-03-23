import gettext
import os
import logging

from sugar.activity import activity

activity_path = activity.get_bundle_path()
service_name = os.environ['SUGAR_BUNDLE_SERVICE_NAME']
gettext.bindtextdomain(service_name, os.path.join(activity_path, "locale"))
gettext.textdomain(service_name)
_ = gettext.gettext
