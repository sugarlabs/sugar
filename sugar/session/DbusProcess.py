import os

from sugar.session.Process import Process
from sugar import env

class DbusProcess(Process):
	def __init__(self):
		config = env.get_dbus_config()
		cmd = "dbus-daemon --print-address --config-file %s" % config
		Process.__init__(self, cmd)

	def get_name(self):
		return 'Dbus'

	def start(self):
		Process.start(self, True)
		dbus_file = os.fdopen(self._stdout)
		addr = dbus_file.readline().strip()
		dbus_file.close()
		os.environ["DBUS_SESSION_BUS_ADDRESS"] = addr
