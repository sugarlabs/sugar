# -*- mode: makefile; coding: utf-8 -*-
# Copyright © 2005-2008 Jonas Smedegaard <dr@jones.dk>
# Description: Check for changes to copyright notices in source
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

ifndef _cdbs_rules_copyright-check
_cdbs_rules_copyright-check := 1

include $(_cdbs_rules_path)/buildcore.mk$(_cdbs_makefile_suffix)

CDBS_BUILD_DEPENDS := $(CDBS_BUILD_DEPENDS), devscripts (>= 2.10.7)

# Single regular expression for files to include or ignore
DEB_COPYRIGHT_CHECK_REGEX = .*
DEB_COPYRIGHT_CHECK_IGNORE_REGEX = ^(debian/.*|(.*/)?config\.(guess|sub|rpath)(\..*)?)$

# By default sort by license and then by filename
DEB_COPYRIGHT_CHECK_SORT_OPTS = -k2,2 -k1

pre-build:: debian/stamp-copyright-check

debian/stamp-copyright-check:
	@echo 'Scanning upstream source for new/changed copyright notices (except debian subdir!)...'

	licensecheck -c '$(DEB_COPYRIGHT_CHECK_REGEX)' -r --copyright -i '$(DEB_COPYRIGHT_CHECK_IGNORE_REGEX)' * \
		| grep -v '^\(\|.*: \*No copyright\* UNKNOWN\)$$' \
		| sed 's/\s*(with incorrect FSF address)\s*$$//; s/\s(\+v\(.\+\) or later)/-\1\+/; s/^\s*\[Copyright:\s*/ \[/' \
		| awk '/^[^ ]/{printf "%s",$$0;next}{print}' \
		| LC_ALL=C sort $(DEB_COPYRIGHT_CHECK_SORT_OPTS) \
		> debian/copyright_newhints
	@patterncount="`cat debian/copyright_newhints | sed 's/^[^:]*://' | LANG=C sort -u | grep . -c`"; \
		echo "Found $$patterncount different copyright and licensing combinations."
	@if [ ! -f debian/copyright_hints ]; then touch debian/copyright_hints; fi
	@newstrings=`diff -u debian/copyright_hints debian/copyright_newhints | sed '1,2d' | egrep '^\+' | sed 's/^\+//'`; \
		if [ -n "$$newstrings" ]; then \
			echo "ERROR: The following new or changed copyright notices discovered:"; \
			echo; \
			echo "$$newstrings"; \
			echo; \
			echo "To fix the situation please do the following:"; \
			echo "  1) Investigate the above changes and update debian/copyright as needed"; \
			echo "  2) Replace debian/copyright_hints with debian/copyright_newhints"; \
			exit 1; \
		fi
	
	@echo 'No new copyright notices found - assuming no news is good news...'
	rm -f debian/copyright_newhints
	touch $@

clean::
	rm -f debian/stamp-copyright-check

endif
