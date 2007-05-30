# Copyright (C) 2007, Red Hat, Inc.
# Copyright (C) 2007, Collabora Ltd.
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
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

from sugar import env

import os.path
import cPickle

class BuddyIconCache(object):
    """Caches icons on disk and finds them based on the jid of their owners."""
    def __init__(self):
        ppath = env.get_profile_path()
        self._cachepath = os.path.join(ppath, "cache", "buddy-icons", "cache")

        # Ensure cache directory exists
        if not os.path.exists(os.path.dirname(self._cachepath)):
            os.makedirs(os.path.dirname(self._cachepath))

        if not os.path.exists(self._cachepath):
            self._cache = {}
            # md5 and server token of the last avatar uploaded
            self._md5 = ''
            self._token = ''
        else:
            self._load_cache()

    def _load_cache(self):
        try:
            self._cache, self._md5, self._token = cPickle.load(open(self._cachepath, "r"))
        except:
            self._cache, self._md5, self._token = {}, '', ''

    def _save_cache(self):
        out = open(self._cachepath, "w")
        cPickle.dump((self._cache, self._md5, self._token), out, protocol=2)

    def get_icon(self, jid, token):
        hit = self._cache.get(jid)

        if hit:
            t, icon = hit[0], hit[1]
            if t == token:
                return icon

        return None

    def store_icon(self, jid, token, data):
        self._cache[jid] = (token, data)
        self._save_cache()

    def check_avatar(self, md5, token):
        return self._md5 == md5 and self._token == token

    def set_avatar(self, md5, token):
        self._md5 = md5
        self._token = token
        self._save_cache()

if __name__ == "__main__":
    my_cache = BuddyIconCache()
    
    # look for the icon in the cache
    icon = my_cache.get_icon("test@olpc.collabora.co.uk", "aaaa")
    print icon

    my_cache.store_icon("test@olpc.collabora.co.uk", "aaaa", "icon1")

    # now we're sure that the icon is in the cache
    icon = my_cache.get_icon("test@olpc.collabora.co.uk", "aaaa")
    print icon

    # new icon
    my_cache.store_icon("test@olpc.collabora.co.uk", "bbbb", "icon2")

    # the icon in the cache is not valid now
    icon = my_cache.get_icon("test@olpc.collabora.co.uk", "aaaa")
    print icon


    my_avatar_md5 = "111"
    my_avatar_token = "222"

    if not my_cache.check_avatar(my_avatar_md5, my_avatar_token):
        # upload of the new avatar
        print "upload of the new avatar"
        my_cache.set_avatar(my_avatar_md5, my_avatar_token)
    else:
        print "No need to upload the new avatar"

    if my_cache.check_avatar(my_avatar_md5, my_avatar_token):
        print "No need to upload the new avatar"
