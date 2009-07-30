#!/usr/bin/python
# Copyright (C) 2009, Sugar Labs
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA
"""Sugar bundle updater: model.

This module implements the non-GUI portions of the bundle updater, including
list of installed bundls, whether updates are needed, and the URL at which to
find the bundle updated.

`UpdateList` inherits from `gtk.ListStore` in order to work closely with the
view pane. This module requires `gtk`.
"""

import os
import tempfile
import locale
import logging
import urllib

import gettext
_ = lambda msg: gettext.dgettext('sugar-update-control', msg)

import gtk
import gobject

from jarabe.model import bundleregistry
from sugar.bundle.activitybundle import ActivityBundle
from sugar.datastore import datastore
from backends import aslo

#_logger = logging.getLogger('update-activity')

##########################################################################
# Fundamental data object.

_column_name_map = dict(globals())

"""List of columns in the `UpdateList`."""
BUNDLE_ID, \
    BUNDLE, \
    ICON, \
    NAME, \
    CURRENT_VERSION, \
    UPDATE_VERSION, \
    UPDATE_SIZE, \
    UPDATE_URL, \
    DESCRIPTION, \
    UPDATE_SELECTED, \
    UPDATE_AVAILABLE, \
    IS_HEADER = xrange(12)


"""Map column names to indices."""
_column_name_map = dict((k,v) for k,v in globals().items()
                        if k not in _column_name_map and k!='_column_name_map')


class UpdateList(gtk.ListStore):
    """Model which provides backing storage for the BUNDLE list treeview."""

    __gproperties__ = {
        'is_valid': (gobject.TYPE_BOOLEAN, 'is valid',
                     'true iff the UpdateList has been properly refreshed',
                     False, gobject.PARAM_READABLE),
        'saw_network_failure': (gobject.TYPE_BOOLEAN, 'saw network failure',
                                'true iff at least one network IO error '+
                                'occurred when the UpdateList was last '+
                                'refreshed',
                                False, gobject.PARAM_READABLE),
        'saw_network_success': (gobject.TYPE_BOOLEAN, 'saw network success',
                                'true iff at least one network operation '+
                                'completed successfully when the UpdateList '+
                                'was last refreshed',
                                False, gobject.PARAM_READABLE),
    }

    def __init__(self):
        logging.debug('STARTUP: Loading the bundle updater')

        gtk.ListStore.__init__(self,
                               str, object, gtk.gdk.Pixbuf, str,
                               long, long, long, str,
                               str, bool, bool, bool)

        self._cancel = False
        self._is_valid = True
        self.registry =bundleregistry.get_registry()

    def refresh_list(self, progress_callback=lambda n, extra: None,
                           clear_cache=True):
        self._cancel = False
        self._progress_cb = progress_callback
        self._progress_cb(None, _('Looking for local actvities...'))

        self.clear()
        self.steps_total = len(self.registry._bundles)
        self.steps_count = 0

        row_map = {}

        for bundle in self.registry._bundles:
            self._make_progress(_('Checking %s...') % bundle.get_name())

            if self._cancel:
                break # Cancel bundle refresh

            row = [None, None, None, None,
                   0, 0, 0, None,
                   None, True, False, False]
            row[BUNDLE] = bundle
            row[BUNDLE_ID] = bundle.get_bundle_id()

            if self.refresh_row(row):
                row_map[row[BUNDLE_ID]] = self.get_path(self.append(row))

    def cancel(self):
        self._cancel = True

    def refresh_row(self, row):
        logging.debug('Looking for %s' % row[BUNDLE].get_name())

        try:
            new_version, new_url, new_size = aslo.fetch_update_info(row[BUNDLE])
        except Exception, e:
            logging.warning('Failure %s updating: %s' % \
                    (row[BUNDLE].get_name(), e))
            return False

        row[CURRENT_VERSION] = row[BUNDLE].get_activity_version()
        row[UPDATE_VERSION] = long(new_version)

        if row[CURRENT_VERSION] >= row[UPDATE_VERSION]:
            logging.debug('Skip %s update' % row[BUNDLE].get_name())
            return False

        row[ICON] = gtk.gdk.pixbuf_new_from_file_at_size(
                row[BUNDLE].get_icon(), 32, 32)
        row[NAME] = row[BUNDLE].get_name()
        row[UPDATE_URL] = new_url
        row[UPDATE_AVAILABLE] = True
        row[UPDATE_SIZE] = new_size
        row[DESCRIPTION] = \
                _('From version %(current)d to %(new)s (Size: %(size)s)') % \
                { 'current' : row[CURRENT_VERSION],
                  'new'     : row[UPDATE_VERSION],
                  'size'    :_humanize_size(row[UPDATE_SIZE]) }
        row[UPDATE_SELECTED] = True

        return True

    def install_updates(self, progress_cb=(lambda n, row: None)):
        self._cancel = False
        self._progress_cb = progress_cb
        self.steps_total = len([0 for row in self if row[UPDATE_SELECTED]]) * 2
        self.steps_count = 0

        installed = 0

        for row in self:
            if self._cancel:
                return installed
            if row[IS_HEADER]:
                continue
            if not row[UPDATE_SELECTED]:
                continue

            logging.debug('Downloading %s from %s' % \
                    (row[NAME], row[UPDATE_URL]))
            self._make_progress(_('Downloading %s...') % row[NAME])

            fd, xofile = tempfile.mkstemp(suffix='.xo')
            os.close(fd)
            try:
                try:
                    urllib.urlretrieve(row[UPDATE_URL], xofile)
                except Exception, e:
                    logging.warning("Can't download %s" % row[UPDATE_URL])
                    continue

                if self._cancel:
                    return installed

                logging.debug('Installing %s' % row[NAME])
                self._make_progress(_('Installing %s...') % row[NAME])

                jobject = datastore.create()
                jobject.metadata['title'] = \
                        '%s-%s' % (row[NAME], row[UPDATE_VERSION])
                jobject.metadata['mime_type'] = ActivityBundle.MIME_TYPE
                jobject.file_path = xofile
                datastore.write(jobject, transfer_ownership=True)

                installed += 1
            finally:
                if os.path.exists(xofile):
                    os.unlink(xofile)

        return installed

###############################################################################

    def _make_progress(self, msg=None): #FIXME needs better name
        """Helper function to do progress update."""
        self.steps_count += 1
        self._progress_cb(float(self.steps_count)/self.steps_total, msg)

    def _sum_rows(self, row_func):
        """Sum the values returned by row_func called on all non-header
        rows."""
        return sum(row_func(r) for r in self if not r[IS_HEADER])

###############################################################################

    def updates_available(self):
        """Return the number of updates available.

        Updated by `refresh`."""
        return self._sum_rows(lambda r: 1 if r[UPDATE_AVAILABLE] else 0)

    def updates_selected(self):
        """Return the number of updates selected."""
        return self._sum_rows(lambda r: 1 if
                              r[UPDATE_AVAILABLE] and r[UPDATE_SELECTED] else 0)

    def updates_size(self):
        """Returns the size (in bytes) of the selected updates available.

        Updated by `refresh`."""
        return self._sum_rows(lambda r: r[UPDATE_SIZE] if
                              r[UPDATE_AVAILABLE] and r[UPDATE_SELECTED] else 0)
    def is_valid(self):
        """The UpdateList is invalidated before it is refreshed, and when
        the group information is modified without refreshing."""
        return self._is_valid

###############################################################################
# Utility Funtions

def _humanize_size(bytes):
    """
    Convert a given size in bytes to a nicer better readable unit
    """
    if bytes == 0:
        # TRANSLATORS: download size is 0
        return _("None")
    elif bytes < 1024:
        # TRANSLATORS: download size of very small updates
        return _("1 KB")
    elif bytes < 1024 * 1024:
        # TRANSLATORS: download size of small updates, e.g. "250 KB"
        return locale.format(_("%.0f KB"), bytes/1024)
    else:
        # TRANSLATORS: download size of updates, e.g. "2.3 MB"
        return locale.format(_("%.1f MB"), bytes / 1024 / 1024)

def print_available(ul):#FIXME this should onlu return available updates
    print
    def opt(x):
        if x is None or x == '': return ''
        return ': %s' % x
    for row in ul:
        if row[IS_HEADER]:
            print row[NAME] + opt(row[DESCRIPTION])
        else:
            print '*', row[NAME] + opt(row[DESCRIPTION])
    print
    #print _('%(number)d updates available.  Size: %(size)s') % \
    #      { 'number': ul.updates_available(),
    #        'size': _humanize_size(ul.updates_size()) }

###############################################################################
# Self-test code.
def _main():
    """Self-test."""
    update_list = UpdateList()
    update_list.refresh_list()
    print_available(update_list)
    update_list.install_updates()

if __name__ == '__main__': _main ()
