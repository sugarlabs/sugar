servicedir = $(datadir)/dbus-1/services
service_in_files = org.laptop.Clipboard.service.in
service_DATA = $(service_in_files:.service.in=.service)

$(service_DATA): $(service_in_files) Makefile
	@sed -e "s|\@bindir\@|$(bindir)|" $< > $@

sugardir = $(pkgdatadir)/services/clipboard
sugar_PYTHON =			\
	__init__.py			\
	ClipboardService.py

bin_SCRIPTS = sugar-clipboard

EXTRA_DIST = $(service_in_files) $(bin_SCRIPTS)
