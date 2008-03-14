# -*- mode: makefile; coding: utf-8 -*-
# Copyright © 2008 Jonas Smedegaard <dr@jones.dk>
# Copyright © 2008 Jonas Smedegaard <dr@jones.dk>
# Description: Defines useful variables for Python packages
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

ifndef _cdbs_class_python_vars
_cdbs_class_python_vars = 1

DEB_PYTHON_PACKAGES = $(filter-out %-doc %-dev %-common, $(DEB_PACKAGES))
## FIXME: Support multiple binary python packages per source package
## TODO: Check and bail out if pultiple packages are declared/resolved

DEB_PYTHON_ARCH_PACKAGES = $(filter $(DEB_PYTHON_PACKAGES), $(DEB_ARCH_PACKAGES))
DEB_PYTHON_INDEP_PACKAGES = $(filter $(DEB_PYTHON_PACKAGES), $(DEB_INDEP_PACKAGES))

# check python system
cdbs_use_xs_field := $(shell grep -q "^XS-Python-Version:" debian/control && echo yes)
cdbs_selected_pycompat := $(shell if [ -e debian/pycompat ]; then cat debian/pycompat; fi)
cdbs_pycompat = $(cdbs_selected_pycompat)
ifeq (pysupport, $(DEB_PYTHON_SYSTEM))
## FIXME: Support multiple binary python packages per source package
  cdbs_python_support_path = usr/share/python-support/$(DEB_PYTHON_PACKAGES)
  ifeq (, $(cdbs_selected_pycompat))
    cdbs_pycompat = 2
  endif # use pycompat
  # warning pysupport compatibility mode
  ifneq (, $(cdbs_use_xs_field))
    $(warning Use of XS-Python-Version and XB-Python-Version fields in 'debian/control' is deprecated with pysupport method, use 'debian/pyversions' if you need to specify specific versions)
  endif # use XS field (compat)
else
  ifeq (pycentral, $(DEB_PYTHON_SYSTEM))
    ifeq (, $(cdbs_selected_pycompat))
      cdbs_pycompat = 2
    endif # use pycompat
  else
    ifneq (, $(DEB_PYTHON_SYSTEM))
      $(error unsupported Python system: $(DEB_PYTHON_SYSTEM) (select either pysupport or pycentral))
    else
      ifneq (, $(cdbs_use_xs_field))
        $(error Your package uses the new Python policy; you must set DEB_PYTHON_SYSTEM to "pysupport" or "pycentral".)
      endif
      ifneq (, $(cdbs_selected_pycompat))
        ifeq (yes, $(shell expr $(cdbs_selected_pycompat) \> 1 >/dev/null && echo yes))
          $(error Your package uses the new Python policy; you must set DEB_PYTHON_SYSTEM to "pysupport" or "pycentral".)
        endif
      endif # use pycompat
    endif # unknown method
  endif # pycentral
endif # pysupport

# Calculate cdbs_python_build_versions
## FIXME: Support multiple binary python packages per source package
cdbs_python_current_version := $(shell pyversions -vd)
ifeq (,$(DEB_PYTHON_ARCH_PACKAGES))
  # check if current is in build versions
  ifneq ($(cdbs_python_current_version), $(filter $(cdbs_python_current_version), $(shell pyversions -vr)))
    cdbs_python_compile_version := $(firstword $(strip $(sort $(shell pyversions -vr))))
    cdbs_python_build_versions := $(cdbs_python_compile_version)
  else
    cdbs_python_build_versions := $(cdbs_python_current_version)
  endif
else
cdbs_python_build_versions := $(shell pyversions -vr)
endif # archall

# check if build is possible
ifeq (, $(cdbs_python_build_versions))
ifeq (pysupport, $(DEB_PYTHON_SYSTEM))
$(error invalid setting in 'debian/pyversions')
else
$(error invalid setting for XS-Python-Version)
endif # system selected
endif # build versions empty


# Declare Build-Deps for packages using this file
ifeq (,$(DEB_PYTHON_ARCH_PACKAGES))
  ifneq (, $(cdbs_python_compile_version))
    CDBS_BUILD_DEPENDS := $(CDBS_BUILD_DEPENDS), python$(cdbs_python_compile_version)-dev, python (>= 2.3.5-11)
  else
    CDBS_BUILD_DEPENDS := $(CDBS_BUILD_DEPENDS), python-dev (>= 2.3.5-11)
  endif
else
CDBS_BUILD_DEPENDS := $(CDBS_BUILD_DEPENDS), python-all-dev (>= 2.3.5-11)
endif
ifeq (pysupport, $(DEB_PYTHON_SYSTEM))
CDBS_BUILD_DEPENDS := $(CDBS_BUILD_DEPENDS), python-support (>= 0.6)
else
CDBS_BUILD_DEPENDS := $(CDBS_BUILD_DEPENDS), python-central (>= 0.6)
endif

# TODO: Support multiple python programs built for different python versions
# FIXME: Understand the above sentence and rephrase it
cdbs_python_curpkg_build_versions = $(cdbs_python_build_versions)

endif
