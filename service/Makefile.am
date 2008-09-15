servicedir = $(datadir)/dbus-1/services

service_in_files =                              \
    org.laptop.ActivityRegistry.service.in

service_DATA =					\
    org.laptop.ActivityRegistry.service

org.laptop.ActivityRegistry.service: org.laptop.ActivityRegistry.service.in Makefile
	@sed -e "s|\@bindir\@|$(bindir)|" $< > $@

sugardir = $(pkgdatadir)/service

sugar_PYTHON =				\
	__init__.py			\
	activityregistryservice.py	\
	bundleregistry.py		\
	config.py			\
	main.py

DISTCLEANFILES = $(service_DATA)

EXTRA_DIST = $(service_in_files)
