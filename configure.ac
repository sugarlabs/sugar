AC_INIT([Sugar],[0.18],[],[sugar])

AC_PREREQ([2.59])

AC_CONFIG_HEADERS([config.h])
AC_CONFIG_SRCDIR([configure.ac])

AM_INIT_AUTOMAKE([1.9 foreign dist-bzip2 no-dist-gzip])

AM_MAINTAINER_MODE

AM_PATH_PYTHON

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
activities/chat/Makefile
activities/terminal/Makefile
shell/Makefile
shell/data/Makefile
shell/home/Makefile
shell/session/Makefile
shell/PresenceService/Makefile
sugar/Makefile
sugar/__installed__.py
sugar/activity/Makefile
sugar/canvas/Makefile
sugar/chat/Makefile
sugar/chat/sketchpad/Makefile
sugar/p2p/Makefile
sugar/p2p/model/Makefile
sugar/presence/Makefile
po/Makefile.in
tools/Makefile
tools/sugar-setup-activity
])
