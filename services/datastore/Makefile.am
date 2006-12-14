servicedir = $(datadir)/dbus-1/services
service_in_files = org.laptop.sugar.DataStore.service.in
service_DATA = $(service_in_files:.service.in=.service)

$(service_DATA): $(service_in_files) Makefile
	@sed -e "s|\@bindir\@|$(bindir)|" $< > $@

sugardir = $(pkgdatadir)/services/datastore
sugar_PYTHON =      \
	__init__.py     \
	datastore.py    \
	dbus_helpers.py

bin_SCRIPTS = sugar-data-store

EXTRA_DIST = $(bin_SCRIPTS) org.laptop.sugar.DataStore.service.in
