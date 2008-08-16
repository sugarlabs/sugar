# -*- mode: makefile; coding: utf-8 -*-
# Copyright © 2004-2006 Jonas Smedegaard <dr@jones.dk>
# Description: Resolve, cleanup and apply package relationships
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

ifndef _cdbs_rules_package_relations
_cdbs_rules_package_relations = 1

include $(_cdbs_rules_path)/buildcore.mk$(_cdbs_makefile_suffix)

# Merge build-dependencies on same packages
# TODO: rewrite (in perl, probably) to be more generic
CDBS_BUILD_DEPENDS := $(shell echo '$(CDBS_BUILD_DEPENDS)' | sed -e '/\bcdbs (>= 0.4.43)/ s/ *,* *\bcdbs (>= \(0.4.23-1.1\|0.4.27\|0.4.39\)) *,* */, /g')
CDBS_BUILD_DEPENDS := $(shell echo '$(CDBS_BUILD_DEPENDS)' | sed -e '/\bcdbs (>= 0.4.39)/ s/ *,* *\bcdbs (>= \(0.4.23-1.1\|0.4.27\)) *,* */, /g')
CDBS_BUILD_DEPENDS := $(shell echo '$(CDBS_BUILD_DEPENDS)' | sed -e '/\bcdbs (>= 0.4.27)/ s/ *,* *\bcdbs (>= \(0.4.23-1.1\)) *,* */, /g')
CDBS_BUILD_DEPENDS := $(shell echo '$(CDBS_BUILD_DEPENDS)' | sed -e '/\bdebhelper (>= 5.0.44)/ s/ *,* *\bdebhelper (>= \(4.1.60\|4.2.0\|4.2.21\|4.2.28\|5\|5.0.37.2\)) *,* */, /g')
CDBS_BUILD_DEPENDS := $(shell echo '$(CDBS_BUILD_DEPENDS)' | sed -e '/\bdebhelper (>= 5.0.37.2)/ s/ *,* *\bdebhelper (>= \(4.1.60\|4.2.0\|4.2.21\|4.2.28\|5\)) *,* */, /g')
CDBS_BUILD_DEPENDS := $(shell echo '$(CDBS_BUILD_DEPENDS)' | sed -e '/\bdebhelper (>= 5)/ s/ *,* *\bdebhelper (>= \(4.1.60\|4.2.0\|4.2.21\|4.2.28\)) *,* */, /g')
CDBS_BUILD_DEPENDS := $(shell echo '$(CDBS_BUILD_DEPENDS)' | sed -e '/\bdebhelper (>= 4.2.28)/ s/ *,* *\bdebhelper (>= \(4.1.60\|4.2.0\|4.2.21\)) *,* */, /g')
CDBS_BUILD_DEPENDS := $(shell echo '$(CDBS_BUILD_DEPENDS)' | sed -e '/\bdebhelper (>= 4.2.21)/ s/ *,* *\bdebhelper (>= \(4.1.60\|4.2.0\)) *,* */, /g')
CDBS_BUILD_DEPENDS := $(shell echo '$(CDBS_BUILD_DEPENDS)' | sed -e '/\bdebhelper (>= 4.2.0)/ s/ *,* *\bdebhelper (>= \(4.1.60\)) *,* */, /g')

# Cleanup superfluous commas
CDBS_BUILD_DEPENDS := $(shell echo '$(CDBS_BUILD_DEPENDS)' | sed -e 's/ *,/,/g' -e 's/^ *, *//' -e 's/ *, *$$//')

# Apply CDBS-declared dependencies to binary packages
$(patsubst %,binary-predeb/%,$(DEB_PACKAGES)) :: binary-predeb/%:
	echo 'cdbs:Depends=$(CDBS_DEPENDS_ALL), $(or $(CDBS_DEPENDS_$(cdbs_curpkg)),$(CDBS_DEPENDS))' \
	  | sed -e 's/ *,/,/g' -e 's/^ *, *//' -e 's/ *, *$$//' \
	  >> debian/$(cdbs_curpkg).substvars

endif
