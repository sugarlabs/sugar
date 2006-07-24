import gtk

from sugar.scene.Actor import Actor

class PixbufActor(Actor):
	def __init__(self, pixbuf):
		Actor.__init__(self)

		self._pixbuf = pixbuf

	def render(self, drawable, transf):
		(x, y) = transf.get_position(self._x, self._y)
		gc = gtk.gdk.GC(drawable)
		drawable.draw_pixbuf(gc, self._pixbuf, 0, 0, x, y)
