import gobject
import gtk
import gettext

_ = lambda msg: gettext.dgettext('sugar', msg)

class SectionView(gtk.VBox):
    __gsignals__ = {
        'valid-section': (gobject.SIGNAL_RUN_FIRST,
                          gobject.TYPE_NONE,
                          ([bool]))
    }
    def __init__(self):
        gtk.VBox.__init__(self)
        self.restart = False
        self.restart_alerts = []
        self._restart_msg = _('Changes require a sugar restart to take effect.')

    def undo(self):
        '''Undo here the changes that have been made in this section.'''
        pass
