sugardir = $(pkgdatadir)/bin
sugar_SCRIPTS = sugar-activity-factory

bin_PROGRAMS = sugar-native-factory

sugar_native_factory_SOURCE = sugar-native-factory.c
sugar_native_factory_CFLAGS = $(NATIVE_FACTORY_CFLAGS)
sugar_native_factory_LDADD = $(NATIVE_FACTORY_LIBS)

bin_SCRIPTS = 			\
	sugar			\
	sugar-activity		\
	sugar-activity-factory	\
	sugar-install-bundle

EXTRA_DIST =                    \
	$(bin_SCRIPTS)		\
	$(sugar_SCRIPTS)	\
	sugar.in

DISTCLEANFILES =                \
	sugar
