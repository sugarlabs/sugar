sessionstoredir = $(pkgdatadir)/mozilla/components

sessionstore_DATA =		\
	nsIBrowserHelper.xpt	\
	nsBrowserHelper.js

BUILT_SOURCES = \
	nsIBrowserHelper.xpt	\
	nsIBrowserHelper.h

stamp_files = \
	stamp-nsIBrowserHelper.xpt	\
	stamp-nsIBrowserHelper.h

nsIBrowserHelper.xpt: stamp-nsIBrowserHelper.xpt
	@true
stamp-nsIBrowserHelper.xpt: nsIBrowserHelper.idl
	$(XPIDL) -m typelib -w -v -I $(MOZILLA_IDL_DIR) -e nsIBrowserHelper.xpt \
	$(srcdir)/nsIBrowserHelper.idl \
	&& echo timestamp > $(@F)

nsIBrowserHelper.h: stamp-nsIBrowserHelper.h
	@true
stamp-nsIBrowserHelper.h: nsIBrowserHelper.idl
	$(XPIDL) -m header -w -v -I $(MOZILLA_IDL_DIR) -e nsIBrowserHelper.h \
	$(srcdir)/nsIBrowserHelper.idl \
	&& echo timestamp > $(@F)

CLEANFILES = $(stamp_files) $(BUILT_SOURCES)
DISTCLEANFILES = $(stamp_files) $(BUILT_SOURCES)
MAINTAINERCLEANFILES = $(stamp_files) $(BUILT_SOURCES)
EXTRA_DIST = nsIBrowserHelper.idl nsBrowserHelper.js
