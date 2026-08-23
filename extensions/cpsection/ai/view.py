# Copyright (C) 2026, Sugar Labs (Shubham Sharma)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import json
import logging
import ssl
import threading
import urllib.error
import urllib.request

from gi.repository import GLib
from gi.repository import Gtk
from gettext import gettext as _

from sugar3 import profile
from sugar3.graphics import style
from sugar3.graphics.icon import Icon
from sugar3.graphics.xocolor import XoColor

from jarabe.controlpanel.sectionview import SectionView

_NEUTRAL_COLOR = '#666666,%s' % style.COLOR_WHITE.get_html()


class AI(SectionView):
    def __init__(self, model, alerts):
        SectionView.__init__(self)

        self._model = model
        self.restart_alerts = alerts
        self._write_timeouts = {}
        self._check_generation = 0
        self._initial = {
            'enabled': model.get_enabled(),
            'url': model.get_url(),
            'api_key': model.get_api_key(),
        }

        self.set_border_width(style.DEFAULT_SPACING * 2)
        self.set_spacing(style.DEFAULT_SPACING)
        group = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)

        label_about = Gtk.Label(
            label=_('Jo asks short questions about Journal entries. '
                    'With a server, Jo asks with AI help; without '
                    'one, Jo uses its built-in questions.'))
        label_about.set_alignment(0, 0)
        label_about.set_line_wrap(True)
        self.pack_start(label_about, False, True, 0)
        label_about.show()

        box_server = Gtk.VBox()
        box_server.set_border_width(style.DEFAULT_SPACING * 2)
        box_server.set_spacing(style.DEFAULT_SPACING)

        frame = Gtk.Frame()
        frame.set_halign(Gtk.Align.START)
        box_card = Gtk.HBox(spacing=style.DEFAULT_SPACING * 4)
        box_card.set_border_width(style.DEFAULT_SPACING * 2)

        box_fields = Gtk.VBox(spacing=style.DEFAULT_SPACING)

        box_enabled = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        self._enabled_button = Gtk.CheckButton()
        label_enabled = Gtk.Label(label=_('Use the AI server'))
        label_enabled.set_alignment(0, 0.5)
        box_enabled.pack_start(self._enabled_button, False, True, 0)
        box_enabled.pack_start(label_enabled, False, True, 0)
        self._enabled_button.show()
        label_enabled.show()
        box_fields.pack_start(box_enabled, False, True, 0)
        box_enabled.show()

        css = Gtk.CssProvider()
        css.load_from_data(
            ('entry { caret-color: %s; }'
             % style.COLOR_TOOLBAR_GREY.get_html()).encode())

        box_url = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        label_url = Gtk.Label(label=_('Address'))
        label_url.set_alignment(0, 0.5)
        group.add_widget(label_url)
        self._url_entry = Gtk.Entry()
        self._url_entry.set_width_chars(30)
        self._url_entry.get_style_context().add_provider(
            css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        box_url.pack_start(label_url, False, True, 0)
        box_url.pack_start(self._url_entry, False, True, 0)
        label_url.show()
        self._url_entry.show()
        box_fields.pack_start(box_url, False, True, 0)
        box_url.show()

        box_key = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        label_key = Gtk.Label(label=_('Key'))
        label_key.set_alignment(0, 0.5)
        group.add_widget(label_key)
        self._key_entry = Gtk.Entry()
        self._key_entry.set_width_chars(30)
        self._key_entry.set_visibility(False)
        self._key_entry.get_style_context().add_provider(
            css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self._key_entry.set_icon_from_icon_name(
            Gtk.EntryIconPosition.SECONDARY, 'view-reveal-symbolic')
        self._key_entry.set_icon_tooltip_text(
            Gtk.EntryIconPosition.SECONDARY, _('Show the key'))
        self._key_entry.connect('icon-press', self.__key_icon_press_cb)
        box_key.pack_start(label_key, False, True, 0)
        box_key.pack_start(self._key_entry, False, True, 0)
        label_key.show()
        self._key_entry.show()
        box_fields.pack_start(box_key, False, True, 0)
        box_key.show()

        box_card.pack_start(box_fields, False, True, 0)
        box_fields.show()

        box_status = Gtk.VBox(spacing=style.DEFAULT_SPACING // 2)
        box_status.set_valign(Gtk.Align.CENTER)
        # Fixed width so verdicts of different lengths cannot resize
        # the card.
        box_status.set_size_request(style.GRID_CELL_SIZE * 3, -1)
        self._status_icon = Icon(icon_name='module-ai',
                                 pixel_size=style.STANDARD_ICON_SIZE)
        self._status_title = Gtk.Label()
        self._status_label = Gtk.Label()
        self._status_label.set_line_wrap(True)
        self._status_label.set_max_width_chars(26)
        self._status_label.set_justify(Gtk.Justification.CENTER)
        self._status_label.set_selectable(True)
        box_status.pack_start(self._status_icon, False, True, 0)
        box_status.pack_start(self._status_title, False, True, 0)
        box_status.pack_start(self._status_label, False, True, 0)
        self._status_title.show()
        self._status_label.show()
        box_card.pack_start(box_status, True, True, 0)
        box_status.show()

        frame.add(box_card)
        box_card.show()
        box_server.pack_start(frame, False, True, 0)
        frame.show()

        self._pending_checks = 0
        self._last_spawn = 0
        self.connect('destroy', self.__destroy_cb)
        self._poll_timer = GLib.timeout_add_seconds(10, self.__poll_cb)
        self._oneshot_timer = GLib.timeout_add(500, self.__oneshot_check_cb)

        self.pack_start(box_server, False, True, 0)
        box_server.show()

        self.setup()

    def setup(self):
        self._enabled_button.set_active(self._initial['enabled'])
        self._url_entry.set_text(self._initial['url'])
        self._key_entry.set_text(self._initial['api_key'])

        self.needs_restart = False
        self.props.is_valid = True

        self._enabled_handler = self._enabled_button.connect(
            'toggled', self.__enabled_toggled_cb)
        self._url_handler = self._url_entry.connect(
            'changed', self.__url_changed_cb)
        self._key_handler = self._key_entry.connect(
            'changed', self.__key_changed_cb)

    def undo(self):
        self._enabled_button.disconnect(self._enabled_handler)
        self._url_entry.disconnect(self._url_handler)
        self._key_entry.disconnect(self._key_handler)
        for source_id in self._write_timeouts.values():
            GLib.source_remove(source_id)
        self._write_timeouts.clear()
        self._check_generation += 1
        self._model.set_enabled(self._initial['enabled'])
        self._model.set_url(self._initial['url'])
        self._model.set_api_key(self._initial['api_key'])

    def __destroy_cb(self, widget):
        self._check_generation += 1
        if self._poll_timer is not None:
            GLib.source_remove(self._poll_timer)
            self._poll_timer = None
        if self._oneshot_timer is not None:
            GLib.source_remove(self._oneshot_timer)
            self._oneshot_timer = None

    def __oneshot_check_cb(self):
        self._oneshot_timer = None
        self.__poll_cb()
        return False

    def __poll_cb(self):
        # Skip while a probe is in flight so slow servers cannot stack
        # threads; the age check keeps one wedged probe from
        # silencing the poll for good.
        if self._pending_checks > 0 and \
                GLib.get_monotonic_time() - self._last_spawn < 60000000:
            return True
        url = self._url_entry.get_text().strip()
        if not url:
            self._status_title.set_text('')
            self._status_label.set_text('')
            self._status_icon.hide()
        elif not url.startswith(('http://', 'https://')):
            self._status_title.set_text('')
            self._status_label.set_text(
                _('The address should start with http:// or https://'))
            self._status_icon.hide()
        elif not self._key_entry.get_text().strip():
            # The journal asks for both, so a green light on the
            # address alone would promise a talk it will not have.
            self._show_status(
                _('This server needs a key too. Ask whoever set '
                  'it up for one.'), False)
        else:
            self.__start_check(url, self._check_generation)
        return True

    def __enabled_toggled_cb(self, widget):
        self._model.set_enabled(widget.get_active())

    def __key_icon_press_cb(self, entry, position, event):
        visible = not entry.get_visibility()
        entry.set_visibility(visible)
        entry.set_icon_from_icon_name(
            Gtk.EntryIconPosition.SECONDARY,
            'view-conceal-symbolic' if visible else 'view-reveal-symbolic')
        entry.set_icon_tooltip_text(
            Gtk.EntryIconPosition.SECONDARY,
            _('Hide the key') if visible else _('Show the key'))

    def __url_changed_cb(self, widget):
        self._invalidate_check()
        self._schedule_write('url', widget.get_text())

    def __key_changed_cb(self, widget):
        self._invalidate_check()
        self._schedule_write('api_key', widget.get_text())

    def _invalidate_check(self):
        # A result for the old address or key must not land on the new
        # one; the stale thread's reply is dropped by generation.
        self._check_generation += 1
        self._status_title.set_text('')
        self._status_label.set_text('')
        self._status_icon.hide()
        if self._oneshot_timer is not None:
            GLib.source_remove(self._oneshot_timer)
        self._oneshot_timer = GLib.timeout_add(
            1200, self.__oneshot_check_cb)

    def _schedule_write(self, option, value):
        # Coalesce keystrokes so half-typed values rarely reach the
        # file the journal rail reads live.
        source_id = self._write_timeouts.pop(option, None)
        if source_id is not None:
            GLib.source_remove(source_id)
        self._write_timeouts[option] = GLib.timeout_add(
            600, self.__write_cb, option, value)

    def __write_cb(self, option, value):
        self._write_timeouts.pop(option, None)
        if option == 'url':
            self._model.set_url(value)
        else:
            self._model.set_api_key(value)
        return False

    def __start_check(self, url, generation):
        self._pending_checks += 1
        self._last_spawn = GLib.get_monotonic_time()
        thread = threading.Thread(
            target=self.__check_health,
            args=(url, self._key_entry.get_text().strip(), generation))
        thread.daemon = True
        thread.start()

    def __check_health(self, url, key, generation):
        connected = False
        try:
            request = urllib.request.Request(url.rstrip('/') + '/health')
            if key:
                request.add_header('X-API-Key', key)
            response = urllib.request.urlopen(request, timeout=5)
            payload = json.loads(response.read(65536).decode())
            if not isinstance(payload, dict):
                raise ValueError('unexpected health reply')
        except urllib.error.HTTPError:
            message = _('That address does not look like a Sugar AI server.')
        except urllib.error.URLError as error:
            if isinstance(getattr(error, 'reason', None), ssl.SSLError):
                message = _('Could not make a secure connection '
                            'to the server.')
            else:
                message = _('Could not reach the server. '
                            'Check the address.')
        except (ValueError, UnicodeDecodeError):
            message = _('That address does not look like a Sugar AI server.')
        except Exception:
            logging.exception('ai: unexpected failure probing %r', url)
            message = _('Could not reach the server. Check the address.')
        else:
            if payload.get('status') == 'healthy':
                connected = True
                model = payload.get('model')
                if model:
                    message = _('The server is ready (%s).') % model
                else:
                    message = _('The server is ready.')
            else:
                message = _('The server answered, but its AI is not ready.')
        GLib.idle_add(self.__check_done_cb, message, generation, connected)

    def __check_done_cb(self, message, generation, connected):
        self._pending_checks = max(0, self._pending_checks - 1)
        if generation != self._check_generation:
            return False
        self._show_status(message, connected)
        return False

    def _show_status(self, message, connected):
        if connected:
            self._status_icon.props.xo_color = profile.get_color()
            title = _('Connected')
        else:
            self._status_icon.props.xo_color = XoColor(_NEUTRAL_COLOR)
            title = _('Not connected')
        self._status_icon.show()
        self._status_title.set_markup(
            '<b>%s</b>' % GLib.markup_escape_text(title))
        self._status_label.set_text(message)
