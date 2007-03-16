SUBDIRS = hardware model view intro

bin_SCRIPTS = 				\
	sugar-activity			\
	sugar-activity-factory		\
	sugar-shell

sugardir = $(pkgdatadir)/shell
sugar_PYTHON =				\
	__init__.py			\
	shellservice.py

confdir = $(pkgdatadir)/shell
conf_DATA = kbdconfig

EXTRA_DIST = $(bin_SCRIPTS) $(conf_DATA)
