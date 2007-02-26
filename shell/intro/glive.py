#!/usr/bin/env python
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import gtk
import pygtk
pygtk.require('2.0')
import sys

import pygst
pygst.require('0.10')
import gst
import gst.interfaces

import gobject
gobject.threads_init()

class Glive(gobject.GObject):
    __gsignals__ = {
        'new-picture': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT])),
        'sink': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT]))
    }

    def __init__(self, parent, width, height):
        gobject.GObject.__init__(self)
        self._parent = parent

        #check out the halfpipe, d00d.
        self.pipeline = gst.Pipeline()

        self.v4l2src = gst.element_factory_make("v4l2src", "v4l2src")
        self.t = gst.element_factory_make("tee", "tee")
        self.t_src_pad = self.t.get_request_pad( "src%d" )
        self.vscale = gst.element_factory_make("videoscale", "videoscale")
        self.ximagesink = gst.element_factory_make("ximagesink", "ximagesink")

        self.pipeline.add(self.v4l2src)
        self.pipeline.add(self.t)
        self.pipeline.add(self.vscale)
        self.pipeline.add(self.ximagesink)

        self.v4l2src.link(self.t)

        videoscale_structure = gst.Structure("video/x-raw-rgb")
        videoscale_structure['width'] = width
        videoscale_structure['height'] = height
        videoscale_structure['bpp'] = 16
        videoscale_structure['depth'] = 16
        videoscale_caps = gst.Caps(videoscale_structure)
        self.t_src_pad.link(self.vscale.get_pad("sink"))
        self.vscale.link(self.ximagesink, videoscale_caps)
        #self.vscale.link(self.ximagesink)

        self.queue = gst.element_factory_make("queue", "queue")
        self.queue.set_property("leaky", True)
        self.queue.set_property("max-size-buffers", 1)
        self.qsrc = self.queue.get_pad( "src" )
        self.qsink = self.queue.get_pad("sink")
        self.ffmpeg = gst.element_factory_make("ffmpegcolorspace", "ffmpegcolorspace")
        self.jpgenc = gst.element_factory_make("jpegenc", "jpegenc")
        self.filesink = gst.element_factory_make("fakesink", "fakesink")
        self.filesink.connect( "handoff", self.copyframe )
        self.filesink.set_property("signal-handoffs", True)
        self.pipeline.add(self.queue, self.ffmpeg, self.jpgenc, self.filesink)

        #only link at snapshot time
        #self.t.link(self.queue)
        self.queue.link(self.ffmpeg)
        self.ffmpeg.link(self.jpgenc)
        self.jpgenc.link(self.filesink)
        self.exposureOpen =  False

        self._bus = self.pipeline.get_bus()
        self._CONNECT_SYNC = -1
        self._CONNECT_MSG = -1
        self.doPostBusStuff()

    def copyframe(self, fsink, buffer, pad, user_data=None):
        #for some reason, we get two back to back buffers, even though we
        #ask for only one.
        if (self.exposureOpen):
            self.exposureOpen = False
            piccy = gtk.gdk.pixbuf_loader_new_with_mime_type("image/jpeg")
            piccy.write( buffer )
            piccy.close()
            pixbuf = piccy.get_pixbuf()
            del piccy

            self.t.unlink(self.queue)
            self.queue.set_property("leaky", True)

            gobject.idle_add(self.loadPic, pixbuf)

    def loadPic( self, pixbuf ):
        self.emit('new-picture', pixbuf)

    def takeSnapshot( self ):
        if (self.exposureOpen):
            return
        else:
            self.exposureOpen = True
            self.t.link(self.queue)

    def doPostBusStuff(self):
        self._bus.enable_sync_message_emission()
        self._bus.add_signal_watch()
        self._CONNECT_SYNC = self._bus.connect('sync-message::element', self.on_sync_message)
        self._CONNECT_MSG = self._bus.connect('message', self.on_message)

    def on_sync_message(self, bus, message):
        if message.structure is None:
            return
        if message.structure.get_name() == 'prepare-xwindow-id':
            self.emit('sink', message.src)
            message.src.set_property('force-aspect-ratio', True)

    def on_message(self, bus, message):
        t = message.type
        if (t == gst.MESSAGE_ERROR):
            err, debug = message.parse_error()
            if (self.on_eos):
                self.on_eos()
                self._playing = False
        elif (t == gst.MESSAGE_EOS):
            if (self.on_eos):
                self.on_eos()
                self._playing = False

    def on_eos( self ):
        pass

    def stop(self):
        self.pipeline.set_state(gst.STATE_NULL)

    def play(self):
        self.pipeline.set_state(gst.STATE_PLAYING)

    def pause(self):
        self.pipeline.set_state(gst.STATE_PAUSED)


class LiveVideoSlot(gtk.EventBox):
    __gsignals__ = {
        'pixbuf': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT])),
    }

    def __init__(self, width, height):
        gtk.EventBox.__init__(self)

        self.imagesink = None
        self.unset_flags(gtk.DOUBLE_BUFFERED)
        self.connect('focus-in-event', self.focus_in)
        self.connect('focus-out-event', self.focus_out)
        self.connect("button-press-event", self._button_press_event_cb)

        self.playa = Glive(self, width, height)
        self.playa.connect('new-picture', self._new_picture_cb)
        self.playa.connect('sink', self._new_sink_cb)

    def _new_picture_cb(self, playa, pixbuf):
        self.emit('pixbuf', pixbuf)

    def _new_sink_cb(self, playa, sink):
        if (self.imagesink != None):
            assert self.window.xid
            self.imagesink = None
            del self.imagesink
        self.imagesink = sink
        self.imagesink.set_xwindow_id(self.window.xid)

    def _button_press_event_cb(self, widget, event):
        self.takeSnapshot()

    def focus_in(self, widget, event, args=None):
        self.play()

    def focus_out(self, widget, event, args=None):
        self.stop()

    def play( self ):
        self.playa.play()

    def pause( self ):
        self.playa.pause()

    def stop( self ):
        self.playa.stop()

    def takeSnapshot( self ):
        self.playa.takeSnapshot()
