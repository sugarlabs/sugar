import codecs

import gobject
import gtk
import gtk.gdk
import pango

from conf import conf
import parse_mirc
import windows

import servers

# Window activity Constants
HILIT = 'h'
TEXT ='t'
EVENT = 'e'

ACTIVITY_MARKUP = {
    HILIT: "<span style='italic' foreground='#00F'>%s</span>",
    TEXT: "<span foreground='#ca0000'>%s</span>",
    EVENT: "<span foreground='#363'>%s</span>",
    }

# This holds all tags for all windows ever
tag_table = gtk.TextTagTable()

link_tag = gtk.TextTag('link')
link_tag.set_property('underline', pango.UNDERLINE_SINGLE)

indent_tag = gtk.TextTag('indent')
indent_tag.set_property('indent', -20)

tag_table.add(link_tag)
tag_table.add(indent_tag)

#FIXME: MEH hates dictionaries, they remind him of the bad words
styles = {}

def style_me(widget, style):
    widget.set_style(styles.get(style))

def set_style(widget_name, style):
    if style:
        # FIXME: find a better way...
        dummy = gtk.Label()
        dummy.set_style(None)
    
        def apply_style_fg(value):
            dummy.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse(value))

        def apply_style_bg(value):
            dummy.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse(value))

        def apply_style_font(value):
            dummy.modify_font(pango.FontDescription(value))
    
        style_functions = (
            ('fg', apply_style_fg),
            ('bg', apply_style_bg),
            ('font', apply_style_font),
            )

        for name, f in style_functions:
            if name in style:
                f(style[name])

        style = dummy.rc_get_style()
    else:
        style = None
    
    styles[widget_name] = style
    
def menu_from_list(alist):
    while alist and not alist[-1]:
        alist.pop(-1)

    last = None
    for item in alist:
        if item != last:
            if item:
                if len(item) == 2:
                    name, function = item
                    
                    menuitem = gtk.ImageMenuItem(name)
                    
                elif len(item) == 3:
                    name, stock_id, function = item
                    
                    if isinstance(stock_id, bool):
                        menuitem = gtk.CheckMenuItem(name)
                        menuitem.set_active(stock_id)
                    else:
                        menuitem = gtk.ImageMenuItem(stock_id)
                    
                if isinstance(function, list):
                    submenu = gtk.Menu()
                    for subitem in menu_from_list(function):
                        submenu.append(subitem)
                    menuitem.set_submenu(submenu)

                else:
                    menuitem.connect("activate", lambda a, f: f(), function)

                yield menuitem

            else:
                yield gtk.SeparatorMenuItem()
                
        last = item

class Nicklist(gtk.TreeView):
    def click(self, event):
        if event.button == 3:
            x, y = event.get_coords()
    
            (data,), path, x, y = self.get_path_at_pos(int(x), int(y))
        
            c_data = self.events.data(window=self.win, data=self[data], menu=[])
        
            self.events.trigger("ListRightClick", c_data)
            
            if c_data.menu:
                menu = gtk.Menu()
                for item in menu_from_list(c_data.menu):
                    menu.append(item)
                menu.show_all()
                menu.popup(None, None, None, event.button, event.time)
        
        elif event.button == 1 and event.type == gtk.gdk._2BUTTON_PRESS:
            x, y = event.get_coords()
    
            (data,), path, x, y = self.get_path_at_pos(int(x), int(y))
        
            self.events.trigger("ListDoubleClick", window=self.win, target=self[data])
        
    def __getitem__(self, pos):
        return self.get_model()[pos][0]
        
    def __setitem__(self, pos, name_markup):
        realname, markedupname, sortkey = name_markup
    
        self.get_model()[pos] = realname, markedupname, sortkey

    def __len__(self):
        return len(self.get_model())
    
    def index(self, item):
        for i, x in enumerate(self):
            if x == item:
                return i
                
        return -1
        
    def append(self, realname, markedupname, sortkey):
        self.get_model().append((realname, markedupname, sortkey))
 
    def insert(self, pos, realname, markedupname, sortkey):
        self.get_model().insert(pos, (realname, markedupname, sortkey))
        
    def replace(self, names):
        self.set_model(gtk.ListStore(str, str, str))
        
        self.insert_column_with_attributes(
            0, '', gtk.CellRendererText(), markup=1
            ).set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)

        for name in names:
            self.append(*name)
        
        self.get_model().set_sort_column_id(2, gtk.SORT_ASCENDING)

    def remove(self, realname):
        index = self.index(realname)
        
        if index == -1:
            raise ValueError

        self.get_model().remove(self.get_model().iter_nth_child(None, index))
    
    def clear(self):
        self.get_model().clear()
        
    def __iter__(self):
        return (r[0] for r in self.get_model())

    def __init__(self, window, core):
        self.win = window
        self.core = core
        self.events = core.events

        gtk.TreeView.__init__(self)
        
        self.replace(())

        self.set_headers_visible(False)
        self.set_property("fixed-height-mode", True)
        self.connect("button-press-event", Nicklist.click)
        self.connect_after("button-release-event", lambda *a: True)
        
        style_me(self, "nicklist")

# Label used to display/edit your current nick on a network
class NickEditor(gtk.EventBox):
    def nick_change(self, entry):
        oldnick, newnick = self.label.get_text(), entry.get_text()
        
        if newnick and newnick != oldnick:
            self.events.run('nick %s' % newnick, self.win, self.win.network)

        self.win.input.grab_focus()

    def update(self, nick=None):
        self.label.set_text(nick or self.win.network.me)
    
    def to_edit_mode(self, widget, event):
        if self.label not in self.get_children():
            return

        if getattr(event, 'button', None) == 3:
            c_data = self.events.data(window=self.win, menu=[])
            self.events.trigger("NickEditMenu", c_data)

            if c_data.menu:
                menu = gtk.Menu()
                for item in menu_from_list(c_data.menu):
                    menu.append(item)
                menu.show_all()
                menu.popup(None, None, None, event.button, event.time)
        
        else:
            entry = gtk.Entry()
            entry.set_text(self.label.get_text())
            entry.connect('activate', self.nick_change)
            entry.connect('focus-out-event', self.to_show_mode)

            self.remove(self.label)
            self.add(entry)
            self.window.set_cursor(None)
                
            entry.show()
            entry.grab_focus()
    
    def to_show_mode(self, widget, event):
        self.remove(widget)
        self.add(self.label)
        self.win.input.grab_focus()
        self.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.XTERM))

    def __init__(self, window, core):
        gtk.EventBox.__init__(self)
        self.events = core.events
        self.win = window

        self.label = gtk.Label()
        self.label.set_padding(5, 0)
        self.add(self.label)

        self.connect("button-press-event", self.to_edit_mode)
        
        self.update()

        self.connect(
            "realize", 
            lambda *a: self.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.XTERM))
            )

# The entry which you type in to send messages        
class TextInput(gtk.Entry):
    # Generates an input event
    def entered_text(self, ctrl):
        #for a in globals():
        #    print a
        #print events.__file__
        #self.core.run_command(self.text)
        for line in self.text.splitlines():
            if line:
                e_data = self.events.data(
                            window=self.win, network=self.win.network,
                            text=line, ctrl=ctrl
                            )
                self.events.trigger('Input', e_data)
                if not e_data.done:
                    self.events.run(line, self.win, self.win.network)

        self.text = ''
    
    def _set_selection(self, s):
        if s:
            self.select_region(*s)
        else:
            self.select_region(self.cursor, self.cursor)

    #some nice toys for the scriptors
    text = property(gtk.Entry.get_text, gtk.Entry.set_text)
    cursor = property(gtk.Entry.get_position, gtk.Entry.set_position)
    selection = property(gtk.Entry.get_selection_bounds, _set_selection)
    
    def insert(self, text):
        self.do_insert_at_cursor(self, text)
    
    #hack to stop it selecting the text when we focus
    def do_grab_focus(self):
        temp = self.text, (self.selection or (self.cursor,)*2)
        self.text = ''
        gtk.Entry.do_grab_focus(self)
        self.text, self.selection = temp

    def keypress(self, event):
        keychar = (
            (gtk.gdk.CONTROL_MASK, '^'),
            (gtk.gdk.SHIFT_MASK, '+'),
            (gtk.gdk.MOD1_MASK, '!')
            )

        key = ''
        for keymod, char in keychar:
            # we make this an int, because otherwise it leaks
            if int(event.state) & keymod:
                key += char
        key += gtk.gdk.keyval_name(event.keyval)

        self.events.trigger('KeyPress', key=key, string=event.string, window=self.win)

        if key == "^Return":
            self.entered_text(True)
        
        up = gtk.gdk.keyval_from_name("Up")
        down = gtk.gdk.keyval_from_name("Down")
        tab = gtk.gdk.keyval_from_name("Tab")

        return event.keyval in (up, down, tab)
    
    def __init__(self, window, core):
        gtk.Entry.__init__(self)
        self.events = core.events
        self.core = core
        self.win = window

        # we don't want key events to propogate so we stop them in connect_after
        self.connect('key-press-event', TextInput.keypress)
        self.connect_after('key-press-event', lambda *a: True)
        
        self.connect('activate', TextInput.entered_text, False)

gobject.type_register(TextInput)

def prop_to_gtk(textview, (prop, val)):
    if val == parse_mirc.BOLD:
        val = pango.WEIGHT_BOLD

    elif val == parse_mirc.UNDERLINE:
        val = pango.UNDERLINE_SINGLE
        
    return {prop: val}
        
def word_from_pos(text, pos):
    if text[pos] == ' ':
        return ' ', pos, pos+1

    else:
        fr = text[:pos].split(" ")[-1]
        to = text[pos:].split(" ")[0]

        return fr + to, pos - len(fr), pos + len(to)
 
def get_iter_at_coords(view, x, y):
    return view.get_iter_at_location(
        *view.window_to_buffer_coords(gtk.TEXT_WINDOW_TEXT, int(x), int(y))
        )

def get_event_at_iter(view, iter, core):
    buffer = view.get_buffer()
        
    line_strt = buffer.get_iter_at_line(iter.get_line())
    line_end = line_strt.copy()
    line_end.forward_lines(1)
    
    pos = iter.get_line_offset()
    
    #Caveat: text must be a unicode string, not utf-8 encoded; otherwise our
    # offsets will be off when we use anything outside 7-bit ascii
    #gtk.TextIter.get_text returns unicode but gtk.TextBuffer.get_text does not
    text = line_strt.get_text(line_end).rstrip("\n")
    
    word, fr, to = word_from_pos(text, pos)
    
    return core.events.data(
                window=view.win, pos=pos, text=text,
                target=word, target_fr=fr, target_to=to,
                )

class TextOutput(gtk.TextView):
    def copy(self):
        startend = self.get_buffer().get_selection_bounds()

        tagsandtext = []
        if startend:
            start, end = startend
            
            while not start.equal(end):
                tags_at_iter = {}
                for tag in start.get_tags():        
                    try:
                        tagname, tagval = eval(tag.get_property('name'))
                        tags_at_iter[tagname] = tagval
                    except NameError:
                        continue

                tagsandtext.append((dict(tags_at_iter), start.get_char()))
                start.forward_char()

        text = parse_mirc.unparse_mirc(tagsandtext)
        
        gtk.clipboard_get(gtk.gdk.SELECTION_CLIPBOARD).set_text(text)
        gtk.clipboard_get(gtk.gdk.SELECTION_PRIMARY).set_text(text)

        return text

    def clear(self):
        self.get_buffer().set_text('')
    
    def get_y(self):
        rect = self.get_visible_rect()
        return rect.y
    
    def set_y(self,y):
        iter = self.get_iter_at_location(0, y)
        if self.get_iter_location(iter).y < y:
            self.forward_display_line(iter)
        yalign = float(self.get_iter_location(iter).y-y)/self.height
        self.scroll_to_iter(iter, 0, True, 0, yalign)
        
        self.check_autoscroll()
    
    def get_ymax(self):
        buffer = self.get_buffer()
        return sum(self.get_line_yrange(buffer.get_end_iter())) - self.height
    
    def get_height(self):
        return self.get_visible_rect().height
    
    y = property(get_y, set_y)
    ymax = property(get_ymax)
    height = property(get_height)
    
    # the unknowing print weird things to our text widget function
    def write(self, text, line_ending='\n', fg=None):
        if not isinstance(text, unicode):
            try:
                text = codecs.utf_8_decode(text)[0]
            except:
                text = codecs.latin_1_decode(text)[0]
        tags, text = parse_mirc.parse_mirc(text)

        if fg:
            tags.append({'data': ("foreground", isinstance(fg, basestring) and ('#%s'%fg) or parse_mirc.get_mirc_color(fg)), 'from': 0, 'to': len(text)})

        buffer = self.get_buffer()
        
        cc = buffer.get_char_count()

        buffer.insert_with_tags_by_name(
            buffer.get_end_iter(),
            text + line_ending,
            'indent'
            )

        for tag in tags:
            tag_name = str(tag['data'])
   
            if not tag_table.lookup(tag_name):
                buffer.create_tag(tag_name, **prop_to_gtk(self, tag['data']))

            buffer.apply_tag_by_name(
                tag_name, 
                buffer.get_iter_at_offset(tag['from'] + cc),
                buffer.get_iter_at_offset(tag['to'] + cc)
                )
    
    def popup(self, menu):    
        hover_iter = get_iter_at_coords(self, *self.hover_coords)
       
        menuitems = []
        if not hover_iter.ends_line():
            c_data = get_event_at_iter(self, hover_iter)
            c_data.menu = []
            
            self.events.trigger("RightClick", c_data)
            
            menuitems = c_data.menu
            
        if not menuitems:
            c_data = self.events.data(menu=[])
            self.events.trigger("MainMenu", c_data)
            
            menuitems = c_data.menu

        for child in menu.get_children():
            menu.remove(child)
        
        for item in menu_from_list(menuitems):
            menu.append(item)
            
        menu.show_all()
    
    def mousedown(self, event):
        if event.button == 3:
            self.hover_coords = event.get_coords()
    
    def mouseup(self, event):
        if not self.get_buffer().get_selection_bounds():
            if event.button == 1:
                hover_iter = get_iter_at_coords(self, event.x, event.y)
            
                if not hover_iter.ends_line():
                    c_data = get_event_at_iter(self, hover_iter, self.core)

                    self.events.trigger("Click", c_data)
                
            if self.is_focus():
                self.win.focus()

    def clear_hover(self, _event=None):
        buffer = self.get_buffer()
    
        for fr, to in self.linking:
            buffer.remove_tag_by_name(
                "link", 
                buffer.get_iter_at_mark(fr), 
                buffer.get_iter_at_mark(to)
                )
        
        self.linking = set()
        self.get_window(gtk.TEXT_WINDOW_TEXT).set_cursor(None)

    def hover(self, event):
        if self.linking:
            self.clear_hover()

        hover_iter = get_iter_at_coords(self, event.x, event.y)

        if not hover_iter.ends_line():        
            h_data = get_event_at_iter(self, hover_iter, self.core)
            h_data.tolink = set()

            self.events.trigger("Hover", h_data)
            
            if h_data.tolink:
                buffer = self.get_buffer()
            
                offset = buffer.get_iter_at_line(
                            hover_iter.get_line()
                            ).get_offset()
                                  
                for fr, to in h_data.tolink:
                    fr = buffer.get_iter_at_offset(offset + fr)
                    to = buffer.get_iter_at_offset(offset + to)
                    
                    buffer.apply_tag_by_name("link", fr, to)
                    
                    self.linking.add(
                        (buffer.create_mark(None, fr), 
                            buffer.create_mark(None, to))
                        )
                        
                    self.get_window(
                        gtk.TEXT_WINDOW_TEXT
                        ).set_cursor(gtk.gdk.Cursor(gtk.gdk.HAND2))
        
        self.get_pointer()

    def scroll(self, _allocation=None):
        if self.autoscroll:
            def do_scroll():
                self.scroller.value = self.scroller.upper - self.scroller.page_size
                self._scrolling = False
            
            if not self._scrolling:
                self._scrolling = gobject.idle_add(do_scroll)
    
    def check_autoscroll(self, *args):
        def set_to_scroll():
            self.autoscroll = self.scroller.value + self.scroller.page_size >= self.scroller.upper
            
        gobject.idle_add(set_to_scroll)

    def __init__(self, core, window, buffer=None):
        if not buffer:
            buffer = gtk.TextBuffer(tag_table)
        
        gtk.TextView.__init__(self, buffer)
        self.core = core
        self.events = core.events
        self.win = window
        
        self.set_size_request(0, -1)
        
        self.set_wrap_mode(gtk.WRAP_WORD_CHAR)
        self.set_editable(False)
        self.set_cursor_visible(False)

        self.set_property("left-margin", 3)
        self.set_property("right-margin", 3)

        self.linking = set()

        self.add_events(gtk.gdk.POINTER_MOTION_HINT_MASK)
        self.add_events(gtk.gdk.LEAVE_NOTIFY_MASK)

        self.connect('populate-popup', TextOutput.popup)
        self.connect('motion-notify-event', TextOutput.hover)
        self.connect('button-press-event', TextOutput.mousedown)
        self.connect('button-release-event', TextOutput.mouseup)
        self.connect_after('button-release-event', lambda *a: True)
        self.connect('leave-notify-event', TextOutput.clear_hover)
          
        self.hover_coords = 0, 0

        self.autoscroll = True
        self._scrolling = False
        self.scroller = gtk.Adjustment()

        def setup_scroll(self, _adj, vadj):
            self.scroller = vadj

            if vadj:
                def set_scroll(adj):
                    self.autoscroll = adj.value + adj.page_size >= adj.upper
    
                vadj.connect("value-changed", set_scroll)

        self.connect("set-scroll-adjustments", setup_scroll)
        self.connect("size-allocate", TextOutput.scroll)

        def set_cursor(widget):
            self.get_window(gtk.TEXT_WINDOW_TEXT).set_cursor(None)      

        self.connect("realize", set_cursor)
        
        style_me(self, "view")

class WindowLabel(gtk.EventBox):
    def update(self):
        title = self.win.get_title()
        
        for escapes in (('&','&amp;'), ('<','&lt;'), ('>','&gt;')):
            title = title.replace(*escapes)

        for a_type in (HILIT, TEXT, EVENT):
            if a_type in self.win.activity:
                title = ACTIVITY_MARKUP[a_type] % title
                break
            
        self.label.set_markup(title)

    def tab_popup(self, event):
        if event.button == 3: # right click
            c_data = self.events.data(window=self.win, menu=[])
            self.events.trigger("WindowMenu", c_data)

            c_data.menu += [
                None,
                ("Close", gtk.STOCK_CLOSE, self.win.close),
                ]

            menu = gtk.Menu()
            for item in menu_from_list(c_data.menu):
                menu.append(item)
            menu.show_all()
            menu.popup(None, None, None, event.button, event.time)

    def __init__(self, window, core):
        gtk.EventBox.__init__(self)
        self.core = core
        self.events = core.events

        self.win = window
        self.connect("button-press-event", WindowLabel.tab_popup)
        
        self.label = gtk.Label()        
        self.add(self.label)

        self.update()
        self.show_all()
        
class FindBox(gtk.HBox):
    def remove(self, *args):
        self.parent.remove(self)
        self.win.focus()

    def clicked(self, button, search_down=False):
        text = self.textbox.get_text()
        
        if not text:
            return
        
        buffer = self.win.output.get_buffer()
        
        if buffer.get_selection_bounds():
            if button == self.down:
                _, cursor_iter = buffer.get_selection_bounds()
            else:
                cursor_iter, _ = buffer.get_selection_bounds()
        else:
           cursor_iter = buffer.get_end_iter()
    
        if search_down:
            cursor = cursor_iter.forward_search(
                text, gtk.TEXT_SEARCH_VISIBLE_ONLY
                )
        else:
            cursor = cursor_iter.backward_search(
                text, gtk.TEXT_SEARCH_VISIBLE_ONLY
                )
        
        if not cursor:
            return
        
        fr, to = cursor
        
        if button == self.up:
            buffer.place_cursor(fr)
            self.win.output.scroll_to_iter(fr, 0)
        elif button == self.down:
            buffer.place_cursor(to)
            self.win.output.scroll_to_iter(to, 0)
            
        buffer.select_range(*cursor)
        
        cursor_iter = buffer.get_iter_at_mark(buffer.get_insert())

    def __init__(self, window):
        gtk.HBox.__init__(self)
        
        self.win = window

        self.up = gtk.Button(stock='gtk-go-up')
        self.down = gtk.Button(stock='gtk-go-down')
        
        self.up.connect('clicked', self.clicked)
        self.down.connect('clicked', self.clicked, True)
        
        self.up.set_property('can_focus', False)
        self.down.set_property('can_focus', False)
        
        self.textbox = gtk.Entry()
        
        self.textbox.connect('focus-out-event', self.remove)
        self.textbox.connect('activate', self.clicked)
                
        self.pack_start(gtk.Label('Find:'), expand=False)
        self.pack_start(self.textbox)

        self.pack_start(self.up, expand=False)
        self.pack_start(self.down, expand=False)

        self.show_all()

#class UrkUITabs(gtk.Window):
class UrkUITabs(object):
    def __init__(self, core):
        # threading stuff
        gtk.gdk.threads_init()
        self.core = core
        self.events = core.events
        self.tabs = gtk.Notebook()
        self.tabs.set_property(
            "tab-pos", 
            conf.get("ui-gtk/tab-pos", gtk.POS_BOTTOM)
            )

        self.tabs.set_scrollable(True)
        self.tabs.set_property("can-focus", False)

        self.box = gtk.VBox(False)
        self.box.pack_end(self.tabs)

    def __iter__(self):
        return iter(self.tabs.get_children())

    def __len__(self):
        return self.tabs.get_n_pages()
    
    def exit(self, *args):
        self.events.trigger("Exit")
        gtk.main_level() and gtk.main_quit()
        
    def get_active(self):
        return self.tabs.get_nth_page(self.tabs.get_current_page())

    def set_active(self, window):
        self.tabs.set_current_page(self.tabs.page_num(window))

    def add(self, window):
        for pos in reversed(range(self.tabs.get_n_pages())):
            if self.tabs.get_nth_page(pos).network == window.network:
                break
        else:
            pos = self.tabs.get_n_pages() - 1
 
        self.tabs.insert_page(window, WindowLabel(window, self.core), pos+1)   

    def remove(self, window):
        self.tabs.remove_page(self.tabs.page_num(window))

    def update(self, window):
        self.tabs.get_tab_label(window).update()

    def show_all(self):
        self.box.show_all()
