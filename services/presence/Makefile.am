servicedir = $(datadir)/dbus-1/services
service_in_files = org.laptop.Sugar.Presence.service.in
service_DATA = $(service_in_files:.service.in=.service)

$(service_DATA): $(service_in_files) Makefile
	@sed -e "s|\@bindir\@|$(bindir)|" $< > $@

sugardir = $(pkgdatadir)/services/presence
sugar_PYTHON = \
	__init__.py \
	activity.py \
	buddy.py \
	buddyiconcache.py \
	linklocal_plugin.py \
	presenceservice.py \
	server_plugin.py

bin_SCRIPTS = sugar-presence-service

DISTCLEANFILES = $(service_DATA)

EXTRA_DIST = $(service_in_files) $(bin_SCRIPTS)
