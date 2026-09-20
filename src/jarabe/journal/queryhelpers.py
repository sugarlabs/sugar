# Copyright (C) 2007-2011, One Laptop per Child
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


def normalize_uid(uid):
    """Return a plain str uid for Journal selection comparisons.

    Datastore and D-Bus calls may yield bytes or dbus string subtypes.
    Selection uses `uid in list`, which fails across those types.
    """
    if uid is None:
        return None
    if isinstance(uid, bytes):
        return uid.decode()
    return str(uid)


def apply_prefix_wildcards(query):
    """Mutate a Journal query so unquoted search words are prefix matches.

    DatastoreResultSet.find() uses this form. Select All must use the same
    query, otherwise prefix searches such as "term" match the list but not
    the id set used to select every visible entry.
    """
    query_text = query.get('query', '')
    if query_text and not query_text.startswith('"'):
        words = []
        for word in query_text.split(' '):
            if word:
                words.append(word + '*')
        query['query'] = ' '.join(words)
    return query


def query_for_find_ids(processed_query):
    """Return the datastore find_ids query for a processed result set."""
    copy = processed_query.copy()
    copy.pop('mountpoints', None)
    return copy
