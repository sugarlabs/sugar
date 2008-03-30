sugardir = $(pkgdatadir)/data
sugar_DATA =			\
	activities.defaults	\
	kbdconfig		\
	mime.defaults

xsessionsdir = $(datadir)/xsessions
xsessions_DATA = sugar.desktop

mime_xml_in_files = sugar.xml.in
mime_xml_files = $(mime_xml_in_files:.xml.in=.xml)
@INTLTOOL_XML_RULE@

mimedir = $(datadir)/mime/packages
mime_DATA = $(mime_xml_files)

install-data-hook:
if ENABLE_UPDATE_MIMEDB
	if [ -z "$$DESTDIR" ]; then \
		update-mime-database "$(datadir)/mime"; \
	fi
endif

uninstall-hook:
if ENABLE_UPDATE_MIMEDB
	if [ -z "$$DESTDIR" ]; then \
		update-mime-database "$(datadir)/mime"; \
	fi
endif

EXTRA_DIST = $(sugar_DATA) $(xsessions_DATA) $(mime_xml_in_files)
CLEANFILES = $(mime_xml_files)
