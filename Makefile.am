SUBDIRS = activities lib po shell sugar services tools

ACLOCAL_AMFLAGS = -I m4

dbusconfdir = $(pkgdatadir)
dbusconf_DATA = dbus-installed.conf

bin_SCRIPTS = 				\
	sugar-emulator

install-data-local:
	$(top_srcdir)/sugar/setup.py \
		$(top_srcdir)/activities \
		$(DESTDIR)$(pkgdatadir)/activities \
		$(bindir)/sugar-activity-factory

uninstall-local:
	rm -rf $(DESTDIR)$(pkgdatadir)/activities/*.activity
	rm -rf $(DESTDIR)$(pkgdatadir)/activities/*.service

DISTCLEANFILES =		\
	intltool-extract	\
	intltool-merge		\
	intltool-update

EXTRA_DIST =                    \
	COPYING.LIB		\
	intltool-merge.in       \
	intltool-update.in      \
	intltool-extract.in
