SUBDIRS = activities shell sugar tools threadframe

dbusconfdir = $(pkgdatadir)
dbusconf_DATA = dbus-installed.conf

install-data-local:
	sugar/setup.py $(top_srcdir)/activities $(pkgdatadir)/activities $(bindir)/sugar-activity-factory
