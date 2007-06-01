SUBDIRS = activity clipboard graphics objects presence datastore

sugardir = $(pythondir)/sugar
sugar_PYTHON =		\
	__init__.py	\
	date.py		\
	env.py		\
	logger.py	\
        ltihooks.py	\
	profile.py	\
	util.py		\
	x11.py

INCLUDES = 				\
	$(LIB_CFLAGS)			\
	$(LIB_BINDINGS_CFLAGS)		\
	$(PYTHON_INCLUDES)		\
	-I$(top_srcdir)/lib		\
	-I$(top_srcdir)/lib/xdgmime

pkgpyexecdir = $(pythondir)/sugar

pkgpyexec_LTLIBRARIES = _sugarext.la

_sugarext_la_LDFLAGS = -module -avoid-version
_sugarext_la_LIBADD =			\
	$(LIB_BINDINGS_LIBS)		\
	$(LIB_LIBS)			\
	$(top_builddir)/lib/libsugar.la

_sugarext_la_SOURCES = 		\
	_sugarextmodule.c

nodist__sugarext_la_SOURCES = _sugarext.c

_sugarext.c: _sugarext.defs _sugarext.override

CLEANFILES = _sugarext.c
EXTRA_DIST = _sugarext.override _sugarext.defs

.defs.c:
	(cd $(srcdir)\
	 && $(PYGTK_CODEGEN) \
	    --register $(PYGTK_DEFSDIR)/gdk-types.defs \
	    --register $(PYGTK_DEFSDIR)/gtk-types.defs \
	    --override $*.override \
	    --prefix py$* $*.defs) > gen-$*.c \
	&& cp gen-$*.c $*.c \
	&& rm -f gen-$*.c
