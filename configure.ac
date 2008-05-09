AC_INIT([Sugar],[0.79.4],[],[sugar])

AC_PREREQ([2.59])

AC_CONFIG_MACRO_DIR([m4])
AC_CONFIG_SRCDIR([configure.ac])

AM_INIT_AUTOMAKE([1.9 foreign dist-bzip2 no-dist-gzip])

AM_PATH_PYTHON

PKG_CHECK_MODULES(SHELL, pygtk-2.0 gtk+-2.0)

# Setup GETTEXT
#
ALL_LINGUAS="am ar ay bn de dz el en es fa fr ha hi ig is it ja ko mk ml ne nl pa pl pt pt_BR qu ro ru rw th ur yo zh_CN zh_TW"
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
bin/sugar
bin/sugar-control-panel
bin/sugar-emulator
bin/sugar-shell
bin/sugar-shell-service
service/config.py
src/config.py
])

AC_OUTPUT([
Makefile
bin/Makefile
data/Makefile
service/Makefile
src/Makefile
src/controlpanel/Makefile
src/controlpanel/model/Makefile
src/intro/Makefile
src/hardware/Makefile
src/view/Makefile
src/view/devices/Makefile
src/view/devices/network/Makefile
src/view/frame/Makefile
src/view/home/Makefile
src/model/Makefile
src/model/devices/Makefile
src/model/devices/network/Makefile
po/Makefile.in
])
