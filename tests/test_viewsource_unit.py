import os
import sys
import types
import tempfile


def _make_module(name, attrs=None):
    m = types.ModuleType(name)
    if attrs:
        for k, v in attrs.items():
            setattr(m, k, v)
    sys.modules[name] = m
    return m


def setup_stub_modules():
    # Minimal gi stub
    gi = _make_module('gi', {'require_version': lambda *a, **k: None})
    repo = types.ModuleType('gi.repository')
    sys.modules['gi.repository'] = repo

    # Simple Pango stub
    class FontDescription:
        def __init__(self, s):
            self.s = s

        def load_font(self, ctx=None):
            class Metrics:
                def get_approximate_char_width(self):
                    return 6

            class PF:
                def get_metrics(self):
                    return Metrics()

            return PF()

    Pango = types.ModuleType('Pango')
    Pango.FontDescription = FontDescription
    Pango.PIXELS = lambda x: x
    sys.modules['gi.repository.Pango'] = Pango
    setattr(repo, 'Pango', Pango)

    # dbus stub
    dbus = types.ModuleType('dbus')
    class DBusException(Exception):
        def __init__(self, name=None):
            super().__init__()
            self._name = name

        def get_dbus_name(self):
            return self._name

    dbus.DBusException = DBusException
    sys.modules['dbus'] = dbus

    # Minimal Gtk/Gdk/GObject/GLib/GdkX11/GtkSource/GdkPixbuf/Gio
    class Dummy:
        pass

    Gtk = types.ModuleType('Gtk')
    # Provide bare classes used as bases; they don't need real behavior
    for cls in ('Window', 'VBox', 'HPaned', 'VPaned', 'ScrolledWindow',
                'TreeView', 'Label', 'Image', 'Toolbar', 'SeparatorToolItem',
                'ToolItem', 'CellRendererText', 'TreeViewColumn', 'EventBox'):
        setattr(Gtk, cls, type(cls, (object,), {}))
    # PolicyType/ResponseType placeholders
    Gtk.PolicyType = types.SimpleNamespace(AUTOMATIC=0)
    Gtk.ResponseType = types.SimpleNamespace(OK=1)
    Gtk.WindowPosition = types.SimpleNamespace(CENTER_ALWAYS=0)
    sys.modules['gi.repository.Gtk'] = Gtk
    setattr(repo, 'Gtk', Gtk)

    Gdk = types.ModuleType('Gdk')
    class Screen:
        @staticmethod
        def width():
            return 800

        @staticmethod
        def height():
            return 600

    Gdk.Screen = Screen
    Gdk.CursorType = types.SimpleNamespace(LEFT_PTR=0, WATCH=1)
    Gdk.Cursor = lambda t: t
    def flush():
        return None
    Gdk.flush = flush
    sys.modules['gi.repository.Gdk'] = Gdk
    setattr(repo, 'Gdk', Gdk)

    GdkX11 = types.ModuleType('GdkX11')
    class X11Window:
        @staticmethod
        def foreign_new_for_display(d, xid):
            return object()

    GdkX11.X11Window = X11Window
    sys.modules['gi.repository.GdkX11'] = GdkX11
    setattr(repo, 'GdkX11', GdkX11)

    GLib = types.ModuleType('GLib')
    GLib.idle_add = lambda *a, **k: None
    sys.modules['gi.repository.GLib'] = GLib
    setattr(repo, 'GLib', GLib)

    GObject = types.ModuleType('GObject')
    GObject.SignalFlags = types.SimpleNamespace(RUN_FIRST=0)
    sys.modules['gi.repository.GObject'] = GObject
    setattr(repo, 'GObject', GObject)

    GtkSource = types.ModuleType('GtkSource')
    class Buffer:
        def set_highlight_syntax(self, v):
            pass

        def set_language(self, v):
            pass

        def set_text(self, text):
            pass

    class View:
        def __init__(self, buffer=None):
            pass

        def set_editable(self, v):
            pass

        def set_cursor_visible(self, v):
            pass

        def set_show_line_numbers(self, v):
            pass

        def set_show_right_margin(self, v):
            pass

        def set_right_margin_position(self, v):
            pass

        def modify_font(self, v):
            pass

    GtkSource.Buffer = Buffer
    GtkSource.View = View
    class LanguageManager:
        @staticmethod
        def get_default():
            return types.SimpleNamespace(get_language_ids=lambda: [])

    GtkSource.LanguageManager = LanguageManager
    sys.modules['gi.repository.GtkSource'] = GtkSource
    setattr(repo, 'GtkSource', GtkSource)

    GdkPixbuf = types.ModuleType('GdkPixbuf')
    class Pixbuf:
        @staticmethod
        def new_from_file(p):
            return object()

    GdkPixbuf.Pixbuf = Pixbuf
    sys.modules['gi.repository.GdkPixbuf'] = GdkPixbuf
    setattr(repo, 'GdkPixbuf', GdkPixbuf)

    Gio = types.ModuleType('Gio')
    class Settings:
        def __init__(self, *a, **k):
            pass

        def get_string(self, k):
            return 'red'

    Gio.Settings = Settings
    sys.modules['gi.repository.Gio'] = Gio
    setattr(repo, 'Gio', Gio)

    # sugar3 package stubs
    sugar3 = _make_module('sugar3')
    sugar3.graphics = types.ModuleType('sugar3.graphics')
    style = types.SimpleNamespace(
        FONT_SIZE=12,
        GRID_CELL_SIZE=40,
        LINE_WIDTH=2,
        STANDARD_ICON_SIZE=32,
        COLOR_TRANSPARENT=types.SimpleNamespace(get_svg=lambda: ''),
        COLOR_WHITE=types.SimpleNamespace(get_svg=lambda: ''),
        ELLIPSIZE_MODE_DEFAULT=0,
        DEFAULT_SPACING=6,
    )
    sugar3.graphics.style = style
    # Create module-like objects for submodules expected by imports
    icon_mod = types.ModuleType('sugar3.graphics.icon')
    icon_mod.Icon = object

    xocolor_mod = types.ModuleType('sugar3.graphics.xocolor')
    xocolor_mod.XoColor = lambda c: c

    alert_mod = types.ModuleType('sugar3.graphics.alert')
    alert_mod.Alert = object
    alert_mod.ConfirmationAlert = object
    alert_mod.NotifyAlert = object

    toolbutton_mod = types.ModuleType('sugar3.graphics.toolbutton')
    toolbutton_mod.ToolButton = object

    palettemenu_mod = types.ModuleType('sugar3.graphics.palettemenu')
    palettemenu_mod.PaletteMenuBox = object
    palettemenu_mod.PaletteMenuItem = object

    radiotoolbutton_mod = types.ModuleType('sugar3.graphics.radiotoolbutton')
    radiotoolbutton_mod.RadioToolButton = object

    bundle_mod = types.ModuleType('sugar3.bundle.activitybundle')
    bundle_mod.get_bundle_instance = lambda path: types.SimpleNamespace(
        get_command=lambda: 'sugar-activity', get_icon=lambda: 'icon', get_name=lambda: 'name')

    datastore_mod = types.ModuleType('sugar3.datastore')
    datastore_mod.datastore = types.SimpleNamespace()
    datastore_mod.create = lambda: types.SimpleNamespace(metadata={}, file_path=None, destroy=lambda: None)
    datastore_mod.write = lambda *a, **k: None

    env_mod = types.ModuleType('sugar3.env')
    env_mod.get_user_activities_path = lambda: tempfile.gettempdir()

    mime_mod = types.ModuleType('sugar3.mime')
    mime_mod.get_for_file = lambda p: 'text/plain'
    mime_mod.get_from_file_name = lambda p: 'text/plain'

    profile_mod = types.ModuleType('sugar3.profile')
    profile_mod.get_nick_name = lambda: 'testnick'
    profile_mod.get_pubkey = lambda: 'pubkey'

    activity_mod = types.ModuleType('sugar3.activity')
    bundlebuilder_mod = types.ModuleType('sugar3.activity.bundlebuilder')
    class Config:
        def __init__(self, **kw):
            pass

    def cmd_dist_xo(cfg, arg):
        return None

    bundlebuilder_mod.Config = Config
    bundlebuilder_mod.cmd_dist_xo = cmd_dist_xo


    sys.modules['sugar3'] = sugar3
    sys.modules['sugar3.graphics'] = sugar3.graphics
    sys.modules['sugar3.graphics.style'] = sugar3.graphics.style
    sys.modules['sugar3.graphics.icon'] = icon_mod
    sys.modules['sugar3.graphics.xocolor'] = xocolor_mod
    sys.modules['sugar3.graphics.alert'] = alert_mod
    sys.modules['sugar3.graphics.toolbutton'] = toolbutton_mod
    sys.modules['sugar3.graphics.palettemenu'] = palettemenu_mod
    sys.modules['sugar3.graphics.radiotoolbutton'] = radiotoolbutton_mod
    sys.modules['sugar3.bundle.activitybundle'] = bundle_mod
    sys.modules['sugar3.datastore'] = datastore_mod
    sys.modules['sugar3.env'] = env_mod
    sys.modules['sugar3.mime'] = mime_mod
    sys.modules['sugar3.profile'] = profile_mod
    sys.modules['sugar3.activity'] = activity_mod
    sys.modules['sugar3.activity.bundlebuilder'] = bundlebuilder_mod


def test_is_gtk3_activity_with_setup_py(tmp_path):
    setup_stub_modules()

    # Create a temporary bundle directory with setup.py containing a GTK3 import
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    setup_py = bundle_dir / 'setup.py'
    setup_py.write_text('from gi.repository import Gtk\n')

    sys.path.insert(0, 'src')
    try:
        from jarabe.view import viewsource
        # Use a bundle id that would previously produce a wrong main_filename
        bundle_id = 'org.example.helloworld'
        assert viewsource._is_gtk3_activity(str(bundle_dir), bundle_id) is True
    finally:
        sys.path.pop(0)


def test_is_gtk2_activity_with_pygtk(tmp_path):
    setup_stub_modules()

    bundle_dir = tmp_path / "bundle2"
    bundle_dir.mkdir()
    setup_py = bundle_dir / 'setup.py'
    setup_py.write_text('import pygtk\n')

    sys.path.insert(0, 'src')
    try:
        from jarabe.view import viewsource
        bundle_id = 'org.example.helloworld'
        assert viewsource._is_gtk3_activity(str(bundle_dir), bundle_id) is False
    finally:
        sys.path.pop(0)
