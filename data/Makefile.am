SUBDIRS = icons

sugar-72.gtkrc: gtkrc.em
	$(srcdir)/em.py -D scaling=\'72\' $(srcdir)/gtkrc.em > \
		$(top_builddir)/data/sugar-72.gtkrc

sugar-100.gtkrc: gtkrc.em
	$(srcdir)/em.py -D scaling=\'100\' $(srcdir)/gtkrc.em > \
		$(top_builddir)/data/sugar-100.gtkrc

sugardir = $(pkgdatadir)/data
sugar_DATA =			\
	activities.defaults	\
	kbdconfig		\
	mime.defaults		\
	$(GTKRC_FILES)

GTKRC_FILES =		\
	sugar-72.gtkrc	\
	sugar-100.gtkrc

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

EXTRA_DIST = $(sugar_DATA) $(xsessions_DATA) $(mime_xml_in_files) em.py gtkrc.em
CLEANFILES = $(GTKRC_FILES) $(mime_xml_files)
