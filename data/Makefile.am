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

EXTRA_DIST = $(sugar_DATA) em.py gtkrc.em
CLEANFILES = $(GTKRC_FILES)
