servicedir = $(datadir)/dbus-1/services

service_in_files =                              \
    org.laptop.ActivityRegistry.service.in      \
    org.laptop.Clipboard.service.in

service_DATA =					\
    org.laptop.ActivityRegistry.service		\
    org.laptop.Clipboard.service

org.laptop.ActivityRegistry.service: org.laptop.ActivityRegistry.service.in Makefile
	@sed -e "s|\@bindir\@|$(bindir)|" $< > $@

org.laptop.Clipboard.service: org.laptop.Clipboard.service.in Makefile
	@sed -e "s|\@bindir\@|$(bindir)|" $< > $@

org.laptop.ObjectTypeRegistry.service: org.laptop.ObjectTypeRegistry.service.in Makefile
	@sed -e "s|\@bindir\@|$(bindir)|" $< > $@

sugardir = $(pkgdatadir)/service

sugar_PYTHON =				\
	__init__.py			\
	activityregistryservice.py	\
	bundleregistry.py		\
	clipboardobject.py      	\
	clipboardservice.py		\
	main.py

DISTCLEANFILES = $(service_DATA)

EXTRA_DIST = $(service_in_files)
