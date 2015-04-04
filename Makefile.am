SUBDIRS = bin data po src extensions

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

lint:
	flake8 $(top_srcdir)

test: lint
	PYTHONPATH=$(pkgdatadir)/extensions:$(PYTHONPATH) \
	python -m sugar3.test.discover $(top_srcdir)/tests
