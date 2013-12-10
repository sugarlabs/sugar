#By SAMdroid
from gi.repository import Gtk

from jarabe.journal.listmodel import ListModel
from jarabe.journal.palettes import ObjectPalette, BuddyPalette
from jarabe.journal import model

ENTRY_SIZE = 320

class ThumbView():
    def __init__(self, win)
        self._grid = Gtk.Grid()
        self._width, h = win.get_size()
        
        self._place_x, self._place_y = 0, 0
        
        self._query = {}
        self._model = ListModel(self._query)
        self._model.connect('ready', self.__model_ready_cb)
        self._model.setup()
        
     def __model_ready_cb(self, tree_model):
         do_continue, iter = self._model.get_iter_first()
         row = self._model[Gtk.TreePath.new_first()]
         l = []
         l.append( Gtk.Label(str(row)) )
         l.append( Gtk.Label(str(iter)) )
         l.append( Gtk.Label(str(self._model)) )
         l.append( Gtk.Label(str(iter.user_data)) )
         for i in l:
             self._grid.add(i)
             i.append()
     
     def _next_pos(self):
         if (self._place_x + 1)*ENTRY_SIZE > self._width:
             self._place_x = 0
             self._palce_y+= 1
         else:
             self._palce_x+= 1
     
     def _add_row(self, title, pixbuf, date=None):
         box = Gtk.Box(Gtk.Orentation.Vertical, 5)
         img = Gtk.Image.new_from_pixbuf(pixbuf)
         box.pack_start(img)
         img.show()
         
         label = Gtk.Label(title)
         box.pack_end(label)
         label.show()
         
         self._grid.attach(box, self._palce_x, self._place_y, 1, 1)
         self._next_pos()
        
