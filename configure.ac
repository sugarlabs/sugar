AC_INIT([Sugar],[0.85.3],[],[sugar])

AC_PREREQ([2.59])

AC_CONFIG_MACRO_DIR([m4])
AC_CONFIG_SRCDIR([configure.ac])

SUCROSE_VERSION="0.85.1"
AC_SUBST(SUCROSE_VERSION)

AM_INIT_AUTOMAKE([1.9 foreign dist-bzip2 no-dist-gzip])

AM_MAINTAINER_MODE

AM_PATH_PYTHON

PKG_CHECK_MODULES(SHELL, pygtk-2.0 gtk+-2.0 gconf-2.0)

# Setup GETTEXT
#
ALL_LINGUAS="af am ar ay bg bn bn_IN ca de dz el en es fa fa_AF ff fr gu ha hi ht ig is it ja km ko mk ml mn mr mvo nb ne nl pa pap pis pl ps pt pt_BR qu ro ru rw sd si sl te th tpi tr ur vi yo zh_CN zh_TW"
GETTEXT_PACKAGE=sugar
AC_PROG_INTLTOOL([0.33])
AC_SUBST(GETTEXT_PACKAGE)
AC_DEFINE_UNQUOTED(GETTEXT_PACKAGE, "$GETTEXT_PACKAGE", [Gettext package])
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


AC_CONFIG_FILES([
bin/sugar
src/jarabe/config.py
])

AC_OUTPUT([
Makefile
bin/Makefile
data/Makefile
data/icons/Makefile
extensions/Makefile
extensions/cpsection/Makefile
extensions/cpsection/aboutme/Makefile
extensions/cpsection/aboutcomputer/Makefile
extensions/cpsection/datetime/Makefile
extensions/cpsection/frame/Makefile
extensions/cpsection/keyboard/Makefile
extensions/cpsection/language/Makefile
extensions/cpsection/network/Makefile
extensions/cpsection/power/Makefile
extensions/cpsection/updater/Makefile
extensions/cpsection/updater/backends/Makefile
extensions/deviceicon/Makefile
extensions/globalkey/Makefile
src/Makefile
src/jarabe/Makefile
src/jarabe/controlpanel/Makefile
src/jarabe/desktop/Makefile
src/jarabe/frame/Makefile
src/jarabe/intro/Makefile
src/jarabe/journal/Makefile
src/jarabe/view/Makefile
src/jarabe/model/Makefile
src/jarabe/util/Makefile
src/jarabe/util/telepathy/Makefile
po/Makefile.in
])
