TESTS_TMPDIR=$(abs_builddir)/tests-tmp

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

test:
	cd $(top_srcdir)/tests && \
    mkdir -p $(TESTS_TMPDIR) && \
    TMPDIR=$(TESTS_TMPDIR) python -m unittest discover && \
    rm -rf $(TESTS_TMPDIR)
