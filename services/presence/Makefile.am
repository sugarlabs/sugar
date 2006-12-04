servicedir = $(datadir)/dbus-1/services
service_in_files = org.laptop.Presence.service.in
service_DATA = $(service_in_files:.service.in=.service)

$(service_DATA): $(service_in_files) Makefile
	@sed -e "s|\@bindir\@|$(bindir)|" $< > $@

sugardir = $(pkgdatadir)/services/presence
sugar_PYTHON =			\
	__init__.py			\
	Activity.py			\
	Buddy.py			\
	BuddyIconCache.py	\
	PresenceService.py	\
	Service.py

bin_SCRIPTS = sugar-presence-service

DISTCLEANFILES = $(service_DATA)

EXTRA_DIST = $(service_in_files) $(bin_SCRIPTS)
