libsugarbrowser_la_CPPFLAGS =				\
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
	-I$(MOZILLA_INCLUDE_DIR)/shistory		\
	-I$(MOZILLA_INCLUDE_DIR)/uriloader		\
	-I$(MOZILLA_INCLUDE_DIR)/webbrwsr		\
	-I$(MOZILLA_INCLUDE_DIR)/webbrowserpersist	\
	-DPLUGIN_DIR=\"$(libdir)/mozilla/plugins\"	\
	-DSHARE_DIR=\"$(pkgdatadir)\"
	
noinst_LTLIBRARIES = libsugarbrowser.la

libsugarbrowser_la_LIBADD = \
	$(LIB_LIBS) 		\
	$(GECKO_LIBS)

libsugarbrowser_la_SOURCES =		\
	$(BUILT_SOURCES)		\
	GeckoContentHandler.h		\
	GeckoContentHandler.cpp		\
	GeckoDownload.h			\
	GeckoDownload.cpp		\
	sugar-address-entry.c		\
	sugar-address-entry.h		\
	sugar-browser.h			\
	sugar-browser.cpp		\
	sugar-download.h		\
	sugar-download.c		\
	sugar-download-manager.h	\
	sugar-download-manager.c

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
