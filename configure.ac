AC_INIT([Sugar],[0.110.0],[],[sugar])

AC_PREREQ([2.59])

AC_CONFIG_MACRO_DIR([m4])
AC_CONFIG_SRCDIR([configure.ac])

SUCROSE_VERSION="0.110.0"
AC_SUBST(SUCROSE_VERSION)

AM_INIT_AUTOMAKE([1.9 foreign dist-xz no-dist-gzip])

AM_MAINTAINER_MODE

PYTHON=python2
AM_PATH_PYTHON

PKG_CHECK_MODULES(SHELL, gtk+-3.0 gconf-2.0)

IT_PROG_INTLTOOL([0.35.0])
GETTEXT_PACKAGE=sugar
AC_SUBST([GETTEXT_PACKAGE])
AM_GLIB_GNU_GETTEXT

AC_ARG_ENABLE(update-mimedb,
   AC_HELP_STRING([--disable-update-mimedb],
                   [disable the update-mime-database after install [default=no]]),,
    enable_update_mimedb=yes)
AM_CONDITIONAL(ENABLE_UPDATE_MIMEDB, test x$enable_update_mimedb = xyes)

# Verify that gconftool is installed 
# 
AC_PATH_PROG(GCONFTOOL, gconftool-2, no)

if test "$GCONFTOOL" = no; then
  AC_MSG_ERROR([gconftool-2 executable not found in your path - should be installed with GConf])
fi

AM_GCONF_SOURCE_2
GLIB_GSETTINGS


AC_CONFIG_FILES([
bin/Makefile
bin/sugar
data/icons/Makefile
data/Makefile
extensions/cpsection/aboutcomputer/Makefile
extensions/cpsection/aboutme/Makefile
extensions/cpsection/background/Makefile
extensions/cpsection/backup/Makefile
extensions/cpsection/backup/backends/Makefile
extensions/cpsection/datetime/Makefile
extensions/cpsection/frame/Makefile
extensions/cpsection/keyboard/Makefile
extensions/cpsection/language/Makefile
extensions/cpsection/modemconfiguration/Makefile
extensions/cpsection/Makefile
extensions/cpsection/network/Makefile
extensions/cpsection/power/Makefile
extensions/cpsection/updater/Makefile
extensions/cpsection/webaccount/services/Makefile
extensions/cpsection/webaccount/Makefile
extensions/deviceicon/Makefile
extensions/globalkey/Makefile
extensions/webservice/Makefile
extensions/Makefile
Makefile
po/Makefile.in
src/jarabe/config.py
src/jarabe/controlpanel/Makefile
src/jarabe/desktop/Makefile
src/jarabe/frame/Makefile
src/jarabe/intro/Makefile
src/jarabe/journal/Makefile
src/jarabe/Makefile
src/jarabe/model/Makefile
src/jarabe/model/update/Makefile
src/jarabe/util/Makefile
src/jarabe/util/telepathy/Makefile
src/jarabe/view/Makefile
src/jarabe/webservice/Makefile
src/Makefile
])

AC_OUTPUT

