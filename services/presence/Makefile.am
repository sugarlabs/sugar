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
	pstest.py \
	psutils.py \
	server_plugin.py

dist_bin_SCRIPTS = sugar-presence-service

DISTCLEANFILES = $(service_DATA)

EXTRA_DIST = $(service_in_files)

dist_check_SCRIPTS = test_psutils.py

TESTS_ENVIRONMENT = \
		    PYTHONPATH=$(top_srcdir):$(top_srcdir)/services/presence \
		    $(PYTHON)
TESTS = $(dist_check_SCRIPTS)
