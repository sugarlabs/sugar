import gtk
import purk

class IRCGui(gtk.VBox):
    _DEFAULT_SERVER = "irc.freenode.net"
    _AUTO_JOIN_CHANNEL = "#olpc-help"

    def __init__(self):
        gtk.VBox.__init__(self, False)

        connect_button = gtk.Button('Connect to OLPC Help Channel')
        connect_button.connect('clicked', self._on_connect_clicked_cb)

        self._client = purk.Client()
        self._client.add_channel(self._AUTO_JOIN_CHANNEL)
        client_widget = self._client.get_widget()

        self.pack_start(connect_button, False, False, 1)
        self.pack_start(client_widget)
        self.show_all()

    def _on_connect_clicked_cb(self, widget):
        self._client.join_server(self._DEFAULT_SERVER)

class Interface(object):
    def __init__(self):
        self.widget = IRCGui()

