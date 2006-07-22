import gtk

from sugar.scene.Actor import Actor

class PixbufActor(Actor):
	def __init__(self, pixbuf):
		Actor.__init__(self)

		self._pixbuf = pixbuf

	def render(self, drawable):
		gc = gtk.gdk.GC(drawable)
		drawable.draw_pixbuf(gc, self._pixbuf, 0, 0, self._x, self._y)
