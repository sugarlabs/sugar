sugardir = $(pkgdatadir)/shell/hardware
sugar_PYTHON =				\
	__init__.py			\
	hardwaremanager.py		\
	keydialog.py			\
	nmclient.py			\
	nminfo.py			\
	schoolserver.py

dbusservicedir = $(sysconfdir)/dbus-1/system.d/
dbusservice_DATA = NetworkManagerInfo.conf

EXTRA_DIST = $(dbusservice_DATA)
