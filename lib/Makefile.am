SUBDIRS = xdgmime

libsugar_la_CPPFLAGS =		\
	$(LIB_CFLAGS)
	
noinst_LTLIBRARIES = libsugar.la

libsugar_la_LIBADD = 					\
	$(LIB_LIBS)					\
	$(top_builddir)/lib/xdgmime/libxdgmime.la

libsugar_la_SOURCES =			\
	sugar-address-entry.c		\
	sugar-address-entry.h		\
	sugar-x11-util.c		\
	sugar-x11-util.h
