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

check-po:
	@for i in $(top_srcdir)/po/*.po ; do \
		if ! grep -q ^`basename $$i | \
		sed 's,.po,,'`$$ $(top_srcdir)/po/LINGUAS ; then \
			echo '***' `basename $$i | \
			sed 's,.po,,'` missing from po/LINGUAS '***' ; \
			exit 1; \
		fi; \
	done;

lint:
	flake8 --ignore E402 $(top_srcdir)/src $(top_srcdir)/extensions

test: lint check-po
	PYTHONPATH=$(pkgdatadir)/extensions:$(PYTHONPATH) \
	python -m sugar3.test.discover $(top_srcdir)/tests
