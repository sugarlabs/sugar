AC_INIT([Sugar],[0.82.0],[],[sugar])

AC_PREREQ([2.59])

AC_CONFIG_MACRO_DIR([m4])
AC_CONFIG_SRCDIR([configure.ac])

SUCROSE_VERSION="0.83.x"
AC_SUBST(SUCROSE_VERSION)

AM_INIT_AUTOMAKE([1.9 foreign dist-bzip2 no-dist-gzip])

AM_PATH_PYTHON

PKG_CHECK_MODULES(SHELL, pygtk-2.0 gtk+-2.0)

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

AC_CONFIG_FILES([
bin/sugar-shell-service
service/config.py
src/config.py
])

AC_OUTPUT([
Makefile
bin/Makefile
data/Makefile
data/icons/Makefile
service/Makefile
src/jarube/Makefile
src/jarube/controlpanel/Makefile
src/jarube/controlpanel/aboutme/Makefile
src/jarube/controlpanel/aboutxo/Makefile
src/jarube/controlpanel/datetime/Makefile
src/jarube/controlpanel/frame/Makefile
src/jarube/controlpanel/language/Makefile
src/jarube/controlpanel/network/Makefile
src/jarube/controlpanel/power/Makefile
src/jarube/intro/Makefile
src/jarube/journal/Makefile
src/jarube/hardware/Makefile
src/jarube/view/Makefile
src/jarube/view/devices/Makefile
src/jarube/view/devices/network/Makefile
src/jarube/view/frame/Makefile
src/jarube/view/home/Makefile
src/jarube/model/Makefile
src/jarube/model/devices/Makefile
src/jarube/model/devices/network/Makefile
po/Makefile.in
])
