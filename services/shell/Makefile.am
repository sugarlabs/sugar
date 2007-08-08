servicedir = $(datadir)/dbus-1/services

service_in_files =                              \
    org.laptop.ActivityRegistry.service.in      \
    org.laptop.Clipboard.service.in             \
    org.laptop.ObjectTypeRegistry.service.in

service_DATA =					\
    org.laptop.ActivityRegistry.service		\
    org.laptop.Clipboard.service		\
    org.laptop.ObjectTypeRegistry.service

org.laptop.ActivityRegistry.service: org.laptop.ActivityRegistry.service.in Makefile
	@sed -e "s|\@bindir\@|$(bindir)|" $< > $@

org.laptop.Clipboard.service: org.laptop.Clipboard.service.in Makefile
	@sed -e "s|\@bindir\@|$(bindir)|" $< > $@

org.laptop.ObjectTypeRegistry.service: org.laptop.ObjectTypeRegistry.service.in Makefile
	@sed -e "s|\@bindir\@|$(bindir)|" $< > $@

sugardir = $(pkgdatadir)/services/shell

sugar_PYTHON =				\
	__init__.py			\
	activityregistryservice.py	\
	bundleregistry.py		\
	clipboardobject.py      	\
	clipboardservice.py     	\
	objecttypeservice.py

bin_SCRIPTS = sugar-shell-service

DISTCLEANFILES = $(service_DATA)

EXTRA_DIST = $(service_in_files) $(bin_SCRIPTS)

