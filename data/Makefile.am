SUBDIRS = icons

# Define common variables for maintainability
PYTHON ?= python3
MIME_DIR = $(datadir)/mime
BUILD_DIR = $(top_builddir)/data

# Automatically detect GTKRC scaling versions
GTKRC_SIZES = 72 100
GTKRC_FILES = $(addprefix $(BUILD_DIR)/sugar-, $(addsuffix .gtkrc, $(GTKRC_SIZES)))

# Generate GTK resource files dynamically
$(BUILD_DIR)/sugar-%.gtkrc: gtkrc.em
	$(PYTHON) -m em -D scaling=\'$*\'' $(srcdir)/gtkrc.em > $@

sugardir = $(pkgdatadir)/data
sugar_DATA = activities.hidden group-labels.defaults ISO-639-2_utf-8.txt \
             kbdconfig mime.defaults GPLv3 $(GTKRC_FILES)

# Use wildcard to dynamically find .xml.in files
mime_xml_in_files = $(wildcard *.xml.in)
mime_xml_files = $(patsubst %.xml.in,%.xml,$(mime_xml_in_files))
@INTLTOOL_XML_RULE@

mimedir = $(MIME_DIR)/packages
mime_DATA = $(mime_xml_files)

nmservicedir = $(sysconfdir)/dbus-1/system.d/
nmservice_DATA = nm-user-settings.conf

# Parallel execution support
.NOTPARALLEL:

install-data-hook: 
if ENABLE_UPDATE_MIMEDB
	@echo "Updating MIME database..."
	@[ -z "$$DESTDIR" ] && update-mime-database "$(MIME_DIR)" || true
endif

uninstall-hook:
if ENABLE_UPDATE_MIMEDB
	@echo "Cleaning up MIME database..."
	@[ -z "$$DESTDIR" ] && update-mime-database "$(MIME_DIR)" || true
endif

gsettings_SCHEMAS = org.sugarlabs.gschema.xml
@GSETTINGS_RULES@

# Use wildcard expansion to automate policy handling
polkit_policydir = $(datadir)/polkit-1/actions
polkit_in_files = $(wildcard org.sugar.*.policy.in)
polkit_policy_DATA = $(patsubst %.policy.in,%.policy,$(polkit_in_files))

EXTRA_DIST = $(sugar_DATA) $(xsessions_DATA) $(nmservice_DATA) $(mime_xml_in_files) gtkrc.em $(icon_DATA) $(gsettings_SCHEMAS) $(convert_DATA) $(polkit_in_files)
CLEANFILES = $(GTKRC_FILES) $(mime_xml_files) $(polkit_policy_DATA)
