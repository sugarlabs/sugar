@INTLTOOL_SCHEMAS_RULE@

schemadir = $(GCONF_SCHEMA_FILE_DIR)
schema_in_files = sugar.schemas.in
schema_DATA = $(schema_in_files:.schemas.in=.schemas)

install-data-local: $(schema_DATA)
if GCONF_SCHEMAS_INSTALL
	if test -z "$(DESTDIR)" ; then \
	for p in $^ ; do \
	GCONF_CONFIG_SOURCE=$(GCONF_SCHEMA_CONFIG_SOURCE) $(GCONFTOOL) --makefile-install-rule $$p 2>&1 > /dev/null; \
	done \
	fi
endif

EXTRA_DIST = \
	$(schema_in_files)		

DISTCLEANFILES = \
	$(schema_in_files:.schemas.in=.schemas)
