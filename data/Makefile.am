SUBDIRS = icons

sugar-72.gtkrc: gtkrc.em
	$(srcdir)/em.py -D scaling=\'72\' $(srcdir)/gtkrc.em > \
		$(top_builddir)/data/sugar-72.gtkrc

sugar-100.gtkrc: gtkrc.em
	$(srcdir)/em.py -D scaling=\'100\' $(srcdir)/gtkrc.em > \
		$(top_builddir)/data/sugar-100.gtkrc

sugardir = $(pkgdatadir)/data
sugar_DATA =			\
	activities.hidden	\
	group-labels.defaults	\
	ISO-639-2_utf-8.txt	\
	kbdconfig		\
	mime.defaults		\
	GPLv3			\
	$(GTKRC_FILES)

GTKRC_FILES =		\
	sugar-72.gtkrc	\
	sugar-100.gtkrc

xsessionsdir = $(datadir)/xsessions
xsessions_DATA = sugar.desktop

mime_xml_in_files = sugar.xml.in
mime_xml_files = $(mime_xml_in_files:.xml.in=.xml)
@INTLTOOL_XML_RULE@

mimedir = $(datadir)/mime/packages
mime_DATA = $(mime_xml_files)

nmservicedir = $(sysconfdir)/dbus-1/system.d/
nmservice_DATA = nm-user-settings.conf

install-data-hook:
if ENABLE_UPDATE_MIMEDB
	if [ -z "$$DESTDIR" ]; then \
		update-mime-database "$(datadir)/mime"; \
	fi
endif

uninstall-hook:
if ENABLE_UPDATE_MIMEDB
	if [ -z "$$DESTDIR" ]; then \
		update-mime-database "$(datadir)/mime"; \
	fi
endif

@INTLTOOL_SCHEMAS_RULE@

schemadir = $(GCONF_SCHEMA_FILE_DIR)
schema_in_files = sugar.schemas.in
schema_DATA = $(schema_in_files:.schemas.in=.schemas)

install-data-local: $(schema_DATA)
if GCONF_SCHEMAS_INSTALL
	GCONF_CONFIG_SOURCE=$(GCONF_SCHEMA_CONFIG_SOURCE) $(GCONFTOOL) --makefile-install-rule sugar.schemas 2>&1 > /dev/null
endif

gsettings_SCHEMAS = org.sugarlabs.gschema.xml
@GSETTINGS_RULES@

convertdir = $(datarootdir)/GConf/gsettings
convert_DATA = sugar-schemas.convert

%.policy : %.policy.in ; sed -e "s|\@bindir\@|$(bindir)|g" $< > $@

polkit_policydir = $(datadir)/polkit-1/actions
polkit_in_files = org.sugar.brightness.policy.in org.sugar.serial-number.policy.in
polkit_policy_DATA = $(polkit_in_files:.policy.in=.policy)

EXTRA_DIST = $(sugar_DATA) $(xsessions_DATA) $(nmservice_DATA) $(mime_xml_in_files) em.py gtkrc.em $(schema_in_files) $(icon_DATA) $(gsettings_SCHEMAS) $(convert_DATA) $(polkit_in_files)
CLEANFILES = $(GTKRC_FILES) $(mime_xml_files) $(schema_DATA) $(polkit_policy_DATA)
