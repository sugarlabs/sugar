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

include $(_cdbs_rules_path)/buildvars.mk$(_cdbs_makefile_suffix)

DEB_PYTHON_PACKAGES = $(filter-out %-doc %-dev %-common, $(DEB_PACKAGES))

DEB_PYTHON_ARCH_PACKAGES = $(filter $(DEB_PYTHON_PACKAGES), $(DEB_ARCH_PACKAGES))
DEB_PYTHON_INDEP_PACKAGES = $(filter $(DEB_PYTHON_PACKAGES), $(DEB_INDEP_PACKAGES))

## FIXME: Resolve DEB_PYTHON_PACKAGES in build targets only
# Avoid including buildcore.mk to not risk breaking when hopefully removing again
cdbs_python_streq = $(if $(filter-out xx,x$(subst $1,,$2)$(subst $2,,$1)x),,yes)
cdbs_python_packages_pre := $(DEB_PYTHON_ARCH_PACKAGES)$(DEB_PYTHON_INDEP_PACKAGES)
cdbs_python_pkgresolve_check = $(if $(call cdbs_python_streq,$(DEB_PYTHON_ARCH_PACKAGES)$(DEB_PYTHON_INDEP_PACKAGES),$(cdbs_python_packages_pre)),, $(warning Setting DEB_PYTHON_*PACKAGES after python-vars in included is currently unsupported))
## TODO: Rephrase when DEB_PYTHON_PACKAGES is only resolved in build targets
cdbs_python_pkg_check = $(if $(DEB_PYTHON_ARCH_PACKAGES)$(DEB_PYTHON_INDEP_PACKAGES),, $(warning No Python packages found or declared - either rename binary packages or set DEB_PYTHON_PACKAGES (or one or both of DEB_PYTHON_ARCH_PACKAGES and DEB_PYTHON_INDEP_PACKAGES) before including python-vars.mk))

# check python system
cdbs_use_xs_field := $(shell grep -q "^XS-Python-Version:" debian/control && echo yes)
cdbs_selected_pycompat := $(shell if [ -e debian/pycompat ]; then cat debian/pycompat; fi)
cdbs_pycompat = $(cdbs_selected_pycompat)
ifeq (pysupport, $(DEB_PYTHON_SYSTEM))
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
cdbs_python_current_version := $(shell pyversions -vd)
## FIXME: Resolve DEB_PYTHON_PACKAGES in build targets only
ifeq (,$(cdbs_python_pkg_check)$(DEB_PYTHON_ARCH_PACKAGES))
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

# TODO: Support multiple python programs built for different python versions
# FIXME: Understand the above sentence and rephrase it
cdbs_python_curpkg_build_versions = $(cdbs_python_build_versions)

## TODO: Drop this when DEB_PYTHON_PACKAGES is only resolved in build targets
pre-build clean::
	$(cdbs_python_pkgresolve_check)

endif
