# -*- mode: makefile; coding: utf-8 -*-
# Copyright © 2008 Jonas Smedegaard <dr@jones.dk>
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
CDBS_BUILD_DEPENDS := $(shell echo '$(CDBS_BUILD_DEPENDS)' | sed -e '/\bcdbs (>= 0.4.43)/ s/\bcdbs *\(,\|(>= \(0.4.23-1.1\|0.4.27\|0.4.39\))\)/, /g')
CDBS_BUILD_DEPENDS := $(shell echo '$(CDBS_BUILD_DEPENDS)' | sed -e '/\bcdbs (>= 0.4.39)/ s/\bcdbs *\(,\|(>= \(0.4.23-1.1\|0.4.27\))\)/, /g')
CDBS_BUILD_DEPENDS := $(shell echo '$(CDBS_BUILD_DEPENDS)' | sed -e '/\bcdbs (>= 0.4.27)/ s/\bcdbs *\(,\|(>= \(0.4.23-1.1\))\)/, /g')
CDBS_BUILD_DEPENDS := $(shell echo '$(CDBS_BUILD_DEPENDS)' | sed -e '/\bdebhelper (>= 7.0.1)/ s/\bdebhelper *\(,\|(>= \(4.1.60\|4.2.0\|4.2.21\|4.2.28\|5\|5.0.37.2\|5.0.44\|6\))\)/, /g')
CDBS_BUILD_DEPENDS := $(shell echo '$(CDBS_BUILD_DEPENDS)' | sed -e '/\bdebhelper (>= 6)/ s/\bdebhelper *\(,\|(>= \(4.1.60\|4.2.0\|4.2.21\|4.2.28\|5\|5.0.37.2\|5.0.44\))\)/, /g')
CDBS_BUILD_DEPENDS := $(shell echo '$(CDBS_BUILD_DEPENDS)' | sed -e '/\bdebhelper (>= 5.0.44)/ s/\bdebhelper *\(,\|(>= \(4.1.60\|4.2.0\|4.2.21\|4.2.28\|5\|5.0.37.2\))\)/, /g')
CDBS_BUILD_DEPENDS := $(shell echo '$(CDBS_BUILD_DEPENDS)' | sed -e '/\bdebhelper (>= 5.0.37.2)/ s/\bdebhelper *\(,\|(>= \(4.1.60\|4.2.0\|4.2.21\|4.2.28\|5\))\)/, /g')
CDBS_BUILD_DEPENDS := $(shell echo '$(CDBS_BUILD_DEPENDS)' | sed -e '/\bdebhelper (>= 5)/ s/\bdebhelper *\(,\|(>= \(4.1.60\|4.2.0\|4.2.21\|4.2.28\))\)/, /g')
CDBS_BUILD_DEPENDS := $(shell echo '$(CDBS_BUILD_DEPENDS)' | sed -e '/\bdebhelper (>= 4.2.28)/ s/\bdebhelper *\(,\|(>= \(4.1.60\|4.2.0\|4.2.21\))\)/, /g')
CDBS_BUILD_DEPENDS := $(shell echo '$(CDBS_BUILD_DEPENDS)' | sed -e '/\bdebhelper (>= 4.2.21)/ s/\bdebhelper *\(,\|(>= \(4.1.60\|4.2.0\))\)/, /g')
CDBS_BUILD_DEPENDS := $(shell echo '$(CDBS_BUILD_DEPENDS)' | sed -e '/\bdebhelper (>= 4.2.0)/ s/\bdebhelper *\(,\|(>= \(4.1.60\))\)/, /g')

# TODO: Move these to buildcore.mk
cdbs_curvar = $(or $($(1)_$(cdbs_curpkg)),$($1))
cdbs_squash_commas = $(shell echo '$1' | sed -e 's/ *,[ ,]*/, /g' -e 's/^[ ,]*//' -e 's/[ ,]*$$//')

# Cleanup superfluous commas and whitespace
CDBS_BUILD_DEPENDS := $(call cdbs_squash_commas,$(CDBS_BUILD_DEPENDS))

comma = ,
cdbs_all_cur_squash_commas = $(call cdbs_squash_commas,$($(1)_ALL)$(comma) $(call cdbs_curvar,$1))

# Apply CDBS-declared dependencies to binary packages
$(patsubst %,binary-predeb/%,$(DEB_PACKAGES)) :: binary-predeb/%:
	@echo 'Adding cdbs dependencies to debian/$(cdbs_curpkg).substvars'
	@echo 'cdbs:Depends=$(call cdbs_all_cur_squash_commas,CDBS_DEPENDS)' >> debian/$(cdbs_curpkg).substvars
	@echo 'cdbs:Pre-Depends=$(call cdbs_all_cur_squash_commas,CDBS_PREDEPENDS)' >> debian/$(cdbs_curpkg).substvars
	@echo 'cdbs:Recommends=$(call cdbs_all_cur_squash_commas,CDBS_RECOMMENDS)' >> debian/$(cdbs_curpkg).substvars
	@echo 'cdbs:Suggests=$(call cdbs_all_cur_squash_commas,CDBS_SUGGESTS)' >> debian/$(cdbs_curpkg).substvars
	@echo 'cdbs:Breaks=$(call cdbs_all_cur_squash_commas,CDBS_BREAKS)' >> debian/$(cdbs_curpkg).substvars
	@echo 'cdbs:Provides=$(call cdbs_all_cur_squash_commas,CDBS_PROVIDES)' >> debian/$(cdbs_curpkg).substvars
	@echo 'cdbs:Replaces=$(call cdbs_all_cur_squash_commas,CDBS_REPLACES)' >> debian/$(cdbs_curpkg).substvars
	@echo 'cdbs:Conflicts=$(call cdbs_all_cur_squash_commas,CDBS_CONFLICTS)' >> debian/$(cdbs_curpkg).substvars
	@echo 'cdbs:Enhances=$(call cdbs_all_cur_squash_commas,CDBS_ENHANCES)' >> debian/$(cdbs_curpkg).substvars

endif
