import windows
import widgets
import irc

shortcuts = {
    '^b': '\x02',
    '^u': '\x1F',
    '^r': '\x16',
    '^k': '\x03',
    '^l': '\x04',
    '^o': '\x0F',
    }

def onKeyPress(e):
    if e.key in shortcuts:
        e.window.input.insert(shortcuts[e.key])

    elif e.key == '!c':
        e.window.output.copy()

    elif e.key == 'Page_Up':
        e.window.output.y = e.window.output.y - e.window.output.height / 2
    
    elif e.key == 'Page_Down':
        e.window.output.y = e.window.output.y + e.window.output.height / 2

    elif e.key == '^Home':
        e.window.output.y = 0
    
    elif e.key == '^End':
        e.window.output.y = e.window.output.ymax

    elif e.key in ('^Page_Up', '^Page_Down'):
        winlist = list(windows.manager)
        index = winlist.index(e.window) + ((e.key == '^Page_Down') and 1 or -1)
        if 0 <= index < len(winlist):
            winlist[index].activate()

    elif e.key == '!a':
        winlist = list(windows.manager)
        winlist = winlist[winlist.index(e.window):]+winlist
        w = [w for w in winlist if widgets.HILIT in w.activity]
        
        if not w:
            w = [w for w in winlist if widgets.TEXT in w.activity]
        
        if w:
            windows.manager.set_active(w[0])

    # tabbed browsing
    elif e.key == '^t':
        windows.new(windows.StatusWindow, irc.Network(), 'status').activate()

    elif e.key == '^w':
        windows.manager.get_active().close()
        
    elif e.key == '^f':
        window = windows.manager.get_active()
        
        find = widgets.FindBox(window)
        
        window.pack_start(find, expand=False)
        
        find.textbox.grab_focus()
    
    elif len(e.key) == 2 and e.key.startswith('!') and e.key[1].isdigit():
        n = int(e.key[1])
        if n and n <= len(core.manager):
             list(core.manager)[n-1].activate()
        #else e.key == "!0"
