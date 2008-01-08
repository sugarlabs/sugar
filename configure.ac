AC_INIT([Sugar],[0.75.0],[],[sugar])

AC_PREREQ([2.59])

AC_CONFIG_MACRO_DIR([m4])
AC_CONFIG_SRCDIR([configure.ac])

AM_INIT_AUTOMAKE([1.9 foreign dist-bzip2 no-dist-gzip])

AC_DISABLE_STATIC
AC_PROG_LIBTOOL

AC_PATH_PROG([GLIB_GENMARSHAL], [glib-genmarshal])

AM_PATH_PYTHON
AM_CHECK_PYTHON_HEADERS(,[AC_MSG_ERROR(could not find Python headers)])

AC_PATH_PROG(PYGTK_CODEGEN, pygtk-codegen-2.0, no)

PKG_CHECK_MODULES(SHELL, pygtk-2.0 gtk+-2.0)

PKG_CHECK_MODULES(LIB, pygtk-2.0 gtk+-2.0)

PYGTK_DEFSDIR=`$PKG_CONFIG --variable=defsdir pygtk-2.0`
AC_SUBST(PYGTK_DEFSDIR)

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

AC_CONFIG_FILES([bin/sugar], [chmod +x sugar])

AC_OUTPUT([
Makefile
bin/Makefile
data/Makefile
lib/Makefile
lib/sugar/Makefile
lib/sugar/activity/Makefile
lib/sugar/bundle/Makefile
lib/sugar/clipboard/Makefile
lib/sugar/graphics/Makefile
lib/sugar/presence/Makefile
lib/sugar/datastore/Makefile
services/Makefile
services/shell/Makefile
shell/Makefile
shell/controlpanel/Makefile
shell/intro/Makefile
shell/hardware/Makefile
shell/view/Makefile
shell/view/devices/Makefile
shell/view/devices/network/Makefile
shell/view/frame/Makefile
shell/view/home/Makefile
shell/model/Makefile
shell/model/devices/Makefile
shell/model/devices/network/Makefile
po/Makefile.in
])
