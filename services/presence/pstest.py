# Copyright (C) 2007, Red Hat, Inc.
# Copyright (C) 2007 Collabora Ltd. <http://www.collabora.co.uk/>
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

import logging
import os
import random
from ConfigParser import ConfigParser, NoOptionError

import gobject

from sugar import env, util

from buddy import GenericOwner, _PROP_NICK, _PROP_CURACT, _PROP_COLOR
from presenceservice import PresenceService


_logger = logging.getLogger('s-p-s.pstest')


class TestOwner(GenericOwner):
    """Class representing the owner of the machine.  This test owner
    changes random attributes periodically."""

    __gtype_name__ = "TestOwner"

    def __init__(self, ps, bus, object_id, test_num, randomize):
        self._cp = ConfigParser()
        self._section = "Info"
        self._test_activities = []
        self._test_cur_act = ""
        self._change_timeout = 0

        self._cfg_file = os.path.join(env.get_profile_path(), 'test-buddy-%d' % test_num)

        (pubkey, privkey, registered) = self._load_config()
        if not pubkey or not len(pubkey) or not privkey or not len(privkey):
            (pubkey, privkey) = _get_new_keypair(test_num)

        if not pubkey or not privkey:
            raise RuntimeError("Couldn't get or create test buddy keypair")

        self._save_config(pubkey, privkey, registered)
        privkey_hash = util.printable_hash(util._sha_data(privkey))

        nick = _get_random_name()
        from sugar.graphics import xocolor
        color = xocolor.XoColor().to_string()
        icon = _get_random_image()

        _logger.debug("pubkey is %s" % pubkey)
        GenericOwner.__init__(self, ps, bus, object_id, key=pubkey, nick=nick,
                color=color, icon=icon, registered=registered, key_hash=privkey_hash)

        # Only do the random stuff if randomize is true
        if randomize:
            self._ps.connect('connection-status', self._ps_connection_status_cb)

    def _share_reply_cb(self, actid, object_path):
        activity = self._ps.internal_get_activity(actid)
        if not activity or not object_path:
            _logger.debug("Couldn't find activity %s even though it was shared." % actid)
            return
        _logger.debug("Shared activity %s (%s)." % (actid, activity.props.name))
        self._test_activities.append(activity)

    def _share_error_cb(self, actid, err):
        _logger.debug("Error sharing activity %s: %s" % (actid, str(err)))

    def _ps_connection_status_cb(self, ps, connected):
        if not connected:
            return

        if not len(self._test_activities):
            # Share some activities
            actid = util.unique_id("Activity 1")
            callbacks = (lambda *args: self._share_reply_cb(actid, *args),
                         lambda *args: self._share_error_cb(actid, *args))
            atype = "org.laptop.WebActivity"
            properties = {"foo": "bar"}
            self._ps._share_activity(actid, atype, "Wembley Stadium", properties, callbacks)

            actid2 = util.unique_id("Activity 2")
            callbacks = (lambda *args: self._share_reply_cb(actid2, *args),
                         lambda *args: self._share_error_cb(actid2, *args))
            atype = "org.laptop.WebActivity"
            properties = {"baz": "bar"}
            self._ps._share_activity(actid2, atype, "Maine Road", properties, callbacks)

        # Change a random property ever 10 seconds
        if self._change_timeout == 0:
            self._change_timeout = gobject.timeout_add(10000, self._update_something)

    def set_registered(self, value):
        if value:
            self._registered = True

    def _load_config(self):
        if not os.path.exists(self._cfg_file):
            return (None, None, False)
        if not self._cp.read([self._cfg_file]):
            return (None, None, False)
        if not self._cp.has_section(self._section):
            return (None, None, False)

        try:
            pubkey = self._cp.get(self._section, "pubkey")
            privkey = self._cp.get(self._section, "privkey")
            registered = self._cp.get(self._section, "registered")
            return (pubkey, privkey, registered)
        except NoOptionError:
            pass

        return (None, None, False)

    def _save_config(self, pubkey, privkey, registered):
        # Save config again
        if not self._cp.has_section(self._section):
            self._cp.add_section(self._section)
        self._cp.set(self._section, "pubkey", pubkey)
        self._cp.set(self._section, "privkey", privkey)
        self._cp.set(self._section, "registered", registered)
        f = open(self._cfg_file, 'w')
        self._cp.write(f)
        f.close()

    def _update_something(self):
        it = random.randint(0, 10000) % 4
        if it == 0:
            self.props.icon = _get_random_image()
        elif it == 1:
            from sugar.graphics import xocolor
            props = {_PROP_COLOR: xocolor.XoColor().to_string()}
            self.set_properties(props)
        elif it == 2:
            props = {_PROP_NICK: _get_random_name()}
            self.set_properties(props)
        elif it == 3:
            actid = ""
            idx = random.randint(0, len(self._test_activities))
            # if idx == len(self._test_activites), it means no current
            # activity
            if idx < len(self._test_activities):
                activity = self._test_activities[idx]
                actid = activity.props.id
            props = {_PROP_CURACT: actid}
            self.set_properties(props)
        return True


class TestPresenceService(PresenceService):

    def __init__(self, test_num=0, randomize=False):
        self.__test_num = test_num
        self.__randomize = randomize
        PresenceService.__init__(self)

    def _create_owner(self):
        return TestOwner(self, self._session_bus, self._get_next_object_id(),
                         self.__test_num, self.__randomize)

    def internal_get_activity(self, actid):
        return self._activities.get(actid, None):


def _extract_public_key(keyfile):
    try:
        f = open(keyfile, "r")
        lines = f.readlines()
        f.close()
    except IOError, e:
        _logger.error("Error reading public key: %s" % e)
        return None

    # Extract the public key
    magic = "ssh-dss "
    key = ""
    for l in lines:
        l = l.strip()
        if not l.startswith(magic):
            continue
        key = l[len(magic):]
        break
    if not len(key):
        _logger.error("Error parsing public key.")
        return None
    return key

def _extract_private_key(keyfile):
    """Get a private key from a private key file"""
    # Extract the private key
    try:
        f = open(keyfile, "r")
        lines = f.readlines()
        f.close()
    except IOError, e:
        _logger.error("Error reading private key: %s" % e)
        return None

    key = ""
    for l in lines:
        l = l.strip()
        if l.startswith("-----BEGIN DSA PRIVATE KEY-----"):
            continue
        if l.startswith("-----END DSA PRIVATE KEY-----"):
            continue
        key += l
    if not len(key):
        _logger.error("Error parsing private key.")
        return None
    return key

def _get_new_keypair(num):
    """Retrieve a public/private key pair for testing"""
    # Generate keypair
    privkeyfile = os.path.join("/tmp", "test%d.key" % num)
    pubkeyfile = os.path.join("/tmp", 'test%d.key.pub' % num)

    # force-remove key files if they exist to ssh-keygen doesn't
    # start asking questions
    try:
        os.remove(pubkeyfile)
        os.remove(privkeyfile)
    except OSError:
        pass

    cmd = "ssh-keygen -q -t dsa -f %s -C '' -N ''" % privkeyfile
    import commands
    print "Generating new keypair..."
    (s, o) = commands.getstatusoutput(cmd)
    print "Done."
    pubkey = privkey = None
    if s != 0:
        _logger.error("Could not generate key pair: %d (%s)" % (s, o))
    else:
        pubkey = _extract_public_key(pubkeyfile)
        privkey = _extract_private_key(privkeyfile)

    try:
        os.remove(pubkeyfile)
        os.remove(privkeyfile)
    except OSError:
        pass
    return (pubkey, privkey)

def _get_random_name():
    """Produce random names for testing"""
    names = ["Liam", "Noel", "Guigsy", "Whitey", "Bonehead"]
    return names[random.randint(0, len(names) - 1)]

def _get_random_image():
    """Produce a random image for display"""
    import cairo, math, gtk

    def rand():
        return random.random()

    SIZE = 200

    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, SIZE, SIZE)
    cr = cairo.Context(s)

    # background gradient
    cr.save()
    g = cairo.LinearGradient(0, 0, 1, 1)
    g.add_color_stop_rgba(1, rand(), rand(), rand(), rand())
    g.add_color_stop_rgba(0, rand(), rand(), rand(), rand())
    cr.set_source(g)
    cr.rectangle(0, 0, SIZE, SIZE);
    cr.fill()
    cr.restore()

    # random path
    cr.set_line_width(10 * rand() + 5)
    cr.move_to(SIZE * rand(), SIZE * rand())
    cr.line_to(SIZE * rand(), SIZE * rand())
    cr.rel_line_to(SIZE * rand() * -1, 0)
    cr.close_path()
    cr.stroke()

    # a circle
    cr.set_source_rgba(rand(), rand(), rand(), rand())
    cr.arc(SIZE * rand(), SIZE * rand(), 100 * rand() + 30, 0, 2 * math.pi)
    cr.fill()

    # another circle
    cr.set_source_rgba(rand(), rand(), rand(), rand())
    cr.arc(SIZE * rand(), SIZE * rand(), 100 * rand() + 30, 0, 2 * math.pi)
    cr.fill()

    def img_convert_func(buf, data):
        data[0] += buf
        return True

    data = [""]
    pixbuf = gtk.gdk.pixbuf_new_from_data(s.get_data(), gtk.gdk.COLORSPACE_RGB,
            True, 8, s.get_width(), s.get_height(), s.get_stride())
    pixbuf.save_to_callback(img_convert_func, "jpeg", {"quality": "90"}, data)
    del pixbuf

    return str(data[0])
