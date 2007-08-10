SUBDIRS = activity clipboard graphics objects presence datastore

sugardir = $(pythondir)/sugar
sugar_PYTHON =		\
	__init__.py	\
	date.py		\
	env.py		\
	logger.py	\
        ltihooks.py	\
        network.py	\
	profile.py	\
	util.py		\
	wm.py

pkgpyexecdir = $(pythondir)/sugar

pkgpyexec_LTLIBRARIES = _sugarext.la _sugaruiext.la

_sugarext_la_CFLAGS = 			\
	$(LIB_CFLAGS)			\
	$(LIB_BINDINGS_CFLAGS)		\
	$(PYTHON_INCLUDES)		\
	-I$(top_srcdir)/lib

_sugarext_la_LDFLAGS = -module -avoid-version
_sugarext_la_LIBADD =				\
	$(LIB_BINDINGS_LIBS)			\
	$(top_builddir)/lib/libsugar.la

_sugarext_la_SOURCES = 		\
	_sugarextmodule.c

nodist__sugarext_la_SOURCES = _sugarext.c

_sugarext.c: _sugarext.defs _sugarext.override

_sugaruiext_la_CFLAGS = 		\
	$(LIBUI_CFLAGS)			\
	$(LIBUI_BINDINGS_CFLAGS)	\
	$(PYTHON_INCLUDES)		\
	-I$(top_srcdir)/lib/ui

_sugaruiext_la_LDFLAGS = -module -avoid-version
_sugaruiext_la_LIBADD =				\
	$(LIBUI_BINDINGS_LIBS)			\
	$(LIBUI_LIBS)				\
	$(top_builddir)/lib/ui/libsugarui.la

_sugaruiext_la_SOURCES = 		\
	_sugaruiextmodule.c

nodist__sugaruiext_la_SOURCES = _sugaruiext.c

_sugaruiext.c: _sugaruiext.defs _sugaruiext.override

CLEANFILES = 		\
	_sugarext.c	\
	_sugaruiext.c

EXTRA_DIST =			\
	_sugarext.override	\
	_sugarext.defs		\
	_sugaruiext.defs	\
	_sugaruiext.override

.defs.c:
	(cd $(srcdir)\
	 && $(PYGTK_CODEGEN) \
	    --register $(PYGTK_DEFSDIR)/gdk-types.defs \
	    --register $(PYGTK_DEFSDIR)/gtk-types.defs \
	    --override $*.override \
	    --prefix py$* $*.defs) > gen-$*.c \
	&& cp gen-$*.c $*.c \
	&& rm -f gen-$*.c
