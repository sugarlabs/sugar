AC_INIT([Sugar],[0.63],[],[sugar])

AC_PREREQ([2.59])

GNOME_COMMON_INIT
GNOME_COMPILE_WARNINGS

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

PKG_CHECK_MODULES(PYGTK, pygtk-2.0)

PKG_CHECK_MODULES(PYCAIRO, pycairo)

PKG_CHECK_MODULES(LIB, gtk+-2.0 gstreamer-0.10 gstreamer-plugins-base-0.10)

PYGTK_DEFSDIR=`$PKG_CONFIG --variable=defsdir pygtk-2.0`
AC_SUBST(PYGTK_DEFSDIR)

#
# Mozilla
#

AC_ARG_WITH(libxul_sdk,
	AC_HELP_STRING([--with-libxul-sdk=DIR], [Path to libxul SDK]))

if test "x$with_libxul_sdk" != x ; then

# xulrunner 1.9

GECKO_CFLAGS="-I$with_libxul_sdk/sdk/include -DXPCOM_GLUE"
XPCOMGLUE_LIBS="-L$with_libxul_sdk/sdk/lib -lxpcomglue"
MOZILLA_INCLUDE_DIR="$with_libxul_sdk/include"

AC_SUBST(XPCOMGLUE_LIBS)
AC_SUBST(GECKO_CFLAGS)

AC_DEFINE([HAVE_GECKO_1_9],[1],[Define if we have gecko 1.9])

else

# xulrunner 1.8

PKG_CHECK_MODULES(GECKO, [xulrunner-gtkmozembed >= 1.8],
  [have_gecko=true; mozpackage=xulrunner],
  [
PKG_CHECK_MODULES(GECKO, [firefox-gtkmozembed >= 1.5],
  [have_gecko=true; mozpackage=firefox],
  have_gecko=false)
  ])

if test "x$have_gecko" = xfalse; then
  AC_MSG_ERROR([Could not find xulrunner, mozilla or firefox $mozilla_required_version])
fi

GECKO_LDFLAGS="-R`$PKG_CONFIG --variable=libdir $mozpackage-gtkmozembed`"
AC_SUBST(GECKO_LDFLAGS)

MOZILLA_INCLUDE_DIR="`$PKG_CONFIG --variable=includedir $mozpackage-gtkmozembed`"
AC_SUBST(MOZILLA_INCLUDE_DIR)

fi

#
# Setup GETTEXT
#
ALL_LINGUAS="it ha ig yo"
GETTEXT_PACKAGE=sugar
AC_PROG_INTLTOOL([0.33])
AC_SUBST(GETTEXT_PACKAGE)
AC_DEFINE_UNQUOTED(GETTEXT_PACKAGE, "$GETTEXT_PACKAGE", [Gettext package])
AM_GLIB_GNU_GETTEXT

AC_OUTPUT([
Makefile
lib/Makefile
lib/data/Makefile
lib/src/Makefile
lib/python/Makefile
lib/threadframe/Makefile
services/Makefile
services/presence/Makefile
services/nm/Makefile
services/clipboard/Makefile
services/datastore/Makefile
shell/Makefile
shell/data/Makefile
shell/view/Makefile
shell/view/home/Makefile
shell/view/frame/Makefile
shell/model/Makefile
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
sugar/__installed__.py
sugar/activity/Makefile
sugar/chat/Makefile
sugar/chat/sketchpad/Makefile
sugar/clipboard/Makefile
sugar/graphics/Makefile
sugar/p2p/Makefile
sugar/presence/Makefile
sugar/datastore/Makefile
po/Makefile.in
tools/Makefile
tools/sugar-setup-activity
])
