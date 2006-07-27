import os

_source_dir = os.path.dirname(os.path.dirname(__file__))

sugar_data_dir = os.path.join(_source_dir, 'shell/data') 
sugar_activities_dir = os.path.join(_source_dir, 'activities')
sugar_dbus_config = os.path.join(_source_dir, 'dbus-uninstalled.conf')
