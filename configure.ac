AC_INIT([Sugar],[0.114],[],[sugar])

AC_PREREQ([2.59])

AC_CONFIG_MACRO_DIR([m4])
AC_CONFIG_SRCDIR([configure.ac])

SUCROSE_VERSION="0.114"
AC_SUBST(SUCROSE_VERSION)

AM_INIT_AUTOMAKE([1.9 foreign dist-xz no-dist-gzip])

AM_MAINTAINER_MODE

PYTHON=python3
AM_PATH_PYTHON

AC_PATH_PROG([EMPY], [empy])
if test -z "$EMPY"; then
	AC_MSG_ERROR([python-empy is required])
fi

PKG_CHECK_MODULES(SHELL, gtk+-3.0)

IT_PROG_INTLTOOL([0.35.0])
GETTEXT_PACKAGE=sugar
AC_SUBST([GETTEXT_PACKAGE])
AM_GLIB_GNU_GETTEXT

AC_ARG_ENABLE(update-mimedb,
   AC_HELP_STRING([--disable-update-mimedb],
                   [disable the update-mime-database after install [default=no]]),,
    enable_update_mimedb=yes)
AM_CONDITIONAL(ENABLE_UPDATE_MIMEDB, test x$enable_update_mimedb = xyes)

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

