SUBDIRS = interface lib

servicedir = $(datadir)/dbus-1/services
service_in_files = org.laptop.sugar.Console.service.in
service_DATA = $(service_in_files:.service.in=.service)

$(service_DATA): $(service_in_files) Makefile
	@sed -e "s|\@bindir\@|$(bindir)|" $< > $@

sugardir = $(pkgdatadir)/services/console
sugar_PYTHON =				\
	__init__.py			\
	console.py

bin_SCRIPTS = sugar-console

DISTCLEANFILES = $(service_DATA)

EXTRA_DIST = $(service_in_files) $(bin_SCRIPTS)
