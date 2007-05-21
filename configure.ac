AC_INIT([Sugar],[0.63],[],[sugar])

AC_PREREQ([2.59])

AC_CONFIG_MACRO_DIR([m4])
AC_CONFIG_HEADERS([config.h])
AC_CONFIG_SRCDIR([configure.ac])

AM_INIT_AUTOMAKE([1.9 foreign dist-bzip2 no-dist-gzip])

AM_MAINTAINER_MODE

AC_DISABLE_STATIC
AC_PROG_LIBTOOL

AC_PATH_PROG([GLIB_GENMARSHAL], [glib-genmarshal])

AM_PATH_PYTHON
AM_CHECK_PYTHON_HEADERS(,[AC_MSG_ERROR(could not find Python headers)])

AC_PATH_PROG(PYGTK_CODEGEN, pygtk-codegen-2.0, no)

PKG_CHECK_MODULES(SHELL, pygtk-2.0 gtk+-2.0 gstreamer-0.10 gstreamer-plugins-base-0.10)

PKG_CHECK_MODULES(LIB, gtk+-2.0)
PKG_CHECK_MODULES(LIB_BINDINGS, pygtk-2.0)

PYGTK_DEFSDIR=`$PKG_CONFIG --variable=defsdir pygtk-2.0`
AC_SUBST(PYGTK_DEFSDIR)

# Setup GETTEXT
#
ALL_LINGUAS="it ha ig yo"
GETTEXT_PACKAGE=sugar
AC_PROG_INTLTOOL([0.33])
AC_SUBST(GETTEXT_PACKAGE)
AC_DEFINE_UNQUOTED(GETTEXT_PACKAGE, "$GETTEXT_PACKAGE", [Gettext package])
AM_GLIB_GNU_GETTEXT

AC_CONFIG_FILES([bin/sugar], [chmod +x sugar])

AC_OUTPUT([
Makefile
bin/Makefile
data/Makefile
lib/Makefile
services/Makefile
services/presence/Makefile
services/clipboard/Makefile
shell/Makefile
shell/extensions/Makefile
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
services/console/lib/procmem/Makefile
services/console/Makefile
services/console/interface/Makefile
services/console/interface/xo/Makefile
services/console/interface/memphis/plugins/clean_size/Makefile
services/console/interface/memphis/plugins/dirty_size/Makefile
services/console/interface/memphis/plugins/Makefile
services/console/interface/memphis/plugins/memphis_init/Makefile
services/console/interface/memphis/plugins/cpu/Makefile
services/console/interface/memphis/Makefile
services/console/interface/logviewer/Makefile
services/console/interface/terminal/Makefile
sugar/Makefile
sugar/activity/Makefile
sugar/clipboard/Makefile
sugar/graphics/Makefile
sugar/p2p/Makefile
sugar/presence/Makefile
sugar/datastore/Makefile
po/Makefile.in
])
