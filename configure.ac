AC_INIT([Sugar],[0.65],[],[sugar])

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

PKG_CHECK_MODULES(NATIVE_FACTORY, dbus-1)

PKG_CHECK_MODULES(LIBUI, gtk+-2.0)
PKG_CHECK_MODULES(LIBUI_BINDINGS, pygtk-2.0)

PKG_CHECK_MODULES(LIB_BINDINGS, pygobject-2.0)

PYGTK_DEFSDIR=`$PKG_CONFIG --variable=defsdir pygtk-2.0`
AC_SUBST(PYGTK_DEFSDIR)

# Setup GETTEXT
#
ALL_LINGUAS="ar de el es fr ha ig it mk pl pt_BR yo"
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
data/icons/Makefile
lib/Makefile
lib/ui/Makefile
services/Makefile
services/shell/Makefile
shell/Makefile
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
services/console/lib/Makefile
services/console/lib/graphics/Makefile
services/console/lib/procmem/Makefile
services/console/lib/net/Makefile
services/console/lib/ui/Makefile
services/console/Makefile
services/console/interface/Makefile
services/console/interface/xo/Makefile
services/console/interface/memphis/plugins/clean_size/Makefile
services/console/interface/memphis/plugins/smaps/Makefile
services/console/interface/memphis/plugins/Makefile
services/console/interface/memphis/plugins/memphis_init/Makefile
services/console/interface/memphis/plugins/cpu/Makefile
services/console/interface/memphis/Makefile
services/console/interface/network/Makefile
services/console/interface/logviewer/Makefile
services/console/interface/terminal/Makefile
services/console/interface/xserver/Makefile
sugar/Makefile
sugar/activity/Makefile
sugar/bundle/Makefile
sugar/clipboard/Makefile
sugar/graphics/Makefile
sugar/objects/Makefile
sugar/presence/Makefile
sugar/datastore/Makefile
po/Makefile.in
])
