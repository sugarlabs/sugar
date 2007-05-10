sessionstoredir = $(pkgdatadir)/mozilla/components

sessionstore_DATA =		\
	nsISessionStore.xpt	\
	nsSessionStore.js

EXTRA_DIST = $(sessionstore_DATA)

BUILT_SOURCES = \
	nsISessionStore.xpt	\
	nsISessionStore.h

stamp_files = \
	stamp-nsISessionStore.xpt	\
	stamp-nsISessionStore.h

nsISessionStore.xpt: stamp-nsISessionStore.xpt
	@true
stamp-nsISessionStore.xpt: nsISessionStore.idl
	$(XPIDL) -m typelib -w -v -I $(MOZILLA_IDL_DIR) -e nsISessionStore.xpt \
	nsISessionStore.idl \
	&& echo timestamp > $(@F)

nsISessionStore.h: stamp-nsISessionStore.h
	@true
stamp-nsISessionStore.h: nsISessionStore.idl
	$(XPIDL) -m header -w -v -I $(MOZILLA_IDL_DIR) -e nsISessionStore.h \
	nsISessionStore.idl \
	&& echo timestamp > $(@F)

CLEANFILES = $(stamp_files) $(BUILT_SOURCES)
DISTCLEANFILES = $(stamp_files) $(BUILT_SOURCES)
MAINTAINERCLEANFILES = $(stamp_files) $(BUILT_SOURCES)
EXTRA_DIST = nsISessionStore.idl
