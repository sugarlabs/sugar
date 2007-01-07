INCLUDES =				\
	$(PYTHON_INCLUDES)		\
	$(PYGTK_CFLAGS)			\
	$(PYCAIRO_CFLAGS)			\
	$(LIB_CFLAGS)			\
	-I $(top_srcdir)/lib/src

pkgpyexecdir = $(pythondir)

pkgpyexec_LTLIBRARIES = _sugar.la

_sugar_la_LDFLAGS = -module -avoid-version -R$(MOZILLA_HOME)
_sugar_la_LIBADD =					\
	$(LIB_LIBS)					\
	$(PYCAIRO_LIBS)					\
	$(top_builddir)/lib/src/libsugarprivate.la

_sugar_la_SOURCES = 		\
	_sugarmodule.c

nodist__sugar_la_SOURCES = _sugar.c

_sugar.c: _sugar.defs _sugar.override

CLEANFILES = _sugar.c
EXTRA_DIST = _sugar.override _sugar.defs

.defs.c:
	(cd $(srcdir)\
	 && $(PYGTK_CODEGEN) \
	    --register $(PYGTK_DEFSDIR)/gdk-types.defs \
	    --register $(PYGTK_DEFSDIR)/gtk-types.defs \
	    --register $(GNOMEPYTHONEXTRAS_DEFSDIR)/gtkmozembed.defs \
	    --override $*.override \
	    --prefix py$* $*.defs) > gen-$*.c \
	&& cp gen-$*.c $*.c \
	&& rm -f gen-$*.c
