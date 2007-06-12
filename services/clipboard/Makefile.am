servicedir = $(datadir)/dbus-1/services

service_in_files =                              \
    org.laptop.Clipboard.service.in             \
    org.laptop.ObjectTypeRegistry.service.in

service_DATA =					\
    org.laptop.Clipboard.service		\
    org.laptop.ObjectTypeRegistry.service

org.laptop.Clipboard.service: org.laptop.Clipboard.service.in Makefile
	@sed -e "s|\@bindir\@|$(bindir)|" $< > $@

org.laptop.ObjectTypeRegistry.service: org.laptop.ObjectTypeRegistry.service.in Makefile
	@sed -e "s|\@bindir\@|$(bindir)|" $< > $@

sugardir = $(pkgdatadir)/services/clipboard

sugar_PYTHON =			\
	__init__.py		\
	clipboardobject.py      \
	clipboardservice.py     \
	objecttypeservice.py    \
	typeregistry.py

bin_SCRIPTS = sugar-clipboard

DISTCLEANFILES = $(service_DATA)

EXTRA_DIST = $(service_in_files) $(bin_SCRIPTS)
