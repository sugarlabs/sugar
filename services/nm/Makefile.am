sugardir = $(pkgdatadir)/services/nm
sugar_PYTHON =			\
	__init__.py			\
	nmclient.py			\
	nminfo.py			\
	bubble.py			\
	wepkeydialog.py

bin_SCRIPTS = sugar-nm-applet

dbusservicedir = $(sysconfdir)/dbus-1/system.d/
dbusservice_DATA = NetworkManagerInfo.conf

EXTRA_DIST = $(dbusservice_DATA) $(bin_SCRIPTS)
