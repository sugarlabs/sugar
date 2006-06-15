AC_INIT([Sugar],[0.9],[],[sugar])

AC_PREREQ([2.59])

AC_CONFIG_HEADERS([config.h])
AC_CONFIG_SRCDIR([configure.ac])

AM_INIT_AUTOMAKE([1.9 foreign dist-bzip2 no-dist-gzip])

AM_MAINTAINER_MODE

AM_PATH_PYTHON

PKG_CHECK_MODULES(PYGTK, pygtk-2.0 >= 2.6)
AC_SUBST(PYGTK_CFLAGS)
AC_SUBST(PYGTK_LIBS)

AC_OUTPUT([
Makefile
cut-n-paste/Makefile
sugar/Makefile
sugar/__installed__.py
sugar/browser/Makefile
sugar/chat/Makefile
sugar/chat/sketchpad/Makefile
sugar/p2p/Makefile
sugar/p2p/model/Makefile
sugar/shell/Makefile
sugar/session/Makefile
sugar/presence/Makefile
])
