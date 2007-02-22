
import dbus.glib
import gobject

from telepathy.client import ConnectionManager, ManagerRegistry, Connection, Channel
from telepathy.interfaces import (
    CONN_MGR_INTERFACE, CONN_INTERFACE, CHANNEL_TYPE_CONTACT_LIST, CHANNEL_INTERFACE_GROUP, CONN_INTERFACE_ALIASING,
    CONN_INTERFACE_AVATARS)
from telepathy.constants import (
    CONNECTION_HANDLE_TYPE_NONE, CONNECTION_HANDLE_TYPE_CONTACT,
    CONNECTION_STATUS_CONNECTED, CONNECTION_STATUS_DISCONNECTED, CONNECTION_STATUS_CONNECTING,
    CONNECTION_HANDLE_TYPE_LIST, CONNECTION_HANDLE_TYPE_CONTACT)

loop = None

import buddy

class TelepathyClient:
    def __init__(self, conn):
        conn[CONN_INTERFACE].connect_to_signal('StatusChanged',
            self._status_changed_cb)
        conn[CONN_INTERFACE].Connect()

        self.conn = conn
        self.buddies = {}

    def _request_list_channel(self, name):
        handle = self.conn[CONN_INTERFACE].RequestHandles(
            CONNECTION_HANDLE_TYPE_LIST, [name])[0]
        chan_path = self.conn[CONN_INTERFACE].RequestChannel(
            CHANNEL_TYPE_CONTACT_LIST, CONNECTION_HANDLE_TYPE_LIST,
            handle, True)
        channel = Channel(self.conn._dbus_object._named_service, chan_path)
        # hack
        channel._valid_interfaces.add(CHANNEL_INTERFACE_GROUP)
        return channel

    def _connected_cb(self):
        # the group of contacts who may receive your presence
        publish = self._request_list_channel('publish')
        publish_handles, local_pending, remote_pending = publish[CHANNEL_INTERFACE_GROUP].GetAllMembers()

        # the group of contacts for whom you wish to receive presence
        subscribe = self._request_list_channel('subscribe')
        subscribe_handles = subscribe[CHANNEL_INTERFACE_GROUP].GetMembers()

        if local_pending:
            # accept pending subscriptions
            #print 'pending: %r' % local_pending
            publish[CHANNEL_INTERFACE_GROUP].AddMembers(local_pending, '')

        not_subscribed = list(set(publish_handles) - set(subscribe_handles))
        self_handle = self.conn[CONN_INTERFACE].GetSelfHandle()

        for handle in not_subscribed:
            # request subscriptions from people subscribed to us if we're not subscribed to them
            subscribe[CHANNEL_INTERFACE_GROUP].AddMembers([self_handle], '')

        # hack
        self.conn._valid_interfaces.add(CONN_INTERFACE_ALIASING)

        #for handle in subscribe_handles:
        #    self.buddies[handle] = buddy.Buddy()

        if CONN_INTERFACE_ALIASING in self.conn:
            aliases = self.conn[CONN_INTERFACE_ALIASING].RequestAliases(subscribe_handles)
        else:
            aliases = self.conn[CONN_INTERFACE].InspectHandles(CONNECTION_HANDLE_TYPE_CONTACT, subscribe_handles)
        print aliases

        #for handle, alias in zip(subscribe_handles, aliases):
        #    print alias
        #    self.buddies[handle].alias = alias

        # hack
        self.conn._valid_interfaces.add(CONN_INTERFACE_AVATARS)

        #if CONN_INTERFACE_AVATARS in self.conn:
        #    #tokens = self.conn[CONN_INTERFACE_AVATARS].RequestAvatarTokens(subscribe_handles)

        #    #for handle, token in zip(subscribe_handles, tokens):
        #    for handle in subscribe_handles:
        #        avatar, mime_type = self.conn[CONN_INTERFACE_AVATARS].RequestAvatar(handle)
        #        self.buddies[handle].avatar = ''.join(map(chr, avatar))

        #        import gtk
        #        window = gtk.Window()
        #        window.set_title(self.buddies[handle].alias)
        #        loader = gtk.gdk.PixbufLoader()
        #        loader.write(self.buddies[handle].avatar)
        #        loader.close()
        #        image = gtk.Image()
        #        image.set_from_pixbuf(loader.get_pixbuf())
        #        window.add(image)
        #        window.show_all()

    def _status_changed_cb(self, state, reason):
        if state == CONNECTION_STATUS_CONNECTING:
            print 'connecting'
        elif state == CONNECTION_STATUS_CONNECTED:
            print 'connected'
            self._connected_cb()
        elif state == CONNECTION_STATUS_DISCONNECTED:
            print 'disconnected'
            loop.quit()

    def disconnect(self):
        self.conn[CONN_INTERFACE].Disconnect()

if __name__ == '__main__':
    import logging
    logging.basicConfig()

    registry = ManagerRegistry()
    registry.LoadManagers()
    mgr = registry.GetManager('gabble')
    protocol = 'jabber'
    account = {
        'account': 'olpc@collabora.co.uk',
        'password': 'learn',
        'server': 'light.bluelinux.co.uk'
    }
    loop = gobject.MainLoop()
    conn_bus_name, conn_object_path = \
        mgr[CONN_MGR_INTERFACE].RequestConnection(protocol, account)
    print conn_bus_name
    print conn_object_path
    conn = Connection(conn_bus_name, conn_object_path)
    client = TelepathyClient(conn)

    try:
        loop.run()
    finally:
        try:
            #conn[CONN_INTERFACE].Disconnect()
            client.disconnect()
        except:
            pass

