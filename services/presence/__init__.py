"""Service to track buddies and activities on the network

Model objects:

    activity.Activity -- tracks a (shared/shareable) activity
        with many properties and observable events
    
    buddy.Buddy -- tracks a reference to a particular actor
        on the network
        
        buddy.GenericOwner -- actor who owns a particular 
            activity on the network 
        
        buddy.ShellOwner -- actor who owns the local machine
            connects to the owner module (on the server)
    
Controller objects:

    presenceservice.PresenceService -- controller which connects 
        a networking plugin to a DBUS service.  Generates events 
        for networking events, forwards updates/requests to the 
        server plugin.
    
    server_plugin.ServerPlugin -- implementation of networking 
        plugin using telepathy Python (Jabber) to provide the 
        underlying communications layer.  Generates GObject 
        events that the PresenceService observes to forward onto 
        the DBUS clients.

Utility machinery:

    buddyiconcache.BuddyIconCache -- caches buddy icons on disk
        based on the "jid" XXX Jabber ID? of the buddy.
    
    psutils -- trivial function to decode int-list to characters
"""
