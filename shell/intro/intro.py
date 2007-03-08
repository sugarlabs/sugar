# Copyright (C) 2007, Red Hat, Inc.
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

import gtk, gobject
import dbus
import hippo
import logging
from gettext import gettext as _

import os
from ConfigParser import ConfigParser

from sugar import env

from sugar.graphics import entry
from sugar.graphics import units
from sugar.graphics import font
from sugar.graphics import color
from sugar.graphics import iconbutton

import colorpicker

_VIDEO_WIDTH = units.points_to_pixels(160)
_VIDEO_HEIGHT = units.points_to_pixels(120)

class IntroImage(gtk.EventBox):
    __gtype_name__ = "IntroImage"

    def __init__(self, **kwargs):
        gtk.EventBox.__init__(self, **kwargs)
        self._image = gtk.Image()
        self.add(self._image)

    def set_pixbuf(self, pixbuf):
        if pixbuf:
            self._image.set_from_pixbuf(pixbuf)
        else:
            self._image.clear()


class IntroFallbackVideo(gtk.EventBox):
    __gtype_name__ = "IntroFallbackVideo"

    __gsignals__ = {
        'pixbuf': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT])),
    }

    def __init__(self, **kwargs):
        gtk.EventBox.__init__(self, **kwargs)
        self._image = gtk.Image()
        self._image.set_from_stock(gtk.STOCK_OPEN, -1)
        self.add(self._image)
        self._image.show()
        self.connect('button-press-event', self._button_press_event_cb)

    def play(self):
        pass

    def stop(self):
        pass

    def _button_press_event_cb(self, widget, event):
        filt = gtk.FileFilter()
        filt.add_pixbuf_formats()
        chooser = gtk.FileChooserDialog(_("Pick a buddy picture"), \
                    buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT, gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        chooser.set_filter(filt)
        resp = chooser.run()
        if resp == gtk.RESPONSE_ACCEPT:
            fname = chooser.get_filename()
            self.load_image(fname)
        chooser.hide()
        chooser.destroy()
        return True

    def load_image(self, path):
        pixbuf = gtk.gdk.pixbuf_new_from_file(path)
        self.emit('pixbuf', pixbuf)

class VideoBox(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = "SugarVideoBox"

    def __init__(self, **kwargs):
        hippo.CanvasBox.__init__(self, **kwargs)
        self.props.orientation = hippo.ORIENTATION_HORIZONTAL
        self._pixbuf = None

        self._label = hippo.CanvasText(text=_("My Picture:"),
                                       xalign=hippo.ALIGNMENT_START,
                                       padding_right=units.grid_to_pixels(0.5))
        self._label.props.color = color.LABEL_TEXT.get_int()
        self._label.props.font_desc = font.DEFAULT.get_pango_desc()
        self.append(self._label)

        # check for camera and if not generate a .jpg
        has_webcam = False
        try:
            sys_bus = dbus.SystemBus()
            hal_obj = sys_bus.get_object ('org.freedesktop.Hal', '/org/freedesktop/Hal/Manager')
            hal = dbus.Interface (hal_obj, 'org.freedesktop.Hal.Manager')

            udis = hal.FindDeviceByCapability ('video4linux')

            # check for the olpc specific camera
            if not udis:
                udis = hal.FindDeviceStringMatch('info.linux.driver','cafe1000-ccic')

            if udis:
                has_webcam = True
                 
        finally:
            if has_webcam:
                import glive
                self._video = glive.LiveVideoSlot(_VIDEO_WIDTH, _VIDEO_HEIGHT)
            else:
                self._video = IntroFallbackVideo()

        self._video.set_size_request(_VIDEO_WIDTH, _VIDEO_HEIGHT)
        self._video.connect('pixbuf', self._new_pixbuf_cb)

        self._video_widget = hippo.CanvasWidget()
        self._video_widget.props.widget = self._video
        self.append(self._video_widget)
        gobject.idle_add(self._video.play)

        self._img = IntroImage()
        self._img.set_size_request(_VIDEO_WIDTH, _VIDEO_HEIGHT)
        self._img.connect('button-press-event', self._clear_image_cb)
        self._img_widget = hippo.CanvasWidget()
        self._img_widget.props.widget = self._img

        if not has_webcam:
            path = os.path.join(env.get_data_dir(),'default-picture.png')
            self._video.load_image(path)

    def _clear_image_cb(self, widget, event):
        del self._pixbuf
        self._pixbuf = None
        self.remove(self._img_widget)
        self._img.set_pixbuf(None)

        self.append(self._video_widget)
        self._video.play()

    def _new_pixbuf_cb(self, widget, pixbuf):
        if self._pixbuf:
            del self._pixbuf
        self._pixbuf = pixbuf
        self._video.stop()
        self.remove(self._video_widget)

        scaled = pixbuf.scale_simple(_VIDEO_WIDTH, _VIDEO_HEIGHT, gtk.gdk.INTERP_BILINEAR)
        self._img.set_pixbuf(scaled)
        self._img.show_all()
        self.append(self._img_widget)

    def get_pixbuf(self):
        return self._pixbuf

class EntryBox(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = "SugarEntryBox"

    def __init__(self, **kwargs):
        hippo.CanvasBox.__init__(self, **kwargs)
        self.props.orientation = hippo.ORIENTATION_HORIZONTAL

        self._label = hippo.CanvasText(text=_("My Name:"),
                                       xalign=hippo.ALIGNMENT_START,
                                       padding_right=units.grid_to_pixels(0.5))
        self._label.props.color = color.LABEL_TEXT.get_int()
        self._label.props.font_desc = font.DEFAULT.get_pango_desc()
        self.append(self._label)

        self._entry = entry.Entry()
        self.append(self._entry)

    def get_text(self):
        return self._entry.props.text


class ColorBox(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = "SugarColorBox"

    def __init__(self, **kwargs):
        hippo.CanvasBox.__init__(self, **kwargs)
        self.props.orientation = hippo.ORIENTATION_HORIZONTAL
        self._color = None

        self._label = hippo.CanvasText(text=_("My Color:"),
                                       xalign=hippo.ALIGNMENT_START,
                                       padding_right=units.grid_to_pixels(0.5))
        self._label.props.color = color.LABEL_TEXT.get_int()
        self._label.props.font_desc = font.DEFAULT.get_pango_desc()
        self.append(self._label)

        self._cp = colorpicker.ColorPicker()
        self._cp.connect('color', self._new_color_cb)
        self.append(self._cp)

        self._color = self._cp.get_color()

    def _new_color_cb(self, widget, color):
        self._color = color

    def get_color(self):
        return self._color

class IntroBox(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'SugarIntroBox'

    __gsignals__ = {
        'ok': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
              ([gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT]))
    }

    def __init__(self, **kwargs):
        hippo.CanvasBox.__init__(self, **kwargs)
        self._pixbuf = None

        self._video_box = VideoBox(xalign=hippo.ALIGNMENT_CENTER,
                                   yalign=hippo.ALIGNMENT_START,
                                   padding_bottom=units.grid_to_pixels(0.5))
        self.append(self._video_box)

        self._entry_box = EntryBox(xalign=hippo.ALIGNMENT_CENTER,
                                   padding_bottom=units.grid_to_pixels(0.5))
        self.append(self._entry_box)

        self._color_box = ColorBox(xalign=hippo.ALIGNMENT_CENTER,
                                   padding_bottom=units.grid_to_pixels(0.5))
        self.append(self._color_box)

        self._ok = iconbutton.IconButton(icon_name="theme:stock-forward",
                                   padding_bottom=units.grid_to_pixels(0.5))
        self._ok.connect('activated', self._ok_activated)
        self.append(self._ok)

    def _ok_activated(self, item):
        pixbuf = self._video_box.get_pixbuf()
        name = self._entry_box.get_text()
        color = self._color_box.get_color()

        if not pixbuf or not name or not color:
            print "not one of pixbuf(%r), name(%r), or color(%r)"
            return

        self.emit('ok', pixbuf, name, color)


class IntroWindow(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self)
        self.set_default_size(gtk.gdk.screen_width(),
                              gtk.gdk.screen_height())
        self.realize()
        self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DESKTOP)

        self._canvas = hippo.Canvas()
        self._intro_box = IntroBox(background_color=0x000000ff,
                                   yalign=hippo.ALIGNMENT_START,
                                   padding_top=units.grid_to_pixels(2),
                                   padding_left=units.grid_to_pixels(3),
                                   padding_right=units.grid_to_pixels(3))
        self._intro_box.connect('ok', self._ok_cb)
        self._canvas.set_root(self._intro_box)
        self.add(self._canvas)
        self._canvas.show_all()

    def _ok_cb(self, widget, pixbuf, name, color):
        self.hide()
        gobject.idle_add(self._create_profile, pixbuf, name, color)

    def _create_profile(self, pixbuf, name, color):
        # Save the buddy icon
        icon_path = os.path.join(env.get_profile_path(), "buddy-icon.jpg")
        scaled = pixbuf.scale_simple(200, 200, gtk.gdk.INTERP_BILINEAR)
        pixbuf.save(icon_path, "jpeg", {"quality":"85"})

        cp = ConfigParser()
        section = 'Buddy'
        if not cp.has_section(section):
            cp.add_section(section)
        cp.set(section, 'NickName', name)
        cp.set(section, 'Color', color.to_string())

        secion = 'Server'
        if not cp.has_section(section):
            cp.add_section(section)
        cp.set(section, 'Server', 'olpc.collabora.co.uk')
        cp.set(section, 'Registered', 'False')

        config_path = os.path.join(env.get_profile_path(), 'config')
        f = open(config_path, 'w')
        cp.write(f)
        f.close()

        # Generate keypair
        import commands
        keypath = os.path.join(env.get_profile_path(), "owner.key")
        cmd = "ssh-keygen -q -t dsa -f %s -C '' -N ''" % keypath
        (s, o) = commands.getstatusoutput(cmd)
        if s != 0:
            logging.error("Could not generate key pair: %d" % s)

        gtk.main_quit()
        return False


if __name__ == "__main__":
    w = IntroWindow()
    w.show_all()
    w.connect('destroy', gtk.main_quit)
    gtk.main()
