# Components of a Software Bill Of Materials (SBOM)

## Primary Components

* maintained by Sugar Labs,

| Component | Description | Repository |
| :-------- | :---------- | :--------- |
| Sugar | Activity Menu, Journal, Network View and Control Panel | https://github.com/sugarlabs/sugar |
| Sugar Toolkit | Activity, Journal, and Plaform library | https://github.com/sugarlabs/sugar-toolkit-gtk3 |
| Sugar Datastore | Journal Storage API | https://github.com/sugarlabs/sugar-datastore |
| Sugar Artwork | Icons, Themes and Cursors | https://github.com/sugarlabs/sugar-artwork |
| Browse Activity | Web Browser | https://github.com/sugarlabs/browse-activity |
| Calculate Activity | Calculator | https://github.com/sugarlabs/calculate-activity |
| Chat Activity | Messaging Client | https://github.com/sugarlabs/chat |
| Image Viewer Activity | Image Viewer | https://github.com/sugarlabs/imageviewer-activity |
| Jukebox Activity | Audio and Video Viewer | https://github.com/sugarlabs/jukebox-activity |
| Log Activity | System Log Viewer | https://github.com/sugarlabs/log-activity |
| Pippy Activity | Python Development Environment | https://github.com/sugarlabs/Pippy |
| Read Activity | Document Reader | https://github.com/sugarlabs/read-activity |
| Terminal Activity | Terminal Emulator | https://github.com/sugarlabs/terminal-activity |
| Turtle Art Activity | Block Programming Language | https://github.com/sugarlabs/turtleart-activity |
| Write Activity | Document Editor | https://github.com/sugarlabs/write-activity |

<details><summary>source of data</summary>

1. Sugar, Toolkit, Datastore and Artwork are the core Sugar components,
1. Fructose activities are the core Sugar activites, as listed in http://download.sugarlabs.org/sources/sucrose/fructose/

</details>

## Dependencies of Primary Components

### Sugar

| Component | Description | Repository |
| :-------- | :---------- | :--------- |
| Cairo | Vector graphics library | https://www.cairographics.org/ |
| D-Bus | Message bus | https://cgit.freedesktop.org/dbus/dbus/ |
| gwebsockets | Python websocket server integrated with GIO and GLib | https://github.com/sugarlabs/gwebsockets |
| Sugar Toolkit | Activity, Journal, and Plaform library | https://github.com/sugarlabs/sugar-toolkit-gtk3 |
| Xapian | Probabilistic search engine library | https://xapian.org/ |
| GIR | Introspection library | https://developer.gnome.org/gobject/stable/ |
| GdkPixbuf | Widget toolkit - pixbuf library | http://www.gtk.org/ |
| GdkX11 | Widget toolkit - X11 library | https://gtk.org/ |
| Gio | Widget toolkit - I/O library | https://gtk.org/ |
| GLib | Widget toolkit - low level library | https://gtk.org/ |
| GObject | Widget toolkit - low level library | https://gtk.org/ |
| GTK | Widget toolkit library | https://gtk.org/ |
| GtkSource | Syntax highlighting widget | https://wiki.gnome.org/Projects/GtkSourceView |
| gi.repository.GUdev | |
| gi.repository.Maliit | |
| gi.repository.NM | |
| gi.repository.Pango | |
| gi.repository.Soup | |
| gi.repository.SugarExt | |
| gi.repository.SugarGestures | |
| gi.repository.TelepathyGLib | |
| gi.repository.UPowerGlib | |
| gi.repository.WebKit2 | |
| gi.repository.Xkl | |

### Sugar Toolkit

| Component | Description | Repository |
| :-------- | :---------- | :--------- |
| Cairo | Vector graphics library | https://www.cairographics.org/ |
| D-Bus | Message bus | https://cgit.freedesktop.org/dbus/dbus/ |
| Six | Compatibility library | https://github.com/benjaminp/six |
| IPython | Python command shell (optional) | https://ipython.org/ |
| Sphinx | Documentation generator | https://www.sphinx-doc.org/ |
| dateutil | Date and time calculation library | https://github.com/dateutil/dateutil/ |
| decorator | Signature-preserving function decorator library | https://github.com/micheles/decorator |
| GIR | Introspection library | https://developer.gnome.org/gobject/stable/ |
| gi.repository.Atspi | |
| GdkPixbuf | Widget toolkit - pixbuf library | http://www.gtk.org/ |
| GdkX11 | Widget toolkit - X11 library | https://gtk.org/ |
| Gio | Widget toolkit - I/O library | https://gtk.org/ |
| GLib | Widget toolkit - low level library | https://gtk.org/ |
| GObject | Widget toolkit - low level library | https://gtk.org/ |
| gi.repository.Gst | |
| GTK | Widget toolkit library | https://gtk.org/ |
| gi.repository.Pango | |
| gi.repository.Rsvg | |
| gi.repository.SugarExt | |
| gi.repository.SugarGestures | |
| gi.repository.TelepathyGLib | |
| gi.repository.WebKit2 | |
| :-------- | :---------- | :--------- |
| ALSA library | | https://www.alsa-project.org/ |
| GLib library | | http://www.gtk.org/ |
| Linux support headers | | http://www.kernel.org/ |
| GNU C Library | | https://www.gnu.org/software/libc/libc.html |
| X11 Input Extension library | | https://gitlab.freedesktop.org/xorg/lib/libXi |
| X11 Inter-Client Exchange library | | https://gitlab.freedesktop.org/xorg/lib/libICE |
| X11 Session Management library | | https://gitlab.freedesktop.org/xorg/lib/libSM |
| X Window System Unified Protocol, X11 extension protocols and auxiliary headers | | https://gitlab.freedesktop.org/xorg/proto/xorgproto |
| Core X11 protocol client library | | https://gitlab.freedesktop.org/xorg/lib/libX11 |
| X Network Transport layer shared code | | https://gitlab.freedesktop.org/xorg/lib/libxtrans |

### Sugar Datastore

| Component | Description | Repository |
| :-------- | :---------- | :--------- |
| D-Bus | Message bus | https://cgit.freedesktop.org/dbus/dbus/ |
| GIR | Introspection library | https://developer.gnome.org/gobject/stable/ |
| GLib | Widget toolkit - low level library | https://gtk.org/ |
| Sugar Toolkit | Activity, Journal, and Plaform library | https://github.com/sugarlabs/sugar-toolkit-gtk3 |
| Xapian | Probabilistic search engine library | https://xapian.org/ |

### Sugar Artwork

<details><summary>source of data</summary>

1. `git grep "import "`
1. `git grep "#include "`
1. dependencies of downstream packages of Sugar,

</details>

## Secondary Components

* dependencies of primary components, and;
* maintained by Sugar Labs,

| Component | Description | Repository |
| :-------- | :---------- | :--------- |
| gwebsockets | Python websocket server integrated with GIO and GLib | https://github.com/sugarlabs/gwebsockets |
| gst-plugins-espeak | GStreamer espeak plugin | https://github.com/sugarlabs/gst-plugins-espeak |
| sugar-web | Sugar activity components for JavaScript | https://github.com/sugarlabs/sugar-web |

<details><summary>source of data</summary>

1. search of https://github.com/sugarlabs repositories,

</details>

## Dependencies of Secondary Components

## Embedded Components

* copied into code of other components,
* maintained by Sugar Labs,

| Component | Description | Repository |
| :-------- | :---------- | :--------- |
| collabwrapper | Telepathy wrapper for Sugar activities | https://github.com/sugarlabs/collabwrapper |
| sugargame | Pygame and GTK wrapper for Sugar activities | https://github.com/sugarlabs/sugargame |

<details><summary>source of data</summary>

1. search of https://github.com/sugarlabs repositories,

</details>

