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

PKG_CHECK_MODULES(LIB, gtk+-2.0)

PKG_CHECK_MODULES(SHELL, gtk+-2.0 gstreamer-0.10 gstreamer-plugins-base-0.10)

PYGTK_DEFSDIR=`$PKG_CONFIG --variable=defsdir pygtk-2.0`
AC_SUBST(PYGTK_DEFSDIR)

#
# Mozilla
#

AC_ARG_WITH(libxul_sdk,
	AC_HELP_STRING([--with-libxul-sdk=DIR], [Path to libxul SDK]))

if test -d "$with_libxul_sdk"; then

# xulrunner 1.9

GECKO_CFLAGS="-I$with_libxul_sdk/sdk/include -DXPCOM_GLUE"
XPCOMGLUE_LIBS="-L$with_libxul_sdk/sdk/lib -lxpcomglue"
MOZILLA_INCLUDE_DIR="$with_libxul_sdk/include"
XPIDL="$with_libxul_sdk/sdk/bin/xpidl"
MOZILLA_IDL_DIR="$with_libxul_sdk/sdk/idl"

AC_SUBST(XPCOMGLUE_LIBS)
AC_SUBST(GECKO_CFLAGS)
AC_SUBST(MOZILLA_INCLUDE_DIR)
AC_SUBST(XPIDL)
AC_SUBST(MOZILLA_IDL_DIR)

PKG_CHECK_MODULES(NSPR, [nspr],
  [have_nspr=true],
  [
PKG_CHECK_MODULES(NSPR, [mozilla-nspr],
  [have_nspr=true],
  [
PKG_CHECK_MODULES(NSPR, [xulrunner-nspr],
  [have_nspr=true],
  have_nspr=false)
  ])
  ])

if test "x$have_nspr" = xfalse; then
  AC_MSG_ERROR([Could not find nspr])
fi

else

AC_MSG_ERROR([Must specify the xulrunner sdk dir (--with-libxul-sdk)])

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

AC_CONFIG_FILES([bin/sugar], [chmod +x sugar])

AC_OUTPUT([
Makefile
bin/Makefile
data/Makefile
browser/Makefile
browser/sessionstore/Makefile
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
sugar/browser/Makefile
sugar/clipboard/Makefile
sugar/graphics/Makefile
sugar/p2p/Makefile
sugar/presence/Makefile
sugar/datastore/Makefile
po/Makefile.in
])
