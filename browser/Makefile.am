sugardir = $(pythondir)/sugar
sugar_PYTHON = browser.py

icondir = $(pkgdatadir)
icon_DATA =		\
	fold.png	\
	unfold.png

# Dbus service file
servicedir = $(datadir)/dbus-1/services
service_in_files = com.redhat.Sugar.Browser.service.in
service_DATA = $(service_in_files:.service.in=.service)
 
# Rule to make the service file with bindir expanded
$(service_DATA): $(service_in_files) Makefile
	@sed -e "s|\@bindir\@|$(bindir)|" $< > $@

EXTRA_DIST =			\
	$(service_in_files)	\
	$(service_DATA)

DISTCLEANFILES =		\
	$(service_DATA)
