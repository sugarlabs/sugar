SUBDIRS = activity bundle clipboard graphics objects presence datastore

sugardir = $(pythondir)/sugar
sugar_PYTHON =		\
	env.py		\
        network.py	\
	profile.py	\
	util.py		\
	wm.py

pkgpyexecdir = $(pythondir)/sugar

pkgpyexec_LTLIBRARIES = _sugaruiext.la

_sugaruiext_la_CFLAGS = 		\
	$(LIBUI_CFLAGS)			\
	$(LIBUI_BINDINGS_CFLAGS)	\
	$(PYTHON_INCLUDES)		\
	-I$(top_srcdir)/lib

_sugaruiext_la_LDFLAGS = -module -avoid-version
_sugaruiext_la_LIBADD =				\
	$(LIBUI_BINDINGS_LIBS)			\
	$(LIBUI_LIBS)				\
	$(top_builddir)/lib/libsugarui.la

_sugaruiext_la_SOURCES = 		\
	_sugaruiextmodule.c

nodist__sugaruiext_la_SOURCES = _sugaruiext.c

_sugaruiext.c: _sugaruiext.defs _sugaruiext.override

CLEANFILES = _sugaruiext.c

EXTRA_DIST =			\
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
