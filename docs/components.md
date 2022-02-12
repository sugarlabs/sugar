# Components of a Software Bill Of Materials (SBOM)

## Primary Components

* maintained by Sugar Labs,

| Component | Description | Repository |
| :-------- | :---------- | :--------- |
| Sugar | Activity Menu, Journal, Network View and Control Panel | https://github.com/sugarlabs/sugar |
| Sugar Toolkit for GTK3 | Activity, Journal, and Plaform library | https://github.com/sugarlabs/sugar-toolkit-gtk3 |
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

<details><summary>source of data</summary>

1. `git grep "#include "`
1. `git grep "import "`
1. `git grep` for fork and exec patterns; os.system, subprocess.Popen, subprocess.call, subprocess.check, os.fork, and os.exec,
1. dependencies of downstream packages of Sugar,

</details>

#### Imports

| Component | Description | Repository |
| :-------- | :---------- | :--------- |
| Cairo | Vector graphics library | https://www.cairographics.org/ |
| D-Bus | Message bus | https://cgit.freedesktop.org/dbus/dbus/ |
| gwebsockets | Python websocket server integrated with GIO and GLib | https://github.com/sugarlabs/gwebsockets |
| Sugar Toolkit for GTK3 | Activity, Journal, and Plaform library | https://github.com/sugarlabs/sugar-toolkit-gtk3 |
| Xapian | Probabilistic search engine library | https://xapian.org/ |
| GIR | Introspection library | https://developer.gnome.org/gobject/stable/ |
| GdkPixbuf | Widget toolkit - pixbuf library | http://www.gtk.org/ |
| GdkX11[^1] | Widget toolkit - X11 library | https://gtk.org/ |
| Gio | Widget toolkit - I/O library | https://gtk.org/ |
| GLib | Widget toolkit - low level library | https://gtk.org/ |
| GObject | Widget toolkit - low level library | https://gtk.org/ |
| GTK | Widget toolkit library | https://gtk.org/ |
| GtkSource | Syntax highlighting widget | https://wiki.gnome.org/Projects/GtkSourceView |
| GUdev | Device information wrapper library | https://www.launchpad.net/gudev-sharp |
| Maliit | Software keyboard library | https://wiki.maliit.org |
| NM | Network manager library | https://www.gnome.org/projects/NetworkManager/ |
| Pango | Text layout and rendering library | https://www.pango.org/ |
| Soup | Asynchronous HTTP library | https://wiki.gnome.org/Projects/libsoup |
| TelepathyGLib | Messaging library | https://telepathy.freedesktop.org/wiki/ |
| UPowerGlib | Power management library | https://upower.freedesktop.org/ |
| WebKit2 | Web content rendering engine | https://webkitgtk.org/ |
| Xkl[^1] | X Keyboard Extension high-level library | https://www.freedesktop.org/wiki/Software/LibXklavier |

[^1]: component is specific to Sugar on Xorg.  Xkl might be avoided by delegating keyboard layout responsibility to distribution installer.

#### Invokes

| Component | Description |
| :-------- | :---------- |
| ping | Network test utility |
| metacity[^2] | Window manager |
| lsb_release | Distribution standards query |
| ethtool | Network interface utility |
| locale | Localisation configuration utility |
| xgettext | Internationalisation database utility |
| xdg-user-dir | Desktop standards query |

[^2]: component is specific to Sugar on Xorg.  A potential replacement for Metacity is Mutter.

### Sugar Toolkit for GTK3

<details><summary>source of data</summary>

1. `git grep "#include "`
1. `git grep "import "`
1. `git grep` for fork and exec patterns; os.system, subprocess.Popen, subprocess.call, subprocess.check, os.fork, and os.exec,
1. dependencies of downstream packages of Sugar,

</details>

#### Imports

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
| Atspi | Assistive technology service provider interface library | https://wiki.gnome.org/Accessibility |
| GdkPixbuf | Widget toolkit - pixbuf library | http://www.gtk.org/ |
| GdkX11[^3] | Widget toolkit - X11 library | https://gtk.org/ |
| Gio | Widget toolkit - I/O library | https://gtk.org/ |
| GLib | Widget toolkit - low level library | https://gtk.org/ |
| GObject | Widget toolkit - low level library | https://gtk.org/ |
| Gst | GStreamer streaming media framework library | https://gstreamer.freedesktop.org |
| GTK | Widget toolkit library | https://gtk.org/ |
| Pango | Text layout and rendering library | https://www.pango.org/ |
| Rsvg | Scalable vector graphics rendering library | https://wiki.gnome.org/Projects/LibRsvg |
| TelepathyGLib | Messaging library | https://telepathy.freedesktop.org/wiki/ |
| WebKit2 | Web content rendering engine | https://webkitgtk.org/ |

[^3]: component is specific to Sugar on Xorg.

#### Includes

| Component | Description | Repository |
| :-------- | :---------- | :--------- |
| libasound[^5] | Audio device library | https://www.alsa-project.org/ |
| Linux[^6] | Linux support headers | http://www.kernel.org/ |
| libc | GNU C Library | https://www.gnu.org/software/libc/libc.html |
| libXi[^4] | X11 Input Extension library | https://gitlab.freedesktop.org/xorg/lib/libXi |
| libICE[^4] | X11 Inter-Client Exchange library | https://gitlab.freedesktop.org/xorg/lib/libICE |
| libSM[^4] | X11 Session Management library | https://gitlab.freedesktop.org/xorg/lib/libSM |
| x11proto[^4] | X Window System Unified Protocol, X11 extension protocols and auxiliary headers | https://gitlab.freedesktop.org/xorg/proto/xorgproto |
| libX11[^4] | Core X11 protocol client library | https://gitlab.freedesktop.org/xorg/lib/libX11 |
| libxtrans[^4] | X Network Transport layer shared code | https://gitlab.freedesktop.org/xorg/lib/libxtrans |

[^4]: component is specific to Sugar on Xorg.  Sugar windowing effects and global keys might be replaced with a compositor.
[^5]: ALSA library dependency is for volume controls, recording and playback via GStreamer, and might be replaced with PipeWire and PulseAudio.
[^6]: Linux support headers dependency is for FAT filesystem support and [may be unused](https://github.com/sugarlabs/sugar-toolkit-gtk3/issues/463).

#### Invokes

| Component | Description |
| :-------- | :---------- |
| msgfmt | Message catalog compiler |
| xgettext | Internationalisation database utility |
| git | Stupid content tracker |

### Sugar Datastore

<details><summary>source of data</summary>

1. `git grep "import "`
1. `git grep` for fork and exec patterns; os.system, subprocess.Popen, subprocess.call, subprocess.check, os.fork, and os.exec,
1. dependencies of downstream packages of Sugar,

</details>

#### Imports

| Component | Description | Repository |
| :-------- | :---------- | :--------- |
| D-Bus | Message bus | https://cgit.freedesktop.org/dbus/dbus/ |
| GIR | Introspection library | https://developer.gnome.org/gobject/stable/ |
| GLib | Widget toolkit - low level library | https://gtk.org/ |
| Sugar Toolkit for GTK3 | Activity, Journal, and Plaform library | https://github.com/sugarlabs/sugar-toolkit-gtk3 |
| Xapian | Probabilistic search engine library | https://xapian.org/ |

#### Invokes

| Component | Description |
| :-------- | :---------- |
| du | File space usage |
| md5sum | Compute MD5 message digest |

### Fructose Activities

<details><summary>source of data</summary>

1. `git grep "import "`
1. `git grep` for fork and exec patterns; os.system, subprocess.Popen, subprocess.call, subprocess.check, os.fork, and os.exec,
1. dependencies of downstream packages of Sugar,

</details>

#### Imports

| Component | Description | Repository |
| :-------- | :---------- | :--------- |
| Abi | AbiWord document editor | http://www.abisource.com/ |
| D-Bus | Message bus | https://cgit.freedesktop.org/dbus/dbus/ |
| Evince | Document viewer | https://wiki.gnome.org/Apps/Evince |
| GIR | Introspection library | https://developer.gnome.org/gobject/stable/ |
| GdkPixbuf | Widget toolkit - pixbuf library | http://www.gtk.org/ |
| GdkX11[^7] | Widget toolkit - X11 library | https://gtk.org/ |
| GLib | Widget toolkit - low level library | https://gtk.org/ |
| GObject | Widget toolkit - low level library | https://gtk.org/ |
| Gst | GStreamer streaming media framework library | https://gstreamer.freedesktop.org |
| GTK | Widget toolkit library | https://gtk.org/ |
| GtkSource | Syntax highlighting widget | https://wiki.gnome.org/Projects/GtkSourceView |
| Pango | Text layout and rendering library | https://www.pango.org/ |
| PyCurl | libcurl bindings | http://pycurl.sourceforge.net |
| Rsvg | Scalable vector graphics rendering library | https://wiki.gnome.org/Projects/LibRsvg |
| Serial | Serial port library | http://pyserial.sourceforge.net/ |
| Soup | Asynchronous HTTP library | https://wiki.gnome.org/Projects/libsoup |
| Sugar | Activity Menu, Journal, Network View and Control Panel | https://github.com/sugarlabs/sugar |
| Sugar Toolkit for GTK3 | Activity, Journal, and Plaform library | https://github.com/sugarlabs/sugar-toolkit-gtk3 |
| TelepathyGLib | Messaging library | https://telepathy.freedesktop.org/wiki/ |
| Vte | Virtual terminal emulator | https://wiki.gnome.org/Apps/Terminal/VTE |
| WebKit2 | Web content rendering engine | https://webkitgtk.org/ |
| XDG | freedesktop.org standards library | http://www.freedesktop.org/wiki/Software/pyxdg |

[^7]: component is specific to Sugar on Xorg.

#### Invokes

| Component | Description |
| :-------- | :---------- |
| clear | Clear terminal screen |
| cp | Copy file |
| csound | Sound synthesis |
| espeak | Voice synthesis |
| evtest | Hardware input event tracing |
| glib-compile-schemas | GSettings schema compiler |
| gunzip | Decompress file |
| rm | Remove file |
| speaker-test | Test audio output channel |

## Secondary Components

* dependencies of primary components, and;
* maintained by Sugar Labs,

<details><summary>source of data</summary>

1. search of https://github.com/sugarlabs repositories,

</details>

| Component | Description | Repository |
| :-------- | :---------- | :--------- |
| gwebsockets | Python websocket server integrated with Gio and GLib | https://github.com/sugarlabs/gwebsockets |
| gst-plugins-espeak | GStreamer espeak plugin | https://github.com/sugarlabs/gst-plugins-espeak |
| sugar-web | Sugar activity components for JavaScript | https://github.com/sugarlabs/sugar-web |

## Dependencies of Secondary Components

* gwebsockets depends on Gio and GLib,
* gst-plugins-espeak depends on GStreamer and eSpeak,

## Embedded Components

* copied into code of other components,
* maintained by Sugar Labs,

<details><summary>source of data</summary>

1. search of https://github.com/sugarlabs repositories,

</details>

| Component | Description | Repository |
| :-------- | :---------- | :--------- |
| collabwrapper | Telepathy wrapper for Sugar activities | https://github.com/sugarlabs/collabwrapper |
| sugargame | Pygame and GTK wrapper for Sugar activities | https://github.com/sugarlabs/sugargame |

## Dependencies of Embedded Components

* collabwrapper depends on Sugar Toolkit for GTK3, D-Bus, Telepathy, and GTK,
* sugargame depends on Sugar Toolkit, Pygame, and GTK,
