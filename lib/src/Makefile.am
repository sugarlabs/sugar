libsugarprivate_la_CPPFLAGS =				\
	$(WARN_CFLAGS)					\
	$(LIB_CFLAGS)					\
	$(GECKO_CFLAGS)					\
	$(NSPR_CFLAGS)					\
	-I$(MOZILLA_INCLUDE_DIR)/dom			\
	-I$(MOZILLA_INCLUDE_DIR)/docshell		\
	-I$(MOZILLA_INCLUDE_DIR)/exthandler		\
	-I$(MOZILLA_INCLUDE_DIR)/gtkembedmoz		\
	-I$(MOZILLA_INCLUDE_DIR)/imglib2		\
	-I$(MOZILLA_INCLUDE_DIR)/mimetype   		\
	-I$(MOZILLA_INCLUDE_DIR)/necko			\
	-I$(MOZILLA_INCLUDE_DIR)/pref			\
	-I$(MOZILLA_INCLUDE_DIR)/uriloader		\
	-I$(MOZILLA_INCLUDE_DIR)/webbrwsr		\
	-I$(MOZILLA_INCLUDE_DIR)/webbrowserpersist	\
	-DPLUGIN_DIR=\"$(libdir)/mozilla/plugins\"	\
	-DSHARE_DIR=\"$(pkgdatadir)\"
	
noinst_LTLIBRARIES = libsugarprivate.la

libsugarprivate_la_LIBADD = \
	$(LIB_LIBS) 		\
	$(GECKO_LIBS) 		\
	-lgstinterfaces-0.10	\
	-lgstaudio-0.10

libsugarprivate_la_SOURCES =		\
	$(BUILT_SOURCES)		\
	eggaccelerators.h		\
	eggaccelerators.c		\
	GeckoContentHandler.h		\
	GeckoContentHandler.cpp		\
	GeckoDownload.h			\
	GeckoDownload.cpp		\
	sugar-address-entry.h		\
	sugar-address-entry.c		\
	sugar-audio-manager.c		\
	sugar-audio-manager.h		\
	sugar-browser.h			\
	sugar-browser.cpp		\
	sugar-download.h		\
	sugar-download.c		\
	sugar-download-manager.h	\
	sugar-download-manager.c	\
	sugar-key-grabber.h		\
	sugar-key-grabber.c		\
	sugar-push-scroller.c		\
	sugar-push-scroller.h		\
	sugar-utils.c			\
	sugar-utils.h

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
