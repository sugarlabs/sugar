INCLUDES =					\
	$(WARN_CFLAGS)				\
	$(LIB_CFLAGS)				\
	-I$(MOZILLA_INCLUDE_DIR)/exthandler

noinst_LTLIBRARIES = libsugarprivate.la

libsugarprivate_la_LIBADD = $(GECKO_LIBS)

libsugarprivate_la_SOURCES = 	\
	$(BUILT_SOURCES)	\
	eggaccelerators.h	\
	eggaccelerators.c	\
	sugar-browser.h		\
	sugar-browser.cpp	\
	sugar-address-entry.h	\
	sugar-address-entry.c	\
	sugar-key-grabber.h	\
	sugar-key-grabber.c	\
	sugar-push-scroller.c	\
	sugar-push-scroller.h	\
	sugar-tray-manager.c	\
	sugar-tray-manager.h

BUILT_SOURCES = 		\
	sugar-marshal.c		\
	sugar-marshal.h

stamp_files = \
	stamp-sugar-marshal.c		\
	stamp-sugar-marshal.h

sugar-marshal.c: stamp-sugar-marshal.c
	@true
stamp-sugar-marshal.c: sugar-marshal.list
	$(GLIB_GENMARSHAL) --prefix=sugar_marshal $(srcdir)/sugar-marshal.list --header --body > sugar-marshal.c \
	&& echo timestamp > $(@F)

sugar-marshal.h: stamp-sugar-marshal.h
	@true
stamp-sugar-marshal.h: sugar-marshal.list
	$(GLIB_GENMARSHAL) --prefix=sugar_marshal $(srcdir)/sugar-marshal.list --header > sugar-marshal.h \
	&& echo timestamp > $(@F)

CLEANFILES = $(stamp_files) $(BUILT_SOURCES)
DISTCLEANFILES = $(stamp_files) $(BUILT_SOURCES)
MAINTAINERCLEANFILES = $(stamp_files) $(BUILT_SOURCES)

EXTRA_DIST = sugar-marshal.list
