INCLUDES =			\
	$(PYTHON_INCLUDES)	\
	$(PYGTK_CFLAGS)		\
	$(GLOBALKEYS_CFLAGS)

pkgpythondir = $(pyexecdir)/sugar

globalkeysdir = $(pkgpythondir)
globalkeys_PYTHON = __init__.py

pkgpyexec_LTLIBRARIES = globalkeys.la

globalkeys_la_LDFLAGS = -module -avoid-version
globalkeys_la_LIBADD = $(GLOBALKEYS_LIBS)

globalkeys_la_SOURCES = 	\
	globalkeysmodule.c	\
	sugar-key-grabber.h	\
	sugar-key-grabber.c

nodist_globalkeys_la_SOURCES = globalkeys.c

globalkeys.c: globalkeys.defs globalkeys.override

CLEANFILES = globalkeys.c
EXTRA_DIST = globalkeys.override globalkeys.defs

.defs.c:
	(cd $(srcdir)\
	 && $(PYGTK_CODEGEN) \
	    --override $*.override \
	    --prefix py$* $*.defs) > gen-$*.c \
	&& cp gen-$*.c $*.c \
	&& rm -f gen-$*.c
