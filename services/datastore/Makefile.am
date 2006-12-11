sugardir = $(pkgdatadir)/services/data-store
sugar_PYTHON =      \
	__init__.py     \
	datastore.py    \
	dbus_helpers.py

bin_SCRIPTS = sugar-data-store

dbusservicedir = $(sysconfdir)/dbus-1/system.d/
dbusservice_DATA = sugar-data-store.conf

EXTRA_DIST = $(dbusservice_DATA) $(bin_SCRIPTS)
