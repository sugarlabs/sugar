sugar.gtkrc: gtkrc.em
	$(srcdir)/em.py -D theme=\'sugar\' $(srcdir)/gtkrc.em > \
		$(top_builddir)/data/sugar.gtkrc

sugar-xo.gtkrc: gtkrc.em
	$(srcdir)/em.py -D theme=\'sugar-xo\' $(srcdir)/gtkrc.em > \
		$(top_builddir)/data/sugar-xo.gtkrc

sugardir = $(pkgdatadir)/data
sugar_DATA =		\
	$(GTKRC_FILES)

GTKRC_FILES =		\
	sugar.gtkrc	\
	sugar-xo.gtkrc


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

EXTRA_DIST = $(sugar_DATA) $(mime_xml_in_files) em.py gtkrc.em
CLEANFILES = $(GTKRC_FILES) $(mime_xml_files)
