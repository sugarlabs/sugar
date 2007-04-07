sugardir = $(pythondir)/sugar/browser
sugar_PYTHON =		\
	__init__.py

INCLUDES =					\
	$(PYTHON_INCLUDES)			\
	$(PYGTK_CFLAGS)				\
	$(PYCAIRO_CFLAGS)			\
	$(LIB_CFLAGS)				\
	$(GECKO_CFLAGS)				\
	$(NSPR_CFLAGS)				\
	-I$(MOZILLA_INCLUDE_DIR)/gtkembedmoz	\
	-I$(top_srcdir)/browser

pkgpyexecdir = $(pythondir)/sugar/browser

pkgpyexec_LTLIBRARIES = _sugarbrowser.la

_sugarbrowser_la_LDFLAGS = -module -avoid-version $(GECKO_LDFLAGS)
_sugarbrowser_la_LIBADD =				\
	$(LIB_LIBS)					\
	$(PYCAIRO_LIBS)					\
	$(GECKO_LIBS)					\
	$(XPCOMGLUE_LIBS)				\
	$(top_builddir)/browser/libsugarbrowser.la

_sugarbrowser_la_SOURCES = 	\
	_sugarbrowsermodule.c	\
	xulrunner.cpp		\
	xulrunner.h

nodist__sugarbrowser_la_SOURCES = _sugarbrowser.c

_sugar.c: _sugarbrowser.defs gtkmozembed.defs _sugarbrowser.override gtkmozembed.override

CLEANFILES = _sugar.c
EXTRA_DIST = _sugarbrowser.override _sugarbrowser.defs gtkmozembed.defs gtkmozembed.override

.defs.c:
	(cd $(srcdir)\
	 && $(PYGTK_CODEGEN) \
	    --register $(PYGTK_DEFSDIR)/gdk-types.defs \
	    --register $(PYGTK_DEFSDIR)/gtk-types.defs \
	    --override $*.override \
	    --prefix py$* $*.defs) > gen-$*.c \
	&& cp gen-$*.c $*.c \
	&& rm -f gen-$*.c
