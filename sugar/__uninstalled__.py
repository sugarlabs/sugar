import os
import tempfile

sugar_source_dir = os.path.dirname(os.path.dirname(__file__))

sugar_data_dir = os.path.join(sugar_source_dir, 'shell/data') 
sugar_activities_dir = os.path.join(tempfile.gettempdir(), 'sugar')
sugar_dbus_config = os.path.join(sugar_source_dir, 'dbus-uninstalled.conf')

sugar_python_path = []
sugar_python_path.append(sugar_source_dir)
sugar_python_path.append(os.path.join(sugar_source_dir, 'shell'))
sugar_python_path.append(os.path.join(sugar_source_dir, 'activities'))

sugar_bin_path = []
sugar_bin_path.append(os.path.join(sugar_source_dir, 'shell'))
