AC_INIT([Sugar],[0.33],[],[sugar])

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

AM_PATH_PYTHON
AM_CHECK_PYTHON_HEADERS(,[AC_MSG_ERROR(could not find Python headers)])

AC_PATH_PROG(PYGTK_CODEGEN, pygtk-codegen-2.0, no)

PKG_CHECK_MODULES(PYGTK, pygtk-2.0)
PKG_CHECK_MODULES(LIB, gtk+-2.0 xulrunner-gtkmozembed)

MOZILLA_HOME="`$PKG_CONFIG --variable=libdir xulrunner-gtkmozembed`"
AC_SUBST(MOZILLA_HOME)

GNOMEPYTHONEXTRAS_DEFSDIR=`$PKG_CONFIG --variable=defsdir pygtk-2.0`
AC_SUBST(GNOMEPYTHONEXTRAS_DEFSDIR)

PYGTK_DEFSDIR=`$PKG_CONFIG --variable=defsdir pygtk-2.0`
AC_SUBST(PYGTK_DEFSDIR)

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
dbus-installed.conf
activities/Makefile
activities/browser/Makefile
activities/web/Makefile
activities/chat/Makefile
activities/groupchat/Makefile
activities/terminal/Makefile
lib/Makefile
lib/src/Makefile
lib/python/Makefile
lib/threadframe/Makefile
services/Makefile
services/presence/Makefile
shell/Makefile
shell/conf/Makefile
shell/data/Makefile
shell/view/Makefile
shell/view/home/Makefile
shell/view/frame/Makefile
shell/model/Makefile
sugar/Makefile
sugar/__installed__.py
sugar/__uninstalled__.py
sugar/activity/Makefile
sugar/chat/Makefile
sugar/chat/sketchpad/Makefile
sugar/graphics/Makefile
sugar/p2p/Makefile
sugar/p2p/model/Makefile
sugar/presence/Makefile
sugar/session/Makefile
po/Makefile.in
tools/Makefile
tools/sugar-setup-activity
])
