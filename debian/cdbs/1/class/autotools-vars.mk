# -*- mode: makefile; coding: utf-8 -*-
# Copyright © 2002,2003 Colin Walters <walters@debian.org>
# Copyright © 2008 Jonas Smedegaard <dr@jones.dk>
# Description: Common variables for GNU autoconf+automake packages
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2, or (at
# your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
# 02111-1307 USA.

_cdbs_scripts_path ?= /usr/lib/cdbs
_cdbs_rules_path ?= /usr/share/cdbs/1/rules
_cdbs_class_path ?= /usr/share/cdbs/1/class

ifndef _cdbs_class_autotools_vars
_cdbs_class_autotools_vars = 1

#include $(_cdbs_class_path)/makefile.mk$(_cdbs_makefile_suffix)
include debian/cdbs/1/class/makefile.mk

DEB_MAKE_INSTALL_TARGET = install DESTDIR=$(DEB_DESTDIR)
DEB_MAKE_CLEAN_TARGET = distclean
#DEB_MAKE_CHECK_TARGET = check

DEB_AC_AUX_DIR = $(DEB_SRCDIR)

DEB_CONFIGURE_SCRIPT = $(CURDIR)/$(DEB_SRCDIR)/configure
DEB_CONFIGURE_SCRIPT_ENV = CC="$(CC)" CXX="$(CXX)" CFLAGS="$(CFLAGS)" CXXFLAGS="$(CXXFLAGS)" CPPFLAGS="$(CPPFLAGS)" LDFLAGS="$(LDFLAGS)"
DEB_CONFIGURE_NORMAL_ARGS = --build=$(DEB_BUILD_GNU_TYPE) --prefix=$(DEB_CONFIGURE_PREFIX) --includedir=$(DEB_CONFIGURE_INCLUDEDIR) --mandir=$(DEB_CONFIGURE_MANDIR) --infodir=$(DEB_CONFIGURE_INFODIR) --sysconfdir=$(DEB_CONFIGURE_SYSCONFDIR) --localstatedir=$(DEB_CONFIGURE_LOCALSTATEDIR) --libexecdir=$(DEB_CONFIGURE_LIBEXECDIR) --disable-maintainer-mode --disable-dependency-tracking

# Provide --host only if different from --build, as recommended in
# autotools-dev README.Debian: When provided (even if equal) autotools
# 2.52+ switches to cross-compiling mode.

ifneq ($(DEB_BUILD_GNU_TYPE), $(DEB_HOST_GNU_TYPE))
DEB_CONFIGURE_NORMAL_ARGS += --host=$(DEB_HOST_GNU_TYPE)
endif

### TODO: Fix the above to also handle 2.13 which needs other tweaks
### (read autotools-dev README.Debian!). For now we conflict with
### autoconf2.13!

# This magic is required because otherwise configure wants to analyse
# $0 to see whether a VPATH build is needed.  This tells it with
# absolute certainly that this is NOT a VPATH build.
DEB_CONFIGURE_NORMAL_ARGS += $(if $(subst $(DEB_SRCDIR),,$(cdbs_make_curbuilddir)),,--srcdir=.)

DEB_CONFIGURE_INVOKE = cd $(cdbs_make_curbuilddir) && $(DEB_CONFIGURE_SCRIPT_ENV) $(DEB_CONFIGURE_SCRIPT) $(DEB_CONFIGURE_NORMAL_ARGS)
DEB_CONFIGURE_PREFIX =/usr
DEB_CONFIGURE_INCLUDEDIR = "\$${prefix}/include"
DEB_CONFIGURE_MANDIR ="\$${prefix}/share/man"
DEB_CONFIGURE_INFODIR ="\$${prefix}/share/info"
DEB_CONFIGURE_SYSCONFDIR =/etc
DEB_CONFIGURE_LOCALSTATEDIR =/var
DEB_CONFIGURE_LIBEXECDIR ="\$${prefix}/lib/$(DEB_SOURCE_PACKAGE)"
DEB_CONFIGURE_EXTRA_FLAGS =

ifneq (, $(DEB_AUTO_UPDATE_LIBTOOL))
CDBS_BUILD_DEPENDS := $(CDBS_BUILD_DEPENDS), libtool
endif

ifneq (:, $(DEB_AUTO_UPDATE_ACLOCAL):$(DEB_AUTO_UPDATE_AUTOMAKE))
ifeq ($(DEB_AUTO_UPDATE_ACLOCAL), $(DEB_AUTO_UPDATE_AUTOMAKE))
# avoid duped build-dependencies
CDBS_BUILD_DEPENDS := $(CDBS_BUILD_DEPENDS), automake$(DEB_AUTO_UPDATE_ACLOCAL)
else
# either only one of them is required, or different versions are
ifneq (, $(DEB_AUTO_UPDATE_ACLOCAL))
CDBS_BUILD_DEPENDS := $(CDBS_BUILD_DEPENDS), automake$(DEB_AUTO_UPDATE_ACLOCAL)
endif
ifneq (, $(DEB_AUTO_UPDATE_AUTOMAKE))
CDBS_BUILD_DEPENDS := $(CDBS_BUILD_DEPENDS), automake$(DEB_AUTO_UPDATE_AUTOMAKE)
endif
endif
endif

ifneq (:, $(DEB_AUTO_UPDATE_AUTOCONF):$(DEB_AUTO_UPDATE_AUTOHEADER))
ifeq ($(DEB_AUTO_UPDATE_AUTOCONF), $(DEB_AUTO_UPDATE_AUTOHEADER))
# avoid duped build-dependencies
ifeq ($(DEB_AUTO_UPDATE_AUTOCONF), 2.13)
CDBS_BUILD_DEPENDS := $(CDBS_BUILD_DEPENDS), autoconf2.13
else
CDBS_BUILD_DEPENDS := $(CDBS_BUILD_DEPENDS), autoconf
endif
else
# either only one of them is required, or different versions are
ifneq (, $(DEB_AUTO_UPDATE_AUTOCONF))
ifeq ($(DEB_AUTO_UPDATE_AUTOCONF), 2.13)
CDBS_BUILD_DEPENDS := $(CDBS_BUILD_DEPENDS), autoconf2.13
else
CDBS_BUILD_DEPENDS := $(CDBS_BUILD_DEPENDS), autoconf
endif
endif
ifneq (, $(DEB_AUTO_UPDATE_AUTOHEADER))
ifeq ($(DEB_AUTO_UPDATE_AUTOHEADER), 2.13)
CDBS_BUILD_DEPENDS := $(CDBS_BUILD_DEPENDS), autoconf2.13
else
CDBS_BUILD_DEPENDS := $(CDBS_BUILD_DEPENDS), autoconf
endif
endif
endif
endif

endif
