SUBDIRS = activity bundle clipboard graphics presence datastore

sugardir = $(pythondir)/sugar
sugar_PYTHON =		\
	env.py		\
        network.py	\
	profile.py	\
	sound.py	\
	util.py		\
	wm.py

pkgpyexecdir = $(pythondir)/sugar

pkgpyexec_LTLIBRARIES = _sugarext.la

_sugarext_la_CFLAGS = 		\
	$(LIB_CFLAGS)		\
	$(PYTHON_INCLUDES)

_sugarext_la_LDFLAGS = -module -avoid-version
_sugarext_la_LIBADD = $(LIB_LIBS)

_sugarext_la_SOURCES =			\
	$(BUILT_SOURCES)		\
	_sugarextmodule.c		\
	eggaccelerators.c		\
	eggaccelerators.h		\
	sexy-icon-entry.h		\
	sexy-icon-entry.c		\
	sugar-address-entry.c		\
	sugar-address-entry.h		\
	sugar-key-grabber.c		\
	sugar-key-grabber.h		\
	sugar-menu.h			\
	sugar-menu.c

BUILT_SOURCES = 			\
	_sugarext.c			\
	sugar-marshal.c			\
	sugar-marshal.h

_sugarext.c: _sugarext.defs _sugarext.override

.defs.c:
	(cd $(srcdir)\
	 && $(PYGTK_CODEGEN) \
	    --register $(PYGTK_DEFSDIR)/gdk-types.defs \
	    --register $(PYGTK_DEFSDIR)/gtk-types.defs \
	    --override $*.override \
	    --prefix py$* $*.defs) > gen-$*.c \
	&& cp gen-$*.c $*.c \
	&& rm -f gen-$*.c
	
sugar-marshal.c: sugar-marshal.list
	$(GLIB_GENMARSHAL) --prefix=sugar_marshal \
		$(srcdir)/sugar-marshal.list --header --body > sugar-marshal.c

sugar-marshal.h: sugar-marshal.list
	$(GLIB_GENMARSHAL) --prefix=sugar_marshal \
		$(srcdir)/sugar-marshal.list --header > sugar-marshal.h

CLEANFILES = $(BUILT_SOURCES)
EXTRA_DIST = sugar-marshal.list _sugarext.defs _sugarext.override
