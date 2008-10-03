SUBDIRS = bin data po src service extensions

DISTCLEANFILES =		\
	intltool-extract	\
	intltool-merge		\
	intltool-update

EXTRA_DIST =                    \
	$(bin_SCRIPTS)		\
	intltool-merge.in       \
	intltool-update.in      \
	intltool-extract.in

DISTCHECK_CONFIGURE_FLAGS = --disable-update-mimedb
