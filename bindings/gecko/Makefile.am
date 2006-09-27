INCLUDES =			\
	$(PYTHON_INCLUDES)	\
	$(PYGTK_CFLAGS)		\
	$(GECKO_CFLAGS)

geckodir = $(pkgdatadir)/bindings
pkgpyexecdir = $(geckodir)

pkgpyexec_LTLIBRARIES = gecko.la

gecko_la_LDFLAGS = -module -avoid-version
gecko_la_LIBADD = $(GECKO_LIBS)

gecko_la_SOURCES = 		\
	geckomodule.c		\
	gecko-browser.h		\
	gecko-browser.cpp

nodist_gecko_la_SOURCES = gecko.c

gecko.c: gecko.defs gecko.override

CLEANFILES = gecko.c
EXTRA_DIST = gecko.override gecko.defs

.defs.c:
	(cd $(srcdir)\
	 && $(PYGTK_CODEGEN) \
	    --register $(GNOMEPYTHONEXTRAS_DEFSDIR)/gtkmozembed.defs \
	    --override $*.override \
	    --prefix py$* $*.defs) > gen-$*.c \
	&& cp gen-$*.c $*.c \
	&& rm -f gen-$*.c
