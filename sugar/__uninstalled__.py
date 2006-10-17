import os
import tempfile

_tmpdir = os.path.join(tempfile.gettempdir(), 'sugar')
_sourcedir = os.path.dirname(os.path.dirname(__file__))

sugar_data_dir = os.path.join(_sourcedir, 'shell/data')
sugar_services_dir = os.path.join(_sourcedir, 'services')
sugar_activity_info_dir = _tmpdir
sugar_dbus_config = os.path.join(_sourcedir, 'dbus-uninstalled.conf')
