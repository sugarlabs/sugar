# -*- mode: makefile; coding: utf-8 -*-
# Copyright © 2008 Jonas Smedegaard <dr@jones.dk>
# Description: Class to configure + build GNU autoconf+automake+python packages
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
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
# 02111-1307 USA.
#

_cdbs_scripts_path ?= /usr/lib/cdbs
_cdbs_rules_path ?= /usr/share/cdbs/1/rules
_cdbs_class_path ?= /usr/share/cdbs/1/class

ifndef _cdbs_class_autotools_python
_cdbs_class_autotools_python = 1

#include $(_cdbs_class_path)/python-vars.mk$(_cdbs_makefile_suffix)
include debian/cdbs/1/class/python-vars.mk

# Flavors are used in implicit rules, so must be set before including makefile
DEB_BUILDDIR = build
DEB_MAKE_FLAVORS = $(cdbs_python_curpkg_build_versions)

#include $(_cdbs_class_path)/autotools.mk$(_cdbs_makefile_suffix)
include debian/cdbs/1/class/autotools.mk

DEB_CONFIGURE_SCRIPT_ENV += PYTHON="python$(cdbs_make_curflavor)"

# This class can optionally use debhelper's commands.
# (if not, this build target should simply be ignored)
$(patsubst %,binary-install/%,$(DEB_PACKAGES)) :: binary-install/%:
ifeq (pysupport, $(DEB_PYTHON_SYSTEM))
	dh_pysupport -p$(cdbs_curpkg) $(DEB_PYTHON_PRIVATE_MODULES_DIRS) $(DEB_PYTHON_PRIVATE_MODULES_DIRS_$(cdbs_curpkg))
else
	dh_pycentral -p$(cdbs_curpkg)
endif

clean::
ifeq (, $(cdbs_selected_pycompat))
	echo "$(cdbs_pycompat)" >debian/pycompat
endif # use pycompat
	rm -rf python-build-stamp

endif
