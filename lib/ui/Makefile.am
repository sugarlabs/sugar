libsugarui_la_CPPFLAGS =		\
	$(LIBUI_CFLAGS)
	
noinst_LTLIBRARIES = libsugarui.la

libsugarui_la_LIBADD = 			\
	$(LIBUI_LIBS)

libsugarui_la_SOURCES =			\
	$(BUILT_SOURCES)		\
	eggaccelerators.c		\
	eggaccelerators.h		\
	sugar-address-entry.c		\
	sugar-address-entry.h		\
	sugar-key-grabber.c		\
	sugar-key-grabber.h		\
	sugar-menu.h			\
	sugar-menu.c			\
	sugar-x11-util.c		\
	sugar-x11-util.h

BUILT_SOURCES = 		\
	sugar-marshal.c		\
	sugar-marshal.h

stamp_files = 			\
	stamp-sugar-marshal.c	\
	stamp-sugar-marshal.h

sugar-marshal.c: stamp-sugar-marshal.c
	@true
stamp-sugar-marshal.c: sugar-marshal.list
	$(GLIB_GENMARSHAL) --prefix=sugar_marshal \
		$(srcdir)/sugar-marshal.list --header --body > \
		sugar-marshal.c && echo timestamp > $(@F)

sugar-marshal.h: stamp-sugar-marshal.h
	@true
stamp-sugar-marshal.h: sugar-marshal.list
	$(GLIB_GENMARSHAL) --prefix=sugar_marshal \
		$(srcdir)/sugar-marshal.list --header > \
		sugar-marshal.h && echo timestamp > $(@F)

CLEANFILES = $(stamp_files) $(BUILT_SOURCES)
DISTCLEANFILES = $(stamp_files) $(BUILT_SOURCES)
MAINTAINERCLEANFILES = $(stamp_files) $(BUILT_SOURCES)

EXTRA_DIST = sugar-marshal.list
