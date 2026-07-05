# Copyright (C) 2008 One Laptop Per Child
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
import difflib
import logging
import math
import os
import re
import shutil
import glob
import subprocess
import threading
import time
from gettext import gettext as _

import cairo

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Pango

from sugar3.graphics import style
from sugar3.graphics.icon import Icon

from jarabe.desktop.favoritesview import FavoritesBox
from jarabe.desktop.activitieslist import ActivitiesList
from jarabe.util.normalize import normalize_string
from jarabe.model import desktop


class HomeBox(Gtk.VBox):
    __gtype_name__ = 'SugarHomeBox'

    def __init__(self, toolbar):
        logging.debug('STARTUP: Loading the home view')

        Gtk.VBox.__init__(self)
        self._toolbar = toolbar

        self._favorites_views_indicies = []
        for i in range(desktop.get_number_of_views()):
            self._favorites_views_indicies.append(i)
        self._list_view_index = self._favorites_views_indicies[-1] + 1

        self._favorites_boxes = []
        for i in range(desktop.get_number_of_views()):
            self._favorites_boxes.append(FavoritesBox(i))
        self._list_view = ActivitiesList()

        self._desktop_model = desktop.get_model()
        self._desktop_model.connect('desktop-view-icons-changed',
                                    self.__desktop_view_icons_changed_cb)

        toolbar.search_entry._icon_selected = []
        toolbar.connect('query-changed', self.__toolbar_query_changed_cb)
        toolbar.connect('view-changed', self.__toolbar_view_changed_cb)
        toolbar.connect('create-ai-activity',
                        self.__toolbar_create_ai_activity_cb)
        toolbar.search_entry.connect('key-press-event',
                                     self.__search_entry_key_press_event_cb)
        toolbar.search_entry.connect('icon-press',
                                     self.__clear_icon_pressed_cb)
        self._list_view.connect('clear-clicked',
                                self.__activitylist_clear_clicked_cb, toolbar)

        self._active_view = self._favorites_views_indicies[0]
        self._set_view(self._active_view)

        self._create_ai_panel = _CreateAIActivityPanel()
        self._create_ai_panel.connect('close-requested',
                                      self.__create_ai_panel_close_cb)
        self.pack_start(self._create_ai_panel, True, True, 0)
        self._create_ai_panel.hide()

        self._query = ''
        self._resume_mode = Gio.Settings.new(
            'org.sugarlabs.user').get_boolean('resume-activity')

    def __desktop_view_icons_changed_cb(self, model):
        number_of_views = desktop.get_number_of_views()

        if len(self._favorites_views_indicies) < number_of_views:
            for i in range(number_of_views -
                           len(self._favorites_views_indicies)):
                self._favorites_views_indicies.append(
                    len(self._favorites_views_indicies) + i)
                self._favorites_boxes.append(
                    FavoritesBox(len(self._favorites_views_indicies) - 1))
        elif number_of_views < len(self._favorites_views_indicies):
            for i in range(len(self._favorites_views_indicies) -
                           number_of_views):
                self._favorites_boxes.remove(self._favorites_boxes[-1])
                self._favorites_views_indicies.remove(
                    self._favorites_views_indicies[-1])

        self._list_view_index = number_of_views
        logging.debug('homebox: reassigning list view index to %d' %
                      (self._list_view_index))

    def __toolbar_query_changed_cb(self, toolbar, query):
        self._query = normalize_string(query)
        self._list_view.set_filter(self._query)
        for i in range(desktop.get_number_of_views()):
            self._favorites_boxes[i].set_filter(self._query)
        toolbar.search_entry._icon_selected = \
            self._list_view.get_activities_selected()

        # verify if one off the selected names is a perfect match
        # this is needed by th case of activities with names contained
        # in other activities like 'Paint' and 'MusicPainter'
        for activity in self._list_view.get_activities_selected():
            if activity['name'].upper() == query.upper():
                toolbar.search_entry._icon_selected = [activity]
                break

        # Don't change the selection if the entry has been autocompleted
        if len(toolbar.search_entry._icon_selected) == 1 \
           and not toolbar.search_entry.get_text() == activity['name']:
            pos = toolbar.search_entry.get_position()
            toolbar.search_entry.set_text(
                toolbar.search_entry._icon_selected[0]['name'])
            toolbar.search_entry.select_region(pos, -1)

    def __toolbar_view_changed_cb(self, toolbar, view):
        self._set_view(view)

    def __toolbar_create_ai_activity_cb(self, toolbar):
        self._show_create_ai_panel()

    def __search_entry_key_press_event_cb(self, entry, event):
        if self.is_create_ai_panel_visible():
            GObject.idle_add(
                self.__redirect_search_text_to_create_ai_prompt, entry)
            return False

        # wherever a single item is selected in a desktop view,
        # launch the activity on pressing return
        if event.keyval == Gdk.KEY_Return and len(entry._icon_selected) == 1:
            self._list_view.run_activity(entry._icon_selected[0]['bundle_id'],
                                         self._resume_mode)
            entry._icon_selected = []
            self.set_resume_mode(self._resume_mode)

    def __activitylist_clear_clicked_cb(self, widget, toolbar):
        toolbar.clear_query()

    def __clear_icon_pressed_cb(self, entry, icon_pos, event):
        self.grab_focus()

    def grab_focus(self):
        if self._create_ai_panel.get_visible():
            self._create_ai_panel.grab_focus()
            return

        # overwrite grab focus to be able to grab focus on the
        # views which are packed inside a box
        children = self.get_children()
        if self._list_view in children:
            self._list_view.grab_focus()
        else:
            for i in range(desktop.get_number_of_views()):
                if self._favorites_boxes[i] in children:
                    self._favorites_boxes[i].grab_focus()

    def _set_view(self, view):
        self._active_view = view

        if hasattr(self, '_create_ai_panel') and \
                self._create_ai_panel.get_visible():
            self._create_ai_panel.cancel_generation()
            self._create_ai_panel.hide()

        if view in self._favorites_views_indicies:
            favorite = self._favorites_views_indicies.index(view)

            children = self.get_children()
            if self._list_view in children:
                self.remove(self._list_view)
            else:
                for i in range(desktop.get_number_of_views()):
                    if i != favorite and self._favorites_boxes[i] in children:
                        self.remove(self._favorites_boxes[i])

            if self._favorites_boxes[favorite] not in children:
                self.add(self._favorites_boxes[favorite])
            self._favorites_boxes[favorite].show()
            self._favorites_boxes[favorite].grab_focus()
        elif view == self._list_view_index:
            children = self.get_children()
            for i in range(desktop.get_number_of_views()):
                if self._favorites_boxes[i] in children:
                    self.remove(self._favorites_boxes[i])

            if self._list_view not in children:
                self.add(self._list_view)
            self._list_view.show()
            self._list_view.grab_focus()
        else:
            raise ValueError('Invalid view: %r' % view)

    def _show_create_ai_panel(self):
        self._toolbar.clear_query()

        children = self.get_children()
        if self._list_view in children:
            self._list_view.hide()
        else:
            for i in range(desktop.get_number_of_views()):
                if self._favorites_boxes[i] in children:
                    self._favorites_boxes[i].hide()

        self._create_ai_panel.reset_view()
        self._create_ai_panel.show()
        self._create_ai_panel.grab_focus()

    def __create_ai_panel_close_cb(self, panel):
        self._create_ai_panel.cancel_generation()
        self._create_ai_panel.hide()
        self._set_view(self._active_view)

    def is_create_ai_panel_visible(self):
        return hasattr(self, '_create_ai_panel') and \
            self._create_ai_panel.get_visible()

    def __redirect_search_text_to_create_ai_prompt(self, entry):
        if not self.is_create_ai_panel_visible():
            return False

        text = entry.get_text()
        if text:
            self._create_ai_panel.append_prompt_text(text)
            entry.set_text('')

        self._create_ai_panel.focus_prompt()
        return False

    _REDRAW_TIMEOUT = 5 * 60 * 1000  # 5 minutes

    def resume(self):
        pass

    def suspend(self):
        pass

    def set_resume_mode(self, resume_mode, favorite_view=0):
        self._resume_mode = resume_mode
        self._favorites_boxes[favorite_view].set_resume_mode(resume_mode)
        if resume_mode and self._query != '':
            self._list_view.set_filter(self._query)
            for i in range(desktop.get_number_of_views()):
                self._favorites_boxes[i].set_filter(self._query)


class _CreateAIActivityPanel(Gtk.EventBox):
    __gtype_name__ = 'SugarCreateAIActivityPanel'
    _css_loaded = False
    _CODE_COLORS = {
        'line_number': '#6e6e6e',
        'keyword': '#0000cc',
        'class_name': '#267f99',
        'function': '#795e26',
        'string': '#a31515',
        'comment': '#007000',
        'number': '#098658',
        'constant': '#0000cc',
        'property': '#001080',
        'plain': '#111111',
        'markdown': '#0451a5',
        'diff_added': '#007000',
        'diff_deleted': '#b00000',
        'diff_added_bg': '#dff8df',
        'diff_deleted_bg': '#ffe0e0',
    }
    _PYTHON_KEYWORDS = set([
        'and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'del',
        'elif', 'else', 'except', 'False', 'finally', 'for', 'from', 'global',
        'if', 'import', 'in', 'is', 'lambda', 'None', 'nonlocal', 'not', 'or',
        'pass', 'raise', 'return', 'True', 'try', 'while', 'with', 'yield',
    ])
    _PYTHON_TYPES = set([
        'Gtk', 'activity', 'GeneratedActivity', 'ToolbarBox',
        'ActivityToolbarButton', 'StopButton', 'Orientation', 'VERTICAL',
        'Activity',
    ])

    __gsignals__ = {
        'close-requested': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self):
        Gtk.EventBox.__init__(self)
        self._ensure_css()
        self.modify_bg(Gtk.StateType.NORMAL, style.COLOR_WHITE.get_gdk_color())
        self.get_style_context().add_class('create-ai-panel')
        self._option_buttons = {}
        self._selected_options = {
            'template': 'logic_math',
            'age_band': 'all',
            'collab': 'solo',
            'planner': 'rag',
            'policy': 'creative',
            'validate': 'on',
            'enhance': 'on',
            'provider': 'default',
            'license': 'mit',
            'code_size': 'standard',
        }
        self._code_size_combo = None
        self._sidebar_visible = True
        self._sidebar_toggle_button = None
        self._sidebar_revealer = None
        self._template_hint = None
        self._planner_hint = None
        self._validate_chip_value_label = None
        self._provider_chip_value_label = None
        self._template_card_icons = {}
        self._template_card_buttons = {}
        self._provider_combo = None
        self._provider_key_entry = None
        self._provider_paste_button = None
        self._provider_model_entry = None
        self._provider_model_switch_row = None
        self._provider_endpoint_entry = None
        self._provider_apply_button = None
        self._provider_remove_button = None
        self._provider_adv_row = None
        self._provider_status_label = None
        self._provider_test_running = False
        self._flatpak_export_running = False
        self._license_hint = None
        self._prompt_text = None
        self._prompt_char_label = None
        self._prompt_status_label = None
        self._studio_prompt_labels = []
        self._preview_content_box = None
        self._last_preview_error = ''
        self._live_preview_canvas = None
        self._live_preview_activity = None
        self._preview_empty_title = None
        self._preview_empty_note = None
        self._preview_generation_spinner = None
        self._preview_generation_progress = None
        self._preview_generation_stage = None
        self._preview_generation_steps = []
        self._generation_animation_id = 0
        self._generation_animation_hide_id = 0
        self._preview_generation_xo = None
        self._preview_generation_fun = None
        self._generation_tick_count = 0
        self._generation_has_fraction = False
        self._preview_generation_canvas = None
        self._generation_wheel_cache = None
        self._generation_anim_start_us = None
        self._generation_anim_t = 0.0
        self._generation_anim_done = False
        self._generation_final_rgb = None
        self._generation_fun_next = None
        self._generation_fun_alpha = 1.0
        self._generation_target_fraction = None
        self._generation_shown_fraction = 0.0
        self._generation_fraction_mix = 0.0
        self._generation_done_at = None
        self._generation_fade_widgets = []
        self._studio_preview_tab = None
        self._studio_review_tab = None
        self._studio_versions_tab = None
        self._studio_mode_stack = None
        self._review_file_buttons = []
        self._review_title_label = None
        self._review_summary_label = None
        self._review_meta_label = None
        self._review_code_label = None
        self._current_review_file = 'activity_py'
        self._review_generation_context = {}
        self._version_history_buttons = []
        self._version_history_box = None
        self._version_source_button = None
        self._version_diff_button = None
        self._version_title_label = None
        self._version_meta_label = None
        self._version_code_label = None
        self._selected_version = 'v6'
        self._version_mode = 'diff'
        self._review_draft_was_shown = False
        self._live_edit_entry = None
        self._live_edit_status_label = None
        self._live_edit_target_label = None
        self._live_edit_target = _('activity canvas')
        self._live_edit_target_is_region = False
        self._live_edit_on_button = None
        self._live_edit_off_button = None
        self._live_edit_enabled = True
        self._live_edit_handler_ids = []
        self._live_edit_highlighted = None
        self._live_edit_panel = None
        self._live_edit_press_handled = False
        self._live_edit_targets = []
        self._preview_shell = None
        self._select_start = None
        self._select_rect = None
        self._ask_bar = None
        self._ask_bar_entry = None
        self._ask_bar_target_label = None
        self._ask_bar_status_label = None
        self._ask_bar_plus = None
        self._ask_bar_edit_on = None
        self._ask_bar_edit_off = None
        self._chat_messages_box = None
        self._chat_entry = None
        self._chat_scroll = None
        self._aod_session_id = ''
        self._aod_active_revision_id = ''
        self._aod_original_prompt = ''
        self._sidebar_messages_box = None
        self._sidebar_chat_scroll = None
        self._sidebar_refine_entry = None
        self._sidebar_refine_status_label = None
        self._sidebar_challenge_box = None
        self._sidebar_level_label = None
        self._prompt_is_placeholder = False
        self._enhance_button = None
        self._enhance_chip_value_label = None
        self._enhance_running = False
        self._enhanced_prompt_announced = False
        self._preview_is_fullscreen = False
        self._preview_fullscreen_button = None
        self._studio_left_panel = None
        self._studio_right_panel = None
        self._generation_result = None
        self._generation_job_id = None
        self._generation_job_callback = \
            self._generation_job_updated_from_worker
        self._prompt_placeholder_text = _(
            'Example: "Create a fractions playground where teams build '
            'and explain models."')
        self._is_fullscreen = False

        box = Gtk.VBox(spacing=style.zoom(8))
        box.set_border_width(style.zoom(10))
        self.add(box)
        box.show()

        self._content_alignment = Gtk.Alignment(xalign=0.5, yalign=0.46,
                                                xscale=1, yscale=0)
        box.pack_start(self._content_alignment, True, True, 0)
        self._content_alignment.show()

        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._stack.set_transition_duration(180)
        self._content_alignment.add(self._stack)
        self._stack.show()

        choose_view = self._create_choose_view()
        self._stack.add_named(choose_view, 'choose')
        choose_view.show()

        create_view = self._create_create_view()
        self._stack.add_named(create_view, 'create')
        create_view.show()

        studio_view = self._create_studio_view()
        self._stack.add_named(studio_view, 'studio')
        studio_view.show()

        self._stack.set_visible_child_name('choose')

    def reset_view(self):
        self.cancel_generation()
        self._generation_result = None
        self._review_generation_context = {}
        self._review_draft_was_shown = False
        self._aod_session_id = ''
        self._aod_active_revision_id = ''
        self._aod_original_prompt = ''
        self._show_empty_activity_preview()
        self._use_centered_layout()
        self._stack.set_visible_child_name('choose')
        self._reset_prompt()

    def cancel_generation(self):
        self._detach_generation_job(cancel=True)
        self._stop_generation_animation()
        self._review_generation_context = {}
        self._review_draft_was_shown = False

    def _detach_generation_job(self, cancel=False):
        if self._generation_job_id is None:
            return

        from jarabe.model.aodservice import get_service

        service = get_service()
        job_id = self._generation_job_id
        self._generation_job_id = None
        service.unwatch(job_id, self._generation_job_callback)
        if cancel:
            service.cancel_job(job_id)

    def _create_choose_view(self):
        content = Gtk.VBox(spacing=style.zoom(22))
        content.set_size_request(style.zoom(1080), -1)

        title = Gtk.Label()
        title.set_markup('<span size="xx-large" weight="bold">%s</span>' %
                         _('How would you like to start?'))
        title.get_style_context().add_class('create-ai-title')
        title.set_justify(Gtk.Justification.CENTER)
        content.pack_start(title, False, False, 0)
        title.show()

        subtitle = Gtk.Label(_('Start here if you\'re new, then try changing '
                               'things, then create your own!'))
        subtitle.get_style_context().add_class('create-ai-subtitle')
        subtitle.set_justify(Gtk.Justification.CENTER)
        subtitle.set_line_wrap(True)
        subtitle.set_max_width_chars(72)
        content.pack_start(subtitle, False, False, 0)
        subtitle.show()

        cards = Gtk.HBox(spacing=style.zoom(32))
        cards.set_halign(Gtk.Align.CENTER)
        content.pack_start(cards, False, False, style.zoom(18))
        cards.show()

        cards.pack_start(self._create_stage_card(
            _('MODIFY'),
            _('Change an existing activity\nPick a starter activity and\n'
              'modify it with guided\nchallenges and hints.'),
            _('Then try\nchanging things')), False, False, 0)

        cards.pack_start(self._create_stage_card(
            _('CREATE'),
            _('Describe something new\nDescribe an activity in your\n'
              'own words and the AI will\ngenerate it for you.'),
            _('Then create\nyour own!'),
            on_click=self.__open_create_view), False, False, 0)

        return content

    def _create_create_view(self):
        container = Gtk.VBox(spacing=style.zoom(10))
        container.set_size_request(style.zoom(1280), -1)

        title = Gtk.Label()
        title.set_text(_('What will you make today?'))
        title.get_style_context().add_class('create-ai-hero-title')
        title.set_justify(Gtk.Justification.CENTER)
        title.set_halign(Gtk.Align.CENTER)
        container.pack_start(title, False, False, style.zoom(6))
        title.show()

        subtitle = Gtk.Label(_('Describe a learning activity and Sugar will '
                               'build it with you.'))
        subtitle.get_style_context().add_class('create-ai-builder-subtitle')
        subtitle.set_justify(Gtk.Justification.CENTER)
        subtitle.set_halign(Gtk.Align.CENTER)
        container.pack_start(subtitle, False, False, style.zoom(2))
        subtitle.show()

        prompt_box = Gtk.EventBox()
        prompt_box.get_style_context().add_class('create-ai-prompt-box')
        prompt_box.set_above_child(False)
        prompt_box.set_size_request(style.zoom(1040), -1)
        prompt_box.set_halign(Gtk.Align.CENTER)
        container.pack_start(prompt_box, False, False, style.zoom(10))
        prompt_box.show()

        prompt_inner = Gtk.VBox(spacing=style.zoom(8))
        prompt_inner.set_border_width(style.zoom(9))
        prompt_box.add(prompt_inner)
        prompt_inner.show()

        prompt_scroll = Gtk.ScrolledWindow()
        prompt_scroll.set_policy(Gtk.PolicyType.NEVER,
                                 Gtk.PolicyType.AUTOMATIC)
        prompt_scroll.set_min_content_height(style.zoom(96))
        prompt_scroll.set_max_content_height(style.zoom(96))
        prompt_scroll.set_propagate_natural_height(False)
        prompt_inner.pack_start(prompt_scroll, False, False, 0)
        prompt_scroll.show()

        text = Gtk.TextView()
        self._prompt_text = text
        text.set_can_focus(True)
        text.set_editable(True)
        text.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        text.set_left_margin(style.zoom(4))
        text.set_right_margin(style.zoom(4))
        text.set_top_margin(style.zoom(6))
        text.set_bottom_margin(style.zoom(6))
        text.get_style_context().add_class('create-ai-textview')
        text.get_buffer().connect('changed',
                                  self.__prompt_buffer_changed_cb)
        text.connect('button-press-event',
                     self.__prompt_button_press_event_cb)
        text.connect('key-press-event', self.__prompt_key_press_event_cb)
        text.connect('focus-in-event',
                     lambda w, e: prompt_box.get_style_context().add_class(
                         'create-ai-prompt-box-focused'))
        text.connect('focus-out-event',
                     lambda w, e: prompt_box.get_style_context().remove_class(
                         'create-ai-prompt-box-focused'))
        text.set_size_request(-1, style.zoom(96))
        prompt_scroll.add(text)
        text.show()
        self._set_prompt_placeholder()

        divider = Gtk.EventBox()
        divider.get_style_context().add_class('create-ai-prompt-divider')
        divider.set_size_request(-1, 1)
        prompt_inner.pack_start(divider, False, False, 0)
        divider.show()

        actions = Gtk.EventBox()
        actions.get_style_context().add_class('create-ai-prompt-actions')
        actions.set_above_child(False)
        prompt_inner.pack_start(actions, False, False, 0)
        actions.show()

        bottom_row = Gtk.HBox(spacing=style.zoom(8))
        bottom_row.set_border_width(style.zoom(8))
        actions.add(bottom_row)
        bottom_row.show()

        hint_icon = Gtk.Button()
        add_icon = Icon(icon_name='list-add',
                        pixel_size=style.SMALL_ICON_SIZE,
                        stroke_color=style.COLOR_WHITE.get_svg(),
                        fill_color=style.COLOR_BLACK.get_svg())
        add_icon.show()
        hint_icon.set_image(add_icon)
        hint_icon.get_style_context().add_class('create-ai-plus')
        hint_icon.set_valign(Gtk.Align.CENTER)
        hint_icon.set_tooltip_text(
            _('Try an example: treasure-map quest where teams solve clues '
              'and explain each step.'))
        hint_icon.connect('clicked', self.__prompt_example_clicked_cb)
        bottom_row.pack_start(hint_icon, False, False, 0)
        hint_icon.show()

        validate_chip = Gtk.ToggleButton()
        validate_chip.set_relief(Gtk.ReliefStyle.NONE)
        validate_chip.get_style_context().add_class('create-ai-prompt-chip')
        validate_chip.get_style_context().add_class(
            'create-ai-prompt-chip-active')
        validate_content, validate_value = self._build_chip_content(
            _('Validation'), _('On'))
        validate_chip.add(validate_content)
        self._validate_chip_value_label = validate_value
        validate_chip.set_active(True)
        validate_chip.connect('toggled', self.__validate_chip_toggled_cb)
        bottom_row.pack_start(validate_chip, False, False, 0)
        validate_chip.show()

        enhance_chip = Gtk.ToggleButton()
        enhance_chip.set_relief(Gtk.ReliefStyle.NONE)
        enhance_chip.get_style_context().add_class('create-ai-prompt-chip')
        enhance_chip.get_style_context().add_class(
            'create-ai-prompt-chip-active')
        enhance_content, enhance_value = self._build_chip_content(
            _('Enhance'), _('Auto'))
        enhance_chip.add(enhance_content)
        self._enhance_chip_value_label = enhance_value
        enhance_chip.set_active(True)
        enhance_chip.set_tooltip_text(
            _('Automatically expand short prompts into a detailed '
              'brief before generating'))
        enhance_chip.connect('toggled', self.__enhance_chip_toggled_cb)
        bottom_row.pack_start(enhance_chip, False, False, 0)
        enhance_chip.show()

        send_btn = Gtk.Button()
        send_icon = Icon(icon_name='go-up',
                         pixel_size=style.SMALL_ICON_SIZE,
                         stroke_color=style.COLOR_WHITE.get_svg(),
                         fill_color=style.COLOR_WHITE.get_svg())
        send_icon.show()
        send_btn.set_image(send_icon)
        send_btn.get_style_context().add_class('create-ai-send')
        send_btn.set_size_request(style.zoom(36), style.zoom(36))
        send_btn.set_valign(Gtk.Align.CENTER)
        send_btn.set_tooltip_text(_('Generate the activity'))
        send_btn.connect('clicked', self.__send_button_clicked_cb)
        bottom_row.pack_end(send_btn, False, False, 0)
        send_btn.show()

        enhance_btn = Gtk.Button.new_with_label('✨ ' + _('Enhance'))
        self._enhance_button = enhance_btn
        enhance_btn.set_relief(Gtk.ReliefStyle.NONE)
        enhance_btn.get_style_context().add_class('create-ai-prompt-chip')
        enhance_btn.set_valign(Gtk.Align.CENTER)
        enhance_btn.set_tooltip_text(
            _('Expand your idea into a detailed brief you can edit'))
        enhance_btn.connect('clicked', self.__enhance_button_clicked_cb)
        bottom_row.pack_end(enhance_btn, False, False, style.zoom(6))
        enhance_btn.show()

        thinking = Gtk.Label('')
        self._prompt_status_label = thinking
        thinking.get_style_context().add_class('create-ai-prompt-status')
        thinking.set_valign(Gtk.Align.CENTER)
        bottom_row.pack_end(thinking, False, False, 0)
        thinking.show()

        code_size_combo = Gtk.ComboBoxText()
        self._code_size_combo = code_size_combo
        for size_id, size_label in (
                ('compact', _('~500 lines')),
                ('standard', _('~1000 lines')),
                ('full', _('Full output')),
        ):
            code_size_combo.append(size_id, size_label)
        code_size_combo.set_active_id(
            self._selected_options.get('code_size', 'standard'))
        code_size_combo.get_style_context().add_class(
            'create-ai-provider-combo')
        code_size_combo.set_valign(Gtk.Align.CENTER)
        code_size_combo.connect('changed', self.__code_size_combo_changed_cb)
        bottom_row.pack_end(code_size_combo, False, False, 0)
        code_size_combo.show()

        provider_selector = self._create_provider_selector()

        model_chip = Gtk.MenuButton()
        model_chip.set_relief(Gtk.ReliefStyle.NONE)
        model_chip.get_style_context().add_class('create-ai-prompt-chip')
        model_content, model_value = self._build_chip_content(
            _('Model'),
            self._get_provider_label(self._selected_options['provider']),
            caret=True)
        model_chip.add(model_content)
        self._provider_chip_value_label = model_value
        model_popover = Gtk.Popover.new(model_chip)
        model_popover.get_style_context().add_class('create-ai-popover')
        model_popover.set_position(Gtk.PositionType.BOTTOM)
        model_popover.add(provider_selector)
        model_chip.set_popover(model_popover)
        bottom_row.pack_end(model_chip, False, False, 0)
        model_chip.show()

        cards_caption = Gtk.Label(_('Start with a learning area...'))
        cards_caption.get_style_context().add_class(
            'create-ai-template-caption')
        cards_caption.set_halign(Gtk.Align.CENTER)
        container.pack_start(cards_caption, False, False, style.zoom(6))
        cards_caption.show()

        cards_row = Gtk.HBox(spacing=style.zoom(10))
        cards_row.set_halign(Gtk.Align.CENTER)
        container.pack_start(cards_row, False, False, 0)
        cards_row.show()

        self._option_buttons['template'] = []
        self._template_card_icons = {}
        self._template_card_buttons = {}
        fan_offsets = [0, 6, 12, 12, 6, 0]
        for index, (value, card_title, card_detail, icon_name) in \
                enumerate(self._get_learning_area_options()):
            card = self._create_template_card(value, card_title,
                                              card_detail, icon_name)
            card.set_margin_top(
                style.zoom(fan_offsets[index % len(fan_offsets)]))
            if value == self._selected_options.get('template'):
                card.get_style_context().add_class(
                    'create-ai-option-card-active')
            cards_row.pack_start(card, False, False, 0)
            card.show()
        self._update_template_card_icons()

        template_hint = Gtk.Label(
            _('Learning area: logic and math activities for puzzles, '
              'patterns, and reasoning.'))
        self._template_hint = template_hint
        template_hint.get_style_context().add_class('create-ai-meta-note')
        template_hint.set_halign(Gtk.Align.CENTER)
        template_hint.set_justify(Gtk.Justification.CENTER)
        container.pack_start(template_hint, False, False, style.zoom(2))
        template_hint.show()

        planner_hint = Gtk.Label()
        planner_hint.get_style_context().add_class('create-ai-meta-note')
        self._planner_hint = planner_hint
        planner_hint.set_halign(Gtk.Align.CENTER)
        planner_hint.set_justify(Gtk.Justification.CENTER)
        planner_hint.set_line_wrap(True)
        planner_hint.set_max_width_chars(132)
        container.pack_start(planner_hint, False, False, 0)
        planner_hint.show()
        self._update_planner_hint()

        return container

    def _get_learning_area_options(self):
        return [
            ('logic_math', _('Logic & math'), _('Puzzles & patterns'),
             'insert-table'),
            ('science', _('Science'), _('Explore & measure'),
             'system-search'),
            ('language', _('Language'), _('Stories & words'),
             'edit-description'),
            ('tools_utils', _('Tools'), _('Build helpful tools'),
             'preferences-system'),
            ('games', _('Games'), _('Play loops & score'),
             'media-playback-start'),
            ('creation', _('Creation'), _('Make & express'),
             'toolbar-colors'),
        ]

    def _build_chip_content(self, caption, value, caret=False):
        box = Gtk.VBox(spacing=0)

        caption_label = Gtk.Label(caption)
        caption_label.get_style_context().add_class('create-ai-chip-caption')
        caption_label.set_xalign(0)
        box.pack_start(caption_label, False, False, 0)
        caption_label.show()

        value_row = Gtk.HBox(spacing=style.zoom(4))
        box.pack_start(value_row, False, False, 0)
        value_row.show()

        value_label = Gtk.Label(value)
        value_label.get_style_context().add_class('create-ai-chip-value')
        value_label.set_xalign(0)
        value_label.set_ellipsize(Pango.EllipsizeMode.END)
        value_label.set_max_width_chars(14)
        value_row.pack_start(value_label, False, False, 0)
        value_label.show()

        if caret:
            caret_label = Gtk.Label('▾')
            caret_label.get_style_context().add_class('create-ai-chip-caret')
            value_row.pack_start(caret_label, False, False, 0)
            caret_label.show()

        box.show()
        return box, value_label

    def _create_template_card(self, value, title, detail, icon_name):
        button = Gtk.Button()
        button.set_relief(Gtk.ReliefStyle.NONE)
        button.get_style_context().add_class('create-ai-template-card')
        button.set_size_request(style.zoom(150), style.zoom(150))
        button.connect('clicked', self.__option_card_clicked_cb,
                       'template', value)

        content = Gtk.VBox(spacing=style.zoom(4))
        content.set_border_width(style.zoom(10))
        button.add(content)
        content.show()

        icon = Icon(icon_name=icon_name,
                    pixel_size=style.STANDARD_ICON_SIZE,
                    stroke_color=style.COLOR_TOOLBAR_GREY.get_svg(),
                    fill_color=style.COLOR_INACTIVE_FILL.get_svg())
        icon.set_halign(Gtk.Align.CENTER)
        content.pack_start(icon, True, True, 0)
        icon.show()

        title_label = Gtk.Label(title)
        title_label.get_style_context().add_class('create-ai-option-title')
        title_label.set_justify(Gtk.Justification.CENTER)
        content.pack_start(title_label, False, False, 0)
        title_label.show()

        detail_label = Gtk.Label(detail)
        detail_label.get_style_context().add_class('create-ai-option-detail')
        detail_label.set_justify(Gtk.Justification.CENTER)
        detail_label.set_line_wrap(True)
        detail_label.set_max_width_chars(16)
        content.pack_start(detail_label, False, False, 0)
        detail_label.show()

        self._template_card_icons[value] = icon
        self._template_card_buttons[value] = button
        self._option_buttons['template'].append(button)
        return button

    def _update_template_card_icons(self):
        selected = self._selected_options.get('template')
        for value, icon in self._template_card_icons.items():
            if value == selected:
                icon.props.stroke_color = style.COLOR_WHITE.get_svg()
                icon.props.fill_color = style.COLOR_BUTTON_GREY.get_svg()
            else:
                icon.props.stroke_color = style.COLOR_TOOLBAR_GREY.get_svg()
                icon.props.fill_color = style.COLOR_INACTIVE_FILL.get_svg()

    def __enhance_chip_toggled_cb(self, button):
        active = button.get_active()
        self._selected_options['enhance'] = 'on' if active else 'off'
        if self._enhance_chip_value_label is not None:
            self._enhance_chip_value_label.set_text(
                _('Auto') if active else _('Off'))
        if active:
            button.get_style_context().add_class(
                'create-ai-prompt-chip-active')
        else:
            button.get_style_context().remove_class(
                'create-ai-prompt-chip-active')
        if self._prompt_status_label is not None:
            self._prompt_status_label.set_text(
                _('Short prompts will be auto-enhanced') if active
                else _('Prompts are sent exactly as written'))

    def __enhance_button_clicked_cb(self, button):
        self._start_prompt_enhancement()

    def _start_prompt_enhancement(self):
        if self._enhance_running:
            return
        prompt = '' if self._prompt_is_placeholder else \
            self._get_prompt_text()
        if not prompt:
            if self._prompt_status_label is not None:
                self._prompt_status_label.set_text(
                    _('Type your idea first, then press Enhance'))
            return

        from jarabe.model.aodllm import get_configured_provider
        from jarabe.model.aodllm import normalize_provider_name

        provider_name = normalize_provider_name(
            self._selected_options.get('provider', 'default'))
        try:
            provider = get_configured_provider(provider_name)
        except Exception:
            logging.exception('Could not resolve provider for enhance')
            provider = None
        if provider is None:
            if self._prompt_status_label is not None:
                self._prompt_status_label.set_text(
                    _('Enhance needs an AI provider (not the local '
                      'template)'))
            return

        self._enhance_running = True
        if self._enhance_button is not None:
            self._enhance_button.set_sensitive(False)
        if self._prompt_status_label is not None:
            self._prompt_status_label.set_text(
                _('Enhancing your idea...'))

        def worker():
            from jarabe.model.aodenhance import enhance_prompt
            text, enhanced = enhance_prompt(provider, prompt)
            GObject.idle_add(self.__enhance_finished_cb, text, enhanced)

        threading.Thread(target=worker, daemon=True).start()

    def __enhance_finished_cb(self, text, enhanced):
        self._enhance_running = False
        if self._enhance_button is not None:
            self._enhance_button.set_sensitive(True)
        if enhanced:
            self._set_prompt_text(text)
            if self._prompt_status_label is not None:
                self._prompt_status_label.set_text(
                    _('Enhanced — edit it if you like, then Send'))
        elif self._prompt_status_label is not None:
            self._prompt_status_label.set_text(
                _('Could not enhance right now; your prompt is '
                  'unchanged'))
        return False

    def __validate_chip_toggled_cb(self, button):
        active = button.get_active()
        self._selected_options['validate'] = 'on' if active else 'off'
        if self._validate_chip_value_label is not None:
            self._validate_chip_value_label.set_text(
                _('On') if active else _('Off'))
        if active:
            button.get_style_context().add_class(
                'create-ai-prompt-chip-active')
        else:
            button.get_style_context().remove_class(
                'create-ai-prompt-chip-active')
        if self._prompt_status_label is not None:
            self._prompt_status_label.set_text(
                _('Validation on') if active else _('Validation off'))

    def _create_section_label(self, text):
        label = Gtk.Label(text)
        label.get_style_context().add_class('create-ai-section-label')
        label.set_halign(Gtk.Align.CENTER)
        label.show()
        return label

    def _create_provider_selector(self):
        selector = Gtk.VBox(spacing=style.zoom(9))
        selector.set_border_width(style.zoom(14))
        selector.set_size_request(style.zoom(340), -1)

        heading = Gtk.Label(_('AI model'))
        heading.get_style_context().add_class('create-ai-provider-heading')
        heading.set_xalign(0)
        selector.pack_start(heading, False, False, 0)
        heading.show()

        subtitle = Gtk.Label(
            _('Choose who generates your activity. API keys stay private '
              'in your Sugar profile.'))
        subtitle.get_style_context().add_class('create-ai-meta-note')
        subtitle.set_xalign(0)
        subtitle.set_line_wrap(True)
        subtitle.set_max_width_chars(46)
        selector.pack_start(subtitle, False, False, 0)
        subtitle.show()

        combo = Gtk.ComboBoxText()
        self._provider_combo = combo
        for provider_name, label in self._get_provider_options():
            combo.append(provider_name, label)
        initial_provider = self._initial_provider_option()
        self._selected_options['provider'] = initial_provider
        combo.set_active_id(initial_provider)
        combo.set_size_request(-1, style.zoom(40))
        combo.get_style_context().add_class('create-ai-provider-combo')
        combo.connect('changed', self.__provider_combo_changed_cb)
        selector.pack_start(combo, False, False, 0)
        combo.show()

        key_row = Gtk.HBox(spacing=style.zoom(6))
        selector.pack_start(key_row, False, False, 0)
        key_row.show()

        key_entry = Gtk.Entry()
        self._provider_key_entry = key_entry
        key_entry.set_visibility(False)
        key_entry.set_invisible_char('*')
        key_entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        key_entry.set_placeholder_text(_('Paste your API key here'))
        key_entry.set_tooltip_text(
            _('Keys stay in your Sugar profile and are never added to '
              'generated activities.'))
        key_entry.set_size_request(-1, style.zoom(40))
        key_entry.get_style_context().add_class('create-ai-provider-entry')
        key_entry.connect('key-press-event',
                          self.__provider_key_entry_key_press_event_cb)
        key_entry.connect('paste-clipboard',
                          self.__provider_key_entry_paste_clipboard_cb)
        key_row.pack_start(key_entry, True, True, 0)
        key_entry.show()

        paste_button = Gtk.Button.new_with_label(_('Paste'))
        self._provider_paste_button = paste_button
        paste_button.set_size_request(style.zoom(72), style.zoom(40))
        paste_button.get_style_context().add_class(
            'create-ai-provider-button')
        paste_button.connect('clicked', self.__provider_paste_clicked_cb)
        key_row.pack_start(paste_button, False, False, 0)
        paste_button.show()

        action_row = Gtk.HBox(spacing=style.zoom(6))
        selector.pack_start(action_row, False, False, 0)
        action_row.show()

        remove_button = Gtk.Button.new_with_label(_('Remove key'))
        self._provider_remove_button = remove_button
        remove_button.set_size_request(style.zoom(104), style.zoom(40))
        remove_button.get_style_context().add_class(
            'create-ai-provider-button')
        remove_button.connect('clicked', self.__provider_remove_clicked_cb)
        action_row.pack_start(remove_button, False, False, 0)
        remove_button.show()

        apply_button = Gtk.Button.new_with_label(_('Save key'))
        self._provider_apply_button = apply_button
        apply_button.set_size_request(style.zoom(104), style.zoom(40))
        apply_button.get_style_context().add_class(
            'create-ai-provider-primary')
        apply_button.connect('clicked', self.__provider_apply_clicked_cb)
        action_row.pack_end(apply_button, False, False, 0)
        apply_button.show()

        # Keep model/endpoint widgets as non-visible stubs so the save
        # callback can still read them without crashing.
        self._provider_model_entry = Gtk.Entry()
        self._provider_endpoint_entry = Gtk.Entry()

        # model_switch_row (opencode-go specific)
        model_switch_row = Gtk.HBox(spacing=style.zoom(6))
        self._provider_model_switch_row = model_switch_row
        model_switch_row.set_halign(Gtk.Align.CENTER)
        selector.pack_start(model_switch_row, False, False, 0)

        for label, model in (
                (_('Kimi K2.6'), 'kimi-k2.6'),
                (_('Kimi K2.7 Code'), 'kimi-k2.7-code')):
            model_button = Gtk.Button.new_with_label(label)
            model_button.get_style_context().add_class(
                'create-ai-provider-button')
            model_button.connect(
                'clicked', self.__provider_model_switch_clicked_cb, model)
            model_switch_row.pack_start(model_button, False, False, 0)
            model_button.show()
        model_switch_row.hide()

        status = Gtk.Label()
        self._provider_status_label = status
        status.get_style_context().add_class('create-ai-provider-status')
        status.set_xalign(0)
        status.set_line_wrap(True)
        status.set_max_width_chars(46)
        selector.pack_start(status, False, False, 0)
        status.show()

        self._update_provider_controls()
        selector.show()
        return selector

    def _get_provider_options(self):
        return [
            ('default', _('Automatic')),
            ('freemodel', _('FreeModel')),
            ('openrouter', _('OpenRouter')),
            ('gemini', _('Gemini')),
            ('openai', _('OpenAI')),
            ('deepseek', _('DeepSeek')),
            ('qwen', _('Qwen')),
            ('moonshot', _('Moonshot')),
            ('opencode', _('OpenCode Zen')),
            ('opencode-go', _('OpenCode Go')),
            ('claude', _('Claude')),
            ('ollama', _('Ollama')),
        ]

    def _get_provider_label(self, provider_name):
        labels = dict(self._get_provider_options())
        return labels.get(provider_name, provider_name)

    def _initial_provider_option(self):
        try:
            from jarabe.model.aodservice import get_service

            provider_name = get_service().preferred_provider_name()
        except Exception:
            logging.exception('Could not read preferred AOD provider')
            return 'default'

        options = dict(self._get_provider_options())
        if provider_name in options and provider_name != 'local-template':
            return provider_name
        return 'default'

    def _get_license_options(self):
        return [
            {
                'value': 'mit',
                'label': _('MIT'),
                'card_detail': _('Simple\npermissive'),
                'spdx': 'MIT',
                'description': _('Short permissive license'),
            },
            {
                'value': 'gplv3_plus',
                'label': _('GPLv3+'),
                'card_detail': _('Sugar\nshare-alike'),
                'spdx': 'GPL-3.0-or-later',
                'description': _('Share-alike default for Sugar activities'),
            },
            {
                'value': 'apache_2',
                'label': _('Apache'),
                'card_detail': _('Patent\ngrant'),
                'spdx': 'Apache-2.0',
                'description': _('Permissive license with patent grant'),
            },
            {
                'value': 'agplv3',
                'label': _('AGPLv3'),
                'card_detail': _('Network\nshare-alike'),
                'spdx': 'AGPL-3.0-or-later',
                'description': _('Network share-alike license'),
            },
            {
                'value': 'lgplv3',
                'label': _('LGPLv3'),
                'card_detail': _('Library\nshare-alike'),
                'spdx': 'LGPL-3.0-or-later',
                'description': _('Library-focused copyleft license'),
            },
            {
                'value': 'mpl_2',
                'label': _('MPL-2.0'),
                'card_detail': _('File-level\nshare-alike'),
                'spdx': 'MPL-2.0',
                'description': _('File-level copyleft license'),
            },
            {
                'value': 'bsd_3',
                'label': _('BSD-3'),
                'card_detail': _('Permissive\nattribution'),
                'spdx': 'BSD-3-Clause',
                'description': _('Permissive license with attribution'),
            },
        ]

    def _get_selected_license(self):
        selected = self._selected_options.get('license', 'mit')
        for option in self._get_license_options():
            if option['value'] == selected:
                return option
        return self._get_license_options()[0]

    def _create_option_group(self, title, group_name, options, active_value,
                             card_width=142, card_height=76,
                             detail_width=15):
        group = Gtk.VBox(spacing=style.zoom(4))
        group.set_halign(Gtk.Align.CENTER)

        label = Gtk.Label(title)
        label.get_style_context().add_class('create-ai-option-heading')
        label.set_halign(Gtk.Align.CENTER)
        group.pack_start(label, False, False, 0)
        if title:
            label.show()

        row = Gtk.HBox(spacing=style.zoom(7))
        row.set_halign(Gtk.Align.CENTER)
        group.pack_start(row, False, False, 0)
        row.show()

        self._option_buttons[group_name] = []
        self._selected_options[group_name] = active_value
        for value, option_title, option_detail in options:
            button = self._create_option_card(
                group_name, value, option_title, option_detail,
                card_width, card_height, detail_width)
            if value == active_value:
                button.get_style_context().add_class(
                    'create-ai-option-card-active')
            row.pack_start(button, False, False, 0)
            button.show()

        group.show()
        return group

    def _create_option_card(self, group_name, value, title, detail,
                            card_width=142, card_height=76,
                            detail_width=15):
        button = Gtk.Button()
        button.set_relief(Gtk.ReliefStyle.NONE)
        button.get_style_context().add_class('create-ai-option-card')
        button.set_size_request(style.zoom(card_width),
                                style.zoom(card_height))
        button.connect('clicked', self.__option_card_clicked_cb,
                       group_name, value)

        content = Gtk.VBox(spacing=style.zoom(2))
        content.set_border_width(style.zoom(7))
        button.add(content)
        content.show()

        title_label = Gtk.Label(title)
        title_label.get_style_context().add_class('create-ai-option-title')
        title_label.set_justify(Gtk.Justification.CENTER)
        title_label.set_line_wrap(True)
        title_label.set_max_width_chars(detail_width)
        content.pack_start(title_label, False, False, 0)
        title_label.show()

        detail_label = Gtk.Label(detail)
        detail_label.get_style_context().add_class('create-ai-option-detail')
        detail_label.set_justify(Gtk.Justification.CENTER)
        detail_label.set_line_wrap(True)
        detail_label.set_max_width_chars(detail_width)
        content.pack_start(detail_label, True, True, 0)
        detail_label.show()

        self._option_buttons[group_name].append(button)
        return button

    def _create_studio_view(self):
        workspace = Gtk.EventBox()
        workspace.get_style_context().add_class('create-ai-studio-workspace')
        workspace.set_margin_top(style.zoom(6))

        studio = Gtk.VBox(spacing=style.zoom(12))
        studio.set_border_width(style.zoom(12))
        workspace.add(studio)
        studio.show()

        body = Gtk.HBox(spacing=style.zoom(14))
        body.get_style_context().add_class('create-ai-studio-body')
        studio.pack_start(body, True, True, 0)
        body.show()

        self._studio_left_panel = self._create_studio_left_panel()
        body.pack_start(self._studio_left_panel, False, False, 0)
        body.pack_start(self._create_studio_preview_panel(),
                        True, True, 0)
        self._studio_right_panel = self._create_learning_sidebar()
        self._sidebar_revealer = Gtk.Revealer()
        self._sidebar_revealer.set_transition_type(
            Gtk.RevealerTransitionType.SLIDE_LEFT)
        self._sidebar_revealer.set_transition_duration(260)
        self._sidebar_revealer.add(self._studio_right_panel)
        self._sidebar_revealer.set_reveal_child(True)
        self._sidebar_revealer.show()
        self._sidebar_revealer.connect(
            'notify::child-revealed', self.__sidebar_reveal_done_cb)
        body.pack_start(self._sidebar_revealer, False, False, 0)

        footer = Gtk.HBox(spacing=style.zoom(8))
        footer.get_style_context().add_class('create-ai-studio-footer')
        footer.set_halign(Gtk.Align.END)
        studio.pack_start(footer, False, False, 0)
        footer.show()

        footer.pack_start(self._create_plain_button(_('Back'),
                                                    self.__studio_back_cb),
                          False, False, 0)
        footer.pack_start(self._create_plain_button(_('Rebuild'),
                                                    self.__studio_rebuild_cb),
                          False, False, 0)
        footer.pack_start(self._create_plain_button(
            _('Export XO'), self.__export_xo_cb),
            False, False, 0)
        footer.pack_start(self._create_plain_button(
            _('Export Flatpak'), self.__export_flatpak_cb),
            False, False, 0)
        footer.pack_start(self._create_primary_button(
            _('Install & Open'), self.__install_and_open_cb),
            False, False, 0)

        workspace.show()
        return workspace

    def _use_centered_layout(self):
        self._content_alignment.props.xalign = 0.5
        self._content_alignment.props.yalign = 0.46
        self._content_alignment.props.xscale = 1
        self._content_alignment.props.yscale = 0

    def _use_studio_layout(self):
        self._content_alignment.props.xalign = 0.5
        self._content_alignment.props.yalign = 0
        self._content_alignment.props.xscale = 1
        self._content_alignment.props.yscale = 1

    def _create_studio_left_panel(self):
        panel = Gtk.EventBox()
        panel.get_style_context().add_class('create-ai-studio-side')
        panel.set_size_request(style.zoom(455), -1)

        box = Gtk.VBox(spacing=style.zoom(11))
        box.set_border_width(style.zoom(14))
        panel.add(box)
        box.show()

        prompt_label = Gtk.Label(_('learning activity'))
        prompt_label.get_style_context().add_class('create-ai-studio-chip')
        prompt_label.set_halign(Gtk.Align.CENTER)
        prompt_label.set_justify(Gtk.Justification.CENTER)
        box.pack_start(prompt_label, False, False, 0)
        prompt_label.show()
        self._studio_prompt_labels.append(prompt_label)

        chat_title = Gtk.Label(_('AI co-designer'))
        chat_title.get_style_context().add_class('create-ai-chat-heading')
        chat_title.set_xalign(0)
        box.pack_start(chat_title, False, False, 0)
        chat_title.show()

        self._chat_scroll = Gtk.ScrolledWindow()
        self._chat_scroll.set_policy(Gtk.PolicyType.NEVER,
                                     Gtk.PolicyType.AUTOMATIC)
        self._chat_scroll.set_max_content_height(style.zoom(420))
        self._chat_scroll.set_propagate_natural_height(True)
        self._chat_scroll.get_style_context().add_class(
            'create-ai-chat-scroll')
        box.pack_start(self._chat_scroll, True, True, 0)
        self._chat_scroll.show()

        self._chat_messages_box = Gtk.VBox(spacing=style.zoom(6))
        self._chat_messages_box.set_border_width(style.zoom(4))
        self._chat_scroll.add_with_viewport(self._chat_messages_box)
        self._chat_messages_box.show()

        chat_messages = [
            (_('Ready. Generate an activity, then select a preview part to '
               'refine it.'), False),
        ]
        for message, from_user in chat_messages:
            self._append_chat_message(message, from_user, scroll=False)

        composer = Gtk.EventBox()
        composer.get_style_context().add_class('create-ai-chat-composer')
        box.pack_start(composer, False, False, 0)
        composer.show()

        composer_box = Gtk.HBox(spacing=style.zoom(10))
        composer_box.set_border_width(style.zoom(11))
        composer.add(composer_box)
        composer_box.show()

        self._chat_entry = Gtk.Entry()
        self._chat_entry.set_placeholder_text(
            _('Type a refinement...'))
        self._chat_entry.get_style_context().add_class(
            'create-ai-chat-entry')
        self._chat_entry.connect('activate', self.__chat_entry_activate_cb)
        composer_box.pack_start(self._chat_entry, True, True, 0)
        self._chat_entry.show()

        send_button = Gtk.Button.new_with_label(_('Send'))
        send_button.get_style_context().add_class('create-ai-chat-send')
        send_button.connect('clicked', self.__chat_send_clicked_cb)
        composer_box.pack_start(send_button, False, False, 0)
        send_button.show()

        panel.show()
        return panel

    def _append_chat_message(self, text, from_user=False, scroll=True):
        if self._chat_messages_box is None:
            return

        row = Gtk.HBox()
        bubble = Gtk.EventBox()
        bubble.get_style_context().add_class('create-ai-chat-bubble')
        if from_user:
            bubble.get_style_context().add_class('create-ai-chat-bubble-user')
        else:
            bubble.get_style_context().add_class('create-ai-chat-bubble-ai')

        label = Gtk.Label(text)
        label.get_style_context().add_class('create-ai-chat-text')
        label.set_line_wrap(True)
        label.set_max_width_chars(40)
        label.set_xalign(0)
        label.set_margin_top(style.zoom(6))
        label.set_margin_bottom(style.zoom(6))
        label.set_margin_start(style.zoom(10))
        label.set_margin_end(style.zoom(10))
        bubble.add(label)
        label.show()

        spacer = Gtk.Label()
        if from_user:
            row.pack_start(spacer, True, True, 0)
            row.pack_start(bubble, False, False, 0)
        else:
            row.pack_start(bubble, False, False, 0)
            row.pack_start(spacer, True, True, 0)

        self._chat_messages_box.pack_start(row, False, False, 0)
        spacer.show()
        bubble.show()
        row.show()

        if scroll:
            GObject.idle_add(self.__scroll_chat_to_bottom)

    def _append_chat_status(self, text, scroll=True):
        if self._chat_messages_box is None:
            return

        row = Gtk.HBox()
        label = Gtk.Label(_('- %s') % text)
        label.get_style_context().add_class('create-ai-chat-status')
        label.set_xalign(0)
        label.set_line_wrap(True)
        label.set_max_width_chars(42)
        row.pack_start(label, True, True, 0)
        self._chat_messages_box.pack_start(row, False, False, 0)
        label.show()
        row.show()

        if scroll:
            GObject.idle_add(self.__scroll_chat_to_bottom)

    def __scroll_chat_to_bottom(self):
        if self._chat_scroll is None:
            return False

        adjustment = self._chat_scroll.get_vadjustment()
        adjustment.set_value(adjustment.get_upper() -
                             adjustment.get_page_size())
        return False

    def _create_studio_preview_panel(self):
        shell = Gtk.EventBox()
        shell.get_style_context().add_class('create-ai-preview-shell')

        panel = Gtk.VBox(spacing=style.zoom(8))
        panel.set_border_width(style.zoom(11))
        shell.add(panel)
        panel.show()

        top = Gtk.HBox(spacing=style.zoom(8))
        panel.pack_start(top, False, False, 0)
        top.show()

        title = Gtk.Label(_('Classroom preview'))
        title.get_style_context().add_class('create-ai-studio-section-title')
        title.set_xalign(0)
        top.pack_start(title, True, True, 0)
        title.show()

        self._preview_fullscreen_button = self._create_plain_button(
            _('⛶ Fullscreen'), self.__preview_fullscreen_toggle_cb)
        top.pack_end(self._preview_fullscreen_button, False, False, 0)

        top.pack_end(self._create_plain_button(
            _('Review and install'), self.__review_and_install_cb),
            False, False, 0)

        self._sidebar_toggle_button = self._create_plain_button(
            _('◀ Sidebar'), self.__sidebar_toggle_cb)
        top.pack_end(self._sidebar_toggle_button, False, False, 0)

        tabs = Gtk.HBox(spacing=style.zoom(8))
        panel.pack_start(tabs, False, False, 0)
        tabs.show()
        self._studio_preview_tab = self._create_studio_tab(_('Preview'), True)
        self._studio_preview_tab.connect('clicked',
                                         self.__studio_tab_clicked_cb,
                                         'preview')
        tabs.pack_start(self._studio_preview_tab, False, False, 0)

        self._studio_review_tab = self._create_studio_tab(_('Review'), False)
        self._studio_review_tab.connect('clicked',
                                        self.__studio_tab_clicked_cb,
                                        'review')
        tabs.pack_start(self._studio_review_tab, False, False, 0)

        self._studio_versions_tab = self._create_studio_tab(
            _('Versions'), False)
        self._studio_versions_tab.connect('clicked',
                                          self.__studio_tab_clicked_cb,
                                          'versions')
        tabs.pack_start(self._studio_versions_tab, False, False, 0)

        modes = Gtk.HBox(spacing=style.zoom(6))
        panel.pack_start(modes, False, False, 0)
        modes.show()
        for label in [_('Make'), _('Play'), _('Share')]:
            modes.pack_start(self._create_soft_pill(label), False, False, 0)

        self._studio_mode_stack = Gtk.Stack()
        self._studio_mode_stack.set_transition_type(
            Gtk.StackTransitionType.CROSSFADE)
        self._studio_mode_stack.set_transition_duration(140)
        panel.pack_start(self._studio_mode_stack, True, True, 0)
        self._studio_mode_stack.show()

        preview_page = Gtk.VBox(spacing=style.zoom(9))
        preview_scroll = Gtk.ScrolledWindow()
        preview_scroll.set_policy(Gtk.PolicyType.NEVER,
                                  Gtk.PolicyType.AUTOMATIC)
        preview_scroll.set_propagate_natural_height(True)
        preview_scroll.set_max_content_height(style.zoom(680))
        preview_scroll.add(self._create_preview_frame())
        preview_page.pack_start(preview_scroll, True, True, 0)
        preview_scroll.show()
        self._live_edit_panel = self._create_live_edit_panel()
        preview_page.pack_start(self._live_edit_panel, False, False, 0)
        self._ask_bar = self._create_ask_bar()
        preview_page.pack_start(self._ask_bar, False, False, 0)
        self._studio_mode_stack.add_named(preview_page, 'preview')
        preview_page.show()

        review_page = self._create_review_page()
        self._studio_mode_stack.add_named(review_page, 'review')
        review_page.show()

        versions_page = self._create_versions_page()
        self._studio_mode_stack.add_named(versions_page, 'versions')
        versions_page.show()

        self._studio_mode_stack.set_visible_child_name('preview')

        shell.show()
        return shell

    def _create_preview_frame(self):
        frame = Gtk.EventBox()
        frame.get_style_context().add_class('create-ai-preview-frame')
        frame.show()

        frame_box = Gtk.VBox(spacing=style.zoom(6))
        frame_box.set_border_width(style.zoom(10))
        frame.add(frame_box)
        frame_box.show()

        preview_align = Gtk.Alignment(xalign=0.5, yalign=0.48, xscale=1,
                                      yscale=1)
        frame_box.pack_start(preview_align, True, True, 0)
        preview_align.show()
        preview_align.add(self._create_activity_preview())

        help_text = Gtk.Label(
            _('Live edit: click a part or drag across an area, then '
              'describe the change.'))
        help_text.get_style_context().add_class('create-ai-meta-note')
        help_text.set_xalign(0)
        frame_box.pack_start(help_text, False, False, 0)
        help_text.show()

        return frame

    def _create_activity_preview(self):
        preview = Gtk.VBox()
        preview.get_style_context().add_class('create-ai-activity-preview')
        preview.set_border_width(style.zoom(18))

        empty = Gtk.Alignment(xalign=0.5, yalign=0.5, xscale=1, yscale=1)
        preview.pack_start(empty, True, True, 0)
        empty.show()

        content = Gtk.VBox(spacing=style.zoom(8))
        content.set_halign(Gtk.Align.FILL)
        content.set_valign(Gtk.Align.FILL)
        self._preview_content_box = content
        empty.add(content)
        content.show()

        self._show_empty_activity_preview()
        preview.show()
        return preview

    def _clear_activity_preview(self):
        self._detach_live_edit_handlers()
        if self._preview_content_box is None:
            return
        for child in self._preview_content_box.get_children():
            self._preview_content_box.remove(child)
        self._live_preview_canvas = None
        self._preview_shell = None
        self._select_start = None
        self._select_rect = None
        if self._live_preview_activity is not None:
            try:
                self._live_preview_activity.cleanup()
            except Exception:
                pass
            self._live_preview_activity = None
        self._preview_empty_title = None
        self._preview_empty_note = None
        self._preview_generation_spinner = None
        self._preview_generation_progress = None
        self._preview_generation_stage = None
        self._preview_generation_xo = None
        self._preview_generation_fun = None
        self._preview_generation_canvas = None
        self._generation_anim_start_us = None
        self._generation_anim_done = False
        self._generation_final_rgb = None
        self._generation_fun_next = None
        self._generation_target_fraction = None
        self._generation_shown_fraction = 0.0
        self._generation_fraction_mix = 0.0
        self._generation_done_at = None
        self._generation_fade_widgets = []
        self._preview_generation_steps = []
        self._preview_generation_step_boxes = []

    def _show_empty_activity_preview(self):
        self._clear_activity_preview()

        title = Gtk.Label(_('Activity preview'))
        self._preview_empty_title = title
        title.get_style_context().add_class('create-ai-preview-title')
        title.set_justify(Gtk.Justification.CENTER)
        self._preview_content_box.pack_start(title, False, False, 0)
        title.show()

        note = Gtk.Label(_('Backend output will render here.'))
        self._preview_empty_note = note
        note.get_style_context().add_class('create-ai-meta-note')
        note.set_justify(Gtk.Justification.CENTER)
        note.set_line_wrap(True)
        note.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        note.set_max_width_chars(70)
        self._preview_content_box.pack_start(note, False, False, 0)
        note.show()

    def _show_generation_activity_preview(self):
        self._clear_activity_preview()

        self._generation_anim_start_us = None
        self._generation_anim_t = 0.0
        self._generation_anim_done = False
        self._generation_final_rgb = None
        self._generation_fun_next = None
        self._generation_fun_alpha = 1.0
        self._generation_target_fraction = None
        self._generation_shown_fraction = 0.0
        self._generation_fraction_mix = 0.0
        self._generation_done_at = None
        self._generation_fade_widgets = []

        xo_icon = None
        canvas = None
        try:
            stroke, fill = self._xo_pulse_color(0)
            xo_icon = Icon(icon_name='computer-xo',
                           pixel_size=style.zoom(120),
                           stroke_color=stroke,
                           fill_color=fill)
        except Exception:
            logging.exception('Could not create pulsing XO icon')
        self._preview_generation_xo = xo_icon
        if xo_icon is not None:
            size = style.zoom(200)
            canvas = Gtk.DrawingArea()
            canvas.set_size_request(size, size)
            canvas.connect('draw', self._draw_generation_canvas)
            self._preview_generation_canvas = canvas

            overlay = Gtk.Overlay()
            overlay.set_halign(Gtk.Align.CENTER)
            overlay.set_margin_top(style.zoom(4))
            overlay.add(canvas)
            canvas.show()

            xo_icon.set_halign(Gtk.Align.CENTER)
            xo_icon.set_valign(Gtk.Align.CENTER)
            overlay.add_overlay(xo_icon)
            xo_icon.show()

            self._preview_content_box.pack_start(overlay, False, False, 0)
            overlay.show()
            canvas.add_tick_callback(self._generation_canvas_tick)

        title = Gtk.Label(_('Building your activity'))
        self._preview_empty_title = title
        title.get_style_context().add_class('create-ai-preview-title')
        title.set_justify(Gtk.Justification.CENTER)
        self._preview_content_box.pack_start(title, False, False, 0)
        title.show()

        note = Gtk.Label(
            _('Turning your idea into a real Sugar activity'))
        self._preview_empty_note = note
        note.get_style_context().add_class('create-ai-meta-note')
        note.set_justify(Gtk.Justification.CENTER)
        note.set_line_wrap(True)
        note.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        note.set_max_width_chars(70)
        self._preview_content_box.pack_start(note, False, False, 0)
        note.show()

        if canvas is None:
            # No orbit canvas to close into a progress ring, so fall
            # back to the plain bar.
            progress = Gtk.ProgressBar()
            self._preview_generation_progress = progress
            progress.set_size_request(style.zoom(280), style.zoom(8))
            progress.get_style_context().add_class(
                'create-ai-generation-progress')
            self._preview_content_box.pack_start(
                progress, False, False, style.zoom(6))
            progress.show()

        stage = Gtk.Label()
        self._preview_generation_stage = stage
        stage.get_style_context().add_class('create-ai-generation-stage')
        stage.set_justify(Gtk.Justification.CENTER)
        stage.set_line_wrap(True)
        stage.set_max_width_chars(60)
        self._preview_content_box.pack_start(
            stage, False, False, style.zoom(4))
        stage.show()

        fun = Gtk.Label(self._generation_fun_messages()[0])
        self._preview_generation_fun = fun
        fun.get_style_context().add_class('create-ai-generation-fun')
        fun.set_justify(Gtk.Justification.CENTER)
        fun.set_line_wrap(True)
        fun.set_max_width_chars(60)
        self._preview_content_box.pack_start(
            fun, False, False, style.zoom(2))
        fun.show()

        steps_box = Gtk.VBox(spacing=style.zoom(8))
        steps_box.set_margin_top(style.zoom(6))
        self._preview_content_box.pack_start(
            steps_box, False, False, 0)
        steps_box.show()

        step_defs = [
            (_('Think'), _('Reading your prompt and planning the activity'),
             'emblem-question'),
            (_('Gather'), _('Finding real Sugar activity examples for context'),
             'system-search'),
            (_('Write'), _('Writing the Python code for your activity'),
             'edit-description'),
            (_('Check'), _('Preparing project files and previewing'),
             'dialog-ok'),
            (_('Ready'), _('Packaging your installable activity bundle'),
             'package_settings'),
        ]
        self._preview_generation_steps = []
        self._preview_generation_step_boxes = []
        for label_text, desc_text, icon_name in step_defs:
            row = Gtk.HBox(spacing=style.zoom(8))
            row.set_halign(Gtk.Align.START)
            row.get_style_context().add_class(
                'create-ai-generation-step-row')

            icon = None
            try:
                icon = Icon(icon_name=icon_name,
                            pixel_size=style.zoom(16))
            except Exception:
                icon = Gtk.Label(label_text[0])
                icon.set_size_request(style.zoom(16), style.zoom(16))
            row.pack_start(icon, False, False, 0)
            icon.show()

            text_box = Gtk.VBox(spacing=0)
            label = Gtk.Label(label_text)
            label.get_style_context().add_class('create-ai-generation-step')
            label.set_halign(Gtk.Align.START)
            text_box.pack_start(label, False, False, 0)
            label.show()

            desc = Gtk.Label(desc_text)
            desc.get_style_context().add_class(
                'create-ai-generation-step-desc')
            desc.set_halign(Gtk.Align.START)
            desc.set_line_wrap(True)
            desc.set_max_width_chars(50)
            text_box.pack_start(desc, False, False, 0)
            desc.show()

            row.pack_start(text_box, True, True, 0)
            text_box.show()

            steps_box.pack_start(row, False, False, 0)
            row.show()
            self._preview_generation_steps.append(label)
            self._preview_generation_step_boxes.append(row)

        if canvas is not None:
            # Staggered entrance: each element fades in a beat after
            # the previous one, driven by the canvas frame tick.
            self._generation_fade_widgets = [
                (xo_icon, 0.0), (title, 0.15), (note, 0.25),
                (stage, 0.35), (fun, 0.45), (steps_box, 0.55)]
            for widget, _unused in self._generation_fade_widgets:
                widget.set_opacity(0.0)

    def _create_review_page(self):
        review = Gtk.EventBox()
        review.get_style_context().add_class('create-ai-review-shell')

        box = Gtk.HBox(spacing=style.zoom(12))
        box.set_border_width(style.zoom(10))
        review.add(box)
        box.show()

        files_panel = Gtk.EventBox()
        files_panel.get_style_context().add_class('create-ai-review-files')
        files_panel.set_size_request(style.zoom(250), -1)
        box.pack_start(files_panel, False, False, 0)
        files_panel.show()

        files_box = Gtk.VBox(spacing=style.zoom(4))
        files_box.set_border_width(style.zoom(8))
        files_panel.add(files_box)
        files_box.show()

        for filename, file_key in [
                (_('README.md'), 'readme'),
                (_('LICENSE'), 'license'),
                (_('activity/'), 'activity_dir'),
                (_('activity.py'), 'activity_py'),
                (_('aod_plan.json'), 'plan_json'),
                (_('setup.py'), 'setup_py')]:
            files_box.pack_start(
                self._create_review_file_button(filename, file_key),
                False, False, 0)

        code_panel = Gtk.EventBox()
        code_panel.get_style_context().add_class('create-ai-review-code')
        box.pack_start(code_panel, True, True, 0)
        code_panel.show()

        code_box = Gtk.VBox(spacing=style.zoom(8))
        code_box.set_border_width(style.zoom(12))
        code_panel.add(code_box)
        code_box.show()

        header = Gtk.HBox(spacing=style.zoom(8))
        code_box.pack_start(header, False, False, 0)
        header.show()

        title_box = Gtk.VBox(spacing=style.zoom(3))
        header.pack_start(title_box, True, True, 0)
        title_box.show()

        title = Gtk.Label()
        self._review_title_label = title
        title.get_style_context().add_class('create-ai-review-title')
        title.set_xalign(0)
        title_box.pack_start(title, False, False, 0)
        title.show()

        summary = Gtk.Label()
        self._review_summary_label = summary
        summary.get_style_context().add_class('create-ai-review-summary')
        summary.set_xalign(0)
        summary.set_line_wrap(True)
        title_box.pack_start(summary, False, False, 0)
        summary.show()

        header.pack_end(self._create_plain_button(_('Explain file'), None),
                        False, False, 0)
        header.pack_end(self._create_plain_button(_('Explain project'), None),
                        False, False, 0)

        meta = Gtk.Label()
        self._review_meta_label = meta
        meta.get_style_context().add_class('create-ai-review-meta')
        meta.set_xalign(0)
        code_box.pack_start(meta, False, False, 0)
        meta.show()

        source_frame = Gtk.EventBox()
        source_frame.get_style_context().add_class('create-ai-code-frame')
        code_box.pack_start(source_frame, True, True, 0)
        source_frame.show()

        source_scroll = Gtk.ScrolledWindow()
        source_scroll.set_policy(Gtk.PolicyType.AUTOMATIC,
                                 Gtk.PolicyType.AUTOMATIC)
        source_frame.add(source_scroll)
        source_scroll.show()

        code_label = Gtk.Label()
        self._review_code_label = code_label
        code_label.get_style_context().add_class('create-ai-code-text')
        code_label.set_xalign(0)
        code_label.set_yalign(0)
        code_label.set_selectable(True)
        code_label.set_line_wrap(False)
        code_label.set_margin_top(style.zoom(10))
        code_label.set_margin_bottom(style.zoom(10))
        code_label.set_margin_start(style.zoom(12))
        code_label.set_margin_end(style.zoom(12))
        source_scroll.add_with_viewport(code_label)
        code_label.show()

        review.show()
        self._set_review_file('activity_py')
        return review

    def _create_review_file_button(self, filename, file_key):
        button = Gtk.Button.new_with_label(filename)
        button.set_relief(Gtk.ReliefStyle.NONE)
        button.get_style_context().add_class('create-ai-review-file')
        if file_key == 'activity_py':
            button.get_style_context().add_class('create-ai-review-file-active')
        button.connect('clicked', self.__review_file_clicked_cb, file_key)
        self._review_file_buttons.append((button, file_key))
        button.show()
        return button

    def _get_review_file_data(self, file_key):
        if self._generation_result is not None:
            return self._get_generated_review_file_data(file_key)
        if self._review_generation_context:
            return self._get_live_generation_review_file_data(file_key)

        license_info = self._get_selected_license()
        license_label = license_info['label']
        license_spdx = license_info['spdx']
        plan_data = {
            'template': self._selected_options['template'],
            'planner': self._selected_options['planner'],
            'policy': self._selected_options['policy'],
            'license': {
                'name': license_label,
                'spdx': license_spdx,
            },
            'checks': [
                'activity imports allowed',
                'Journal hooks present',
                'license metadata present',
                'preview can render without network',
            ],
            'live_edits': [],
        }
        files = {
            'readme': {
                'title': _('README.md'),
                'summary': _('Introduces the generated activity, learner '
                             'goal, classroom flow, license, and install '
                             'steps.'),
                'meta': _('Source (editable)    README.md • Markdown • '
                          'Generated'),
                'language': 'markdown',
                'code': _(
                    '# Learning Activity\n\n'
                    'A Sugar activity generated from the learner prompt.\n\n'
                    '## Classroom goal\n'
                    '- Make something playful and visible.\n'
                    '- Try it in the preview canvas.\n'
                    '- Share the finished activity as an XO bundle.\n\n'
                    '## License\n'
                    'Selected license: %(license)s (%(spdx)s).\n\n'
                    '## Next steps\n'
                    'Use the live edit prompt to refine copy, layout, '
                    'behavior, and Journal saving.') % {
                        'license': license_label,
                        'spdx': license_spdx,
                    },
            },
            'license': {
                'title': _('LICENSE'),
                'summary': _('Contains the selected license text for the '
                             'generated activity bundle.'),
                'meta': _('Legal file    LICENSE • Text • %s') %
                        license_spdx,
                'language': 'text',
                'code': _(
                    '%(license)s\n\n'
                    'SPDX-License-Identifier: %(spdx)s\n\n'
                    'The exported Sugar activity will include the full '
                    '%(license)s license text here. Source files and bundle '
                    'metadata will use the same SPDX identifier.') % {
                        'license': license_label,
                        'spdx': license_spdx,
                    },
            },
            'activity_dir': {
                'title': _('activity/'),
                'summary': _('Contains the Sugar bundle metadata, license, '
                             'icon, and localization files used when '
                             'packaging.'),
                'meta': _('Bundle folder    activity/ • Sugar metadata • '
                          'Generated'),
                'language': 'tree',
                'code': _(
                    'activity/\n'
                    '  activity.info\n'
                    '  activity.svg\n'
                    '  locale/\n\n'
                    'activity.info declares the bundle id, title, launcher, '
                    'icon, supported Sugar version, and license: %(spdx)s.')
                    % {'spdx': license_spdx},
            },
            'activity_py': {
                'title': _('activity.py'),
                'summary': _('Defines the generated Sugar activity, toolbar, '
                             'canvas placeholder, Journal hooks, and preview '
                             'bridge.'),
                'meta': _('Source (editable)    activity.py • Python • '
                          'Generated'),
                'language': 'python',
                'code': (
                    '# SPDX-License-Identifier: %s\n'
                    '\n'
                    'from gi.repository import Gtk\n'
                    '\n'
                    'from sugar3.activity import activity\n'
                    'from sugar3.activity.widgets import ActivityToolbarButton\n'
                    'from sugar3.activity.widgets import StopButton\n'
                    'from sugar3.graphics.toolbarbox import ToolbarBox\n'
                    '\n'
                    '\n'
                    'class GeneratedActivity(activity.Activity):\n'
                    '    def __init__(self, handle):\n'
                    '        activity.Activity.__init__(self, handle)\n'
                    '        self.max_participants = 1\n'
                    '        self._build_toolbar()\n'
                    '        self._build_canvas()\n'
                    '\n'
                    '    def _build_toolbar(self):\n'
                    '        toolbar_box = ToolbarBox()\n'
                    '        toolbar = toolbar_box.toolbar\n'
                    '        toolbar.insert(ActivityToolbarButton(self), 0)\n'
                    '        toolbar.insert(StopButton(self), -1)\n'
                    '        self.set_toolbar_box(toolbar_box)\n'
                    '        toolbar_box.show_all()\n'
                    '\n'
                    '    def _build_canvas(self):\n'
                    '        canvas = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)\n'
                    '        canvas.set_border_width(24)\n'
                    '        title = Gtk.Label(label="Activity preview")\n'
                    '        title.set_justify(Gtk.Justification.CENTER)\n'
                    '        canvas.pack_start(title, True, True, 0)\n'
                    '        self.set_canvas(canvas)\n'
                    '        canvas.show_all()\n'
                    '\n'
                    '    def write_file(self, file_path):\n'
                    '        """Save learner work into the Journal."""\n'
                    '        pass\n'
                    '\n'
                    '    def read_file(self, file_path):\n'
                    '        """Restore learner work from the Journal."""\n'
                    '        pass\n') % license_spdx,
            },
            'plan_json': {
                'title': _('aod_plan.json'),
                'summary': _('Stores the AI plan, safety notes, selected '
                             'template, license, and live edit history.'),
                'meta': _('Plan artifact    aod_plan.json • JSON • Generated'),
                'language': 'json',
                'code': json.dumps(plan_data, indent=2) + '\n',
            },
            'setup_py': {
                'title': _('setup.py'),
                'summary': _('Packages the generated project as a Sugar '
                             'activity bundle.'),
                'meta': _('Build script    setup.py • Python • Generated'),
                'language': 'python',
                'code': (
                    'from sugar3.activity import bundlebuilder\n'
                    '\n'
                    '\n'
                    'if __name__ == "__main__":\n'
                    '    bundlebuilder.start()\n'),
            },
        }
        return files[file_key]

    def _get_live_generation_review_file_data(self, file_key):
        context = self._review_generation_context
        stage = context.get('stage', 'queued')
        progress = int(context.get('progress', 0.0) * 100)
        provider = context.get('provider', _('Provider'))
        prompt = context.get('prompt', '')
        message = context.get('message', _('Starting generation'))
        draft_source = context.get('draft_activity_source', '')
        mode = _('Refinement') if context.get('is_refinement') else \
            _('Generation')
        checklist = [
            _('Sugar Activity subclass'),
            _('Toolbar and Stop button'),
            _('Full-window GTK canvas'),
            _('Journal read/write hooks'),
            _('Prompt-specific interaction checks'),
        ]
        plan_data = {
            'mode': mode,
            'provider': provider,
            'stage': stage,
            'progress_percent': progress,
            'message': message,
            'prompt': prompt,
            'draft_activity_source_available': bool(draft_source),
            'draft_activity_source_chars': len(draft_source),
            'checks_pending': checklist,
        }
        common_meta = _('%(mode)s in progress    %(provider)s - '
                        '%(progress)d%%') % {
                            'mode': mode,
                            'provider': provider,
                            'progress': progress,
                        }

        activity_summary = _(
            'Live generation status. The model-generated source will '
            'appear here when the code is ready.')
        activity_meta = common_meta
        activity_code = (
            '# activity.py is being generated by %(provider)s\n'
            '# Stage: %(stage)s\n'
            '# Progress: %(progress)d%%\n'
            '# Status: %(message)s\n'
            '# Prompt: %(prompt)s\n'
            '\n'
            '# Sugar will replace this temporary scaffold with the\n'
            '# generated source once the model finishes writing it.\n'
            '\n'
            'from sugar3.activity import activity\n'
            '\n'
            '\n'
            'class GeneratedActivity(activity.Activity):\n'
            '    pass  # waiting for model-generated code\n') % {
                'provider': provider,
                'stage': stage,
                'progress': progress,
                'message': message,
                'prompt': prompt,
            }
        if draft_source:
            if stage == 'failed':
                activity_summary = _(
                    'The model wrote this activity.py but generation '
                    'encountered an error. The reasons are shown in the '
                    'preview panel and the chat. You can read the draft '
                    'here, then try a smaller prompt or a different model.')
                activity_meta = _(
                    'Draft source    %(provider)s - generation failed'
                ) % {
                    'provider': provider,
                }
            else:
                activity_summary = _(
                    'Draft activity.py returned by the model. Sugar is '
                    'assembling the project.')
                activity_meta = _(
                    'Draft source    %(provider)s - assembling - %(progress)d%%'
                ) % {
                    'provider': provider,
                    'progress': progress,
                }
            activity_code = draft_source

        files = {
            'activity_py': {
                'title': _('activity.py'),
                'summary': activity_summary,
                'meta': activity_meta,
                'language': 'python',
                'code': activity_code,
            },
            'plan_json': {
                'title': _('aod_plan.json'),
                'summary': _('Live generation plan and progress status.'),
                'meta': common_meta,
                'language': 'json',
                'code': json.dumps(plan_data, indent=2,
                                   sort_keys=True) + '\n',
            },
            'readme': {
                'title': _('README.md'),
                'summary': _('The generated README will describe classroom '
                             'use after generation completes.'),
                'meta': common_meta,
                'language': 'markdown',
                'code': _(
                    '# Activity generation in progress\n\n'
                    '- Provider: %(provider)s\n'
                    '- Stage: %(stage)s\n'
                    '- Progress: %(progress)d%%\n'
                    '- Current status: %(message)s\n\n'
                    'Prompt:\n\n'
                    '> %(prompt)s\n') % {
                        'provider': provider,
                        'stage': stage,
                        'progress': progress,
                        'message': message,
                        'prompt': prompt,
                    },
            },
            'license': {
                'title': _('LICENSE'),
                'summary': _('The selected license will be bundled with the '
                             'generated activity.'),
                'meta': common_meta,
                'language': 'text',
                'code': _('License file will be written after generation.\n'),
            },
            'activity_dir': {
                'title': _('activity/'),
                'summary': _('Sugar bundle metadata will be assembled after '
                             'the code is generated.'),
                'meta': common_meta,
                'language': 'tree',
                'code': _('activity/\n  activity.info\n  activity.svg\n'),
            },
            'setup_py': {
                'title': _('setup.py'),
                'summary': _('Packaging script will be written after '
                             'generation.'),
                'meta': common_meta,
                'language': 'python',
                'code': _('from sugar3.activity import bundlebuilder\n\n'
                          '# written after activity.py is generated\n'),
            },
        }
        return files[file_key]

    def _get_generated_review_file_data(self, file_key):
        result = self._generation_result
        path_by_key = {
            'readme': 'README.md',
            'license': 'LICENSE',
            'activity_py': 'activity.py',
            'plan_json': 'aod_plan.json',
            'setup_py': 'setup.py',
        }
        metadata = {
            'readme': (
                _('README.md'),
                _('Explains the generated learning goal and classroom flow.'),
                'markdown',
            ),
            'license': (
                _('LICENSE'),
                _('Contains the selected activity license.'),
                'text',
            ),
            'activity_py': (
                _('activity.py'),
                _('Runnable GTK3 and Sugar activity source.'),
                'python',
            ),
            'plan_json': (
                _('aod_plan.json'),
                _('Records the normalized plan and provider details.'),
                'json',
            ),
            'setup_py': (
                _('setup.py'),
                _('Builds the generated project as an XO bundle.'),
                'python',
            ),
        }

        if file_key == 'activity_dir':
            paths = sorted(
                path for path in result.files if path.startswith('activity/')
            )
            return {
                'title': _('activity/'),
                'summary': _('Sugar bundle metadata and icon files.'),
                'meta': _('Generated directory    %s') % result.bundle_id,
                'language': 'tree',
                'code': '\n'.join(paths) + '\n',
            }

        relative_path = path_by_key[file_key]
        title, summary, language = metadata[file_key]
        return {
            'title': title,
            'summary': summary,
            'meta': _('Generated file    %s') % relative_path,
            'language': language,
            'code': result.files.get(
                relative_path,
                _('The generated file is unavailable.'),
            ),
        }

    def _set_review_file(self, file_key):
        if self._review_title_label is None:
            return

        data = self._get_review_file_data(file_key)
        self._current_review_file = file_key
        self._review_title_label.set_text(data['title'])
        self._review_summary_label.set_text(data['summary'])
        self._review_meta_label.set_text(data['meta'])
        self._review_code_label.set_markup(
            self._format_code_markup(data['code'], data['language']))

        for button, key in self._review_file_buttons:
            button.get_style_context().remove_class(
                'create-ai-review-file-active')
            if key == file_key:
                button.get_style_context().add_class(
                    'create-ai-review-file-active')

    def _create_versions_page(self):
        versions = Gtk.EventBox()
        versions.get_style_context().add_class('create-ai-versions-shell')

        box = Gtk.HBox(spacing=style.zoom(12))
        box.set_border_width(style.zoom(10))
        versions.add(box)
        box.show()

        history_panel = Gtk.EventBox()
        history_panel.get_style_context().add_class(
            'create-ai-version-history')
        history_panel.set_size_request(style.zoom(285), -1)
        box.pack_start(history_panel, False, False, 0)
        history_panel.show()

        history_box = Gtk.VBox(spacing=style.zoom(8))
        history_box.set_border_width(style.zoom(10))
        history_panel.add(history_box)
        history_box.show()

        history_title = Gtk.Label(_('VERSION HISTORY'))
        history_title.get_style_context().add_class(
            'create-ai-version-heading')
        history_title.set_xalign(0)
        history_box.pack_start(history_title, False, False, 0)
        history_title.show()

        history_scroll = Gtk.ScrolledWindow()
        history_scroll.set_policy(Gtk.PolicyType.NEVER,
                                  Gtk.PolicyType.AUTOMATIC)
        history_box.pack_start(history_scroll, True, True, 0)
        history_scroll.show()

        version_list = Gtk.VBox(spacing=style.zoom(9))
        self._version_history_box = version_list
        version_list.set_border_width(style.zoom(2))
        history_scroll.add_with_viewport(version_list)
        version_list.show()

        self._refresh_version_history()

        content = Gtk.VBox(spacing=style.zoom(9))
        box.pack_start(content, True, True, 0)
        content.show()

        switch_row = Gtk.HBox(spacing=style.zoom(8))
        content.pack_start(switch_row, False, False, 0)
        switch_row.show()

        self._version_source_button = self._create_version_switch_button(
            _('View Source'), 'source')
        switch_row.pack_start(self._version_source_button, False, False, 0)

        self._version_diff_button = self._create_version_switch_button(
            _('Diff View'), 'diff')
        switch_row.pack_start(self._version_diff_button, False, False, 0)

        compare_row = Gtk.HBox(spacing=style.zoom(8))
        content.pack_start(compare_row, False, False, 0)
        compare_row.show()

        compare_label = Gtk.Label(_('Compare'))
        compare_label.get_style_context().add_class('create-ai-meta-label')
        compare_label.set_xalign(0)
        compare_row.pack_start(compare_label, False, False, 0)
        compare_label.show()

        compare_row.pack_start(self._create_version_compare_pill(_('v1')),
                               False, False, 0)

        arrow = Gtk.Label(_('->'))
        arrow.get_style_context().add_class('create-ai-meta-note')
        compare_row.pack_start(arrow, False, False, 0)
        arrow.show()

        compare_row.pack_start(self._create_version_compare_pill(_('v6')),
                               False, False, 0)

        title = Gtk.Label()
        self._version_title_label = title
        title.get_style_context().add_class('create-ai-review-title')
        title.set_xalign(0)
        content.pack_start(title, False, False, 0)
        title.show()

        meta = Gtk.Label()
        self._version_meta_label = meta
        meta.get_style_context().add_class('create-ai-review-meta')
        meta.set_xalign(0)
        content.pack_start(meta, False, False, 0)
        meta.show()

        source_frame = Gtk.EventBox()
        source_frame.get_style_context().add_class('create-ai-code-frame')
        content.pack_start(source_frame, True, True, 0)
        source_frame.show()

        source_scroll = Gtk.ScrolledWindow()
        source_scroll.set_policy(Gtk.PolicyType.AUTOMATIC,
                                 Gtk.PolicyType.AUTOMATIC)
        source_frame.add(source_scroll)
        source_scroll.show()

        code_label = Gtk.Label()
        self._version_code_label = code_label
        code_label.get_style_context().add_class('create-ai-code-text')
        code_label.set_xalign(0)
        code_label.set_yalign(0)
        code_label.set_selectable(True)
        code_label.set_line_wrap(False)
        code_label.set_margin_top(style.zoom(10))
        code_label.set_margin_bottom(style.zoom(10))
        code_label.set_margin_start(style.zoom(12))
        code_label.set_margin_end(style.zoom(12))
        source_scroll.add_with_viewport(code_label)
        code_label.show()

        versions.show()
        self._set_versions_mode('diff')
        return versions

    def _refresh_version_history(self):
        if self._version_history_box is None:
            return

        for child in self._version_history_box.get_children():
            self._version_history_box.remove(child)
        self._version_history_buttons = []

        versions = self._get_version_history()
        keys = [version['key'] for version in versions]
        if keys and self._selected_version not in keys:
            self._selected_version = keys[-1]

        for version in versions:
            self._version_history_box.pack_start(
                self._create_version_card(version),
                False,
                False,
                0,
            )
        self._version_history_box.show_all()

        if self._version_title_label is not None:
            self._set_versions_mode(self._version_mode)

    def _get_version_history(self):
        revisions = self._get_session_revisions()
        if revisions:
            versions = []
            for index, revision in enumerate(revisions, 1):
                summary = revision.result_summary or {}
                prompt = ' '.join((revision.prompt or '').split())
                if len(prompt) > 72:
                    prompt = prompt[:69].rstrip() + '...'
                activity_name = summary.get('activity_name') or \
                    self._get_prompt_text() or _('Generated activity')
                provider = summary.get('provider', '')
                model = summary.get('model', '')
                if model:
                    provider = '%s / %s' % (provider, model)
                detail = prompt or summary.get('template', '')
                if provider:
                    detail = '%s • %s' % (provider, detail)
                versions.append({
                    'key': revision.revision_id,
                    'label': _('v%d') % index,
                    'date': time.strftime(
                        '%Y-%m-%d %H:%M:%S',
                        time.localtime(revision.created_at),
                    ),
                    'summary': _('%(name)s\n%(detail)s') % {
                        'name': activity_name,
                        'detail': detail,
                    },
                    'revision': revision,
                })
            return versions

        return [
            {
                'key': 'v1',
                'label': _('v1'),
                'date': _('2026-06-01 11:42:10'),
                'summary': _('Initial activity scaffold from the first '
                             'learning prompt.'),
            },
            {
                'key': 'v2',
                'label': _('v2'),
                'date': _('2026-06-01 11:45:04'),
                'summary': _('Added learner-facing prompt copy and starter '
                             'canvas structure.'),
            },
            {
                'key': 'v3',
                'label': _('v3'),
                'date': _('2026-06-01 11:48:31'),
                'summary': _('Connected toolbar actions and preview metadata.'),
            },
            {
                'key': 'v4',
                'label': _('v4'),
                'date': _('2026-06-01 11:50:59'),
                'summary': _('Prepared Journal save and restore hooks.'),
            },
            {
                'key': 'v5',
                'label': _('v5'),
                'date': _('2026-06-01 11:53:31'),
                'summary': _('Added safety checks and guided edit notes.'),
            },
            {
                'key': 'v6',
                'label': _('v6'),
                'date': _('2026-06-01 11:56:57'),
                'summary': _('Latest version with preview bridge and export '
                             'metadata ready.'),
            },
        ]

    def _get_session_revisions(self):
        if not self._aod_session_id:
            return []

        from jarabe.model.aodservice import get_service

        session = get_service().get_session(self._aod_session_id)
        if session is None:
            return []
        return list(session.revisions)

    def _create_version_card(self, version):
        card = Gtk.EventBox()
        card.get_style_context().add_class('create-ai-version-card')
        if version['key'] == self._selected_version:
            card.get_style_context().add_class('create-ai-version-card-active')
        card.add_events(Gdk.EventMask.BUTTON_RELEASE_MASK)
        card.connect('button-release-event',
                     self.__version_card_button_release_cb, version['key'])
        self._version_history_buttons.append((card, version['key']))

        box = Gtk.VBox(spacing=style.zoom(7))
        box.set_border_width(style.zoom(10))
        card.add(box)
        box.show()

        header = Gtk.HBox(spacing=style.zoom(8))
        box.pack_start(header, False, False, 0)
        header.show()

        chip = Gtk.Label(version['label'])
        chip.get_style_context().add_class('create-ai-version-chip')
        header.pack_start(chip, False, False, 0)
        chip.show()

        date = Gtk.Label(version['date'])
        date.get_style_context().add_class('create-ai-version-date')
        date.set_xalign(1)
        header.pack_start(date, True, True, 0)
        date.show()

        summary = Gtk.Label(version['summary'])
        summary.get_style_context().add_class('create-ai-studio-note-label')
        summary.set_xalign(0)
        summary.set_line_wrap(True)
        summary.set_max_width_chars(28)
        box.pack_start(summary, False, False, 0)
        summary.show()

        action = Gtk.Label(_('View Source'))
        action.get_style_context().add_class('create-ai-version-card-action')
        action.set_justify(Gtk.Justification.CENTER)
        box.pack_start(action, False, False, 0)
        action.show()

        card.show()
        return card

    def _create_version_switch_button(self, label, mode):
        button = Gtk.Button.new_with_label(label)
        button.set_relief(Gtk.ReliefStyle.NONE)
        button.get_style_context().add_class('create-ai-version-switch')
        button.connect('clicked', self.__version_switch_clicked_cb, mode)
        button.show()
        return button

    def _create_version_compare_pill(self, label):
        pill = Gtk.Label(label)
        pill.get_style_context().add_class('create-ai-version-compare-pill')
        pill.show()
        return pill

    def _set_versions_mode(self, mode):
        self._version_mode = mode
        if self._version_source_button is not None:
            self._version_source_button.get_style_context().remove_class(
                'create-ai-version-switch-active')
        if self._version_diff_button is not None:
            self._version_diff_button.get_style_context().remove_class(
                'create-ai-version-switch-active')

        if mode == 'source':
            if self._version_source_button is not None:
                self._version_source_button.get_style_context().add_class(
                    'create-ai-version-switch-active')
            self._set_version_source(self._selected_version)
        else:
            if self._version_diff_button is not None:
                self._version_diff_button.get_style_context().add_class(
                    'create-ai-version-switch-active')
            self._set_version_diff()

    def _set_version_source(self, version_key):
        if self._version_title_label is None:
            return

        self._selected_version = version_key
        for card, key in self._version_history_buttons:
            card.get_style_context().remove_class(
                'create-ai-version-card-active')
            if key == version_key:
                card.get_style_context().add_class(
                    'create-ai-version-card-active')

        self._version_title_label.set_text(
            _('Source - %s (read-only)') %
            self._version_label_for_key(version_key))
        self._version_meta_label.set_text(
            _('activity.py • Python • generated version snapshot'))
        self._version_code_label.set_markup(
            self._format_code_markup(
                self._get_version_source(version_key), 'python'))

    def _set_version_diff(self):
        if self._version_title_label is None:
            return

        self._version_title_label.set_text(_('Diff View'))
        before, after = self._get_version_diff_pair()
        if before and after:
            lines = self._get_version_diff_lines()
            added = sum(1 for marker, unused in lines if marker == '+')
            removed = sum(1 for marker, unused in lines if marker == '-')
            self._version_meta_label.set_text(
                _('%(before)s -> %(after)s  •  +%(added)d / -%(removed)d '
                  'lines  •  activity.py') % {
                      'before': self._version_label_for_key(before),
                      'after': self._version_label_for_key(after),
                      'added': added,
                      'removed': removed,
                  })
        else:
            self._version_meta_label.set_text(
                _('v1 -> v6  •  +12 / -5 lines  •  activity.py'))
        self._version_code_label.set_markup(self._format_diff_markup())

    def _get_version_source(self, version_key):
        source = self._read_revision_source(version_key)
        if source:
            return source

        prompt = self._get_prompt_text() or _('learning activity')
        if len(prompt) > 42:
            prompt = prompt[:39] + '...'

        lines = [
            'from gi.repository import Gtk',
            '',
            'from sugar3.activity import activity',
            'from sugar3.activity.widgets import ActivityToolbarButton',
            'from sugar3.activity.widgets import StopButton',
            'from sugar3.graphics.toolbarbox import ToolbarBox',
            '',
            '',
            'ACTIVITY_TITLE = "%s"' % prompt,
            'TEMPLATE_NAME = "starter"',
        ]

        if version_key in ('v4', 'v5', 'v6'):
            lines.extend([
                'JOURNAL_ENABLED = True',
                'PREVIEW_BRIDGE = "%s"' %
                ('ready' if version_key == 'v6' else 'planned'),
            ])
        if version_key in ('v5', 'v6'):
            lines.append('SAFETY_CHECKS = ["imports", "journal", "offline"]')

        lines.extend([
            '',
            '',
            'class GeneratedActivity(activity.Activity):',
            '    def __init__(self, handle):',
            '        activity.Activity.__init__(self, handle)',
            '        self.max_participants = 1',
            '        self._build_toolbar()',
            '        self._build_canvas()',
            '',
            '    def _build_toolbar(self):',
            '        toolbar_box = ToolbarBox()',
            '        toolbar_box.toolbar.insert(ActivityToolbarButton(self), 0)',
            '        toolbar_box.toolbar.insert(StopButton(self), -1)',
            '        self.set_toolbar_box(toolbar_box)',
            '        toolbar_box.show_all()',
            '',
            '    def _build_canvas(self):',
            '        canvas = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)',
            '        title = Gtk.Label(label=ACTIVITY_TITLE)',
            '        canvas.pack_start(title, True, True, 0)',
            '        self.set_canvas(canvas)',
            '        canvas.show_all()',
        ])

        if version_key in ('v4', 'v5', 'v6'):
            lines.extend([
                '',
                '    def write_file(self, file_path):',
                '        # Journal save hook will be connected by backend.',
                '        pass',
                '',
                '    def read_file(self, file_path):',
                '        # Journal restore hook will be connected by backend.',
                '        pass',
            ])

        return '\n'.join(lines)

    def _get_version_diff_lines(self):
        before, after = self._get_version_diff_pair()
        if before and after:
            before_source = self._get_version_source(before).splitlines()
            after_source = self._get_version_source(after).splitlines()
            lines = []
            for line in difflib.ndiff(before_source, after_source):
                if line.startswith('?'):
                    continue
                marker = line[:1]
                text = line[2:]
                if marker not in ('+', '-'):
                    marker = ' '
                lines.append((marker, text))
            return lines or [(' ', '# No source changes in this revision.')]

        return [
            (' ', 'from gi.repository import Gtk'),
            (' ', ''),
            (' ', 'from sugar3.activity import activity'),
            (' ', 'from sugar3.activity.widgets import ActivityToolbarButton'),
            (' ', 'from sugar3.activity.widgets import StopButton'),
            (' ', 'from sugar3.graphics.toolbarbox import ToolbarBox'),
            (' ', ''),
            ('-', 'ACTIVITY_TITLE = "learning activity"'),
            ('+', 'ACTIVITY_TITLE = "%s"' %
             (self._get_prompt_text() or _('learning activity'))[:42]),
            (' ', 'TEMPLATE_NAME = "starter"'),
            ('+', 'JOURNAL_ENABLED = True'),
            ('+', 'PREVIEW_BRIDGE = "ready"'),
            ('+', 'SAFETY_CHECKS = ["imports", "journal", "offline"]'),
            (' ', ''),
            (' ', ''),
            (' ', 'class GeneratedActivity(activity.Activity):'),
            (' ', '    def __init__(self, handle):'),
            (' ', '        activity.Activity.__init__(self, handle)'),
            (' ', '        self.max_participants = 1'),
            (' ', '        self._build_toolbar()'),
            ('+', '        self._preview_ready = True'),
            (' ', '        self._build_canvas()'),
            (' ', ''),
            ('-', '        title = Gtk.Label(label="Activity preview")'),
            ('+', '        title = Gtk.Label(label=ACTIVITY_TITLE)'),
            ('+', '        title.set_justify(Gtk.Justification.CENTER)'),
            ('-', '        canvas.pack_start(title, False, False, 0)'),
            ('+', '        canvas.pack_start(title, True, True, 0)'),
            (' ', '        self.set_canvas(canvas)'),
            (' ', '        canvas.show_all()'),
            ('+', ''),
            ('+', '    def write_file(self, file_path):'),
            ('+', '        # Journal save hook will be connected by backend.'),
            ('+', '        pass'),
        ]

    def _get_version_diff_pair(self):
        revisions = self._get_session_revisions()
        if len(revisions) < 2:
            return '', ''

        revision_ids = [revision.revision_id for revision in revisions]
        selected = self._selected_version
        if selected not in revision_ids:
            selected = revision_ids[-1]
        index = revision_ids.index(selected)
        if index == 0:
            index = 1
        return revision_ids[index - 1], revision_ids[index]

    def _version_label_for_key(self, version_key):
        for version in self._get_version_history():
            if version['key'] == version_key:
                return version['label']
        return version_key

    def _revision_for_key(self, version_key):
        for revision in self._get_session_revisions():
            if revision.revision_id == version_key:
                return revision
        return None

    def _read_revision_source(self, version_key):
        revision = self._revision_for_key(version_key)
        if revision is None:
            return ''

        if self._generation_result is not None and \
                version_key == self._aod_active_revision_id:
            files = getattr(self._generation_result, 'files', {})
            if isinstance(files, dict):
                source = files.get('activity.py', '')
                if source:
                    return source

        summary = revision.result_summary or {}
        project_path = summary.get('project_path', '')
        if not project_path:
            return ''
        source_path = os.path.join(project_path, 'activity.py')
        try:
            with open(source_path, encoding='utf-8') as source_file:
                return source_file.read()
        except OSError:
            return ''

    def _format_diff_markup(self):
        lines = self._get_version_diff_lines()
        width = len(str(len(lines)))
        markup_lines = []

        for number, (marker, line) in enumerate(lines, 1):
            line_number = self._span(str(number).rjust(width),
                                     self._CODE_COLORS['line_number'])
            if marker == '+':
                sign = self._span('+', self._CODE_COLORS['diff_added'],
                                  bold=True)
                code = self._highlight_python_line(line)
                markup = line_number + self._escape_code_markup('  ') + \
                    sign + self._escape_code_markup(' ') + code + \
                    self._escape_code_markup(
                        ' ' * max(8, 92 - len(line)))
                markup_lines.append(
                    self._background(markup,
                                     self._CODE_COLORS['diff_added_bg']))
            elif marker == '-':
                sign = self._span('-', self._CODE_COLORS['diff_deleted'],
                                  bold=True)
                code = self._highlight_python_line(line)
                markup = line_number + self._escape_code_markup('  ') + \
                    sign + self._escape_code_markup(' ') + code + \
                    self._escape_code_markup(
                        ' ' * max(8, 92 - len(line)))
                markup_lines.append(
                    self._background(markup,
                                     self._CODE_COLORS['diff_deleted_bg']))
            else:
                markup_lines.append(
                    line_number + self._escape_code_markup('    ') +
                    self._highlight_python_line(line))

        return '\n'.join(markup_lines)

    def _format_code_markup(self, code, language):
        lines = code.split('\n')
        width = len(str(max(1, len(lines))))
        markup_lines = []

        for number, line in enumerate(lines, 1):
            line_number = str(number).rjust(width)
            markup_lines.append(
                self._span(line_number, self._CODE_COLORS['line_number']) +
                self._escape_code_markup('  ') +
                self._highlight_code_line(line, language))

        return '\n'.join(markup_lines)

    def _highlight_code_line(self, line, language):
        if language == 'python':
            return self._highlight_python_line(line)
        if language == 'json':
            return self._highlight_json_line(line)
        if language == 'markdown':
            return self._highlight_markdown_line(line)
        return self._escape_code_markup(line)

    def _highlight_python_line(self, line):
        code, comment = self._split_python_comment(line)
        highlighted = self._highlight_python_code(code)
        if comment:
            highlighted += self._span(comment, self._CODE_COLORS['comment'])
        return highlighted

    def _highlight_python_code(self, code):
        token_re = re.compile(
            r'(\"[^\"\\]*(?:\\.[^\"\\]*)*\"|'
            r'\'[^\'\\]*(?:\\.[^\'\\]*)*\'|'
            r'\b\d+(?:\.\d+)?\b|'
            r'\b[A-Za-z_][A-Za-z0-9_]*\b)')
        parts = []
        cursor = 0

        for match in token_re.finditer(code):
            start, end = match.span()
            token = match.group(0)
            parts.append(self._escape_code_markup(code[cursor:start]))
            prefix = code[:start]

            if token.startswith('"') or token.startswith("'"):
                parts.append(self._span(token, self._CODE_COLORS['string']))
            elif token in self._PYTHON_KEYWORDS:
                color = self._CODE_COLORS['keyword']
                if token in ('True', 'False', 'None'):
                    color = self._CODE_COLORS['constant']
                parts.append(self._span(token, color, bold=True))
            elif re.search(r'\bclass\s+$', prefix):
                parts.append(self._span(token, self._CODE_COLORS['class_name'],
                                        bold=True))
            elif re.search(r'\bdef\s+$', prefix):
                parts.append(self._span(token, self._CODE_COLORS['function'],
                                        bold=True))
            elif token in self._PYTHON_TYPES:
                parts.append(self._span(token, self._CODE_COLORS['class_name']))
            elif re.match(r'^\d', token):
                parts.append(self._span(token, self._CODE_COLORS['number']))
            elif start > 0 and code[start - 1] == '.':
                parts.append(self._span(token, self._CODE_COLORS['property']))
            else:
                parts.append(self._escape_code_markup(token))

            cursor = end

        parts.append(self._escape_code_markup(code[cursor:]))
        return ''.join(parts)

    def _highlight_json_line(self, line):
        token_re = re.compile(
            r'(\"[^\"\\]*(?:\\.[^\"\\]*)*\"|'
            r'\b(?:true|false|null)\b|'
            r'-?\b\d+(?:\.\d+)?\b)')
        parts = []
        cursor = 0

        for match in token_re.finditer(line):
            start, end = match.span()
            token = match.group(0)
            parts.append(self._escape_code_markup(line[cursor:start]))
            if token.startswith('"'):
                if line[end:].lstrip().startswith(':'):
                    parts.append(self._span(token,
                                            self._CODE_COLORS['property']))
                else:
                    parts.append(self._span(token,
                                            self._CODE_COLORS['string']))
            elif token in ('true', 'false', 'null'):
                parts.append(self._span(token,
                                        self._CODE_COLORS['constant'],
                                        bold=True))
            else:
                parts.append(self._span(token, self._CODE_COLORS['number']))
            cursor = end

        parts.append(self._escape_code_markup(line[cursor:]))
        return ''.join(parts)

    def _highlight_markdown_line(self, line):
        stripped = line.lstrip()
        if stripped.startswith('#'):
            return self._span(line, self._CODE_COLORS['markdown'], bold=True)
        if stripped.startswith('-'):
            indent = line[:len(line) - len(stripped)]
            return self._escape_code_markup(indent) + \
                self._span(stripped[0], self._CODE_COLORS['keyword'],
                           bold=True) + \
                self._escape_code_markup(stripped[1:])
        return self._escape_code_markup(line)

    def _split_python_comment(self, line):
        quote = None
        escaped = False

        for index, char in enumerate(line):
            if escaped:
                escaped = False
                continue
            if char == '\\':
                escaped = True
                continue
            if quote is not None:
                if char == quote:
                    quote = None
                continue
            if char in ('"', "'"):
                quote = char
                continue
            if char == '#':
                return line[:index], line[index:]

        return line, ''

    def _span(self, text, color, bold=False):
        weight = ' weight="bold"' if bold else ''
        return '<span foreground="%s"%s>%s</span>' % (
            color, weight, self._escape_code_markup(text))

    def _background(self, markup, color):
        return '<span background="%s">%s</span>' % (color, markup)

    def _escape_code_markup(self, text):
        return text.replace('&', '&amp;') \
            .replace('<', '&lt;') \
            .replace('>', '&gt;') \
            .replace('\t', '&#160;&#160;&#160;&#160;') \
            .replace(' ', '&#160;')

    def _create_live_edit_panel(self):
        panel = Gtk.EventBox()
        panel.get_style_context().add_class('create-ai-live-edit-panel')
        panel.set_size_request(-1, style.zoom(164))

        box = Gtk.VBox(spacing=style.zoom(8))
        box.set_border_width(style.zoom(12))
        panel.add(box)
        box.show()

        header = Gtk.HBox(spacing=style.zoom(8))
        box.pack_start(header, False, False, 0)
        header.show()

        title = Gtk.Label(_('Live Edit Mode'))
        title.get_style_context().add_class('create-ai-studio-section-title')
        title.set_xalign(0)
        header.pack_start(title, True, True, 0)
        title.show()

        toggle = Gtk.HBox(spacing=0)
        toggle.get_style_context().add_class('create-ai-live-toggle-group')
        header.pack_start(toggle, False, False, 0)
        toggle.show()

        self._live_edit_on_button = self._create_live_toggle_button(
            _('On'), True)
        self._live_edit_off_button = self._create_live_toggle_button(
            _('Off'), False)
        toggle.pack_start(self._live_edit_on_button, False, False, 0)
        toggle.pack_start(self._live_edit_off_button, False, False, 0)

        description = Gtk.Label(
            _('Turn on, then click a part or drag across an area of the '
              'preview to target it.'))
        description.get_style_context().add_class('create-ai-meta-note')
        description.set_xalign(0)
        description.set_line_wrap(True)
        box.pack_start(description, False, False, 0)
        description.show()

        self._live_edit_target_label = Gtk.Label()
        self._live_edit_target_label.get_style_context().add_class(
            'create-ai-live-target')
        self._live_edit_target_label.set_xalign(0)
        self._live_edit_target_label.set_size_request(-1, style.zoom(34))
        box.pack_start(self._live_edit_target_label, False, False, 0)
        self._live_edit_target_label.show()
        self._set_live_edit_target(_('activity canvas'))

        row = Gtk.HBox(spacing=style.zoom(10))
        box.pack_start(row, False, False, 0)
        row.show()

        self._live_edit_entry = Gtk.Entry()
        self._live_edit_entry.set_placeholder_text(
            _('Describe a preview change...'))
        self._live_edit_entry.get_style_context().add_class(
            'create-ai-live-entry')
        self._live_edit_entry.connect(
            'activate', self.__live_edit_entry_activate_cb)
        self._live_edit_entry.set_size_request(-1, style.zoom(44))
        row.pack_start(self._live_edit_entry, True, True, 0)
        self._live_edit_entry.show()

        add_button = Gtk.Button.new_with_label(_('Apply Change'))
        add_button.get_style_context().add_class('create-ai-preview-change')
        add_button.connect('clicked', self.__live_edit_add_clicked_cb)
        add_button.set_size_request(style.zoom(170), style.zoom(44))
        row.pack_start(add_button, False, False, 0)
        add_button.show()

        self._live_edit_status_label = Gtk.Label(_('Ready for preview edits'))
        self._live_edit_status_label.get_style_context().add_class(
            'create-ai-meta-note')
        self._live_edit_status_label.set_xalign(0)
        box.pack_start(self._live_edit_status_label, False, False, 0)
        self._live_edit_status_label.show()

        panel.show()
        return panel

    def _create_ask_bar(self):
        bar = Gtk.EventBox()
        bar.get_style_context().add_class('create-ai-ask-bar')
        bar.set_halign(Gtk.Align.CENTER)
        bar.set_size_request(style.zoom(720), -1)

        row = Gtk.HBox(spacing=style.zoom(8))
        row.set_border_width(style.zoom(6))
        bar.add(row)
        row.show()

        mode_group = Gtk.HBox(spacing=0)
        mode_group.get_style_context().add_class('create-ai-ask-mode-group')
        mode_group.set_valign(Gtk.Align.CENTER)
        row.pack_start(mode_group, False, False, 0)
        mode_group.show()

        edit_button = Gtk.Button.new_with_label(_('Edit'))
        self._ask_bar_edit_on = edit_button
        edit_button.set_relief(Gtk.ReliefStyle.NONE)
        edit_button.get_style_context().add_class('create-ai-ask-mode')
        if self._live_edit_enabled:
            edit_button.get_style_context().add_class(
                'create-ai-ask-mode-active')
        edit_button.set_tooltip_text(
            _('Edit mode: click or drag on the preview to pick a target.'))
        edit_button.connect('clicked', self.__live_toggle_clicked_cb, True)
        mode_group.pack_start(edit_button, False, False, 0)
        edit_button.show()

        play_button = Gtk.Button.new_with_label(_('Play'))
        self._ask_bar_edit_off = play_button
        play_button.set_relief(Gtk.ReliefStyle.NONE)
        play_button.get_style_context().add_class('create-ai-ask-mode')
        if not self._live_edit_enabled:
            play_button.get_style_context().add_class(
                'create-ai-ask-mode-active')
        play_button.set_tooltip_text(
            _('Play mode: try the activity like a learner.'))
        play_button.connect('clicked', self.__live_toggle_clicked_cb, False)
        mode_group.pack_start(play_button, False, False, 0)
        play_button.show()

        plus = Gtk.Button()
        plus_icon = Icon(icon_name='list-add',
                         pixel_size=style.SMALL_ICON_SIZE,
                         stroke_color='#e2e2e2',
                         fill_color='#e2e2e2')
        plus_icon.show()
        plus.set_image(plus_icon)
        plus.set_relief(Gtk.ReliefStyle.NONE)
        plus.get_style_context().add_class('create-ai-ask-plus')
        plus.set_valign(Gtk.Align.CENTER)
        plus.set_tooltip_text(_('Target the whole activity again'))
        plus.connect('clicked', self.__ask_bar_reset_target_cb)
        row.pack_start(plus, False, False, 0)
        plus.show()
        self._ask_bar_plus = plus

        target = Gtk.Label(self._live_edit_target)
        self._ask_bar_target_label = target
        target.get_style_context().add_class('create-ai-ask-target')
        target.set_valign(Gtk.Align.CENTER)
        target.set_ellipsize(Pango.EllipsizeMode.END)
        target.set_max_width_chars(18)
        target.set_tooltip_text(
            _('Click a part of the preview, or drag across an area, '
              'to change just that part.'))
        row.pack_start(target, False, False, 0)
        target.show()

        entry = Gtk.Entry()
        self._ask_bar_entry = entry
        entry.set_placeholder_text(
            _('Describe a change for the selected part')
            if self._live_edit_enabled else _('Ask anything'))
        entry.set_has_frame(False)
        entry.get_style_context().add_class('create-ai-ask-entry')
        entry.connect('activate', self.__ask_bar_send_cb)
        row.pack_start(entry, True, True, 0)
        entry.show()

        status = Gtk.Label('')
        self._ask_bar_status_label = status
        status.get_style_context().add_class('create-ai-ask-status')
        status.set_valign(Gtk.Align.CENTER)
        status.set_ellipsize(Pango.EllipsizeMode.END)
        status.set_max_width_chars(24)
        row.pack_start(status, False, False, 0)
        status.show()

        send = Gtk.Button()
        send_icon = Icon(icon_name='go-up',
                         pixel_size=style.SMALL_ICON_SIZE,
                         stroke_color=style.COLOR_WHITE.get_svg(),
                         fill_color=style.COLOR_WHITE.get_svg())
        send_icon.show()
        send.set_image(send_icon)
        send.set_relief(Gtk.ReliefStyle.NONE)
        send.get_style_context().add_class('create-ai-ask-send')
        send.set_valign(Gtk.Align.CENTER)
        send.set_tooltip_text(_('Apply the change'))
        send.connect('clicked', self.__ask_bar_send_cb)
        row.pack_start(send, False, False, 0)
        send.show()

        return bar

    def _set_live_edit_status(self, text):
        if self._live_edit_status_label is not None:
            self._live_edit_status_label.set_text(text)
        if self._ask_bar_status_label is not None:
            self._ask_bar_status_label.set_text(text)

    def __ask_bar_reset_target_cb(self, button):
        self._set_live_edit_target(_('activity canvas'))
        if self._ask_bar_entry is not None:
            self._ask_bar_entry.grab_focus()

    def __ask_bar_send_cb(self, widget):
        if self._ask_bar_entry is None or self._live_edit_entry is None:
            return

        text = self._ask_bar_entry.get_text().strip()
        if not text:
            self._ask_bar_entry.grab_focus()
            self._set_live_edit_status(_('Describe the change first.'))
            return

        self._ask_bar_entry.set_text('')
        if self._live_edit_enabled:
            self._live_edit_entry.set_text(text)
            self.__live_edit_add_clicked_cb(widget)
            return

        # Play mode: send the request as a whole-activity refinement.
        if self._generation_result is None:
            self._set_live_edit_status(
                _('Generate an activity before asking for changes.'))
            return
        self._set_live_edit_status(_('Refining...'))
        self._submit_refinement_from_prompt(text, source='chat')

    def _create_learning_sidebar(self):
        panel = Gtk.EventBox()
        panel.get_style_context().add_class('create-ai-learning-sidebar')
        panel.set_size_request(style.zoom(260), -1)

        box = Gtk.VBox(spacing=style.zoom(9))
        box.set_border_width(style.zoom(11))
        panel.add(box)
        box.show()

        title = Gtk.Label(_('Learning sidebar'))
        title.get_style_context().add_class('create-ai-studio-section-title')
        title.set_xalign(0)
        box.pack_start(title, False, False, 0)
        title.show()

        subtitle = Gtk.Label(
            _('Challenges, reflections, and annotations stay visible while '
              'the left chat handles generation and refinements.'))
        subtitle.get_style_context().add_class('create-ai-meta-note')
        subtitle.set_xalign(0)
        subtitle.set_line_wrap(True)
        box.pack_start(subtitle, False, False, 0)
        subtitle.show()




        guided = Gtk.EventBox()
        guided.get_style_context().add_class('create-ai-learning-card')
        box.pack_start(guided, False, False, 0)
        guided.show()

        guided_box = Gtk.VBox(spacing=style.zoom(4))
        guided_box.set_border_width(style.zoom(10))
        guided.add(guided_box)
        guided_box.show()

        guided_header = Gtk.HBox(spacing=style.zoom(8))
        guided_box.pack_start(guided_header, False, False, 0)
        guided_header.show()

        guided_title = Gtk.Label(_('Guided code exploration'))
        guided_title.get_style_context().add_class(
            'create-ai-studio-note-label')
        guided_title.set_xalign(0)
        guided_header.pack_start(guided_title, True, True, 0)
        guided_title.show()

        guided_counts = Gtk.Label(
            _('Challenges 137   Reflections 8   Notes 11'))
        guided_counts.get_style_context().add_class(
            'create-ai-learning-counts')
        guided_header.pack_end(guided_counts, False, False, 0)
        guided_counts.show()

        guided_subtitle = Gtk.Label(
            _('Practice edits, reflection, and reading key lines.'))
        guided_subtitle.get_style_context().add_class('create-ai-meta-note')
        guided_subtitle.set_xalign(0)
        guided_box.pack_start(guided_subtitle, False, False, 0)
        guided_subtitle.show()

        tabs = Gtk.HBox(spacing=style.zoom(8))
        box.pack_start(tabs, False, False, 0)
        tabs.show()
        tabs.pack_start(self._create_sidebar_tab(_('Challenges'), True),
                        True, True, 0)
        tabs.pack_start(self._create_sidebar_tab(_('Reflections'), False),
                        True, True, 0)
        tabs.pack_start(self._create_sidebar_tab(_('Annotations'), False),
                        True, True, 0)

        self._sidebar_level_label = Gtk.Label(
            _('Level 1 unlocked - 8 starter challenges'))
        self._sidebar_level_label.get_style_context().add_class(
            'create-ai-meta-label')
        self._sidebar_level_label.set_xalign(0)
        box.pack_start(self._sidebar_level_label, False, False, 0)
        self._sidebar_level_label.show()

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        box.pack_start(scroll, True, True, 0)
        scroll.show()

        self._sidebar_challenge_box = Gtk.VBox(spacing=style.zoom(8))
        self._sidebar_challenge_box.set_border_width(style.zoom(2))
        scroll.add_with_viewport(self._sidebar_challenge_box)
        self._sidebar_challenge_box.show()

        challenges = [
            _('Rename the activity title in your own words.'),
            _('Change one greeting to include the learner name.'),
            _('Rewrite the instructions for younger learners.'),
            _('Add a teamwork prompt before the first move.'),
            _('Find where Journal saving will be connected.'),
            _('Describe what this activity teaches.'),
            _('Change one color and explain the choice.'),
            _('Export when the preview feels ready.'),
        ]
        for text in challenges:
            self._sidebar_challenge_box.pack_start(
                self._create_challenge_card(text), False, False, 0)

        panel.show()
        return panel

    def _create_sidebar_refinement_card(self):
        card = Gtk.EventBox()
        card.get_style_context().add_class('create-ai-learning-card')

        box = Gtk.VBox(spacing=style.zoom(7))
        box.set_border_width(style.zoom(10))
        card.add(box)
        box.show()

        title = Gtk.Label(_('Refine activity'))
        title.get_style_context().add_class('create-ai-studio-note-label')
        title.set_xalign(0)
        box.pack_start(title, False, False, 0)
        title.show()

        note = Gtk.Label(
            _('After generation, type another prompt to improve the current '
              'activity.'))
        note.get_style_context().add_class('create-ai-meta-note')
        note.set_xalign(0)
        note.set_line_wrap(True)
        box.pack_start(note, False, False, 0)
        note.show()

        self._sidebar_chat_scroll = Gtk.ScrolledWindow()
        self._sidebar_chat_scroll.set_policy(Gtk.PolicyType.NEVER,
                                             Gtk.PolicyType.AUTOMATIC)
        self._sidebar_chat_scroll.get_style_context().add_class(
            'create-ai-chat-scroll')
        self._sidebar_chat_scroll.set_size_request(-1, style.zoom(150))
        box.pack_start(self._sidebar_chat_scroll, True, True, 0)
        self._sidebar_chat_scroll.show()

        self._sidebar_messages_box = Gtk.VBox(spacing=style.zoom(6))
        self._sidebar_messages_box.set_border_width(style.zoom(2))
        self._sidebar_chat_scroll.add_with_viewport(
            self._sidebar_messages_box)
        self._sidebar_messages_box.show()
        self._append_sidebar_status(
            _('Ready for a first prompt or a refinement.'),
            scroll=False,
        )

        row = Gtk.HBox(spacing=style.zoom(7))
        box.pack_start(row, False, False, 0)
        row.show()

        self._sidebar_refine_entry = Gtk.Entry()
        self._sidebar_refine_entry.set_placeholder_text(
            _('Ask for a refinement...'))
        self._sidebar_refine_entry.get_style_context().add_class(
            'create-ai-chat-entry')
        self._sidebar_refine_entry.connect(
            'activate', self.__sidebar_refine_entry_activate_cb)
        row.pack_start(self._sidebar_refine_entry, True, True, 0)
        self._sidebar_refine_entry.show()

        send = Gtk.Button.new_with_label(_('Refine'))
        send.get_style_context().add_class('create-ai-chat-send')
        send.connect('clicked', self.__sidebar_refine_send_clicked_cb)
        row.pack_start(send, False, False, 0)
        send.show()

        self._sidebar_refine_status_label = Gtk.Label(
            _('Generate first, then refine here.'))
        self._sidebar_refine_status_label.get_style_context().add_class(
            'create-ai-meta-note')
        self._sidebar_refine_status_label.set_xalign(0)
        self._sidebar_refine_status_label.set_line_wrap(True)
        box.pack_start(self._sidebar_refine_status_label, False, False, 0)
        self._sidebar_refine_status_label.show()

        card.show()
        return card

    def _append_sidebar_message(self, text, from_user=False, scroll=True):
        if self._sidebar_messages_box is None:
            return

        row = Gtk.HBox()
        bubble = Gtk.EventBox()
        bubble.get_style_context().add_class('create-ai-chat-bubble')
        if from_user:
            bubble.get_style_context().add_class('create-ai-chat-bubble-user')
        else:
            bubble.get_style_context().add_class('create-ai-chat-bubble-ai')

        label = Gtk.Label(text)
        label.get_style_context().add_class('create-ai-chat-text')
        label.set_line_wrap(True)
        label.set_max_width_chars(32)
        label.set_xalign(0)
        label.set_margin_top(style.zoom(5))
        label.set_margin_bottom(style.zoom(5))
        label.set_margin_start(style.zoom(8))
        label.set_margin_end(style.zoom(8))
        bubble.add(label)
        label.show()

        spacer = Gtk.Label()
        if from_user:
            row.pack_start(spacer, True, True, 0)
            row.pack_start(bubble, False, False, 0)
        else:
            row.pack_start(bubble, False, False, 0)
            row.pack_start(spacer, True, True, 0)

        self._sidebar_messages_box.pack_start(row, False, False, 0)
        spacer.show()
        bubble.show()
        row.show()

        if scroll:
            GObject.idle_add(self.__scroll_sidebar_chat_to_bottom)

    def _append_sidebar_status(self, text, scroll=True):
        if self._sidebar_messages_box is None:
            return

        row = Gtk.HBox()
        label = Gtk.Label(_('- %s') % text)
        label.get_style_context().add_class('create-ai-chat-status')
        label.set_xalign(0)
        label.set_line_wrap(True)
        label.set_max_width_chars(34)
        row.pack_start(label, True, True, 0)
        self._sidebar_messages_box.pack_start(row, False, False, 0)
        label.show()
        row.show()

        if scroll:
            GObject.idle_add(self.__scroll_sidebar_chat_to_bottom)

    def __scroll_sidebar_chat_to_bottom(self):
        if self._sidebar_chat_scroll is None:
            return False

        adjustment = self._sidebar_chat_scroll.get_vadjustment()
        adjustment.set_value(adjustment.get_upper() -
                             adjustment.get_page_size())
        return False

    def _create_challenge_card(self, text):
        card = Gtk.EventBox()
        card.get_style_context().add_class('create-ai-challenge-card')

        box = Gtk.VBox(spacing=style.zoom(6))
        box.set_border_width(style.zoom(10))
        card.add(box)
        box.show()

        title = Gtk.Label(_('Level 1 - Cosmetic'))
        title.get_style_context().add_class('create-ai-meta-label')
        title.set_xalign(0)
        box.pack_start(title, False, False, 0)
        title.show()

        body = Gtk.Label(text)
        body.get_style_context().add_class('create-ai-studio-note-label')
        body.set_xalign(0)
        body.set_line_wrap(True)
        box.pack_start(body, False, False, 0)
        body.show()

        row = Gtk.HBox(spacing=style.zoom(6))
        box.pack_start(row, False, False, 0)
        row.show()
        row.pack_start(self._create_soft_pill(_('Hint')), False, False, 0)
        row.pack_start(self._create_soft_pill(_('Done')), False, False, 0)

        card.show()
        return card

    def _create_studio_tab(self, label, active):
        button = Gtk.Button.new_with_label(label)
        button.set_relief(Gtk.ReliefStyle.NONE)
        button.get_style_context().add_class('create-ai-studio-tab')
        if active:
            button.get_style_context().add_class('create-ai-studio-tab-active')
        button.show()
        return button

    def _create_sidebar_tab(self, label, active):
        button = Gtk.Button.new_with_label(label)
        button.set_relief(Gtk.ReliefStyle.NONE)
        button.get_style_context().add_class('create-ai-sidebar-tab')
        if active:
            button.get_style_context().add_class(
                'create-ai-sidebar-tab-active')
        button.show()
        return button

    def _create_soft_pill(self, label):
        pill = Gtk.Label(label)
        pill.get_style_context().add_class('create-ai-soft-pill')
        pill.show()
        return pill

    def _create_live_toggle_button(self, label, active):
        button = Gtk.Button.new_with_label(label)
        button.set_relief(Gtk.ReliefStyle.NONE)
        button.get_style_context().add_class('create-ai-live-toggle')
        if active:
            button.get_style_context().add_class('create-ai-live-toggle-active')
        button.connect('clicked', self.__live_toggle_clicked_cb, active)
        button.show()
        return button

    def _create_plain_button(self, label, callback):
        button = Gtk.Button.new_with_label(label)
        button.get_style_context().add_class('create-ai-studio-button')
        if callback is not None:
            button.connect('clicked', callback)
        button.show()
        return button

    def _create_primary_button(self, label, callback=None):
        button = Gtk.Button.new_with_label(label)
        button.get_style_context().add_class('create-ai-studio-primary')
        if callback is not None:
            button.connect('clicked', callback)
        button.show()
        return button

    def _ensure_css(self):
        if _CreateAIActivityPanel._css_loaded:
            return

        css_provider = Gtk.CssProvider()
        colors = {
            'black': style.COLOR_BLACK.get_html(),
            'button': style.COLOR_BUTTON_GREY.get_html(),
            'highlight': style.COLOR_HIGHLIGHT.get_html(),
            'inactive_fill': style.COLOR_INACTIVE_FILL.get_html(),
            'inactive_stroke': style.COLOR_INACTIVE_STROKE.get_html(),
            'panel': style.COLOR_PANEL_GREY.get_html(),
            'selection': style.COLOR_SELECTION_GREY.get_html(),
            'text_field': style.COLOR_TEXT_FIELD_GREY.get_html(),
            'toolbar': style.COLOR_TOOLBAR_GREY.get_html(),
            'white': style.COLOR_WHITE.get_html(),
            'studio_canvas': '#f2f2f2',
            'studio_surface': '#ffffff',
            'studio_preview': '#fcfcfc',
            'studio_edge': '#cfcfcf',
            'studio_edge_soft': '#e7e7e7',
            'studio_dark': '#2f2f2f',
            'studio_dark_hover': '#414141',
            'studio_dark_text': '#ffffff',
            'studio_lavender': '#e9e9e9',
            'studio_lavender_soft': '#f7f7f7',
            'studio_lavender_faint': '#d8d8d8',
            'studio_lavender_border': '#9a9a9a',
            'studio_lavender_text': '#202020',
            'studio_cream': '#fff4d8',
            'studio_cream_border': '#ddbd73',
            'studio_cream_text': '#322717',
        }
        css_provider.load_from_data(('''
            .create-ai-panel {
                background-color: %(studio_canvas)s;
            }
            .create-ai-title {
                color: %(black)s;
            }
            .create-ai-subtitle {
                color: %(inactive_stroke)s;
            }
            .create-ai-overlay-button {
                border-radius: 999px;
                border: 1px solid %(studio_edge)s;
                background-image: none;
                background-color: %(studio_surface)s;
                padding: 2px;
                min-width: 0;
                min-height: 0;
            }
            .create-ai-overlay-button:hover {
                background-color: %(studio_lavender_soft)s;
            }
            .create-ai-stage-card {
                background-color: %(studio_surface)s;
                border: 1px solid %(studio_edge)s;
                border-radius: 12px;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.10);
            }
            .create-ai-stage-card-hover {
                background-color: %(studio_lavender_soft)s;
                border: 1px solid %(studio_lavender_border)s;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.14);
            }
            .create-ai-stage-card-hover label {
                color: %(toolbar)s;
            }
            .create-ai-stage-title {
                color: %(toolbar)s;
                font-weight: 700;
            }
            .create-ai-stage-details {
                color: %(toolbar)s;
            }
            .create-ai-stage-footer {
                color: %(black)s;
                font-weight: 700;
            }
            .create-ai-builder-title {
                color: #202020;
                font-weight: 700;
                font-size: 24px;
            }
            .create-ai-builder-subtitle {
                color: #686868;
                font-size: 13px;
            }
            .create-ai-hero-title {
                color: #1c1c1c;
                font-weight: 700;
                font-size: 30px;
            }
            .create-ai-template-caption {
                color: #8a8a8a;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.04em;
            }
            button.create-ai-prompt-chip {
                border-radius: 10px;
                border: 1px solid #e3e3e3;
                background-image: none;
                background-color: #fafafa;
                padding: 3px 10px;
                min-height: 0;
            }
            button.create-ai-prompt-chip label {
                color: #333333;
            }
            button.create-ai-prompt-chip:hover {
                background-color: %(studio_lavender_soft)s;
                border-color: %(studio_lavender_faint)s;
            }
            button.create-ai-prompt-chip-active {
                background-color: %(studio_lavender_soft)s;
                border-color: %(studio_lavender_border)s;
            }
            .create-ai-chip-caption {
                color: #9a9a9a;
                font-size: 9px;
            }
            .create-ai-chip-value {
                color: %(toolbar)s;
                font-size: 11px;
                font-weight: 700;
            }
            .create-ai-chip-caret {
                color: #9a9a9a;
                font-size: 8px;
            }
            .create-ai-prompt-status {
                color: #8a8a8a;
                font-size: 11px;
            }
            popover.create-ai-popover {
                background-color: %(studio_surface)s;
                border: 1px solid %(studio_edge)s;
                border-radius: 10px;
            }
            .create-ai-provider-heading {
                color: #202020;
                font-weight: 700;
                font-size: 13px;
            }
            .create-ai-provider-status {
                color: #7a7a7a;
                font-size: 10px;
            }
            button.create-ai-provider-primary {
                border-radius: 7px;
                border: 1px solid %(studio_dark)s;
                background-image: none;
                background-color: %(studio_dark)s;
                color: %(studio_dark_text)s;
                padding: 7px 12px;
                font-size: 11px;
                font-weight: 700;
            }
            button.create-ai-provider-primary label {
                color: %(studio_dark_text)s;
            }
            button.create-ai-provider-primary:hover {
                background-color: %(studio_dark_hover)s;
                border-color: %(studio_dark_hover)s;
            }
            button.create-ai-template-card {
                border-radius: 12px;
                border: 1px solid %(studio_edge)s;
                background-image: none;
                background-color: %(studio_surface)s;
                color: %(toolbar)s;
                padding: 0;
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
                transition: background-color 120ms ease,
                            border-color 120ms ease,
                            box-shadow 120ms ease;
            }
            button.create-ai-template-card:hover {
                background-color: %(studio_lavender_soft)s;
                border-color: %(studio_lavender_faint)s;
                box-shadow: 0 4px 9px rgba(0, 0, 0, 0.12);
            }
            .create-ai-meta-label {
                color: %(toolbar)s;
                font-weight: 700;
                font-size: 12px;
            }
            .create-ai-meta-note {
                color: #747474;
                font-size: 11px;
            }
            progressbar.create-ai-generation-progress trough {
                min-height: 6px;
                border-radius: 999px;
                border: 0;
                background-color: #ececec;
            }
            progressbar.create-ai-generation-progress progress {
                min-height: 6px;
                border-radius: 999px;
                background-color: %(studio_lavender_border)s;
            }
            .create-ai-generation-stage {
                color: #888;
                font-weight: 400;
                font-size: 11px;
            }
            .create-ai-generation-fun {
                color: #a58324;
                font-size: 11px;
                font-style: italic;
            }
            .create-ai-generation-step {
                color: #aaa;
                font-size: 11px;
                font-weight: 400;
                transition: color 250ms ease-out;
            }
            .create-ai-generation-step-active {
                color: #333;
                font-weight: 600;
            }
            .create-ai-generation-step-desc {
                color: #b8b8b8;
                font-size: 9px;
            }
            .create-ai-generation-step-row {
                padding: 6px 10px;
                border-radius: 8px;
                border: 1px solid transparent;
                transition: background-color 250ms ease-out,
                            border-color 250ms ease-out;
            }
            .create-ai-generation-step-row-active {
                background-color: %(studio_lavender_soft)s;
                border: 1px solid %(studio_lavender_border)s;
            }
            .create-ai-generated-preview {
                border-radius: 8px;
                border: 0;
                background-color: transparent;
                box-shadow: none;
            }
            .create-ai-generated-title {
                color: #202020;
                font-weight: 700;
                font-size: 17px;
            }
            .create-ai-generated-badge {
                border-radius: 999px;
                border: 1px solid %(studio_edge)s;
                background-color: %(studio_lavender_soft)s;
                color: #555555;
                padding: 2px 9px;
                font-size: 10px;
            }
            .create-ai-generated-summary {
                color: #696969;
                font-size: 11px;
            }
            .create-ai-generated-body {
                border-radius: 8px;
                border: 1px solid %(studio_edge_soft)s;
                background-color: %(studio_preview)s;
                padding: 12px;
            }
            .create-ai-generated-kicker {
                color: #6f6f6f;
                font-size: 10px;
                font-weight: 700;
            }
            .create-ai-generated-question {
                color: #202020;
                font-size: 14px;
                font-weight: 700;
            }
            entry.create-ai-generated-entry {
                border-radius: 7px;
                border: 1px solid %(studio_edge)s;
                background-color: %(studio_surface)s;
                padding: 7px 9px;
                font-size: 11px;
            }
            button.create-ai-generated-action {
                border-radius: 7px;
                border: 1px solid %(studio_edge)s;
                background-image: none;
                background-color: %(studio_surface)s;
                color: %(toolbar)s;
                padding: 6px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            button.create-ai-generated-tile {
                border-radius: 7px;
                border: 1px solid %(studio_edge)s;
                background-image: none;
                background-color: %(studio_surface)s;
                color: %(toolbar)s;
                font-weight: 700;
            }
            button.create-ai-generated-tile:checked {
                background-color: %(studio_cream)s;
                border-color: %(studio_cream_border)s;
            }
            .create-ai-generated-canvas {
                border-radius: 8px;
                border: 1px solid %(studio_edge)s;
                background-color: %(studio_surface)s;
            }
            .create-ai-generated-log {
                border-radius: 8px;
                border: 1px solid %(studio_edge)s;
                background-color: %(studio_surface)s;
            }
            button.create-ai-generated-chess-square {
                border-radius: 2px;
                border: 0;
                background-image: none;
                background-color: #eeeeee;
                color: #202020;
                font-weight: 700;
                font-size: 20px;
                padding: 0;
            }
            button.create-ai-generated-chess-dark {
                background-color: #cfcfcf;
            }
            button.create-ai-generated-chess-selected {
                background-color: #f4d06f;
            }
            .create-ai-generated-pill {
                border-radius: 999px;
                border: 1px solid %(studio_edge)s;
                background-color: %(studio_lavender_soft)s;
                color: #5f5f5f;
                padding: 2px 8px;
                font-size: 10px;
            }
            .create-ai-pill-button {
                border-radius: 999px;
                border: 1px solid %(studio_edge)s;
                background-image: none;
                background-color: %(studio_surface)s;
                color: %(toolbar)s;
                padding: 1px 10px;
                min-height: 0;
                font-size: 11px;
            }
            .create-ai-pill-button:hover {
                background-color: %(studio_lavender_soft)s;
                border-color: %(studio_lavender_faint)s;
            }
            .create-ai-pill-active {
                background-color: %(studio_lavender)s;
                color: %(studio_lavender_text)s;
                border-color: %(studio_lavender_border)s;
            }
            .create-ai-pill-active label {
                color: %(studio_lavender_text)s;
            }
            .create-ai-meta-button {
                border-radius: 999px;
                border: 1px solid %(studio_edge)s;
                background-image: none;
                background-color: %(studio_surface)s;
                color: %(toolbar)s;
                padding: 2px 12px;
                font-size: 11px;
            }
            .create-ai-meta-button:checked {
                background-color: %(studio_lavender_soft)s;
                border-color: %(studio_lavender_border)s;
                color: %(studio_lavender_text)s;
            }
            combobox.create-ai-provider-combo button {
                border-radius: 7px;
                border: 1px solid %(studio_edge)s;
                background-image: none;
                background-color: %(studio_surface)s;
                color: %(toolbar)s;
                padding: 7px 10px;
                font-size: 11px;
            }
            entry.create-ai-provider-entry {
                border-radius: 7px;
                border: 1px solid %(studio_edge)s;
                background-color: %(studio_surface)s;
                color: %(black)s;
                padding: 8px 10px;
                font-size: 11px;
            }
            button.create-ai-provider-button {
                border-radius: 7px;
                border: 1px solid %(studio_edge)s;
                background-image: none;
                background-color: %(studio_surface)s;
                color: %(toolbar)s;
                padding: 7px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            button.create-ai-provider-button:hover {
                background-color: %(studio_lavender_soft)s;
                border-color: %(studio_lavender_border)s;
            }
            .create-ai-section-label {
                color: %(inactive_stroke)s;
                font-size: 10px;
                font-weight: 600;
                letter-spacing: 0.06em;
            }
            .create-ai-expander {
                color: %(toolbar)s;
                font-size: 12px;
            }
            .create-ai-option-heading {
                color: %(toolbar)s;
                font-weight: 700;
                font-size: 12px;
            }
            button.create-ai-option-card {
                border-radius: 8px;
                border: 1px solid %(studio_edge)s;
                background-image: none;
                background-color: %(studio_surface)s;
                color: %(toolbar)s;
                padding: 0;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
                transition: background-color 120ms ease,
                            border-color 120ms ease,
                            box-shadow 120ms ease;
            }
            button.create-ai-option-card:hover {
                background-color: %(studio_lavender_soft)s;
                border-color: %(studio_lavender_faint)s;
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.09);
            }
            button.create-ai-option-card-active {
                background-color: %(studio_dark)s;
                border-color: %(studio_dark)s;
                color: %(studio_dark_text)s;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.18);
            }
            button.create-ai-option-card-active:hover {
                background-color: %(studio_dark_hover)s;
                border-color: %(studio_dark_hover)s;
            }
            button.create-ai-option-card-active:hover label {
                color: %(studio_dark_text)s;
            }
            .create-ai-option-title {
                color: %(toolbar)s;
                font-weight: 700;
                font-size: 12px;
            }
            .create-ai-option-detail {
                color: %(inactive_stroke)s;
                font-size: 10px;
            }
            button.create-ai-option-card-active label {
                color: %(studio_dark_text)s;
            }
            .create-ai-prompt-box {
                border-radius: 14px;
                border: 1px solid #e2e2e2;
                background-color: %(studio_surface)s;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04);
            }
            .create-ai-prompt-box-focused {
                border-color: #b8b8b8;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.09), 0 1px 3px rgba(0, 0, 0, 0.05);
            }
            textview.create-ai-textview {
                color: %(black)s;
                background-color: transparent;
                border: 0;
                border-radius: 0;
                font-size: 13px;
            }
            textview.create-ai-textview text {
                color: %(black)s;
                background-color: transparent;
            }
            textview.create-ai-textview:focus {
                border: 0;
                box-shadow: none;
                background-color: transparent;
            }
            .create-ai-prompt-divider {
                background-color: #ebebeb;
                min-height: 1px;
            }
            .create-ai-prompt-actions {
                border-radius: 0 0 13px 13px;
                border: 0;
                background-color: transparent;
            }
            .create-ai-plus {
                border-radius: 999px;
                border: 1px solid #d4d4d4;
                background-image: none;
                background-color: #f5f5f5;
                color: %(studio_lavender_text)s;
                padding: 0 4px;
                min-width: 28px;
                min-height: 28px;
            }
            .create-ai-plus:hover {
                background-color: %(studio_lavender_soft)s;
                border-color: %(studio_lavender_border)s;
            }
            .create-ai-plus label {
                color: %(studio_lavender_text)s;
            }
            .create-ai-send {
                border-radius: 999px;
                border: 1px solid %(toolbar)s;
                background-image: none;
                background-color: %(toolbar)s;
                color: %(white)s;
                padding: 0;
                min-width: 34px;
                min-height: 34px;
            }
            .create-ai-send label {
                color: %(white)s;
            }
            .create-ai-send:hover {
                background-color: %(black)s;
                border-color: %(black)s;
            }
            .create-ai-studio-workspace {
                border-radius: 14px;
                border: 1px solid %(studio_edge)s;
                background-color: %(studio_canvas)s;
            }
            .create-ai-studio-side {
                border-radius: 12px;
                border: 1px solid %(studio_edge)s;
                background-color: %(studio_surface)s;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.07);
            }
            .create-ai-studio-chip {
                border-radius: 12px;
                border: 1px solid %(studio_lavender_border)s;
                background-color: %(studio_lavender)s;
                color: %(studio_lavender_text)s;
                padding: 8px 16px;
                font-weight: 700;
            }
            .create-ai-studio-chip label {
                color: %(studio_lavender_text)s;
            }
            .create-ai-studio-note {
                border-radius: 10px;
                border: 1px solid %(studio_cream_border)s;
                background-color: %(studio_cream)s;
            }
            .create-ai-studio-note-label {
                color: %(toolbar)s;
                font-size: 11px;
            }
            .create-ai-chat-scroll {
                border: 0;
                background-color: transparent;
            }
            .create-ai-chat-heading {
                color: %(toolbar)s;
                font-weight: 700;
                font-size: 12px;
            }
            .create-ai-chat-bubble {
                border-radius: 12px;
                border: 1px solid %(studio_edge)s;
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
            }
            .create-ai-chat-bubble-ai {
                background-color: %(studio_cream)s;
                border-color: %(studio_cream_border)s;
            }
            .create-ai-chat-bubble-user {
                background-color: %(studio_lavender)s;
                border-color: %(studio_lavender_border)s;
            }
            .create-ai-chat-bubble-user label {
                color: %(studio_lavender_text)s;
            }
            .create-ai-chat-text {
                color: %(toolbar)s;
                font-size: 12px;
            }
            .create-ai-chat-status {
                color: #5f5f5f;
                font-size: 11px;
                padding: 2px 4px;
            }
            .create-ai-chat-composer {
                border-radius: 12px;
                border: 1px solid %(studio_edge)s;
                background-color: %(studio_surface)s;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.07);
            }
            entry.create-ai-chat-entry {
                border-radius: 7px;
                border: 1px solid %(studio_edge)s;
                background-color: %(studio_surface)s;
                color: %(toolbar)s;
                padding: 9px;
                font-size: 12px;
            }
            button.create-ai-chat-send {
                border-radius: 7px;
                border: 1px solid %(studio_lavender_border)s;
                background-image: none;
                background-color: %(studio_lavender)s;
                color: %(studio_lavender_text)s;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: 700;
            }
            button.create-ai-chat-send:hover {
                background-color: %(studio_lavender_soft)s;
                border-color: %(studio_lavender_border)s;
                color: %(studio_lavender_text)s;
            }
            button.create-ai-chat-send label {
                color: %(studio_lavender_text)s;
            }
            .create-ai-studio-mini-prompt {
                border-radius: 10px;
                border: 1px solid %(studio_edge)s;
                background-color: %(studio_surface)s;
            }
            entry.create-ai-studio-entry {
                border-radius: 6px;
                border: 1px solid %(studio_edge)s;
                background-color: %(studio_surface)s;
                color: %(inactive_stroke)s;
                font-size: 11px;
            }
            .create-ai-studio-section-title {
                color: %(toolbar)s;
                font-weight: 700;
                font-size: 12px;
            }
            button.create-ai-studio-button {
                border-radius: 999px;
                border: 1px solid %(studio_edge)s;
                background-image: none;
                background-color: %(studio_surface)s;
                color: %(toolbar)s;
                padding: 5px 13px;
                font-size: 11px;
            }
            button.create-ai-studio-button:hover {
                background-color: %(studio_preview)s;
                border-color: %(studio_edge)s;
            }
            button.create-ai-studio-primary {
                border-radius: 999px;
                border: 1px solid %(studio_lavender_border)s;
                background-image: none;
                background-color: %(studio_lavender)s;
                color: %(studio_lavender_text)s;
                padding: 5px 13px;
                font-size: 11px;
                font-weight: 700;
            }
            button.create-ai-studio-primary label {
                color: %(studio_lavender_text)s;
            }
            button.create-ai-studio-tab {
                border-radius: 8px;
                border: 1px solid %(studio_edge)s;
                background-image: none;
                background-color: %(studio_surface)s;
                color: %(toolbar)s;
                padding: 7px 16px;
                font-weight: 700;
                font-size: 11px;
            }
            button.create-ai-studio-tab:hover {
                background-color: %(studio_preview)s;
                border-color: %(studio_edge)s;
            }
            button.create-ai-studio-tab-active {
                background-color: %(studio_dark)s;
                border-color: %(studio_dark)s;
                color: %(studio_dark_text)s;
                box-shadow: 0 2px 3px rgba(0, 0, 0, 0.16);
            }
            button.create-ai-studio-tab-active:hover {
                background-color: %(studio_dark_hover)s;
                border-color: %(studio_dark_hover)s;
                color: %(studio_dark_text)s;
            }
            button.create-ai-studio-tab-active label {
                color: %(studio_dark_text)s;
            }
            button.create-ai-studio-tab-active:hover label {
                color: %(studio_dark_text)s;
            }
            .create-ai-soft-pill {
                border-radius: 999px;
                border: 1px solid %(studio_lavender_border)s;
                background-color: %(studio_lavender)s;
                color: %(studio_lavender_text)s;
                padding: 3px 9px;
                font-size: 10px;
                font-weight: 700;
            }
            .create-ai-soft-pill:hover {
                background-color: %(studio_lavender_soft)s;
                border-color: %(studio_lavender_border)s;
            }
            .create-ai-preview-shell {
                border-radius: 12px;
                border: 1px solid %(studio_edge)s;
                background-color: %(studio_surface)s;
                box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
            }
            .create-ai-preview-frame {
                border-radius: 12px;
                border: 1px solid %(studio_edge)s;
                background-color: %(studio_preview)s;
                box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.75);
            }
            .create-ai-activity-preview {
                background-color: transparent;
            }
            .create-ai-preview-title {
                color: %(toolbar)s;
                font-size: 18px;
                font-weight: 700;
            }
            .create-ai-review-shell {
                border-radius: 12px;
                border: 1px solid %(studio_edge)s;
                background-color: %(studio_surface)s;
                box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
            }
            .create-ai-review-files {
                border-radius: 10px;
                border: 1px solid %(studio_edge)s;
                background-color: %(studio_canvas)s;
            }
            button.create-ai-review-file {
                border-radius: 6px;
                border: 1px solid transparent;
                background-image: none;
                background-color: transparent;
                color: %(toolbar)s;
                padding: 7px 9px;
                font-size: 12px;
                text-shadow: none;
            }
            button.create-ai-review-file:hover {
                background-color: %(studio_preview)s;
                border-color: %(studio_edge)s;
            }
            button.create-ai-review-file-active {
                background-color: %(studio_lavender)s;
                border-color: %(studio_lavender_border)s;
                color: %(studio_lavender_text)s;
                font-weight: 700;
            }
            button.create-ai-review-file-active:hover {
                background-color: %(studio_lavender)s;
                border-color: %(studio_lavender_border)s;
                color: %(studio_lavender_text)s;
            }
            button.create-ai-review-file-active label {
                color: %(studio_lavender_text)s;
            }
            button.create-ai-review-file-active:hover label {
                color: %(studio_lavender_text)s;
            }
            .create-ai-review-code {
                border-radius: 10px;
                border: 1px solid %(studio_edge)s;
                background-color: %(studio_surface)s;
            }
            .create-ai-review-title {
                color: %(toolbar)s;
                font-size: 16px;
                font-weight: 700;
            }
            .create-ai-review-summary {
                color: %(toolbar)s;
                font-size: 12px;
            }
            .create-ai-review-meta {
                color: %(inactive_stroke)s;
                font-size: 11px;
                font-weight: 700;
            }
            .create-ai-code-frame {
                border-radius: 8px;
                border: 1px solid %(studio_edge)s;
                background-color: %(studio_surface)s;
            }
            .create-ai-code-text {
                color: %(black)s;
                font-family: monospace;
                font-size: 13px;
            }
            .create-ai-versions-shell {
                border-radius: 12px;
                border: 1px solid %(studio_edge)s;
                background-color: %(studio_surface)s;
                box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
            }
            .create-ai-version-history {
                border-radius: 10px;
                border: 1px solid %(studio_edge)s;
                background-color: %(studio_canvas)s;
            }
            .create-ai-version-heading {
                color: %(toolbar)s;
                font-size: 11px;
                font-weight: 700;
            }
            .create-ai-version-card {
                border-radius: 10px;
                border: 1px solid %(studio_edge)s;
                background-color: %(studio_surface)s;
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
            }
            .create-ai-version-card-active {
                border-color: %(studio_lavender_border)s;
                background-color: %(studio_lavender_soft)s;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
            }
            .create-ai-version-chip {
                border-radius: 999px;
                border: 1px solid %(studio_lavender_border)s;
                background-color: %(studio_lavender)s;
                color: %(studio_lavender_text)s;
                padding: 3px 8px;
                font-size: 10px;
                font-weight: 700;
            }
            .create-ai-version-date {
                color: %(inactive_stroke)s;
                font-size: 9px;
                font-weight: 700;
            }
            .create-ai-version-card-action {
                border-radius: 7px;
                border: 1px solid %(studio_lavender_border)s;
                background-color: %(studio_lavender)s;
                color: %(studio_lavender_text)s;
                padding: 5px 10px;
                font-size: 10px;
                font-weight: 700;
            }
            .create-ai-version-card-action label {
                color: %(studio_lavender_text)s;
            }
            button.create-ai-version-switch {
                border-radius: 8px;
                border: 1px solid %(studio_edge)s;
                background-image: none;
                background-color: %(studio_surface)s;
                color: %(toolbar)s;
                padding: 7px 18px;
                font-weight: 700;
                font-size: 11px;
            }
            button.create-ai-version-switch:hover {
                background-color: %(studio_preview)s;
                border-color: %(studio_edge)s;
            }
            button.create-ai-version-switch-active {
                background-color: %(studio_lavender)s;
                border-color: %(studio_lavender_border)s;
                color: %(studio_lavender_text)s;
                box-shadow: 0 2px 3px rgba(0, 0, 0, 0.09);
            }
            button.create-ai-version-switch-active:hover {
                background-color: %(studio_lavender)s;
                border-color: %(studio_lavender_border)s;
                color: %(studio_lavender_text)s;
            }
            button.create-ai-version-switch-active label {
                color: %(studio_lavender_text)s;
            }
            button.create-ai-version-switch-active:hover label {
                color: %(studio_lavender_text)s;
            }
            .create-ai-version-compare-pill {
                border-radius: 999px;
                border: 1px solid %(studio_edge)s;
                background-color: %(studio_surface)s;
                color: %(toolbar)s;
                padding: 4px 12px;
                font-size: 10px;
                font-weight: 700;
            }
            .create-ai-live-edit-panel {
                border-radius: 10px;
                border: 1px solid %(studio_edge)s;
                background-color: %(studio_surface)s;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.07);
            }
            .create-ai-live-toggle-group {
                border-radius: 999px;
                border: 1px solid %(studio_edge)s;
                background-color: %(studio_canvas)s;
            }
            button.create-ai-live-toggle {
                border-radius: 999px;
                border: 1px solid transparent;
                background-image: none;
                background-color: transparent;
                color: %(inactive_stroke)s;
                padding: 3px 12px;
                font-size: 10px;
                font-weight: 700;
                min-height: 0;
            }
            button.create-ai-live-toggle:hover {
                background-color: %(studio_lavender_soft)s;
            }
            button.create-ai-live-toggle-active {
                background-color: %(studio_cream)s;
                border-color: %(studio_cream_border)s;
                color: %(studio_cream_text)s;
            }
            button.create-ai-live-toggle-active label {
                color: %(studio_cream_text)s;
            }
            .create-ai-live-target {
                border-radius: 7px;
                border: 1px solid %(studio_lavender_border)s;
                background-color: %(studio_lavender_soft)s;
                color: %(toolbar)s;
                padding: 11px 12px;
                font-size: 11px;
            }
            entry.create-ai-live-entry {
                border-radius: 7px;
                border: 1px solid %(studio_edge)s;
                background-color: %(studio_surface)s;
                color: %(black)s;
                padding: 12px;
                font-size: 12px;
            }
            button.create-ai-preview-change {
                border-radius: 8px;
                border: 1px solid %(studio_lavender_border)s;
                background-image: none;
                background-color: %(studio_lavender)s;
                color: %(studio_lavender_text)s;
                padding: 12px 18px;
                font-size: 12px;
                font-weight: 700;
            }
            button.create-ai-preview-change:hover {
                background-color: %(studio_lavender_soft)s;
                border-color: %(studio_lavender_border)s;
                color: %(studio_lavender_text)s;
            }
            button.create-ai-preview-change label {
                color: %(studio_lavender_text)s;
            }
            .live-edit-selected {
                border: 2px solid rgba(255, 200, 0, 0.85);
                border-radius: 3px;
            }
            .create-ai-ask-bar {
                border-radius: 999px;
                border: 1px solid #3d3d3d;
                background-color: #2b2b2b;
                box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
            }
            .create-ai-ask-mode-group {
                border-radius: 999px;
                border: 1px solid #4d4d4d;
                background-color: #232323;
            }
            button.create-ai-ask-mode {
                border-radius: 999px;
                border: 1px solid transparent;
                background-image: none;
                background-color: transparent;
                padding: 2px 10px;
                font-size: 10px;
                font-weight: 700;
                min-height: 0;
            }
            button.create-ai-ask-mode label {
                color: #b8b8b8;
            }
            button.create-ai-ask-mode:hover {
                background-color: #3d3d3d;
            }
            button.create-ai-ask-mode-active {
                background-color: %(studio_cream)s;
                border-color: %(studio_cream_border)s;
            }
            button.create-ai-ask-mode-active label {
                color: %(studio_cream_text)s;
            }
            button.create-ai-ask-mode-active:hover {
                background-color: %(studio_cream)s;
            }
            button.create-ai-ask-plus {
                border-radius: 999px;
                border: 0;
                background-image: none;
                background-color: transparent;
                padding: 0;
                min-width: 30px;
                min-height: 30px;
            }
            button.create-ai-ask-plus:hover {
                background-color: #3d3d3d;
            }
            .create-ai-ask-target {
                border-radius: 999px;
                background-color: #3d3d3d;
                color: #d8d8d8;
                padding: 2px 10px;
                font-size: 10px;
            }
            entry.create-ai-ask-entry {
                border: 0;
                border-radius: 0;
                background-color: transparent;
                background-image: none;
                box-shadow: none;
                color: #f0f0f0;
                caret-color: #ffffff;
                font-size: 13px;
            }
            entry.create-ai-ask-entry:focus {
                border: 0;
                box-shadow: none;
            }
            .create-ai-ask-status {
                color: #9a9a9a;
                font-size: 10px;
            }
            button.create-ai-ask-send {
                border-radius: 999px;
                border: 1px solid #4d4d4d;
                background-image: none;
                background-color: #454545;
                padding: 0;
                min-width: 32px;
                min-height: 32px;
            }
            button.create-ai-ask-send:hover {
                background-color: #5a5a5a;
            }
            .create-ai-learning-sidebar {
                border-radius: 12px;
                border: 1px solid %(studio_edge)s;
                background-color: %(studio_surface)s;
                box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
            }
            .create-ai-learning-card {
                border-radius: 10px;
                border: 1px solid %(studio_edge)s;
                background-color: %(studio_surface)s;
            }
            .create-ai-learning-counts {
                border-radius: 999px;
                border: 1px solid %(studio_edge)s;
                background-color: %(studio_surface)s;
                color: %(inactive_stroke)s;
                padding: 3px 9px;
                font-size: 9px;
                font-weight: 700;
            }
            button.create-ai-sidebar-tab {
                border-radius: 8px;
                border: 1px solid %(studio_edge)s;
                background-image: none;
                background-color: %(studio_surface)s;
                color: %(toolbar)s;
                padding: 7px 12px;
                font-weight: 700;
                font-size: 11px;
            }
            button.create-ai-sidebar-tab:hover {
                background-color: %(studio_preview)s;
                border-color: %(studio_edge)s;
            }
            button.create-ai-sidebar-tab-active {
                background-color: %(studio_lavender)s;
                border-color: %(studio_lavender_border)s;
                color: %(studio_lavender_text)s;
                box-shadow: 0 2px 3px rgba(0, 0, 0, 0.09);
            }
            button.create-ai-sidebar-tab-active:hover {
                background-color: %(studio_lavender)s;
                border-color: %(studio_lavender_border)s;
                color: %(studio_lavender_text)s;
            }
            button.create-ai-sidebar-tab-active label {
                color: %(studio_lavender_text)s;
            }
            button.create-ai-sidebar-tab-active:hover label {
                color: %(studio_lavender_text)s;
            }
            .create-ai-challenge-card {
                border-radius: 10px;
                border: 1px solid %(studio_edge_soft)s;
                background-color: %(studio_surface)s;
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
            }
        ''' % colors).encode('utf-8'))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        _CreateAIActivityPanel._css_loaded = True

    def _create_chrome_button(self, icon_name):
        button = Gtk.Button()
        button.set_relief(Gtk.ReliefStyle.NONE)
        button.get_style_context().add_class('create-ai-overlay-button')
        button.set_image(Icon(icon_name=icon_name,
                              pixel_size=style.SMALL_ICON_SIZE))
        return button

    def _create_stage_card(self, title, details, footer, on_click=None):
        column = Gtk.VBox(spacing=style.zoom(16))

        card = Gtk.EventBox()
        card.get_style_context().add_class('create-ai-stage-card')
        card.set_visible_window(True)
        card.set_above_child(True)
        card.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK |
                        Gdk.EventMask.LEAVE_NOTIFY_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK)
        card.connect('enter-notify-event', self.__stage_card_enter_notify_cb)
        card.connect('leave-notify-event', self.__stage_card_leave_notify_cb)
        if on_click is not None:
            card.connect('button-release-event',
                         self.__stage_card_button_release_cb, on_click)
        card.set_size_request(style.zoom(350), style.zoom(285))
        column.pack_start(card, False, False, 0)
        card.show()

        card_box = Gtk.VBox(spacing=style.DEFAULT_PADDING)
        card_box.set_border_width(style.zoom(24))
        card.add(card_box)
        card_box.show()

        title_label = Gtk.Label()
        title_label.get_style_context().add_class('create-ai-stage-title')
        stage_text = style.COLOR_TOOLBAR_GREY.get_html()
        title_label.set_markup(
            '<span size="x-large" weight="bold" foreground="%s">%s</span>'
            % (stage_text, title))
        title_label.set_justify(Gtk.Justification.CENTER)
        card_box.pack_start(title_label, False, False, style.zoom(4))
        title_label.show()

        details_label = Gtk.Label()
        details_label.get_style_context().add_class('create-ai-stage-details')
        details_label.set_markup('<span foreground="%s">%s</span>' %
                                 (stage_text, details))
        details_label.set_justify(Gtk.Justification.CENTER)
        details_label.set_max_width_chars(24)
        details_label.set_line_wrap(True)
        card_box.pack_start(details_label, True, True, 0)
        details_label.show()

        footer_label = Gtk.Label(footer)
        footer_label.get_style_context().add_class('create-ai-stage-footer')
        footer_label.set_justify(Gtk.Justification.CENTER)
        column.pack_start(footer_label, False, False, style.zoom(6))
        footer_label.show()

        column.show()
        return column

    def _reset_prompt(self):
        if self._prompt_text is not None:
            self._set_prompt_placeholder()
        if self._prompt_status_label is not None:
            self._prompt_status_label.set_text('')

    def _set_prompt_placeholder(self):
        if self._prompt_text is None:
            return

        self._prompt_is_placeholder = False
        self._prompt_text.get_buffer().set_text('')
        if self._prompt_char_label is not None:
            self._prompt_char_label.set_text('')

    def _clear_prompt_placeholder(self):
        self._prompt_is_placeholder = False

    def _get_prompt_text(self):
        if self._prompt_text is None:
            return ''

        text_buffer = self._prompt_text.get_buffer()
        start, end = text_buffer.get_bounds()
        return text_buffer.get_text(start, end, True).strip()

    def _set_prompt_text(self, text):
        if self._prompt_text is None:
            return

        self._prompt_is_placeholder = False
        text_buffer = self._prompt_text.get_buffer()
        text_buffer.set_text(text)
        end = text_buffer.get_end_iter()
        text_buffer.place_cursor(end)

    def append_prompt_text(self, text):
        if self._prompt_text is None or not text:
            return

        current = self._get_prompt_text()
        if current:
            text = current + text
        self._set_prompt_text(text)
        self.focus_prompt()
        if self._prompt_status_label is not None:
            self._prompt_status_label.set_text('')

    def focus_prompt(self):
        GObject.idle_add(self.__focus_prompt_text)

    def _set_studio_prompt(self, prompt):
        prompt = prompt.strip()
        if not prompt:
            prompt = _('learning activity')

        if len(prompt) > 36:
            prompt = prompt[:33] + '...'
        for label in self._studio_prompt_labels:
            label.set_text(prompt)

    def _set_live_edit_target(self, target, is_region=False):
        target = target.strip() if isinstance(target, str) else ''
        if not target:
            target = _('activity canvas')
        self._live_edit_target = target
        self._live_edit_target_is_region = is_region
        if self._live_edit_target_label is not None:
            self._live_edit_target_label.set_text(
                _('Preview target: %s') % target)
        if self._ask_bar_target_label is not None:
            self._ask_bar_target_label.set_text(target)
        self._set_live_edit_status(_('Target selected: %s') % target)

    def _attach_live_edit_handlers_to_preview(self, canvas, toolbar):
        """Walk the live preview widget tree and attach click-to-select handlers."""
        self._detach_live_edit_handlers()
        if isinstance(toolbar, Gtk.Widget):
            self._walk_and_attach_live_edit(toolbar, in_toolbar=True)
        if isinstance(canvas, Gtk.Widget):
            self._walk_and_attach_live_edit(canvas, in_toolbar=False)

    def _detach_live_edit_handlers(self):
        if self._live_edit_highlighted is not None:
            try:
                self._live_edit_highlighted.get_style_context().remove_class(
                    'live-edit-selected')
            except Exception:
                pass
            self._live_edit_highlighted = None
        for widget, handler_id in self._live_edit_handler_ids:
            try:
                widget.disconnect(handler_id)
            except Exception:
                pass
        self._live_edit_handler_ids = []
        self._live_edit_targets = []

    def _walk_and_attach_live_edit(self, widget, in_toolbar=False, depth=0):
        if depth > 12:
            return
        desc = self._describe_widget_for_live_edit(widget, in_toolbar)
        if desc:
            # Leaf/interactive widget — attach handler and stop recursing
            self._live_edit_targets.append((widget, desc))
            try:
                widget.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
                hid = widget.connect(
                    'button-press-event',
                    self.__live_edit_widget_press_cb,
                    desc,
                )
                self._live_edit_handler_ids.append((widget, hid))
            except Exception:
                pass
            return  # Don't recurse into interactive widget's internal children
        # Container widget — recurse into children
        if isinstance(widget, Gtk.Toolbar):
            for i in range(widget.get_n_items()):
                item = widget.get_nth_item(i)
                if item is not None:
                    self._walk_and_attach_live_edit(item, True, depth + 1)
        elif isinstance(widget, Gtk.ToolItem):
            child = widget.get_child()
            if child is not None:
                self._walk_and_attach_live_edit(child, True, depth + 1)
        elif isinstance(widget, Gtk.Notebook):
            for i in range(widget.get_n_pages()):
                page = widget.get_nth_page(i)
                if page is not None:
                    self._walk_and_attach_live_edit(page, False, depth + 1)
        elif isinstance(widget, Gtk.Stack):
            visible = widget.get_visible_child()
            if visible is not None:
                self._walk_and_attach_live_edit(visible, False, depth + 1)
        elif hasattr(widget, 'get_children'):
            try:
                children = widget.get_children()
            except Exception:
                return
            for child in children:
                self._walk_and_attach_live_edit(child, in_toolbar, depth + 1)

    def _describe_widget_for_live_edit(self, widget, in_toolbar):
        """Return a human-readable target name for a widget, or None to skip."""
        if isinstance(widget, Gtk.DrawingArea):
            return _('drawing canvas')
        if isinstance(widget, Gtk.ToolButton):
            tip = (widget.get_tooltip_text() or '').strip()
            lbl = (widget.get_label() or '').strip()
            name = tip or lbl
            return (_('toolbar: %s') % name) if name else _('toolbar button')
        if isinstance(widget, Gtk.SpinButton):
            return _('number input')
        if isinstance(widget, Gtk.Button):
            lbl = (widget.get_label() or '').strip()
            tip = (widget.get_tooltip_text() or '').strip()
            name = lbl or tip
            if name:
                return ((_('toolbar button: %s') % name)
                        if in_toolbar
                        else (_('button: %s') % name[:40]))
            return _('toolbar button') if in_toolbar else _('button')
        if isinstance(widget, Gtk.Entry):
            ph = (widget.get_placeholder_text() or '').strip()
            return (_('input: %s') % ph[:40]) if ph else _('text input')
        if isinstance(widget, Gtk.TextView):
            return _('text area')
        if isinstance(widget, Gtk.Scale):
            return _('slider')
        if isinstance(widget, Gtk.Label):
            text = (widget.get_text() or '').strip()
            if text and not text.startswith('<') and len(text) > 2:
                return _('label: %s') % text[:30]
            return None
        if isinstance(widget, (Gtk.Toolbar, Gtk.ToolbarBox)):
            return _('activity toolbar')
        if isinstance(widget, Gtk.Grid):
            return _('grid')
        return None

    def __live_edit_widget_press_cb(self, widget, event, description):
        if not self._live_edit_enabled:
            return False
        # Mark this press as handled so the outer shell's generic
        # 'activity canvas' handler does not overwrite the target, but
        # still return False so the activity itself reacts to the click.
        self._live_edit_press_handled = True
        GObject.idle_add(self.__clear_live_edit_press_flag)
        self._set_live_edit_target(description)
        self._highlight_live_edit_widget(widget)
        return False

    def _highlight_live_edit_widget(self, widget):
        if self._live_edit_highlighted is not None:
            try:
                self._live_edit_highlighted.get_style_context().remove_class(
                    'live-edit-selected')
            except Exception:
                pass
        self._live_edit_highlighted = widget
        if widget is None:
            return
        try:
            widget.get_style_context().add_class('live-edit-selected')
        except Exception:
            pass

    def _focus_live_edit_entry(self):
        if self._preview_is_fullscreen and self._ask_bar_entry is not None:
            self._ask_bar_entry.grab_focus()
        elif self._live_edit_entry is not None:
            self._live_edit_entry.grab_focus()

    def __preview_shell_press_cb(self, shell, event):
        if not self._live_edit_enabled or event.button != 1:
            return False
        self._select_start = (event.x, event.y)
        self._select_rect = None
        shell.queue_draw()
        return True

    def __preview_shell_motion_cb(self, shell, event):
        if self._select_start is None:
            return False
        x0, y0 = self._select_start
        self._select_rect = (min(x0, event.x), min(y0, event.y),
                             abs(event.x - x0), abs(event.y - y0))
        shell.queue_draw()
        return True

    def __preview_shell_release_cb(self, shell, event):
        if self._select_start is None:
            return False
        self._select_start = None
        rect = self._select_rect
        if rect is None or (rect[2] < 8 and rect[3] < 8):
            # A plain click: target the widget under the pointer.
            self._select_rect = None
            target = self._pick_live_edit_target_at(shell, event.x, event.y)
            self._set_live_edit_target(target or _('activity canvas'))
        else:
            # A drag: target the marked region, described in percentages
            # of the preview so refinements know where to look.
            self._highlight_live_edit_widget(None)
            alloc = shell.get_allocation()
            width = max(alloc.width, 1)
            height = max(alloc.height, 1)
            x, y, w, h = rect
            self._set_live_edit_target(
                _('area %(x)d%%, %(y)d%% • %(w)d%% × %(h)d%%') % {
                    'x': int(round(x * 100.0 / width)),
                    'y': int(round(y * 100.0 / height)),
                    'w': int(round(w * 100.0 / width)),
                    'h': int(round(h * 100.0 / height)),
                }, is_region=True)
        shell.queue_draw()
        self._focus_live_edit_entry()
        return True

    def __preview_shell_draw_after_cb(self, shell, cr):
        rect = self._select_rect
        if rect is None or not self._live_edit_enabled:
            return False
        x, y, w, h = rect
        cr.set_source_rgba(1.0, 0.78, 0.0, 0.14)
        cr.rectangle(x, y, w, h)
        cr.fill()
        cr.set_source_rgba(1.0, 0.78, 0.0, 0.9)
        cr.set_line_width(2)
        cr.rectangle(x, y, w, h)
        cr.stroke()
        return False

    def _pick_live_edit_target_at(self, shell, x, y):
        best_desc = None
        best_widget = None
        best_area = None
        for widget, desc in self._live_edit_targets:
            try:
                if not widget.get_mapped():
                    continue
                pos = widget.translate_coordinates(shell, 0, 0)
                if not pos:
                    continue
                wx, wy = pos
                alloc = widget.get_allocation()
            except Exception:
                continue
            if not (wx <= x <= wx + alloc.width and
                    wy <= y <= wy + alloc.height):
                continue
            area = alloc.width * alloc.height
            if best_area is None or area < best_area:
                best_desc = desc
                best_widget = widget
                best_area = area
        if best_widget is not None:
            self._highlight_live_edit_widget(best_widget)
        return best_desc

    def __clear_live_edit_press_flag(self):
        self._live_edit_press_handled = False
        return False

    def __preview_target_button_press_event_cb(self, widget, event, target):
        if self._live_edit_press_handled:
            return False
        if self._live_edit_enabled:
            self._set_live_edit_target(target)
        return False

    def _update_planner_hint(self):
        if self._planner_hint is None:
            return

        provider = self._get_provider_label(
            self._selected_options['provider'])
        self._planner_hint.set_text(
            _('Provider: %s. Generated code is still checked before it '
              'becomes an activity.') % provider)

    def _update_provider_controls(self):
        if self._provider_key_entry is None:
            return

        provider_name = self._selected_options['provider']
        cloud_provider = provider_name in (
            'freemodel', 'openrouter', 'gemini', 'openai', 'deepseek',
            'qwen', 'moonshot', 'opencode', 'opencode-go', 'claude')

        self._provider_key_entry.set_sensitive(cloud_provider)
        self._provider_paste_button.set_sensitive(cloud_provider)
        self._provider_remove_button.set_sensitive(False)

        if self._provider_model_switch_row is not None:
            if provider_name == 'opencode-go':
                self._provider_model_switch_row.show()
            else:
                self._provider_model_switch_row.hide()

        if not cloud_provider:
            self._provider_key_entry.set_visibility(False)

        if provider_name == 'default':
            self._provider_status_label.set_text(
                _('Automatic uses the last saved provider for RAG generation. '
                  'Save an API key before generating.'))
            return
        if provider_name == 'local-template':
            self._provider_status_label.set_text(
                _('Local templates work offline and do not require an API '
                  'key.'))
            return

        from jarabe.model.aodservice import get_service

        try:
            status = get_service().provider_credential_status(provider_name)
        except Exception as error:
            logging.exception('Could not read saved provider settings')
            self._provider_status_label.set_text(str(error))
            return
        self._provider_model_entry.set_text(status['model'])
        self._provider_endpoint_entry.set_text(status['endpoint'])
        self._provider_remove_button.set_sensitive(
            cloud_provider and status['has_api_key'])

        if provider_name == 'ollama':
            self._provider_status_label.set_text(
                _('Ollama runs locally. Model and endpoint preferences are '
                  'saved in the private Sugar profile.'))
        elif status['storage'] == 'keyring':
            self._provider_status_label.set_text(
                _('API key saved in the system keyring. Enter a new key only '
                  'to replace it.'))
        elif status['storage'] == 'profile-file':
            self._provider_status_label.set_text(
                _('API key saved in the private Sugar profile file with '
                  'owner-only permissions.'))
        else:
            self._provider_status_label.set_text(
                _('Enter an API key. It stays masked and is never added to '
                  'the generated activity.'))

    def _configure_selected_provider(self, persist=True):
        provider_name = self._selected_options['provider']
        if provider_name == 'default':
            self._provider_status_label.set_text(
                _('Automatic provider selection is ready.'))
            return True
        if provider_name == 'local-template':
            self._provider_status_label.set_text(
                _('Local template generation is ready.'))
            return True

        from jarabe.model.aodcredentials import CredentialStoreError
        from jarabe.model.aodllm import ProviderError
        from jarabe.model.aodservice import get_service

        api_key = self._provider_key_entry.get_text().strip()
        model = self._provider_model_entry.get_text().strip()
        endpoint = self._provider_endpoint_entry.get_text().strip()
        try:
            provider = get_service().configure_provider(
                provider_name,
                api_key=api_key or None,
                model=model or None,
                endpoint=endpoint or None,
                persist=persist,
            )
        except (CredentialStoreError, ProviderError,
                TypeError, ValueError) as error:
            self._provider_status_label.set_text(str(error))
            if self._prompt_status_label is not None:
                self._prompt_status_label.set_text(_('Provider setup needed'))
            return False

        self._provider_key_entry.set_text('')
        self._update_provider_controls()
        self._provider_status_label.set_text(
            _('%s is ready with model %s. The API key is not shown.')
            % (provider.label, provider.model))
        return provider

    def _start_provider_test(self, provider):
        if self._provider_test_running:
            self._provider_status_label.set_text(
                _('Model test already running.'))
            return

        self._provider_test_running = True
        self._provider_status_label.set_text(
            _('Testing %s / %s...') % (provider.label, provider.model))
        if self._prompt_status_label is not None:
            self._prompt_status_label.set_text(_('Testing model'))

        worker = threading.Thread(
            target=self._provider_test_worker,
            args=(provider,),
        )
        worker.daemon = True
        worker.start()

    def _provider_test_worker(self, provider):
        try:
            response = provider.generate_plan(
                'Return exactly one JSON object and no Markdown. '
                'Use this schema: {"ok": true, "message": "ready"}.',
                'Reply with {"ok": true, "message": "ready"} if this model '
                'can answer Sugar Activity on Demand requests.',
                timeout=60,
            )
            if not isinstance(response, dict):
                raise ValueError('Model test did not return JSON.')
            if not response.get('ok', True):
                raise ValueError(
                    response.get('message') or
                    'Model test returned ok=false.'
                )
            message = response.get('message') or 'ready'
            GObject.idle_add(
                self._provider_test_finished_cb,
                True,
                provider.label,
                provider.model,
                message,
            )
        except Exception as error:
            GObject.idle_add(
                self._provider_test_finished_cb,
                False,
                provider.label,
                provider.model,
                self._redact_provider_error_text(error, provider),
            )

    def _provider_test_finished_cb(self, passed, label, model, message):
        self._provider_test_running = False
        if self._generation_job_id is not None:
            return False
        if passed:
            self._provider_status_label.set_text(
                _('Model test passed: %s / %s answered.') %
                (label, model))
            if self._prompt_status_label is not None:
                self._prompt_status_label.set_text(_('Model ready'))
        else:
            self._provider_status_label.set_text(
                _('Model test failed: %s') % message)
            if self._prompt_status_label is not None:
                self._prompt_status_label.set_text(_('Model failed'))
        return False

    def _redact_provider_error_text(self, error, provider):
        text = str(error)
        api_key = getattr(provider, '_api_key', '')
        if api_key:
            text = text.replace(api_key, '[redacted]')
        return text

    def __provider_model_switch_clicked_cb(self, button, model):
        if self._provider_model_entry is None:
            return

        self._provider_model_entry.set_text(model)
        if self._provider_status_label is not None:
            self._provider_status_label.set_text(
                _('Model set to %s. Press Save & use to keep it.') % model)

    def _paste_provider_key_from_clipboard(self):
        if self._provider_key_entry is None:
            return False
        if not self._provider_key_entry.get_sensitive():
            if self._provider_status_label is not None:
                self._provider_status_label.set_text(
                    _('Choose a cloud provider before pasting a key.'))
            return True

        self._provider_key_entry.grab_focus()
        if self._provider_status_label is not None:
            self._provider_status_label.set_text(
                _('Reading clipboard...'))
        Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).request_text(
            self.__provider_clipboard_text_received_cb,
            False,
        )
        return True

    def __provider_clipboard_text_received_cb(self, clipboard, text,
                                              tried_primary):
        if not text:
            if not tried_primary:
                Gtk.Clipboard.get(Gdk.SELECTION_PRIMARY).request_text(
                    self.__provider_clipboard_text_received_cb,
                    True,
                )
                return
            previous_text = ''
            if self._provider_key_entry is not None:
                previous_text = self._provider_key_entry.get_text()
                self._provider_key_entry.paste_clipboard()
            GObject.timeout_add(
                180,
                self.__provider_key_default_paste_checked_cb,
                previous_text,
            )
            if self._provider_status_label is not None:
                self._provider_status_label.set_text(
                    _('Trying the system paste shortcut...'))
            return

        text = self._clean_pasted_api_key(text)
        if not text:
            if self._provider_status_label is not None:
                self._provider_status_label.set_text(
                    _('Clipboard does not contain an API key.'))
            return

        self._set_provider_key_text(text)
        if self._provider_status_label is not None:
            self._provider_status_label.set_text(
                _('API key pasted. Send your prompt to start generation.'))

    def _clean_pasted_api_key(self, text):
        text = text.strip()
        if not text:
            return ''

        lines = [
            line.strip() for line in text.splitlines()
            if line.strip()
        ]
        if len(lines) == 1:
            text = lines[0]

        if '=' in text and not any(char.isspace() for char in text):
            text = text.split('=', 1)[1]

        return text.strip().strip('\'"')

    def _set_provider_key_text(self, text):
        entry = self._provider_key_entry
        if entry is None:
            return
        entry.set_text(text)
        entry.set_position(len(text))

    def __provider_key_entry_paste_clipboard_cb(self, entry):
        if self._provider_status_label is not None:
            self._provider_status_label.set_text(_('Pasting API key...'))
        GObject.idle_add(self.__provider_key_entry_paste_finished_cb)

    def __provider_key_entry_paste_finished_cb(self):
        if self._provider_key_entry is None:
            return False

        text = self._provider_key_entry.get_text()
        cleaned = self._clean_pasted_api_key(text)
        if cleaned and cleaned != text:
            self._set_provider_key_text(cleaned)

        if cleaned and self._provider_status_label is not None:
            self._provider_status_label.set_text(
                _('API key pasted. Press Save & use or send your prompt.'))
        return False

    def __provider_key_default_paste_checked_cb(self, previous_text):
        if self._provider_key_entry is None:
            return False

        text = self._provider_key_entry.get_text()
        if text and text != previous_text:
            if self._provider_status_label is not None:
                self._provider_status_label.set_text(
                    _('API key pasted. Send your prompt to start generation.'))
            return False

        external_text = self._read_external_clipboard_text()
        if external_text:
            self._set_provider_key_text(external_text)
            if self._provider_status_label is not None:
                self._provider_status_label.set_text(
                    _('API key pasted from the desktop clipboard. Send your '
                      'prompt to start generation.'))
            return False

        if self._provider_status_label is not None:
            self._provider_status_label.set_text(
                _('Paste did not add text. Copy the key again, then press '
                  'Ctrl+V or the Paste button.'))
        return False

    def _read_external_clipboard_text(self):
        display_names = []
        requested = os.environ.get('SUGAR_AOD_CLIPBOARD_DISPLAY', '')
        if requested:
            display_names.append(requested)
        for display_name in (':1', ':0'):
            if display_name not in display_names and \
                    display_name != os.environ.get('DISPLAY'):
                display_names.append(display_name)

        for display_name in display_names:
            for xauthority in self._get_external_xauthority_paths():
                text = self._read_external_clipboard_with_helper(
                    display_name, xauthority)
                if text:
                    return text
        return ''

    def _read_external_prompt_clipboard_text(self):
        display_names = []
        requested = os.environ.get('SUGAR_AOD_CLIPBOARD_DISPLAY', '')
        if requested:
            display_names.append(requested)
        for display_name in (':1', ':0'):
            if display_name not in display_names and \
                    display_name != os.environ.get('DISPLAY'):
                display_names.append(display_name)

        for display_name in display_names:
            for xauthority in self._get_external_xauthority_paths():
                text = self._read_external_clipboard_with_helper(
                    display_name, xauthority, clean=False)
                if text:
                    return text
        return ''

    def _read_external_clipboard_with_helper(self, display_name, xauthority,
                                             clean=True):
        script = '''
import sys

import gi
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gdk, Gtk

clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
if clipboard.wait_is_text_available():
    sys.stdout.write(clipboard.wait_for_text() or '')
'''
        env = {
            'DISPLAY': display_name,
            'GDK_BACKEND': 'x11',
            'HOME': os.path.expanduser('~'),
            'NO_AT_BRIDGE': '1',
            'PATH': '/usr/bin:/bin',
        }
        runtime_dir = os.environ.get('XDG_RUNTIME_DIR')
        if runtime_dir:
            env['XDG_RUNTIME_DIR'] = runtime_dir
        if xauthority:
            env['XAUTHORITY'] = xauthority

        try:
            output = subprocess.check_output(
                ['/usr/bin/python3', '-c', script],
                env=env,
                stderr=subprocess.DEVNULL,
                timeout=2,
            )
        except (OSError, subprocess.SubprocessError):
            logging.debug(
                'Could not read external clipboard with helper from %s',
                display_name,
                exc_info=True,
            )
            return ''

        text = output.decode('utf-8', 'replace')
        if clean:
            return self._clean_pasted_api_key(text)
        return text

    def _get_external_xauthority_paths(self):
        paths = []
        requested = os.environ.get('SUGAR_AOD_CLIPBOARD_XAUTHORITY', '')
        if requested:
            paths.append(requested)
        current = os.environ.get('XAUTHORITY', '')
        if current:
            paths.append(current)

        runtime_dir = os.environ.get('XDG_RUNTIME_DIR',
                                     '/run/user/%d' % os.getuid())
        mutter_paths = glob.glob(os.path.join(runtime_dir,
                                              '.mutter-Xwaylandauth.*'))
        mutter_paths.sort(
            key=lambda path: os.path.getmtime(path)
            if os.path.exists(path) else 0,
            reverse=True)
        paths.extend(mutter_paths)
        paths.append(os.path.expanduser('~/.Xauthority'))
        paths.append('')

        seen = set()
        existing_paths = []
        for path in paths:
            if path in seen:
                continue
            seen.add(path)
            if not path or os.path.exists(path):
                existing_paths.append(path)
        return existing_paths

    def _resolve_generation_provider_name(self, service):
        planner = self._selected_options['planner']
        policy = self._selected_options['policy']
        selected = self._selected_options['provider']

        if planner == 'validate' or policy == 'strict':
            return 'local-template'
        if policy == 'local':
            if selected == 'ollama':
                return 'ollama'
            return service.preferred_local_provider_name()
        if selected == 'default':
            preferred = service.preferred_provider_name()
            if preferred == 'local-template':
                return 'default'
            return preferred
        return selected

    def _update_template_hint(self):
        if self._template_hint is None:
            return

        notes = {
            'logic_math': _('Puzzles, patterns, and reasoning — number games, '
                            'sequence finders, logic grids.'),
            'science': _('Experiments and measurement — simulations, data '
                         'collectors, interactive models.'),
            'language': _('Stories and words — writing prompts, word games, '
                          'vocabulary builders, storytelling.'),
            'tools_utils': _('Tools and utilities — calculators, converters, '
                             'organizers, exploration helpers.'),
            'games': _('Play loops and scoring — turn-based games, reflex '
                       'challenges, board games, simulations.'),
            'creation': _('Making and expression — drawing canvases, music '
                          'makers, collage builders, animations.'),
        }
        self._template_hint.set_text(
            notes.get(self._selected_options['template'],
                      self._selected_options['template']))

    def _update_license_hint(self):
        if self._license_hint is None:
            return

        license_info = self._get_selected_license()
        self._license_hint.set_text(
            _('%s. Adds LICENSE, SPDX headers, and bundle metadata. SPDX: %s')
            % (license_info['description'], license_info['spdx']))

    def _refresh_generated_context(self):
        self._update_preview_license_summary()
        if self._review_title_label is not None:
            self._set_review_file(self._current_review_file)

    def _update_preview_license_summary(self):
        if self._preview_empty_note is None:
            return

        license_info = self._get_selected_license()
        self._preview_empty_note.set_text(
            _('Generation uses %s, RAG examples, and the configured model.')
            % license_info['label'])

    def _start_generation_animation(self, message=None):
        if self._generation_animation_hide_id:
            GLib.source_remove(self._generation_animation_hide_id)
            self._generation_animation_hide_id = 0
        self._generation_tick_count = 0
        self._generation_has_fraction = False
        self._show_generation_activity_preview()
        if self._preview_generation_progress is not None:
            self._preview_generation_progress.set_fraction(0.0)
            self._preview_generation_progress.show()
        if self._preview_generation_stage is not None:
            self._preview_generation_stage.set_text(
                message or _('Starting activity generation...'))
            self._preview_generation_stage.show()
        self._set_generation_step_active(0)
        if not self._generation_animation_id:
            self._generation_animation_id = GLib.timeout_add(
                400, self._pulse_generation_progress)

    def _stop_generation_animation(self):
        if self._generation_animation_id:
            GLib.source_remove(self._generation_animation_id)
            self._generation_animation_id = 0
        if self._generation_animation_hide_id:
            GLib.source_remove(self._generation_animation_hide_id)
            self._generation_animation_hide_id = 0
        if self._preview_generation_progress is not None:
            self._preview_generation_progress.hide()
        if self._preview_generation_stage is not None:
            self._preview_generation_stage.hide()
        was_done = self._generation_anim_done
        # Settle the orbit canvas into its calm full ring, then freeze
        # it; the tick callback removes itself once the reference drops.
        canvas = self._preview_generation_canvas
        self._preview_generation_canvas = None
        if canvas is not None and not was_done:
            self._generation_anim_done = True
            canvas.queue_draw()
        self._generation_fun_next = None
        # The staggered entrance may not have finished (or even started,
        # if generation failed within milliseconds) — restore every
        # faded element so nothing is left invisible.
        for child, _unused in self._generation_fade_widgets:
            child.set_opacity(1.0)
        self._generation_fade_widgets = []
        if self._preview_generation_fun is not None:
            self._generation_fun_alpha = 1.0
            self._preview_generation_fun.set_opacity(1.0)
            if not was_done:
                # A playful "building..." quip reads wrong next to a
                # failure or cancel notice.
                self._preview_generation_fun.hide()

    def _generation_fun_messages(self):
        return [
            _('Great ideas take a moment to build...'),
            _('Turning "make X" into a plan learners can touch...'),
            _('Real Sugar activities are lending a hand as examples.'),
            _('Mixing colors, code, and curiosity...'),
            _('Teaching your activity how to play fair...'),
            _('Almost like magic — but it\'s Python!'),
            _('Wiring up buttons for curious fingers...'),
            _('Your idea is becoming something learners can touch.'),
        ]

    def _hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        try:
            return tuple(int(hex_color[i:i + 2], 16) / 255.0
                         for i in (0, 2, 4))
        except (ValueError, IndexError):
            return (0.16, 0.16, 0.16)

    def _generation_color_wheel(self):
        if self._generation_wheel_cache is not None:
            return self._generation_wheel_cache
        try:
            from sugar3.graphics.xocolor import colors as xo_colors
        except Exception:
            xo_colors = [['#282828', '#B8B8B8']]
        wheel = []
        for stroke, fill in xo_colors:
            red, green, blue = self._hex_to_rgb(fill)
            # Near-white fills make the XO body vanish on the light
            # preview panel, so leave them out of the drift.
            if 0.299 * red + 0.587 * green + 0.114 * blue > 0.86:
                continue
            wheel.append((stroke, fill))
        if not wheel:
            wheel = [('#282828', '#B8B8B8')]
        self._generation_wheel_cache = wheel
        return wheel

    def _xo_pulse_color(self, index):
        wheel = self._generation_color_wheel()
        stroke, fill = wheel[index % len(wheel)]
        return stroke, fill

    def _generation_wheel_rgb(self, phase):
        """Smoothly interpolated (stroke, fill) rgb along the XO wheel."""
        wheel = self._generation_color_wheel()
        index = int(phase)
        frac = phase - index
        stroke_a, fill_a = wheel[index % len(wheel)]
        stroke_b, fill_b = wheel[(index + 1) % len(wheel)]

        def _lerp(hex_a, hex_b):
            rgb_a = self._hex_to_rgb(hex_a)
            rgb_b = self._hex_to_rgb(hex_b)
            return tuple(a + (b - a) * frac for a, b in zip(rgb_a, rgb_b))

        return _lerp(stroke_a, stroke_b), _lerp(fill_a, fill_b)

    def _generation_canvas_tick(self, widget, frame_clock):
        if widget is not self._preview_generation_canvas:
            return GLib.SOURCE_REMOVE
        now = frame_clock.get_frame_time()
        if self._generation_anim_start_us is None:
            self._generation_anim_start_us = now
        previous = self._generation_anim_t
        self._generation_anim_t = \
            (now - self._generation_anim_start_us) / 1000000.0
        dt = max(0.0, self._generation_anim_t - previous)

        # Glide the displayed progress toward the backend's fraction so
        # the ring never jumps.
        if self._generation_target_fraction is not None:
            self._generation_fraction_mix = min(
                1.0, self._generation_fraction_mix + dt * 2.0)
            gap = self._generation_target_fraction - \
                self._generation_shown_fraction
            self._generation_shown_fraction += gap * min(1.0, dt * 2.5)

        fun = self._preview_generation_fun
        if fun is not None:
            # Crossfade the playful messages instead of snapping them.
            if self._generation_fun_next is not None:
                self._generation_fun_alpha = max(
                    0.0, self._generation_fun_alpha - dt * 4.0)
                if self._generation_fun_alpha == 0.0:
                    fun.set_text(self._generation_fun_next)
                    self._generation_fun_next = None
            elif self._generation_fun_alpha < 1.0:
                self._generation_fun_alpha = min(
                    1.0, self._generation_fun_alpha + dt * 4.0)

        # Staggered entrance fades; afterwards opacities hold steady
        # (GTK ignores set_opacity calls with an unchanged value).
        for child, delay in self._generation_fade_widgets:
            progress = (self._generation_anim_t - delay) / 0.5
            progress = max(0.0, min(1.0, progress))
            eased = progress * progress * (3.0 - 2.0 * progress)
            if child is fun:
                eased *= self._generation_fun_alpha
            child.set_opacity(eased)

        widget.queue_draw()
        return GLib.SOURCE_CONTINUE

    def _draw_generation_canvas(self, widget, cr):
        alloc = widget.get_allocation()
        center_x = alloc.width / 2.0
        center_y = alloc.height / 2.0
        t = self._generation_anim_t
        orbit_radius = style.zoom(78)

        # Everything eases in together over the first beat.
        entrance = max(0.0, min(1.0, t / 0.7))
        entrance = entrance * entrance * (3.0 - 2.0 * entrance)

        if self._generation_anim_done and \
                self._generation_final_rgb is not None:
            stroke_rgb, fill_rgb = self._generation_final_rgb
        else:
            stroke_rgb, fill_rgb = self._generation_wheel_rgb(t / 0.8)

        # A soft halo breathing behind the XO, like a slow heartbeat.
        breath = 0.5 + 0.5 * math.sin(t * 2.0 * math.pi / 3.2)
        if self._generation_anim_done:
            breath = 0.75
        halo_radius = style.zoom(58) + style.zoom(10) * breath
        halo = cairo.RadialGradient(center_x, center_y, style.zoom(20),
                                    center_x, center_y, halo_radius)
        halo_alpha = (0.10 + 0.10 * breath) * entrance
        halo.add_color_stop_rgba(0.0, *fill_rgb, halo_alpha)
        halo.add_color_stop_rgba(1.0, *fill_rgb, 0.0)
        cr.set_source(halo)
        cr.arc(center_x, center_y, halo_radius, 0, 2.0 * math.pi)
        cr.fill()

        if self._generation_anim_done:
            # Settled: a calm, complete ring in the learner's colors,
            # marked once by a soft outward ripple.
            cr.set_source_rgba(*stroke_rgb, 0.45)
            cr.set_line_width(style.zoom(3))
            cr.arc(center_x, center_y, orbit_radius, 0, 2.0 * math.pi)
            cr.stroke()
            if self._generation_done_at is not None:
                ripple = (t - self._generation_done_at) / 0.7
                if 0.0 <= ripple < 1.0:
                    cr.set_source_rgba(*stroke_rgb, 0.30 * (1.0 - ripple))
                    cr.set_line_width(max(1, style.zoom(2)))
                    cr.arc(center_x, center_y,
                           orbit_radius + style.zoom(18) * ripple,
                           0, 2.0 * math.pi)
                    cr.stroke()
            return False

        # Faint guide ring the comet travels on.
        cr.set_line_width(style.zoom(2))
        cr.set_source_rgba(*stroke_rgb, 0.10 * entrance)
        cr.arc(center_x, center_y, orbit_radius, 0, 2.0 * math.pi)
        cr.stroke()

        # Tiny seeds drifting the other way, barely there.
        seed_angle = -t * 2.0 * math.pi / 14.0
        for i in range(3):
            angle = seed_angle + i * 2.0 * math.pi / 3.0
            cr.set_source_rgba(*stroke_rgb, 0.16 * entrance)
            cr.arc(center_x + orbit_radius * math.cos(angle),
                   center_y + orbit_radius * math.sin(angle),
                   max(2, style.zoom(2)), 0, 2.0 * math.pi)
            cr.fill()

        mix = self._generation_fraction_mix
        free_alpha = (1.0 - mix) * entrance
        if free_alpha > 0.01:
            # While progress is unknown the comet roams freely; a touch
            # of sinusoidal drift keeps the motion organic.
            head_angle = t * 2.0 * math.pi / 4.5 - math.pi / 2.0 + \
                0.15 * math.sin(t * 0.7)
            self._draw_generation_comet(
                cr, center_x, center_y, orbit_radius, head_angle,
                stroke_rgb, fill_rgb, free_alpha)

        if mix > 0.01 and self._generation_shown_fraction > 0.002:
            # Real progress: the ring closes as the work completes,
            # with the comet as the pen drawing it.
            arc_alpha = mix * entrance
            start = -math.pi / 2.0
            end = start + \
                2.0 * math.pi * self._generation_shown_fraction
            cr.set_source_rgba(*stroke_rgb, 0.40 * arc_alpha)
            cr.set_line_width(style.zoom(3))
            cr.arc(center_x, center_y, orbit_radius, start, end)
            cr.stroke()
            self._draw_generation_comet_head(
                cr, center_x, center_y, orbit_radius, end,
                stroke_rgb, fill_rgb, arc_alpha)
        return False

    def _draw_generation_comet(self, cr, center_x, center_y, radius,
                               head_angle, stroke_rgb, fill_rgb, alpha):
        tail_span = math.radians(110)
        segments = 22
        cr.set_line_width(style.zoom(3))
        for i in range(segments):
            frac0 = i / float(segments)
            frac1 = (i + 1) / float(segments)
            cr.set_source_rgba(
                *stroke_rgb, 0.5 * alpha * (1.0 - frac0) ** 1.7)
            cr.arc(center_x, center_y, radius,
                   head_angle - tail_span * frac1,
                   head_angle - tail_span * frac0)
            cr.stroke()
        self._draw_generation_comet_head(
            cr, center_x, center_y, radius, head_angle,
            stroke_rgb, fill_rgb, alpha)

    def _draw_generation_comet_head(self, cr, center_x, center_y, radius,
                                    angle, stroke_rgb, fill_rgb, alpha):
        head_x = center_x + radius * math.cos(angle)
        head_y = center_y + radius * math.sin(angle)
        glow = cairo.RadialGradient(head_x, head_y, 0,
                                    head_x, head_y, style.zoom(9))
        glow.add_color_stop_rgba(0.0, *stroke_rgb, 0.8 * alpha)
        glow.add_color_stop_rgba(1.0, *stroke_rgb, 0.0)
        cr.set_source(glow)
        cr.arc(head_x, head_y, style.zoom(9), 0, 2.0 * math.pi)
        cr.fill()
        cr.set_source_rgba(*fill_rgb, 0.9 * alpha)
        cr.arc(head_x, head_y, max(3, style.zoom(3)), 0, 2.0 * math.pi)
        cr.fill()

    def _pulse_generation_progress(self):
        self._generation_tick_count += 1
        if self._preview_generation_progress is not None and \
                not self._generation_has_fraction:
            self._preview_generation_progress.pulse()

        xo_icon = self._preview_generation_xo
        if xo_icon is not None and not self._generation_anim_done and \
                self._generation_tick_count % 2 == 0:
            # Drift through the XO color wheel one neighbor at a time,
            # like Sugar's boot pulse — slow enough to feel calm.
            stroke, fill = self._xo_pulse_color(
                self._generation_tick_count // 2)
            try:
                xo_icon.props.stroke_color = stroke
                xo_icon.props.fill_color = fill
            except Exception:
                pass

        fun = self._preview_generation_fun
        if fun is not None and self._generation_tick_count % 9 == 0:
            messages = self._generation_fun_messages()
            text = messages[
                (self._generation_tick_count // 9) % len(messages)]
            if self._preview_generation_canvas is not None:
                self._generation_fun_next = text
            else:
                fun.set_text(text)
        return True

    def _update_generation_animation(self, stage, fraction, message):
        if fraction > 0:
            self._generation_has_fraction = True
            self._generation_target_fraction = max(
                0.0, min(0.98, float(fraction)))
        if self._preview_generation_progress is not None:
            self._preview_generation_progress.show()
            if fraction > 0:
                self._preview_generation_progress.set_fraction(
                    max(0.0, min(0.98, float(fraction))))
        if self._preview_generation_stage is not None:
            self._preview_generation_stage.set_text(message)
            self._preview_generation_stage.show()
        self._set_generation_step_active(
            self._generation_step_index_for_stage(stage))

    def _complete_generation_animation(self, result=None):
        if self._generation_animation_id:
            GLib.source_remove(self._generation_animation_id)
            self._generation_animation_id = 0
        if self._preview_generation_progress is not None:
            self._preview_generation_progress.set_fraction(1.0)
            self._preview_generation_progress.show()
        if self._preview_generation_xo is not None:
            # Settle the pulsing XO on the learner's own colors.
            try:
                from sugar3 import profile
                color = profile.get_color()
                self._preview_generation_xo.props.stroke_color = \
                    color.get_stroke_color()
                self._preview_generation_xo.props.fill_color = \
                    color.get_fill_color()
                self._generation_final_rgb = (
                    self._hex_to_rgb(color.get_stroke_color()),
                    self._hex_to_rgb(color.get_fill_color()))
            except Exception:
                pass
        self._generation_anim_done = True
        self._generation_target_fraction = 1.0
        self._generation_done_at = self._generation_anim_t
        if self._preview_generation_stage is not None:
            self._preview_generation_stage.set_text(
                _('Your activity is ready!'))
            self._preview_generation_stage.show()
        if self._preview_generation_fun is not None:
            self._generation_fun_next = None
            self._generation_fun_alpha = 1.0
            self._preview_generation_fun.set_opacity(1.0)
            self._preview_generation_fun.set_text(_('Have fun exploring!'))
        self._set_generation_step_active(4)
        if self._generation_animation_hide_id:
            GLib.source_remove(self._generation_animation_hide_id)
        self._generation_animation_hide_id = GLib.timeout_add(
            700, self._show_generated_activity_preview, result)

    def _show_generated_activity_preview(self, result):
        self._generation_animation_hide_id = 0
        self._stop_generation_animation()
        if result is not None:
            self._render_generated_activity_preview(result)
        return False

    def _render_generated_activity_preview(self, result):
        try:
            if self._render_live_generated_activity_preview(result):
                return
        except Exception:
            logging.exception('Could not embed live activity preview')

        self._clear_activity_preview()

        error_box = Gtk.VBox(spacing=style.zoom(12))
        error_box.set_halign(Gtk.Align.CENTER)
        error_box.set_valign(Gtk.Align.CENTER)
        error_box.set_border_width(style.zoom(30))

        error_icon = Gtk.Label('⚠')
        error_icon.set_markup(
            '<span size="xx-large">⚠</span>')
        error_box.pack_start(error_icon, False, False, 0)

        error_title = Gtk.Label(
            _('Preview could not render this activity'))
        error_title.get_style_context().add_class(
            'create-ai-generated-title')
        error_box.pack_start(error_title, False, False, 0)

        error_note = Gtk.Label(
            _('The generated code has an issue that prevents live '
              'preview. Switch to the Review tab to see the code, '
              'or type a refinement to fix it.'))
        error_note.get_style_context().add_class('create-ai-meta-note')
        error_note.set_line_wrap(True)
        error_note.set_max_width_chars(60)
        error_note.set_justify(Gtk.Justification.CENTER)
        error_box.pack_start(error_note, False, False, 0)

        if self._last_preview_error:
            error_detail = Gtk.Label(self._last_preview_error[:220])
            error_detail.get_style_context().add_class(
                'create-ai-generation-stage')
            error_detail.set_line_wrap(True)
            error_detail.set_max_width_chars(70)
            error_detail.set_justify(Gtk.Justification.CENTER)
            error_box.pack_start(error_detail, False, False, 0)
            try:
                self._append_chat_status(
                    _('Preview issue: %s')
                    % self._last_preview_error[:160])
            except Exception:
                logging.exception('Could not post preview issue to chat')

        self._preview_content_box.pack_start(error_box, True, True, 0)
        error_box.show_all()

    def _render_live_generated_activity_preview(self, result):
        project_path = getattr(result, 'project_path', '')
        if not project_path:
            return False

        try:
            from jarabe.model.aodpreview import render_activity_preview
            preview, canvas, toolbar = render_activity_preview(
                project_path,
                getattr(result.spec, 'name', '') or _('Generated Activity'),
            )
        except Exception as error:
            logging.exception('Could not render live generated activity')
            self._last_preview_error = str(error)
            return False

        if preview is None or not isinstance(canvas, Gtk.Widget):
            logging.error(
                'Live preview failed for %s: %s',
                project_path, canvas)
            self._last_preview_error = str(canvas)
            return False
        self._last_preview_error = ''

        self._clear_activity_preview()

        shell = Gtk.EventBox()
        shell.get_style_context().add_class('create-ai-generated-preview')
        shell.set_hexpand(True)
        shell.set_vexpand(True)
        shell.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                         Gdk.EventMask.BUTTON_RELEASE_MASK |
                         Gdk.EventMask.POINTER_MOTION_MASK |
                         Gdk.EventMask.BUTTON1_MOTION_MASK)
        shell.connect('button-press-event', self.__preview_shell_press_cb)
        shell.connect('motion-notify-event', self.__preview_shell_motion_cb)
        shell.connect('button-release-event', self.__preview_shell_release_cb)
        shell.connect_after('draw', self.__preview_shell_draw_after_cb)
        # With live edit on, the shell's input window sits above the
        # activity so clicks and drags select targets instead of playing.
        shell.set_above_child(self._live_edit_enabled)
        self._preview_shell = shell
        self._select_start = None
        self._select_rect = None

        box = Gtk.VBox(spacing=style.zoom(6))
        box.set_border_width(style.zoom(4))
        box.set_hexpand(True)
        box.set_vexpand(True)
        shell.add(box)

        if isinstance(toolbar, Gtk.Widget):
            self._detach_preview_widget(toolbar)
            toolbar.set_hexpand(True)
            box.pack_start(toolbar, False, False, 0)

        self._detach_preview_widget(canvas)
        canvas.set_hexpand(True)
        canvas.set_vexpand(True)
        box.pack_start(canvas, True, True, 0)

        self._live_preview_canvas = canvas
        self._live_preview_activity = preview
        self._preview_content_box.pack_start(shell, True, True, 0)
        shell.show_all()
        GObject.idle_add(self._refresh_preview_layout)
        # Attach live-edit handlers after the shell is shown so any failure
        # here never blanks the preview.
        try:
            self._attach_live_edit_handlers_to_preview(
                canvas,
                toolbar if isinstance(toolbar, Gtk.Widget) else None,
            )
        except Exception:
            logging.exception('Could not attach live edit handlers to preview')
        return True

    def _detach_preview_widget(self, widget):
        parent = widget.get_parent()
        if parent is not None:
            parent.remove(widget)

    def _create_generated_preview_body(self, result, template):
        plan = result.plan if isinstance(result.plan, dict) else {}
        source = self._get_generated_activity_source(result)
        if self._source_mentions_turn_drawing_canvas(source):
            return self._create_turn_drawing_activity_preview(plan, source)
        if self._source_mentions_paired_canvas(source):
            return self._create_paired_canvas_activity_preview(plan, source)
        if self._source_mentions_canvas(source) and template == 'utility':
            return self._create_canvas_activity_preview(plan, source)
        if template == 'quiz':
            return self._create_quiz_activity_preview(plan)
        if template == 'carrom':
            return self._create_carrom_activity_preview(plan)
        if template == 'chess':
            return self._create_chess_activity_preview(plan)
        if template == 'grid':
            return self._create_grid_activity_preview(plan)
        if template == 'canvas':
            if (self._is_paired_canvas_activity(plan) or
                    self._source_mentions_paired_canvas(source)):
                return self._create_paired_canvas_activity_preview(
                    plan, source)
            return self._create_canvas_activity_preview(plan, source)
        if template == 'narrative':
            return self._create_narrative_activity_preview(plan, result)
        return self._create_utility_activity_preview(plan, result)

    def _create_quiz_activity_preview(self, plan):
        box = Gtk.VBox(spacing=style.zoom(8))
        box.get_style_context().add_class('create-ai-generated-body')

        questions = plan.get('questions') or []
        first = questions[0] if questions else {}
        question_text = first.get(
            'question', _('What is one idea you can explain?'))

        label = Gtk.Label(_('Question 1'))
        label.get_style_context().add_class('create-ai-generated-kicker')
        label.set_xalign(0)
        box.pack_start(label, False, False, 0)

        question = Gtk.Label(question_text)
        question.get_style_context().add_class('create-ai-generated-question')
        question.set_xalign(0)
        question.set_line_wrap(True)
        box.pack_start(question, True, True, 0)

        entry = Gtk.Entry()
        entry.set_placeholder_text(_('Type your answer here'))
        entry.get_style_context().add_class('create-ai-generated-entry')
        entry.connect('button-press-event',
                      self.__preview_target_button_press_event_cb,
                      _('quiz answer input'))
        box.pack_start(entry, False, False, 0)

        row = Gtk.HBox(spacing=style.zoom(6))
        box.pack_start(row, False, False, 0)
        button = Gtk.Button.new_with_label(_('Check answer'))
        button.get_style_context().add_class('create-ai-generated-action')
        row.pack_start(button, False, False, 0)
        feedback = Gtk.Label(_('Score: 0'))
        feedback.get_style_context().add_class('create-ai-generated-summary')
        row.pack_start(feedback, False, False, 0)
        return box

    def _create_chess_activity_preview(self, plan):
        box = Gtk.VBox(spacing=style.zoom(8))
        box.get_style_context().add_class('create-ai-generated-body')
        box.set_hexpand(True)
        box.set_vexpand(True)
        show_move_log = plan.get('chess_show_move_log', True)

        status = Gtk.Label(_('White to move. Select a piece.'))
        status.get_style_context().add_class('create-ai-generated-summary')
        status.set_justify(Gtk.Justification.CENTER)
        box.pack_start(status, False, False, 0)

        play_area = Gtk.HBox(spacing=style.zoom(16))
        play_area.set_halign(Gtk.Align.FILL)
        play_area.set_valign(Gtk.Align.FILL)
        box.pack_start(play_area, True, True, 0)

        board_frame = Gtk.Alignment(xalign=0.5, yalign=0.5, xscale=0,
                                    yscale=0)
        play_area.pack_start(board_frame, True, True, 0)

        board_box = Gtk.VBox(spacing=style.zoom(4))
        board_frame.add(board_box)

        files = Gtk.HBox(spacing=style.zoom(2))
        files.set_halign(Gtk.Align.CENTER)
        files.pack_start(Gtk.Label(label='  '), False, False, 0)
        for file_name in 'abcdefgh':
            label = Gtk.Label(label=file_name)
            label.get_style_context().add_class('create-ai-generated-summary')
            label.set_size_request(style.zoom(62), style.zoom(16))
            files.pack_start(label, False, False, 0)
        board_box.pack_start(files, False, False, 0)

        board_row = Gtk.HBox(spacing=style.zoom(6))
        board_box.pack_start(board_row, False, False, 0)

        ranks = Gtk.VBox(spacing=style.zoom(2))
        board_row.pack_start(ranks, False, False, 0)

        grid = Gtk.Grid(row_spacing=style.zoom(2), column_spacing=style.zoom(2))
        grid.set_halign(Gtk.Align.CENTER)
        grid.set_valign(Gtk.Align.CENTER)
        board_row.pack_start(grid, False, False, 0)

        side = Gtk.VBox(spacing=style.zoom(8))
        side.set_size_request(style.zoom(320), -1)
        side.set_valign(Gtk.Align.FILL)
        play_area.pack_start(side, False, False, 0)

        hint = Gtk.Label(
            _('Use the preview like the activity: pick a piece, then choose '
              'where it should move. The generated activity saves this work '
              'in the Journal.'))
        hint.get_style_context().add_class('create-ai-generated-summary')
        hint.set_xalign(0)
        hint.set_line_wrap(True)
        side.pack_start(hint, False, False, 0)

        log = None
        if show_move_log:
            log_frame = Gtk.EventBox()
            log_frame.get_style_context().add_class('create-ai-generated-log')
            log_frame.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            log_frame.connect('button-press-event',
                              self.__preview_target_button_press_event_cb,
                              _('move log panel'))
            side.pack_start(log_frame, True, True, 0)

            log_box = Gtk.VBox(spacing=style.zoom(5))
            log_box.set_border_width(style.zoom(9))
            log_frame.add(log_box)

            log_title = Gtk.Label(_('Move log'))
            log_title.get_style_context().add_class(
                'create-ai-generated-kicker')
            log_title.set_xalign(0)
            log_box.pack_start(log_title, False, False, 0)

            log = Gtk.Label()
            log.get_style_context().add_class('create-ai-generated-summary')
            log.set_xalign(0)
            log.set_yalign(0)
            log.set_line_wrap(True)
            log_box.pack_start(log, True, True, 0)
        else:
            clean_note = Gtk.Label(
                _('Clean board mode: move history is hidden.'))
            clean_note.get_style_context().add_class(
                'create-ai-generated-summary')
            clean_note.set_xalign(0)
            clean_note.set_line_wrap(True)
            side.pack_start(clean_note, False, False, 0)

        reset = Gtk.Button.new_with_label(_('Reset preview'))
        reset.get_style_context().add_class('create-ai-generated-action')
        reset.connect('button-press-event',
                      self.__preview_target_button_press_event_cb,
                      _('reset control'))
        side.pack_start(reset, False, False, 0)

        pieces = [
            ['♜', '♞', '♝', '♛', '♚', '♝', '♞', '♜'],
            ['♟', '♟', '♟', '♟', '♟', '♟', '♟', '♟'],
            ['', '', '', '', '', '', '', ''],
            ['', '', '', '', '', '', '', ''],
            ['', '', '', '', '', '', '', ''],
            ['', '', '', '', '', '', '', ''],
            ['♙', '♙', '♙', '♙', '♙', '♙', '♙', '♙'],
            ['♖', '♘', '♗', '♕', '♔', '♗', '♘', '♖'],
        ]
        state = {
            'board': [row[:] for row in pieces],
            'turn': 'white',
            'selected': None,
            'moves': [],
            'show_move_log': show_move_log,
        }
        buttons = []
        for row in range(8):
            rank = Gtk.Label(label=str(8 - row))
            rank.get_style_context().add_class('create-ai-generated-summary')
            rank.set_size_request(style.zoom(14), style.zoom(58))
            ranks.pack_start(rank, False, False, 0)
            button_row = []
            for col in range(8):
                label = pieces[row][col] or ' '
                button = Gtk.Button.new_with_label(label)
                button.get_style_context().add_class(
                    'create-ai-generated-chess-square')
                if (row + col) % 2:
                    button.get_style_context().add_class(
                        'create-ai-generated-chess-dark')
                button.set_size_request(style.zoom(62), style.zoom(58))
                button.connect('clicked',
                               self.__generated_chess_square_clicked_cb,
                               status, state, buttons, log, row, col)
                grid.attach(button, col, row, 1, 1)
                button_row.append(button)
            buttons.append(button_row)
        reset.connect('clicked', self.__generated_chess_reset_clicked_cb,
                      status, state, buttons, log, pieces)
        self._refresh_generated_chess_preview(status, state, buttons, log)
        return box

    def _create_carrom_activity_preview(self, plan):
        box = Gtk.VBox(spacing=style.zoom(8))
        box.get_style_context().add_class('create-ai-generated-body')
        box.set_hexpand(True)
        box.set_vexpand(True)

        status = Gtk.Label(
            _('Student A to shoot. Click the board to place the striker aim.'))
        status.get_style_context().add_class('create-ai-generated-summary')
        status.set_line_wrap(True)
        status.set_xalign(0)
        box.pack_start(status, False, False, 0)

        play_area = Gtk.HBox(spacing=style.zoom(16))
        play_area.set_halign(Gtk.Align.FILL)
        play_area.set_valign(Gtk.Align.FILL)
        box.pack_start(play_area, True, True, 0)

        drawing = Gtk.DrawingArea()
        drawing.set_size_request(style.zoom(560), style.zoom(420))
        drawing.get_style_context().add_class('create-ai-generated-canvas')
        drawing.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        play_area.pack_start(drawing, True, True, 0)

        side = Gtk.VBox(spacing=style.zoom(8))
        side.set_size_request(style.zoom(320), -1)
        side.set_valign(Gtk.Align.FILL)
        play_area.pack_start(side, False, False, 0)

        score = Gtk.Label()
        score.get_style_context().add_class('create-ai-generated-summary')
        score.set_xalign(0)
        score.set_line_wrap(True)
        side.pack_start(score, False, False, 0)

        buttons = Gtk.Grid(row_spacing=style.zoom(5),
                           column_spacing=style.zoom(5))
        side.pack_start(buttons, False, False, 0)

        log_frame = Gtk.EventBox()
        log_frame.get_style_context().add_class('create-ai-generated-log')
        log_frame.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        log_frame.connect('button-press-event',
                          self.__preview_target_button_press_event_cb,
                          _('carrom shot log'))
        side.pack_start(log_frame, True, True, 0)

        log_box = Gtk.VBox(spacing=style.zoom(5))
        log_box.set_border_width(style.zoom(8))
        log_frame.add(log_box)

        log_title = Gtk.Label(_('Shot log'))
        log_title.get_style_context().add_class('create-ai-generated-kicker')
        log_title.set_xalign(0)
        log_box.pack_start(log_title, False, False, 0)

        log = Gtk.Label()
        log.get_style_context().add_class('create-ai-generated-summary')
        log.set_xalign(0)
        log.set_yalign(0)
        log.set_line_wrap(True)
        log_box.pack_start(log, True, True, 0)

        state = {
            'turn': 'A',
            'scores': {'A': 0, 'B': 0},
            'fouls': {'A': 0, 'B': 0},
            'coins': {'white': 9, 'black': 9, 'queen': 1},
            'aim': [0.5, 0.82],
            'log': [],
        }
        actions = (
            (_('Pocket white'), 'white'),
            (_('Pocket black'), 'black'),
            (_('Pocket queen'), 'queen'),
            (_('Foul'), 'foul'),
            (_('Switch turn'), 'switch'),
            (_('Reset'), 'reset'),
        )
        for index, item in enumerate(actions):
            label, action = item
            button = Gtk.Button.new_with_label(label)
            button.get_style_context().add_class('create-ai-generated-action')
            button.connect('clicked',
                           self.__generated_carrom_action_clicked_cb,
                           action, state, status, score, log, drawing)
            buttons.attach(button, index % 2, index // 2, 1, 1)

        drawing.connect('draw', self.__generated_carrom_draw_cb, state)
        drawing.connect('button-press-event',
                        self.__generated_carrom_board_press_cb,
                        state, status, score, log)
        self._refresh_generated_carrom_preview(
            status, score, log, drawing, state)
        return box

    def _create_grid_activity_preview(self, plan):
        box = Gtk.VBox(spacing=style.zoom(8))
        box.get_style_context().add_class('create-ai-generated-body')

        grid = Gtk.Grid(row_spacing=style.zoom(6), column_spacing=style.zoom(6))
        grid.set_halign(Gtk.Align.CENTER)
        box.pack_start(grid, True, True, 0)
        for index in range(16):
            button = Gtk.ToggleButton.new_with_label(str(index + 1))
            button.get_style_context().add_class('create-ai-generated-tile')
            button.set_size_request(style.zoom(48), style.zoom(40))
            button.connect('clicked',
                           self.__generated_grid_tile_clicked_cb,
                           index)
            if index in (1, 4, 6, 9, 11, 14):
                button.set_active(True)
            grid.attach(button, index % 4, index // 4, 1, 1)

        status = Gtk.Label(_('6 squares are part of your pattern.'))
        status.get_style_context().add_class('create-ai-generated-summary')
        status.set_justify(Gtk.Justification.CENTER)
        box.pack_start(status, False, False, 0)
        return box

    def _create_canvas_activity_preview(self, plan, source=''):
        box = Gtk.VBox(spacing=style.zoom(8))
        box.get_style_context().add_class('create-ai-generated-body')
        box.set_hexpand(True)
        box.set_vexpand(True)

        drawing = Gtk.DrawingArea()
        drawing.set_size_request(style.zoom(720), style.zoom(320))
        drawing.get_style_context().add_class('create-ai-generated-canvas')
        drawing.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        drawing.connect('button-press-event',
                        self.__preview_target_button_press_event_cb,
                        _('drawing canvas'))
        drawing.connect('draw', self.__generated_canvas_draw_cb)
        box.pack_start(drawing, True, True, 0)

        row = Gtk.HBox(spacing=style.zoom(6))
        row.set_halign(Gtk.Align.CENTER)
        box.pack_start(row, False, False, 0)
        labels = self._activity_source_canvas_actions(source)
        if not labels:
            labels = [_('Draw'), _('Clear drawing')]
        for label in labels[:6]:
            button = Gtk.Button.new_with_label(label)
            button.get_style_context().add_class('create-ai-generated-action')
            row.pack_start(button, False, False, 0)
        return box

    def _get_generated_activity_source(self, result):
        files = getattr(result, 'files', None)
        if not isinstance(files, dict):
            return ''
        return files.get('activity.py') or files.get('./activity.py') or ''

    def _source_mentions_paired_canvas(self, source):
        text = (source or '').lower()
        if not self._source_mentions_canvas(source):
            return False
        pair_hits = sum(phrase in text for phrase in (
            'student a',
            'student b',
            'switch turn',
            'two student',
            'two learner',
            'partner',
            'shared drawing',
            'take turns',
            'together',
        ))
        tool_hits = len(self._activity_source_canvas_tools(source))
        if self._source_has_label(source, _('Undo last mark')):
            tool_hits += 1
        if self._source_has_label(source, _('Clear drawing')):
            tool_hits += 1
        return pair_hits >= 2 and tool_hits >= 2

    def _source_mentions_canvas(self, source):
        text = (source or '').lower()
        return (
            ('drawingarea' in text or 'drawing area' in text) and
            any(phrase in text for phrase in (
                'canvas', 'draw', 'drawing', 'paint', 'sketch', 'stroke'))
        )

    def _source_mentions_turn_drawing_canvas(self, source):
        text = (source or '').lower()
        if not self._source_mentions_canvas(source):
            return False
        return (
            'switch turn' in text and
            ('label mode' in text or 'label_entry' in text) and
            ('brush_spin' in text or 'brush size' in text or 'size:' in text)
        )

    def _source_has_label(self, source, label):
        if not source or not label:
            return False
        return ("'%s'" % label) in source or ('"%s"' % label) in source

    def _activity_source_canvas_actions(self, source):
        candidates = (
            _('Draw'),
            _('Free Draw'),
            _('Line'),
            _('Rectangle'),
            _('Circle'),
            _('Eraser'),
            _('Undo last mark'),
            _('Clear drawing'),
        )
        labels = []
        for label in candidates:
            if self._source_has_label(source, label):
                labels.append(label)
        return labels

    def _is_paired_canvas_activity(self, plan):
        fields = [
            plan.get('activity_kind', ''),
            plan.get('summary', ''),
            plan.get('interaction_model', ''),
            plan.get('learner_goal', ''),
            plan.get('state_schema', ''),
        ]
        for key in ('ui_regions', 'features', 'learner_steps',
                    'classroom_flow'):
            value = plan.get(key)
            if isinstance(value, list):
                fields.extend(str(item) for item in value)
        text = ' '.join(fields).lower()
        return any(phrase in text for phrase in (
            'student a',
            'student b',
            'two student',
            'two learners',
            'partner',
            'paired',
            'shared drawing',
            'take turns',
            'switch turns',
            'together',
        ))

    def _create_turn_drawing_activity_preview(self, plan, source=''):
        box = Gtk.VBox(spacing=style.zoom(8))
        box.get_style_context().add_class('create-ai-generated-body')
        box.set_hexpand(True)
        box.set_vexpand(True)

        state = {
            'current_turn': 1,
            'turn_counts': {1: 0, 2: 0},
            'student_colors': {
                1: (0.9, 0.2, 0.2, 1.0),
                2: (0.2, 0.4, 0.9, 1.0),
            },
            'brush_size': 3,
            'strokes': [],
            'labels': [],
            'current_stroke': None,
        }

        controls = Gtk.HBox(spacing=style.zoom(8))
        controls.set_halign(Gtk.Align.FILL)
        box.pack_start(controls, False, False, 0)

        status = Gtk.Label()
        status.get_style_context().add_class('create-ai-generated-summary')
        status.set_xalign(0)
        controls.pack_start(status, False, False, 0)

        palette = Gtk.HBox(spacing=style.zoom(2))
        controls.pack_start(palette, False, False, style.zoom(4))
        colors = [
            ('#e74c3c', (0.9, 0.2, 0.2, 1.0)),
            ('#2ecc71', (0.2, 0.7, 0.2, 1.0)),
            ('#3498db', (0.2, 0.4, 0.9, 1.0)),
            ('#f1c40f', (0.9, 0.8, 0.2, 1.0)),
            ('#9b59b6', (0.7, 0.2, 0.7, 1.0)),
            ('#000000', (0.1, 0.1, 0.1, 1.0)),
        ]
        for hex_color, rgba in colors:
            button = Gtk.Button()
            button.get_style_context().add_class('create-ai-generated-action')
            label = Gtk.Label()
            label.set_markup(
                '<span size="large" foreground="%s">■</span>' % hex_color)
            button.add(label)
            button.connect('clicked',
                           self.__turn_preview_color_clicked_cb,
                           state, rgba)
            palette.pack_start(button, False, False, 0)

        size_row = Gtk.HBox(spacing=style.zoom(3))
        size_row.pack_start(Gtk.Label(label=_('Size:')), False, False, 0)
        adjustment = Gtk.Adjustment(value=3, lower=1, upper=20,
                                    step_increment=1)
        brush_spin = Gtk.SpinButton()
        brush_spin.set_adjustment(adjustment)
        brush_spin.set_numeric(True)
        brush_spin.connect('value-changed',
                           self.__turn_preview_brush_changed_cb,
                           state)
        size_row.pack_start(brush_spin, False, False, 0)
        controls.pack_start(size_row, False, False, style.zoom(4))

        label_entry = Gtk.Entry()
        label_entry.set_placeholder_text(_('Type label...'))
        label_entry.set_width_chars(14)
        controls.pack_start(label_entry, False, False, 0)

        label_toggle = Gtk.ToggleButton.new_with_label(_('Label Mode'))
        label_toggle.get_style_context().add_class(
            'create-ai-generated-action')
        controls.pack_start(label_toggle, False, False, 0)

        switch = Gtk.Button.new_with_label(_('Switch Turn ->'))
        switch.get_style_context().add_class('create-ai-generated-action')
        switch.connect('clicked',
                       self.__turn_preview_switch_clicked_cb,
                       state, status)
        controls.pack_end(switch, False, False, 0)

        drawing = Gtk.DrawingArea()
        drawing.set_size_request(style.zoom(900), style.zoom(420))
        drawing.get_style_context().add_class('create-ai-generated-canvas')
        drawing.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK
        )
        drawing.connect('draw', self.__turn_preview_draw_cb, state)
        drawing.connect('button-press-event',
                        self.__turn_preview_press_cb,
                        state, label_entry, label_toggle)
        drawing.connect('motion-notify-event',
                        self.__turn_preview_motion_cb, state)
        drawing.connect('button-release-event',
                        self.__turn_preview_release_cb, state)
        box.pack_start(drawing, True, True, 0)

        note = Gtk.Label(
            _('Preview mirrors the generated activity.py controls. Install '
              'and open to run the exact Sugar activity.'))
        note.get_style_context().add_class('create-ai-generated-summary')
        note.set_xalign(0)
        note.set_line_wrap(True)
        box.pack_start(note, False, False, 0)

        self._refresh_turn_preview_status(status, state)
        return box

    def _create_paired_canvas_activity_preview(self, plan, source=''):
        box = Gtk.HBox(spacing=style.zoom(10))
        box.get_style_context().add_class('create-ai-generated-body')
        box.set_hexpand(True)
        box.set_vexpand(True)

        state = {
            'active': 'A',
            'tool': _('Free Draw'),
            'marks_a': 1,
            'marks_b': 1,
        }

        side = Gtk.VBox(spacing=style.zoom(7))
        side.set_size_request(style.zoom(235), -1)
        box.pack_start(side, False, False, 0)

        partner_label = Gtk.Label(_('Partner controls'))
        partner_label.get_style_context().add_class('create-ai-generated-kicker')
        partner_label.set_xalign(0)
        side.pack_start(partner_label, False, False, 0)

        status = Gtk.Label()
        status.get_style_context().add_class('create-ai-generated-summary')
        status.set_xalign(0)
        status.set_line_wrap(True)
        side.pack_start(status, False, False, 0)

        student_row = Gtk.HBox(spacing=style.zoom(5))
        side.pack_start(student_row, False, False, 0)
        for student, label in (('A', _('Student A')), ('B', _('Student B'))):
            button = Gtk.Button.new_with_label(label)
            button.get_style_context().add_class('create-ai-generated-action')
            button.connect('clicked',
                           self.__paired_preview_student_clicked_cb,
                           state, status, student)
            student_row.pack_start(button, True, True, 0)

        switch = Gtk.Button.new_with_label(_('Switch Turn'))
        switch.get_style_context().add_class('create-ai-generated-action')
        switch.connect('clicked', self.__paired_preview_switch_clicked_cb,
                       state, status)
        side.pack_start(switch, False, False, 0)

        tools_label = Gtk.Label(_('Drawing tools'))
        tools_label.get_style_context().add_class('create-ai-generated-kicker')
        tools_label.set_xalign(0)
        side.pack_start(tools_label, False, False, 0)

        tool_grid = Gtk.Grid(row_spacing=style.zoom(4),
                             column_spacing=style.zoom(4))
        side.pack_start(tool_grid, False, False, 0)
        tools = self._activity_source_canvas_tools(source)
        if not tools:
            tools = [
                _('Free Draw'), _('Line'), _('Rectangle'),
                _('Circle'), _('Point'), _('Eraser'),
            ]
        for index, tool in enumerate(tools):
            button = Gtk.Button.new_with_label(tool)
            button.get_style_context().add_class('create-ai-generated-action')
            button.connect('clicked',
                           self.__paired_preview_tool_clicked_cb,
                           state, status, tool)
            tool_grid.attach(button, index % 2, index // 2, 1, 1)

        sample = Gtk.Button.new_with_label(_('Add sample mark'))
        sample.get_style_context().add_class('create-ai-generated-action')
        sample.connect('clicked', self.__paired_preview_mark_clicked_cb,
                       state, status)
        side.pack_start(sample, False, False, 0)

        clear = Gtk.Button.new_with_label(_('Clear preview'))
        clear.get_style_context().add_class('create-ai-generated-action')
        clear.connect('clicked', self.__paired_preview_clear_clicked_cb,
                      state, status)
        side.pack_start(clear, False, False, 0)

        if 'undo' in (source or '').lower():
            undo = Gtk.Button.new_with_label(_('Undo last mark'))
            undo.get_style_context().add_class('create-ai-generated-action')
            undo.connect('button-press-event',
                         self.__preview_target_button_press_event_cb,
                         _('undo control'))
            side.pack_start(undo, False, False, 0)

        words = Gtk.Label(_('Word bank: pattern, symmetry, turn, shape, '
                            'coordinate, repeat, rule'))
        words.get_style_context().add_class('create-ai-generated-summary')
        words.set_xalign(0)
        words.set_line_wrap(True)
        side.pack_start(words, False, False, 0)

        right = Gtk.VBox(spacing=style.zoom(7))
        box.pack_start(right, True, True, 0)

        drawing = Gtk.DrawingArea()
        drawing.set_size_request(style.zoom(760), style.zoom(360))
        drawing.get_style_context().add_class('create-ai-generated-canvas')
        drawing.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        drawing.connect('button-press-event',
                        self.__preview_target_button_press_event_cb,
                        _('shared drawing canvas'))
        drawing.connect('draw', self.__paired_canvas_draw_cb, state)
        right.pack_start(drawing, True, True, 0)

        explain = Gtk.TextView()
        explain.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        explain.get_buffer().set_text(
            _('We used a repeating shape rule and took turns adding marks.'))
        explain.connect('button-press-event',
                        self.__preview_target_button_press_event_cb,
                        _('partner explanation box'))
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_size_request(-1, style.zoom(88))
        scroll.add(explain)
        right.pack_start(scroll, False, True, 0)

        self._refresh_paired_preview_status(status, state)
        return box

    def _activity_source_canvas_tools(self, source):
        candidates = (
            _('Free Draw'),
            _('Line'),
            _('Rectangle'),
            _('Circle'),
            _('Point'),
            _('Eraser'),
        )
        labels = []
        for label in candidates:
            if self._source_has_label(source, label):
                labels.append(label)
        return labels

    def _create_narrative_activity_preview(self, plan, result):
        box = Gtk.VBox(spacing=style.zoom(8))
        box.get_style_context().add_class('create-ai-generated-body')

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_size_request(style.zoom(450), style.zoom(190))
        text = Gtk.TextView()
        text.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        text.get_buffer().set_text(
            plan.get('starter_text') or result.spec.prompt)
        text.connect('button-press-event',
                     self.__preview_target_button_press_event_cb,
                     _('writing area'))
        scroll.add(text)
        box.pack_start(scroll, True, True, 0)
        return box

    def _create_utility_activity_preview(self, plan, result):
        mode = plan.get('utility_mode', 'word_counter')
        if mode == 'counter':
            return self._create_counter_activity_preview()
        if mode == 'timer':
            return self._create_timer_activity_preview()

        box = Gtk.VBox(spacing=style.zoom(8))
        box.get_style_context().add_class('create-ai-generated-body')

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_size_request(style.zoom(450), style.zoom(160))
        text = Gtk.TextView()
        text.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        text.get_buffer().set_text(result.spec.prompt)
        text.connect('button-press-event',
                     self.__preview_target_button_press_event_cb,
                     _('utility text area'))
        scroll.add(text)
        box.pack_start(scroll, True, True, 0)

        count = len(result.spec.prompt.split())
        label = Gtk.Label(_('%d words, %d characters') %
                          (count, len(result.spec.prompt)))
        label.get_style_context().add_class('create-ai-generated-summary')
        label.set_xalign(0)
        box.pack_start(label, False, False, 0)
        return box

    def _create_counter_activity_preview(self):
        box = Gtk.VBox(spacing=style.zoom(10))
        box.get_style_context().add_class('create-ai-generated-body')
        box.set_halign(Gtk.Align.CENTER)

        count = Gtk.Label('0')
        count.get_style_context().add_class('create-ai-generated-title')
        count.set_margin_top(style.zoom(24))
        count.set_margin_bottom(style.zoom(12))
        count.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        count.connect('button-press-event',
                      self.__preview_target_button_press_event_cb,
                      _('counter display'))
        box.pack_start(count, True, True, 0)

        state = {'count': 0}
        row = Gtk.HBox(spacing=style.zoom(8))
        row.set_halign(Gtk.Align.CENTER)
        box.pack_start(row, False, False, 0)
        for label, amount in ((_('-1'), -1), (_('+1'), 1)):
            button = Gtk.Button.new_with_label(label)
            button.get_style_context().add_class('create-ai-generated-action')
            button.connect('clicked',
                           self.__generated_counter_clicked_cb,
                           count, state, amount)
            row.pack_start(button, False, False, 0)

        reset = Gtk.Button.new_with_label(_('Reset'))
        reset.get_style_context().add_class('create-ai-generated-action')
        reset.connect('clicked',
                      self.__generated_counter_reset_clicked_cb,
                      count, state)
        row.pack_start(reset, False, False, 0)

        note = Gtk.Label(_('Use the count, then explain what it means.'))
        note.get_style_context().add_class('create-ai-generated-summary')
        note.set_justify(Gtk.Justification.CENTER)
        box.pack_start(note, False, False, 0)
        return box

    def _create_timer_activity_preview(self):
        box = Gtk.VBox(spacing=style.zoom(10))
        box.get_style_context().add_class('create-ai-generated-body')
        box.set_halign(Gtk.Align.CENTER)

        timer = Gtk.Label('00:00')
        timer.get_style_context().add_class('create-ai-generated-title')
        timer.set_margin_top(style.zoom(24))
        timer.set_margin_bottom(style.zoom(12))
        timer.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        timer.connect('button-press-event',
                      self.__preview_target_button_press_event_cb,
                      _('timer display'))
        box.pack_start(timer, True, True, 0)

        row = Gtk.HBox(spacing=style.zoom(8))
        row.set_halign(Gtk.Align.CENTER)
        box.pack_start(row, False, False, 0)
        for label in (_('Start'), _('Reset')):
            button = Gtk.Button.new_with_label(label)
            button.get_style_context().add_class('create-ai-generated-action')
            row.pack_start(button, False, False, 0)

        note = Gtk.Label(_('Generated activity includes a working timer.'))
        note.get_style_context().add_class('create-ai-generated-summary')
        note.set_justify(Gtk.Justification.CENTER)
        box.pack_start(note, False, False, 0)
        return box

    def __turn_preview_color_clicked_cb(self, button, state, rgba):
        state['student_colors'][state['current_turn']] = rgba

    def __turn_preview_brush_changed_cb(self, spin, state):
        state['brush_size'] = spin.get_value_as_int()

    def __turn_preview_switch_clicked_cb(self, button, state, status):
        current = state['current_turn']
        state['turn_counts'][current] = \
            state['turn_counts'].get(current, 0) + 1
        state['current_turn'] = 2 if current == 1 else 1
        self._refresh_turn_preview_status(status, state)

    def __turn_preview_press_cb(self, widget, event, state, label_entry,
                                label_toggle):
        if label_toggle.get_active():
            text = label_entry.get_text().strip()
            if text:
                state['labels'].append({
                    'text': text,
                    'x': event.x,
                    'y': event.y,
                    'student_id': state['current_turn'],
                })
                label_entry.set_text('')
                widget.queue_draw()
            return True

        state['current_stroke'] = {
            'points': [(event.x, event.y)],
            'rgba': state['student_colors'][state['current_turn']],
            'width': state['brush_size'],
            'student_id': state['current_turn'],
        }
        return True

    def __turn_preview_motion_cb(self, widget, event, state):
        stroke = state.get('current_stroke')
        if stroke is not None:
            stroke['points'].append((event.x, event.y))
            widget.queue_draw()
        return True

    def __turn_preview_release_cb(self, widget, event, state):
        stroke = state.get('current_stroke')
        if stroke is not None:
            stroke['points'].append((event.x, event.y))
            state['strokes'].append(stroke)
            state['current_stroke'] = None
            widget.queue_draw()
        return True

    def _refresh_turn_preview_status(self, status, state):
        status.set_markup(
            _('<b>Student %(student)d Turn</b>  '
              '(Turns taken: S1=%(s1)d, S2=%(s2)d)') % {
                  'student': state['current_turn'],
                  's1': state['turn_counts'].get(1, 0),
                  's2': state['turn_counts'].get(2, 0),
              }
        )

    def __turn_preview_draw_cb(self, widget, context, state):
        allocation = widget.get_allocation()
        width = allocation.width
        height = allocation.height
        context.set_source_rgb(1, 1, 1)
        context.rectangle(0, 0, width, height)
        context.fill()

        for stroke in state['strokes']:
            self._draw_turn_preview_stroke(context, stroke)
        if state.get('current_stroke'):
            self._draw_turn_preview_stroke(context, state['current_stroke'])

        for label in state['labels']:
            student_id = label.get('student_id', 1)
            rgba = state['student_colors'].get(
                student_id,
                (0.1, 0.1, 0.1, 1.0),
            )
            context.set_source_rgba(*rgba)
            context.arc(label['x'], label['y'], 5, 0, 2 * math.pi)
            context.fill()
            context.set_source_rgb(0, 0, 0)
            context.set_font_size(14)
            context.move_to(label['x'] + 8, label['y'] + 4)
            context.show_text(label.get('text', ''))
        return False

    def _draw_turn_preview_stroke(self, context, stroke):
        points = stroke.get('points', [])
        if len(points) < 2:
            return
        context.set_source_rgba(*stroke.get('rgba', (0.1, 0.1, 0.1, 1.0)))
        context.set_line_width(stroke.get('width', 3))
        context.move_to(points[0][0], points[0][1])
        for x, y in points[1:]:
            context.line_to(x, y)
        context.stroke()

    def __paired_preview_student_clicked_cb(self, button, state, status,
                                            student):
        state['active'] = student
        self._refresh_paired_preview_status(status, state)

    def __paired_preview_switch_clicked_cb(self, button, state, status):
        state['active'] = 'B' if state.get('active') == 'A' else 'A'
        self._refresh_paired_preview_status(status, state)

    def __paired_preview_tool_clicked_cb(self, button, state, status, tool):
        state['tool'] = tool
        self._refresh_paired_preview_status(status, state)

    def __paired_preview_mark_clicked_cb(self, button, state, status):
        if state.get('active') == 'A':
            state['marks_a'] = state.get('marks_a', 0) + 1
            state['active'] = 'B'
        else:
            state['marks_b'] = state.get('marks_b', 0) + 1
            state['active'] = 'A'
        self._refresh_paired_preview_status(status, state)

    def __paired_preview_clear_clicked_cb(self, button, state, status):
        state['marks_a'] = 0
        state['marks_b'] = 0
        state['active'] = 'A'
        self._refresh_paired_preview_status(status, state)

    def _refresh_paired_preview_status(self, status, state):
        active = _('Student A') if state.get('active') == 'A' else \
            _('Student B')
        status.set_text(
            _('Active: %(active)s\nTool: %(tool)s\nMarks: A=%(a)d B=%(b)d\n'
              'Partners take turns, then explain the pattern or rule.') % {
                'active': active,
                'tool': state.get('tool', _('Free Draw')),
                'a': state.get('marks_a', 0),
                'b': state.get('marks_b', 0),
            }
        )

    def __paired_canvas_draw_cb(self, widget, context, state):
        allocation = widget.get_allocation()
        width = allocation.width
        height = allocation.height
        context.set_source_rgb(1, 1, 1)
        context.rectangle(0, 0, width, height)
        context.fill()

        context.set_line_width(1)
        context.set_source_rgb(0.88, 0.88, 0.88)
        step = style.zoom(28)
        for x in range(0, max(step, width), step):
            context.move_to(x, 0)
            context.line_to(x, height)
        for y in range(0, max(step, height), step):
            context.move_to(0, y)
            context.line_to(width, y)
        context.stroke()

        context.set_line_width(2)
        context.set_source_rgb(0.70, 0.70, 0.70)
        context.move_to(width / 2.0, 0)
        context.line_to(width / 2.0, height)
        context.move_to(0, height / 2.0)
        context.line_to(width, height / 2.0)
        context.stroke()

        context.set_line_width(5)
        context.set_source_rgb(0.12, 0.45, 0.78)
        context.move_to(width * 0.14, height * 0.70)
        context.curve_to(width * 0.26, height * 0.22,
                         width * 0.44, height * 0.28,
                         width * 0.54, height * 0.56)
        context.stroke()

        context.set_source_rgb(0.95, 0.50, 0.08)
        context.rectangle(width * 0.62, height * 0.22,
                          width * 0.19, height * 0.23)
        context.stroke()
        context.arc(width * 0.72, height * 0.68,
                    min(width, height) * 0.09, 0, 2 * math.pi)
        context.stroke()

        context.set_font_size(12)
        context.set_source_rgb(0.12, 0.45, 0.78)
        context.move_to(width * 0.14, height * 0.78)
        context.show_text('Student A')
        context.set_source_rgb(0.95, 0.50, 0.08)
        context.move_to(width * 0.62, height * 0.18)
        context.show_text('Student B')
        return False

    def __generated_canvas_draw_cb(self, widget, context):
        allocation = widget.get_allocation()
        width = allocation.width
        height = allocation.height
        context.set_source_rgb(1, 1, 1)
        context.rectangle(0, 0, width, height)
        context.fill()
        context.set_source_rgb(0.88, 0.88, 0.88)
        for x in range(24, max(24, width), 32):
            context.move_to(x, 0)
            context.line_to(x, height)
        for y in range(24, max(24, height), 32):
            context.move_to(0, y)
            context.line_to(width, y)
        context.stroke()
        context.set_source_rgb(0.18, 0.32, 0.62)
        context.set_line_width(4)
        context.move_to(width * 0.18, height * 0.62)
        context.curve_to(width * 0.34, height * 0.20,
                         width * 0.58, height * 0.78,
                         width * 0.82, height * 0.34)
        context.stroke()
        return False

    def __generated_chess_square_clicked_cb(self, button, status, state,
                                            buttons, log, row, col):
        board = state['board']
        piece = board[row][col]
        turn = state['turn']
        selected = state['selected']
        square = self._generated_chess_square_name(row, col)
        self._set_live_edit_target(_('chess board square %s') % square)

        if selected is None:
            if not piece:
                status.set_text(
                    _('Choose a %s piece first.') % turn.capitalize())
                return
            if self._generated_chess_piece_color(piece) != turn:
                status.set_text(
                    _('%s to move. Pick a %s piece.') %
                    (turn.capitalize(), turn))
                return
            state['selected'] = (row, col)
            status.set_text(
                _('Selected %s on %s. Choose a destination.') %
                (self._generated_chess_piece_name(piece), square))
            self._refresh_generated_chess_preview(
                status, state, buttons, log)
            return

        start_row, start_col = selected
        moving = board[start_row][start_col]
        if (row, col) == selected:
            state['selected'] = None
            status.set_text(_('Selection cleared.'))
            self._refresh_generated_chess_preview(
                status, state, buttons, log)
            return

        if piece and self._generated_chess_piece_color(piece) == turn:
            state['selected'] = (row, col)
            status.set_text(
                _('Selected %s on %s. Choose a destination.') %
                (self._generated_chess_piece_name(piece), square))
            self._refresh_generated_chess_preview(
                status, state, buttons, log)
            return

        if not self._generated_chess_can_move(
                board, moving, start_row, start_col, row, col):
            status.set_text(
                _('%s cannot move to %s. Try a legal chess move.') %
                (self._generated_chess_piece_name(moving), square))
            return

        capture = piece
        board[row][col] = moving
        board[start_row][start_col] = ''
        start_square = self._generated_chess_square_name(start_row, start_col)
        move_text = _('%s %s to %s') % (
            self._generated_chess_piece_name(moving),
            start_square,
            square,
        )
        if capture:
            move_text = _('%s captures %s') % (
                move_text, self._generated_chess_piece_name(capture))
        if state.get('show_move_log', True):
            state['moves'].append(move_text)
        state['turn'] = 'black' if turn == 'white' else 'white'
        state['selected'] = None
        status.set_text(
            _('%s. %s to move.') %
            (move_text, state['turn'].capitalize()))
        self._refresh_generated_chess_preview(status, state, buttons, log)

    def __generated_chess_reset_clicked_cb(self, button, status, state,
                                           buttons, log, pieces):
        self._set_live_edit_target(_('reset control'))
        state['board'] = [row[:] for row in pieces]
        state['turn'] = 'white'
        state['selected'] = None
        state['moves'] = []
        status.set_text(_('Board reset. White to move.'))
        self._refresh_generated_chess_preview(status, state, buttons, log)

    def __generated_grid_tile_clicked_cb(self, button, index):
        self._set_live_edit_target(
            _('grid tile %d') % (index + 1))

    def __generated_carrom_board_press_cb(self, widget, event, state,
                                          status, score, log):
        left, top, size = self._generated_square_geometry(widget)
        if event.x < left or event.y < top or \
                event.x > left + size or event.y > top + size:
            return False
        state['aim'] = [
            (event.x - left) / float(size),
            (event.y - top) / float(size),
        ]
        self._set_live_edit_target(_('carrom striker aim marker'))
        status.set_text(
            _('%s set the striker aim. Record the shot result.') %
            self._generated_carrom_player_name(state))
        self._refresh_generated_carrom_preview(
            status, score, log, widget, state)
        return True

    def __generated_carrom_action_clicked_cb(self, button, action, state,
                                             status, score, log, drawing):
        player = state['turn']
        player_name = self._generated_carrom_player_name(state)
        if action in ('white', 'black', 'queen'):
            coins = state['coins']
            if coins[action] <= 0:
                status.set_text(_('No %s coins remain.') % action)
            else:
                coins[action] -= 1
                points = 3 if action == 'queen' else 1
                state['scores'][player] += points
                state['log'].append(
                    _('%s pocketed %s for %d point%s.') % (
                        player_name,
                        action,
                        points,
                        '' if points == 1 else 's',
                    ))
                status.set_text(
                    _('%s scored. Switch turns when ready.') % player_name)
            self._set_live_edit_target(_('carrom pocket controls'))
        elif action == 'foul':
            state['fouls'][player] += 1
            if state['scores'][player] > 0:
                state['scores'][player] -= 1
            state['log'].append(_('%s made a foul.') % player_name)
            status.set_text(_('Foul recorded. Switch turns.'))
            self._set_live_edit_target(_('carrom foul control'))
        elif action == 'switch':
            state['turn'] = 'B' if player == 'A' else 'A'
            status.set_text(
                _('%s to shoot next.') %
                self._generated_carrom_player_name(state))
            self._set_live_edit_target(_('carrom turn control'))
        elif action == 'reset':
            state['turn'] = 'A'
            state['scores'] = {'A': 0, 'B': 0}
            state['fouls'] = {'A': 0, 'B': 0}
            state['coins'] = {'white': 9, 'black': 9, 'queen': 1}
            state['aim'] = [0.5, 0.82]
            state['log'] = []
            status.set_text(_('New carrom match ready.'))
            self._set_live_edit_target(_('carrom reset control'))
        state['log'] = state['log'][-8:]
        self._refresh_generated_carrom_preview(
            status, score, log, drawing, state)

    def __generated_counter_clicked_cb(self, button, label, state, amount):
        state['count'] += amount
        label.set_text(str(state['count']))
        self._set_live_edit_target(_('counter controls'))

    def __generated_counter_reset_clicked_cb(self, button, label, state):
        state['count'] = 0
        label.set_text('0')
        self._set_live_edit_target(_('counter reset control'))

    def __generated_carrom_draw_cb(self, widget, context, state):
        left, top, size = self._generated_square_geometry(widget)
        context.set_source_rgb(0.92, 0.80, 0.58)
        context.rectangle(left, top, size, size)
        context.fill()

        border = max(style.zoom(7), size * 0.035)
        context.set_source_rgb(0.44, 0.22, 0.10)
        context.set_line_width(border)
        context.rectangle(left + border / 2.0, top + border / 2.0,
                          size - border, size - border)
        context.stroke()

        context.set_source_rgb(0.64, 0.35, 0.16)
        context.set_line_width(max(2, size * 0.006))
        context.rectangle(left + size * 0.12, top + size * 0.12,
                          size * 0.76, size * 0.76)
        context.stroke()

        for nx, ny in ((0.08, 0.08), (0.92, 0.08),
                       (0.08, 0.92), (0.92, 0.92)):
            self._draw_generated_disc(
                context, left + nx * size, top + ny * size,
                size * 0.052, (0.05, 0.05, 0.05), (0.35, 0.18, 0.08))

        context.set_source_rgb(0.52, 0.22, 0.12)
        context.arc(left + size * 0.5, top + size * 0.5,
                    size * 0.16, 0, 2 * math.pi)
        context.stroke()

        self._draw_generated_carrom_coins(context, left, top, size, state)

        aim_x = left + state['aim'][0] * size
        aim_y = top + state['aim'][1] * size
        context.set_source_rgb(0.20, 0.35, 0.75)
        context.set_line_width(max(2, size * 0.006))
        context.move_to(aim_x, aim_y)
        context.line_to(left + size * 0.5, top + size * 0.5)
        context.stroke()
        self._draw_generated_disc(
            context, aim_x, aim_y, size * 0.04,
            (0.94, 0.94, 0.98), (0.20, 0.35, 0.75))
        return False

    def _draw_generated_carrom_coins(self, context, left, top, size, state):
        positions = (
            (0.00, -0.09), (0.08, -0.04), (0.08, 0.05),
            (0.00, 0.10), (-0.08, 0.05), (-0.08, -0.04),
            (0.15, 0.00), (-0.15, 0.00), (0.00, 0.18),
            (0.00, -0.18), (0.14, 0.12), (-0.14, 0.12),
            (0.14, -0.12), (-0.14, -0.12), (0.21, 0.08),
            (-0.21, 0.08), (0.21, -0.08), (-0.21, -0.08),
        )
        radius = size * 0.028
        index = 0
        for count, fill, stroke in (
                (state['coins']['white'],
                 (0.96, 0.94, 0.86), (0.55, 0.48, 0.38)),
                (state['coins']['black'],
                 (0.08, 0.08, 0.08), (0.35, 0.35, 0.35))):
            for unused in range(count):
                dx, dy = positions[index % len(positions)]
                self._draw_generated_disc(
                    context, left + size * (0.5 + dx),
                    top + size * (0.5 + dy), radius, fill, stroke)
                index += 1
        if state['coins']['queen']:
            self._draw_generated_disc(
                context, left + size * 0.5, top + size * 0.5,
                radius * 1.05, (0.72, 0.05, 0.08),
                (0.40, 0.02, 0.04))

    def _draw_generated_disc(self, context, x, y, radius, fill, stroke):
        context.set_source_rgb(fill[0], fill[1], fill[2])
        context.arc(x, y, radius, 0, 2 * math.pi)
        context.fill_preserve()
        context.set_source_rgb(stroke[0], stroke[1], stroke[2])
        context.set_line_width(max(1, radius * 0.16))
        context.stroke()

    def _generated_square_geometry(self, widget):
        allocation = widget.get_allocation()
        size = min(allocation.width, allocation.height) - style.zoom(18)
        if size <= 0:
            size = min(allocation.width, allocation.height)
        left = (allocation.width - size) / 2.0
        top = (allocation.height - size) / 2.0
        return left, top, size

    def _generated_carrom_player_name(self, state):
        return _('Student A') if state['turn'] == 'A' else _('Student B')

    def _refresh_generated_carrom_preview(self, status, score, log, drawing,
                                          state):
        score.set_text(
            _('Score - Student A: %(a)d  Student B: %(b)d\n'
              'Fouls - Student A: %(fa)d  Student B: %(fb)d\n'
              'Coins left - white: %(white)d  black: %(black)d  '
              'queen: %(queen)d\n'
              'Aim marker: %(x).0f%% across, %(y).0f%% down') % {
                  'a': state['scores']['A'],
                  'b': state['scores']['B'],
                  'fa': state['fouls']['A'],
                  'fb': state['fouls']['B'],
                  'white': state['coins']['white'],
                  'black': state['coins']['black'],
                  'queen': state['coins']['queen'],
                  'x': state['aim'][0] * 100,
                  'y': state['aim'][1] * 100,
              })
        moves = state['log']
        if moves:
            log.set_text('\n'.join(
                '%d. %s' % (index + 1, move)
                for index, move in enumerate(moves[-8:])
            ))
        else:
            log.set_text(
                _('1. Student A chooses an aim point\n'
                  '2. Record pocket, queen, or foul\n'
                  '3. Switch to Student B\n'
                  '4. Save the match in the Journal'))
        drawing.queue_draw()

    def _refresh_generated_chess_preview(self, status, state, buttons, log):
        board = state['board']
        selected = state['selected']
        for row in range(8):
            for col in range(8):
                button = buttons[row][col]
                button.set_label(board[row][col] or ' ')
                context = button.get_style_context()
                if selected == (row, col):
                    context.add_class('create-ai-generated-chess-selected')
                else:
                    context.remove_class('create-ai-generated-chess-selected')
                square = self._generated_chess_square_name(row, col)
                piece = board[row][col]
                tooltip = self._generated_chess_piece_name(piece)
                button.set_tooltip_text('%s %s' % (square, tooltip))

        if log is None:
            return

        moves = state['moves']
        if moves:
            first = max(0, len(moves) - 8)
            log.set_text('\n'.join(
                '%d. %s' % (index + 1, move)
                for index, move in enumerate(moves[first:], first)
            ))
        else:
            log.set_text(
                _('1. White makes a legal move\n'
                  '2. Black answers\n'
                  '3. Explain the move idea\n'
                  '4. Install and open when the preview feels ready'))

    def _generated_chess_square_name(self, row, col):
        return '%s%d' % ('abcdefgh'[col], 8 - row)

    def _generated_chess_piece_color(self, piece):
        if piece in '♙♖♘♗♕♔':
            return 'white'
        if piece in '♟♜♞♝♛♚':
            return 'black'
        return ''

    def _generated_chess_piece_name(self, piece):
        names = {
            '♔': _('White king'),
            '♕': _('White queen'),
            '♖': _('White rook'),
            '♗': _('White bishop'),
            '♘': _('White knight'),
            '♙': _('White pawn'),
            '♚': _('Black king'),
            '♛': _('Black queen'),
            '♜': _('Black rook'),
            '♝': _('Black bishop'),
            '♞': _('Black knight'),
            '♟': _('Black pawn'),
        }
        return names.get(piece, _('empty square'))

    def _generated_chess_piece_kind(self, piece):
        kinds = {
            '♔': 'king', '♚': 'king',
            '♕': 'queen', '♛': 'queen',
            '♖': 'rook', '♜': 'rook',
            '♗': 'bishop', '♝': 'bishop',
            '♘': 'knight', '♞': 'knight',
            '♙': 'pawn', '♟': 'pawn',
        }
        return kinds.get(piece, '')

    def _generated_chess_can_move(self, board, piece, start_row, start_col,
                                  row, col):
        if not piece:
            return False
        color = self._generated_chess_piece_color(piece)
        target = board[row][col]
        if target and self._generated_chess_piece_color(target) == color:
            return False

        dr = row - start_row
        dc = col - start_col
        abs_dr = abs(dr)
        abs_dc = abs(dc)
        kind = self._generated_chess_piece_kind(piece)

        if kind == 'pawn':
            direction = -1 if color == 'white' else 1
            home_row = 6 if color == 'white' else 1
            if dc == 0 and not target:
                if dr == direction:
                    return True
                if start_row == home_row and dr == 2 * direction:
                    return not board[start_row + direction][start_col]
            return abs_dc == 1 and dr == direction and bool(target)
        if kind == 'knight':
            return (abs_dr, abs_dc) in ((1, 2), (2, 1))
        if kind == 'king':
            return max(abs_dr, abs_dc) == 1
        if kind == 'bishop':
            return abs_dr == abs_dc and self._generated_chess_path_clear(
                board, start_row, start_col, row, col)
        if kind == 'rook':
            return (dr == 0 or dc == 0) and \
                self._generated_chess_path_clear(
                    board, start_row, start_col, row, col)
        if kind == 'queen':
            diagonal = abs_dr == abs_dc
            straight = dr == 0 or dc == 0
            return (diagonal or straight) and \
                self._generated_chess_path_clear(
                    board, start_row, start_col, row, col)
        return False

    def _generated_chess_path_clear(self, board, start_row, start_col,
                                    row, col):
        step_row = self._generated_chess_step(row - start_row)
        step_col = self._generated_chess_step(col - start_col)
        current_row = start_row + step_row
        current_col = start_col + step_col
        while (current_row, current_col) != (row, col):
            if board[current_row][current_col]:
                return False
            current_row += step_row
            current_col += step_col
        return True

    def _generated_chess_step(self, value):
        if value < 0:
            return -1
        if value > 0:
            return 1
        return 0

    def _set_generation_step_active(self, active_index):
        for index, step in enumerate(self._preview_generation_steps):
            context = step.get_style_context()
            if index <= active_index:
                context.add_class('create-ai-generation-step-active')
            else:
                context.remove_class('create-ai-generation-step-active')
        for index, row in enumerate(
                self._preview_generation_step_boxes):
            context = row.get_style_context()
            if index == active_index:
                context.add_class('create-ai-generation-step-row-active')
            else:
                context.remove_class(
                    'create-ai-generation-step-row-active')

    def _generation_step_index_for_stage(self, stage):
        stage_indexes = {
            'queued': 0,
            'enhancing': 0,
            'planning': 0,
            'provider': 0,
            'grounding': 1,
            'generating': 2,
            'validating': 3,
            'packaging': 4,
            'finished': 4,
        }
        return stage_indexes.get(stage, 0)

    def __expand_button_clicked_cb(self, button):
        window = self.get_toplevel()
        if not isinstance(window, Gtk.Window):
            return

        if self._is_fullscreen:
            window.unfullscreen()
            self._is_fullscreen = False
        else:
            window.fullscreen()
            window.present()
            self._is_fullscreen = True

    def __option_card_clicked_cb(self, clicked_button, group_name, value):
        for button in self._option_buttons[group_name]:
            button.get_style_context().remove_class(
                'create-ai-option-card-active')
        clicked_button.get_style_context().add_class(
            'create-ai-option-card-active')
        self._selected_options[group_name] = value

        if group_name == 'template':
            self._update_template_hint()
            self._update_template_card_icons()
        elif group_name in ('planner', 'policy'):
            self._update_planner_hint()
        elif group_name == 'license':
            self._update_license_hint()
        self._refresh_generated_context()

        status = {
            'make': _('Make'),
            'play': _('Play'),
            'share': _('Share'),
            'logic_math': _('Logic & math'),
            'science': _('Science'),
            'language': _('Language'),
            'tools_utils': _('Tools/utilities'),
            'games': _('Games'),
            'creation': _('Creation'),
            'default': _('Default'),
            'rag': _('RAG'),
            'validate': _('Validate'),
            'standard': _('Standard'),
            'local': _('Local'),
            'strict': _('Strict'),
            'on': _('On'),
            'off': _('Off'),
        }
        if self._prompt_status_label is not None:
            if group_name == 'license':
                self._prompt_status_label.set_text(
                    self._get_selected_license()['label'])
            else:
                self._prompt_status_label.set_text(status.get(value, value))

    def __code_size_combo_changed_cb(self, combo):
        self._selected_options['code_size'] = combo.get_active_id() or 'standard'

    def __provider_combo_changed_cb(self, combo):
        provider_name = combo.get_active_id() or 'default'
        if provider_name == self._selected_options['provider']:
            return

        self._selected_options['provider'] = provider_name
        self._provider_key_entry.set_text('')
        self._provider_model_entry.set_text('')
        self._provider_endpoint_entry.set_text('')
        if self._provider_chip_value_label is not None:
            self._provider_chip_value_label.set_text(
                self._get_provider_label(provider_name))
        self._update_provider_controls()
        self._update_planner_hint()

    def __provider_apply_clicked_cb(self, button):
        provider = self._configure_selected_provider(persist=True)
        if provider is not True and provider:
            if self._provider_status_label is not None:
                self._provider_status_label.set_text(
                    _('Provider saved. Ready to generate activities.'))
            if self._prompt_status_label is not None:
                self._prompt_status_label.set_text(_('Ready to generate'))

    def __provider_paste_clicked_cb(self, button):
        self._paste_provider_key_from_clipboard()

    def __provider_key_entry_key_press_event_cb(self, entry, event):
        modifiers = Gtk.accelerator_get_default_mod_mask()
        state = event.state & modifiers
        ctrl = state & Gdk.ModifierType.CONTROL_MASK
        shift = state & Gdk.ModifierType.SHIFT_MASK
        if ctrl and event.keyval in (Gdk.KEY_v, Gdk.KEY_V):
            if not entry.get_sensitive():
                if self._provider_status_label is not None:
                    self._provider_status_label.set_text(
                        _('Choose a cloud provider before pasting a key.'))
                return True
            if self._provider_status_label is not None:
                self._provider_status_label.set_text(_('Pasting API key...'))
            GObject.idle_add(self.__provider_key_entry_paste_finished_cb)
            return False
        if shift and event.keyval == Gdk.KEY_Insert:
            if self._provider_status_label is not None:
                self._provider_status_label.set_text(_('Pasting API key...'))
            GObject.idle_add(self.__provider_key_entry_paste_finished_cb)
            return False
        return False

    def __provider_remove_clicked_cb(self, button):
        provider_name = self._selected_options['provider']
        if provider_name not in (
                'freemodel', 'gemini', 'openai', 'deepseek', 'qwen', 'moonshot',
                'opencode', 'opencode-go', 'claude'):
            return

        from jarabe.model.aodservice import get_service

        try:
            get_service().remove_provider_api_key(provider_name)
        except Exception as error:
            logging.exception('Could not remove saved provider key')
            self._provider_status_label.set_text(str(error))
            return
        self._provider_key_entry.set_text('')
        self._update_provider_controls()
        self._provider_status_label.set_text(
            _('%s API key removed.') %
            self._get_provider_label(provider_name))

    def _select_studio_tab(self, tab_name):
        if self._studio_mode_stack is not None:
            self._studio_mode_stack.set_visible_child_name(tab_name)

        if self._studio_preview_tab is not None:
            self._studio_preview_tab.get_style_context().remove_class(
                'create-ai-studio-tab-active')
        if self._studio_review_tab is not None:
            self._studio_review_tab.get_style_context().remove_class(
                'create-ai-studio-tab-active')
        if self._studio_versions_tab is not None:
            self._studio_versions_tab.get_style_context().remove_class(
                'create-ai-studio-tab-active')

        if tab_name == 'review' and self._studio_review_tab is not None:
            self._studio_review_tab.get_style_context().add_class(
                'create-ai-studio-tab-active')
        elif tab_name == 'versions' and self._studio_versions_tab is not None:
            self._studio_versions_tab.get_style_context().add_class(
                'create-ai-studio-tab-active')
        elif self._studio_preview_tab is not None:
            self._studio_preview_tab.get_style_context().add_class(
                'create-ai-studio-tab-active')

    def __studio_tab_clicked_cb(self, button, tab_name):
        self._select_studio_tab(tab_name)

    def __review_file_clicked_cb(self, button, file_key):
        self._set_review_file(file_key)

    def __version_switch_clicked_cb(self, button, mode):
        self._set_versions_mode(mode)

    def __version_card_button_release_cb(self, card, event, version_key):
        if event.button != 1:
            return False

        self._selected_version = version_key
        self._set_versions_mode('source')
        return False

    def __prompt_buffer_changed_cb(self, text_buffer):
        if self._prompt_char_label is None:
            return

        start, end = text_buffer.get_bounds()
        count = len(text_buffer.get_text(start, end, True))
        if count > 0:
            self._prompt_char_label.set_text(_('%d chars') % count)
        else:
            self._prompt_char_label.set_text('')

    def __prompt_entry_activate_cb(self, entry):
        self.__send_button_clicked_cb(entry)

    def __prompt_button_press_event_cb(self, text_view, event):
        self._clear_prompt_placeholder()
        text_view.grab_focus()
        return False

    def __prompt_key_press_event_cb(self, text_view, event):
        self._clear_prompt_placeholder()
        modifiers = Gtk.accelerator_get_default_mod_mask()
        state = event.state & modifiers
        ctrl = state & Gdk.ModifierType.CONTROL_MASK
        shift = state & Gdk.ModifierType.SHIFT_MASK
        if ctrl and event.keyval in (Gdk.KEY_v, Gdk.KEY_V):
            return self._paste_prompt_from_clipboard()
        if shift and event.keyval == Gdk.KEY_Insert:
            return self._paste_prompt_from_clipboard()
        return False

    def _paste_prompt_from_clipboard(self):
        if self._prompt_text is None:
            return False

        self._clear_prompt_placeholder()
        self._prompt_text.grab_focus()
        Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).request_text(
            self.__prompt_clipboard_text_received_cb)
        return True

    def __prompt_clipboard_text_received_cb(self, clipboard, text):
        if not text:
            text = self._read_external_prompt_clipboard_text()
        if not text:
            if self._prompt_status_label is not None:
                self._prompt_status_label.set_text(_('Clipboard empty'))
            return

        text_buffer = self._prompt_text.get_buffer()
        insert_iter = text_buffer.get_iter_at_mark(text_buffer.get_insert())
        text_buffer.insert(insert_iter, text)
        if self._prompt_status_label is not None:
            self._prompt_status_label.set_text(_('Ready'))

    def __prompt_focus_in_event_cb(self, text_view, event):
        self._clear_prompt_placeholder()
        return False

    def __prompt_focus_out_event_cb(self, text_view, event):
        if not self._get_prompt_text():
            self._set_prompt_placeholder()
        return False

    def __prompt_example_clicked_cb(self, button):
        self._set_prompt_text(
            _('Treasure-map quest where teams solve clues and explain each '
              'step.'))
        self._prompt_text.grab_focus()
        if self._prompt_status_label is not None:
            self._prompt_status_label.set_text(_('Ready'))

    def __send_button_clicked_cb(self, button):
        prompt = self._get_prompt_text()
        if not prompt:
            self._clear_prompt_placeholder()
            self._prompt_text.grab_focus()
            if self._prompt_status_label is not None:
                self._prompt_status_label.set_text(_('Need prompt'))
            return

        self._submit_generation_from_prompt(prompt, chat_prompt=prompt)

    def _submit_generation_from_prompt(self, prompt, chat_prompt=None):
        from jarabe.model.aodspec import ActivitySpec
        from jarabe.model.aodspec import name_from_prompt

        license_info = self._get_selected_license()

        age_band_map = {
            'primary': 'ages 6-9',
            'middle': 'ages 10-13',
            'senior': 'ages 14+',
            'all': 'all',
        }
        age_band = age_band_map.get(
            self._selected_options.get('age_band', 'all'), 'all')

        collab_prefix = {
            'pair': _('Two learners collaborate together. '),
            'class': _('Whole class activity with teacher facilitation. '),
        }.get(self._selected_options.get('collab', 'solo'), '')

        spec = ActivitySpec(
            name=name_from_prompt(prompt),
            prompt=collab_prefix + prompt,
            category=self._selected_options['template'],
            license_id=license_info['spdx'],
            code_size=self._selected_options.get('code_size', 'standard'),
            age_band=age_band,
        )
        self._submit_generation_spec(
            spec,
            chat_prompt=chat_prompt or prompt,
            display_prompt=prompt,
            is_refinement=False,
        )

    def _submit_refinement_from_prompt(self, refinement, source='chat'):
        if self._generation_result is None:
            self._submit_generation_from_prompt(
                refinement,
                chat_prompt=refinement,
            )
            return

        target = self._live_edit_target or _('activity canvas')
        backend_refinement = refinement
        display_refinement = refinement
        if source == 'preview':
            if self._live_edit_target_is_region:
                target_note = (
                    'The learner dragged a selection over the live '
                    'preview. The target below is that rectangle, in '
                    'percent of the activity canvas measured from its '
                    'top-left corner (x, y • width × height). '
                    'Work out which widgets or drawing fall inside that '
                    'region and apply the change to them.'
                )
            else:
                target_note = (
                    'The learner clicked this specific part of the live '
                    'preview. Apply the change to it.'
                )
            backend_refinement = (
                '%(note)s Keep the rest of the activity working '
                'unchanged.\n'
                'Target: %(target)s\n'
                'Change: %(change)s'
            ) % {
                'note': target_note,
                'target': target,
                'change': refinement,
            }
            display_refinement = _('%(target)s: %(change)s') % {
                'target': target,
                'change': refinement,
            }
        if source == 'preview':
            self._set_live_edit_status(_('Refining preview...'))
        if source == 'sidebar' and \
                self._sidebar_refine_status_label is not None:
            self._sidebar_refine_status_label.set_text(_('Refining...'))
        spec = self._build_refinement_spec(backend_refinement)
        self._submit_generation_spec(
            spec,
            chat_prompt=display_refinement,
            display_prompt=_('Refine: %s') % display_refinement,
            is_refinement=True,
        )

    def _build_refinement_spec(self, refinement):
        from jarabe.model.aodspec import ActivitySpec

        result = self._generation_result
        base_spec = result.spec.normalized()
        plan = result.plan if isinstance(result.plan, dict) else {}
        flow = plan.get('classroom_flow') or plan.get('learner_steps') or []
        flow_text = '\n'.join('- %s' % step for step in flow[:5])
        plan_context = self._compact_plan_for_refinement(plan)
        original_prompt = self._aod_original_prompt or base_spec.prompt
        prompt = (
            'Refine the existing generated Sugar activity. Preserve working '
            'behavior unless the new request changes it.\n\n'
            'Original learner request:\n%(original)s\n\n'
            'Current generated activity:\n'
            '- Name: %(name)s\n'
            '- Template: %(template)s\n'
            '- Summary: %(summary)s\n'
            '- Classroom flow:\n%(flow)s\n\n'
            'Current plan JSON excerpt:\n%(plan_context)s\n\n'
            'Current activity.py excerpt:\n%(source)s\n\n'
            'Refinement request:\n%(refinement)s'
        ) % {
            'original': original_prompt,
            'name': base_spec.name,
            'template': plan.get('template', base_spec.template),
            'summary': plan.get('summary', ''),
            'flow': flow_text or '- Keep the activity usable for learners.',
            'plan_context': plan_context,
            'source': self._source_context_for_refinement(result),
            'refinement': refinement,
        }
        prompt = self._limit_refinement_prompt(prompt)
        template = plan.get('template', base_spec.template)
        return ActivitySpec(
            name=base_spec.name,
            prompt=prompt,
            category=base_spec.category,
            license_id=base_spec.license_id,
            template=template,
            age_band=base_spec.age_band,
            learner_goal=base_spec.learner_goal or
            plan.get('learner_goal', ''),
            code_size=self._selected_options.get('code_size', 'standard'),
        )

    def _compact_plan_for_refinement(self, plan):
        if not isinstance(plan, dict):
            return '{}'
        keys = (
            'template',
            'activity_kind',
            'summary',
            'learner_goal',
            'learner_steps',
            'interaction_model',
            'ui_regions',
            'state_schema',
            'features',
            'classroom_flow',
        )
        compact = {
            key: plan[key]
            for key in keys
            if key in plan
        }
        text = json.dumps(compact, indent=2, sort_keys=True)
        if len(text) <= 2200:
            return text
        return text[:2100].rstrip() + '\n...'

    def _source_context_for_refinement(self, result):
        files = getattr(result, 'files', {})
        if not isinstance(files, dict):
            return '# Current source is unavailable.'
        source = files.get('activity.py', '').strip()
        if not source:
            return '# Current source is unavailable.'
        return self._compact_source_for_refinement(source)

    def _compact_source_for_refinement(self, source):
        if len(source) <= 6500:
            return source
        head = source[:4200].rstrip()
        tail = source[-2200:].lstrip()
        return '%s\n\n# ... current source shortened ...\n\n%s' % (
            head,
            tail,
        )

    def _limit_refinement_prompt(self, prompt):
        if len(prompt) <= 18000:
            return prompt
        keep_head = prompt[:8800].rstrip()
        keep_tail = prompt[-8800:].lstrip()
        return '%s\n\n[Previous context shortened]\n\n%s' % (
            keep_head, keep_tail)

    def _submit_generation_spec(self, spec, chat_prompt=None,
                                display_prompt=None,
                                is_refinement=False):
        if self._has_active_generation_job():
            if self._prompt_status_label is not None:
                self._prompt_status_label.set_text(_('Already generating'))
            if self._sidebar_refine_status_label is not None:
                self._sidebar_refine_status_label.set_text(
                    _('Wait for the current generation to finish.'))
            self._append_chat_message(
                _('Please wait for the current activity generation to finish.'))
            return

        from jarabe.model.aodservice import get_service

        license_info = self._get_selected_license()
        planner = self._selected_options['planner']
        policy = self._selected_options['policy']
        service = get_service()
        provider_name = self._resolve_generation_provider_name(service)
        selected_provider = self._selected_options['provider']
        if provider_name == selected_provider and provider_name in (
                'freemodel', 'gemini', 'openai', 'deepseek', 'qwen', 'moonshot',
                'opencode', 'opencode-go', 'claude', 'ollama'):
            if not self._configure_selected_provider(persist=True):
                return

        if self._sidebar_refine_status_label is not None:
            if is_refinement:
                self._sidebar_refine_status_label.set_text(_('Refining...'))
            else:
                self._sidebar_refine_status_label.set_text(
                    _('Generating activity...'))
        use_rag = (planner != 'direct'
                   and policy not in ('local', 'strict'))
        validate_code = self._selected_options.get('validate', 'on') == 'on'

        self._detach_generation_job()
        self._generation_result = None
        if not is_refinement:
            self._aod_session_id = ''
            self._aod_active_revision_id = ''
            self._aod_original_prompt = spec.prompt
        if display_prompt is None:
            display_prompt = spec.prompt
        if is_refinement:
            self._set_prompt_text(display_prompt)
        else:
            self._set_prompt_text(spec.prompt)
        self._set_studio_prompt(display_prompt)
        self._update_preview_license_summary()
        self._append_chat_message(chat_prompt or display_prompt,
                                  from_user=True)
        self._append_sidebar_message(chat_prompt or display_prompt,
                                     from_user=True)
        if is_refinement:
            self._append_chat_status(_('Refining selected activity'))
            self._append_sidebar_status(_('Refining selected activity'))
        else:
            self._append_chat_status(_('Generating activity'))
            self._append_sidebar_status(_('Generating activity'))
        self._append_chat_status(
            _('Planner: %s · %s') %
            (self._get_provider_label(provider_name),
             license_info['label']))
        self._append_sidebar_status(
            _('Planner: %s · %s') %
            (self._get_provider_label(provider_name),
             license_info['label']))
        self._review_generation_context = {
            'provider': self._get_provider_label(provider_name),
            'stage': 'queued',
            'progress': 0.0,
            'message': _('Queued generation request'),
            'prompt': chat_prompt or display_prompt,
            'is_refinement': is_refinement,
            'draft_activity_source': '',
        }
        self._review_draft_was_shown = False
        self._set_review_file(self._current_review_file)
        self._use_studio_layout()
        self._select_studio_tab('preview')
        self._stack.set_visible_child_name('studio')
        if self._preview_empty_title is not None:
            if is_refinement:
                self._preview_empty_title.set_text(_('Refining activity'))
            else:
                self._preview_empty_title.set_text(_('Generating activity'))
        if is_refinement:
            self._start_generation_animation(
                _('Applying the refinement and preparing files...'))
        else:
            self._start_generation_animation(
                _('Planning the activity and preparing files...'))

        if self._provider_status_label is not None:
            self._provider_status_label.set_text(
                _('Generating with %s...') %
                self._get_provider_label(provider_name))
        if self._prompt_status_label is not None:
            if is_refinement:
                self._prompt_status_label.set_text(_('Refining'))
            else:
                self._prompt_status_label.set_text(_('Generating'))

        self._enhanced_prompt_announced = False
        try:
            job = service.submit_activity(
                spec,
                provider_name=provider_name,
                use_rag=use_rag,
                validate_code=validate_code,
                session_id=self._aod_session_id if is_refinement else '',
                parent_revision_id=(
                    self._aod_active_revision_id if is_refinement else ''),
                user_prompt=chat_prompt or display_prompt,
                enhance=self._selected_options.get('enhance', 'on') == 'on',
            )
        except Exception as error:
            logging.exception('Could not submit Activity on Demand job')
            self._generation_failed_cb(str(error))
            return

        self._generation_job_id = job.job_id
        self._aod_session_id = job.session_id
        self._set_chat_entry_sensitive(False)
        service.watch(job.job_id, self._generation_job_callback)
        self._generation_job_updated_from_worker(job)

    def _set_chat_entry_sensitive(self, sensitive):
        if self._chat_entry is not None:
            self._chat_entry.set_sensitive(sensitive)
            if sensitive:
                self._chat_entry.set_placeholder_text(
                    _('Ask for a refinement...'))
                if self._stack.get_visible_child_name() == 'studio':
                    self._chat_entry.grab_focus()

    def _has_active_generation_job(self):
        if self._generation_job_id is None:
            return False

        from jarabe.model.aodservice import get_service

        job = get_service().get_job(self._generation_job_id)
        return job is not None and not job.is_terminal()

    def _generation_job_updated_from_worker(self, job):
        GObject.idle_add(self._generation_job_updated_cb, job.job_id)

    def _generation_job_updated_cb(self, job_id):
        if job_id != self._generation_job_id:
            return False

        from jarabe.model.aodjobs import STATUS_CANCELLED
        from jarabe.model.aodjobs import STATUS_FAILED
        from jarabe.model.aodjobs import STATUS_FINISHED
        from jarabe.model.aodservice import get_service

        job = get_service().get_job(job_id)
        if job is None:
            return False

        if job.status == STATUS_FINISHED:
            if job.result is not None:
                self._aod_session_id = job.session_id
                self._aod_active_revision_id = job.result_summary.get(
                    'revision_id', '')
                self._generation_finished_cb(job.result)
            return False

        if job.status == STATUS_FAILED:
            self._generation_failed_cb(job.error or job.message, job=job)
            return False

        if job.status == STATUS_CANCELLED:
            self._generation_failed_cb(_('Generation cancelled'))
            return False

        self._generation_progress_cb(
            job.stage,
            job.progress,
            job.message,
            job,
        )
        return False

    def _generation_progress_cb(self, stage, fraction, message, job=None):
        if self._prompt_status_label is not None:
            self._prompt_status_label.set_text(message)
        enhanced = getattr(job, 'enhanced_prompt', '') if job else ''
        if enhanced and not self._enhanced_prompt_announced:
            self._enhanced_prompt_announced = True
            self._append_chat_status(_('✨ Enhanced your prompt'))
            self._append_chat_message(
                _('I understood your idea as:\n%s') % enhanced,
                from_user=False)
        self._update_live_review_generation(stage, fraction, message, job)
        self._update_provider_call_status(stage, fraction, message)
        self._update_generation_animation(stage, fraction, message)
        if self._preview_empty_title is not None:
            if self._preview_empty_title.get_text() != _('Building your activity'):
                self._preview_empty_title.set_text(_('Building your activity'))
        if self._preview_empty_note is not None:
            self._preview_empty_note.set_text(
                _('%(stage)s - %(percent)d%%') % {
                    'stage': message,
                    'percent': int(fraction * 100),
                }
            )
        return False

    def _update_live_review_generation(self, stage, fraction, message,
                                       job=None):
        if not self._review_generation_context:
            return
        self._review_generation_context['stage'] = stage
        self._review_generation_context['progress'] = max(
            0.0,
            min(1.0, float(fraction)),
        )
        self._review_generation_context['message'] = message
        draft_source = getattr(job, 'draft_activity_source', '') if job else ''
        if draft_source:
            self._review_generation_context['draft_activity_source'] = \
                draft_source
            if not self._review_draft_was_shown:
                self._review_draft_was_shown = True
        self._set_review_file(self._current_review_file)

    def _update_provider_call_status(self, stage, fraction, message):
        if self._provider_status_label is None:
            return

        provider = self._get_provider_label(
            self._selected_options.get('provider', 'default'))
        percent = int(fraction * 100)
        if stage == 'enhancing':
            self._provider_status_label.set_text(
                _('%(provider)s is clarifying the idea before planning '
                  '- %(percent)d%%') % {
                    'provider': provider,
                    'percent': percent,
                }
            )
        elif stage == 'grounding':
            self._provider_status_label.set_text(
                _('RAG selected Sugar examples for %(provider)s context - '
                  '%(percent)d%%. No training or ingestion is happening.') % {
                    'provider': provider,
                    'percent': percent,
                }
            )
        elif stage == 'provider':
            self._provider_status_label.set_text(
                _('API call active: %(provider)s is planning from RAG context '
                  '- '
                  '%(percent)d%%. %(message)s') % {
                    'provider': provider,
                    'percent': percent,
                    'message': message,
                }
            )
        elif stage == 'generating':
            self._provider_status_label.set_text(
                _('API/code step active: %(provider)s is preparing the '
                  'activity - %(percent)d%%. %(message)s') % {
                    'provider': provider,
                    'percent': percent,
                    'message': message,
                }
            )
        elif stage == 'validating':
            self._provider_status_label.set_text(
                _('Model response received. Sugar is assembling the activity '
                  '- %(percent)d%%') % {'percent': percent}
            )
        elif stage == 'packaging':
            self._provider_status_label.set_text(
                _('Activity generated. Sugar is packaging the XO - '
                  '%(percent)d%%') % {'percent': percent}
            )

    def _generation_finished_cb(self, result):
        self._detach_generation_job()
        self._generation_result = result
        self._review_generation_context = {}
        self._review_draft_was_shown = False
        self._complete_generation_animation(result)
        plan = result.plan if isinstance(result.plan, dict) else {}
        provider_status = self._generation_provider_status_text(result, plan)
        if self._prompt_status_label is not None:
            self._prompt_status_label.set_text(_('Ready'))
        if self._provider_status_label is not None:
            self._provider_status_label.set_text(provider_status)
        if self._preview_empty_title is not None:
            self._preview_empty_title.set_text(result.spec.name)
        if self._preview_empty_note is not None:
            provider = result.provider
            if result.model:
                provider = '%s / %s' % (provider, result.model)
            self._preview_empty_note.set_text(
                _('Reference family: %(template)s\nPlanner: %(provider)s\n'
                  '%(provider_status)s\n'
                  'Project: %(project)s\n'
                  'XO will be packaged when you export or install.') % {
                    'template': plan.get('template', ''),
                    'provider': provider,
                    'provider_status': provider_status,
                    'project': os.path.basename(result.project_path),
                }
            )
        if self._sidebar_refine_status_label is not None:
            self._sidebar_refine_status_label.set_text(
                _('Ready for another refinement.'))
        self._set_review_file(self._current_review_file)
        if self._aod_active_revision_id:
            self._selected_version = self._aod_active_revision_id
        self._refresh_version_history()
        self._append_chat_status(provider_status)
        chat_msgs = self._build_generation_chat_messages(result, plan)
        for i, msg in enumerate(chat_msgs):
            self._append_chat_message(
                msg, from_user=False,
                scroll=(i == len(chat_msgs) - 1))
        self._set_chat_entry_sensitive(True)
        self._append_sidebar_status(provider_status)
        self._append_sidebar_message(
            _('Generated. Type another prompt here to refine '
              'this activity.'))
        self._update_sidebar_challenges(result, plan)
        return False

    def _build_generation_chat_messages(self, result, plan):
        """Return a list of short chat bubbles describing the generated activity."""
        spec = result.spec
        name = spec.name or _('the activity')
        summary = plan.get('summary', '')
        activity_kind = plan.get('activity_kind', '')
        interaction = plan.get('interaction_model', '')
        template = plan.get('template', '')
        learner_steps = plan.get('learner_steps') or []
        features = plan.get('features') or []

        msgs = []

        # Bubble 1 — short opener with name + kind
        kind_parts = [p for p in (activity_kind, template) if p]
        if kind_parts:
            msgs.append(
                _("Done! I built %(name)s — %(kind)s.") % {
                    'name': name,
                    'kind': kind_parts[0],
                })
        else:
            msgs.append(_("Done! %(name)s is ready.") % {'name': name})

        # Bubble 2 — one-line summary or interaction model
        detail = summary or (
            _('Interaction: %s') % interaction if interaction else '')
        if detail:
            msgs.append(detail[:120])

        # Bubble 3 — first learner step or feature as a teaser
        teaser = next(iter(learner_steps or features), '')
        if teaser:
            msgs.append('• %s' % str(teaser)[:100])

        # Final bubble — action prompt
        msgs.append(_('Click anywhere in the preview to pick a target, '
                       'then tell me what to change.'))

        return msgs

    def _update_sidebar_challenges(self, result, plan):
        """Replace the learning sidebar challenge cards with activity-specific ones."""
        if self._sidebar_challenge_box is None:
            return

        for child in self._sidebar_challenge_box.get_children():
            self._sidebar_challenge_box.remove(child)

        challenges = self._build_activity_challenges(result, plan)

        for text in challenges:
            card = self._create_challenge_card(text)
            self._sidebar_challenge_box.pack_start(card, False, False, 0)
            card.show_all()

        if self._sidebar_level_label is not None:
            count = len(challenges)
            self._sidebar_level_label.set_text(
                _('Level 1 unlocked - %(count)d challenges') % {
                    'count': count})

    def _build_activity_challenges(self, result, plan):
        """Return a list of activity-specific challenge strings from the plan."""
        template = plan.get('template', '').lower()
        activity_kind = plan.get('activity_kind', '').lower()
        interaction = plan.get('interaction_model', '').lower()
        features = [str(f).lower() for f in (plan.get('features') or [])]
        learner_steps = [str(s) for s in (plan.get('learner_steps') or [])]
        spec = result.spec
        name = spec.name or _('the activity')

        challenges = []

        # 1 — always: rename the title to something personal
        challenges.append(
            _('Rename the activity title to reflect your own topic.'))

        # 2 — learner steps → suggest modifying one of them
        if learner_steps:
            step_hint = learner_steps[0]
            challenges.append(
                _('Find the code that handles: "%(step)s" and add a hint '
                  'message for the learner.') % {'step': step_hint})

        # 3 — template/kind specific
        if 'chess' in template or 'chess' in activity_kind:
            challenges.append(
                _('Locate the move-validation logic and add a console print '
                  'for each illegal move attempt.'))
            challenges.append(
                _('Change the board colors and explain why you chose them.'))
        elif 'carrom' in template or 'carrom' in activity_kind:
            challenges.append(
                _('Find where the striker is drawn and change its color.'))
            challenges.append(
                _('Locate the score counter and add a "foul" penalty.'))
        elif 'draw' in template or 'paint' in template or 'draw' in activity_kind:
            challenges.append(
                _('Change the default brush size and add a label showing '
                  'the current size.'))
            challenges.append(
                _('Add a "Clear canvas" button that resets the drawing.'))
        elif 'quiz' in template or 'quiz' in activity_kind:
            challenges.append(
                _('Add one new question and answer to the quiz data.'))
            challenges.append(
                _('Change the feedback message shown when a learner answers '
                  'incorrectly.'))
        elif 'puzzle' in template or 'puzzle' in activity_kind:
            challenges.append(
                _('Find where the puzzle pieces are created and change one '
                  "piece's image or color."))
        elif 'story' in template or 'story' in activity_kind:
            challenges.append(
                _('Replace one paragraph of the story with your own version.'))
            challenges.append(
                _('Add a learner name field that appears at the start of '
                  'the story.'))
        else:
            # Generic fallbacks for unknown templates
            challenges.append(
                _('Find the main label or title widget and personalise the '
                  'text.'))
            challenges.append(
                _('Change one button label to make it more descriptive for '
                  'learners.'))

        # 4 — interaction-model specific
        if 'turn' in interaction or 'multiplayer' in interaction:
            challenges.append(
                _('Find where turns are tracked and add a visual indicator '
                  'showing whose turn it is.'))
        elif 'timed' in interaction or 'timer' in interaction:
            challenges.append(
                _('Locate the timer logic and change the countdown duration.'))

        # 5 — feature-based
        if any('journal' in f for f in features):
            challenges.append(
                _('Trace the write_file / read_file methods and describe '
                  'what data is saved to the Journal.'))
        if any('score' in f for f in features):
            challenges.append(
                _('Find the score variable and add a "high score" display '
                  'that persists across sessions.'))
        if any('color' in f or 'colour' in f for f in features):
            challenges.append(
                _('Change the color scheme in the activity and note which '
                  'variable controls each color.'))

        # 6 — always: Journal connection and export
        challenges.append(
            _('Describe what %(name)s teaches and why it matters for '
              'learners your age.') % {'name': name})
        challenges.append(
            _('Export the activity and test it by opening the XO file '
              'in another window.'))

        return challenges[:8]

    def _generation_provider_status_text(self, result, plan):
        fallback_reason = plan.get('provider_fallback_reason', '')
        if fallback_reason:
            return _('Provider did not answer: %s') % (
                self._short_provider_status(fallback_reason))

        if result.provider == 'local':
            return _('Provider: local activity builder')

        provider = self._get_provider_label(result.provider)
        if result.model:
            provider = '%s / %s' % (provider, result.model)

        if plan.get('code_source') == 'provider':
            return _('Provider plan and code received: %s') % provider

        code_fallback_reason = plan.get('codegen_fallback_reason', '')
        if code_fallback_reason:
            return _(
                'Provider planned activity; code generation failed: %s'
            ) % self._short_provider_status(code_fallback_reason)

        return _('Provider response received: %s') % provider

    def _short_provider_status(self, text):
        text = ' '.join(str(text).split())
        if len(text) <= 140:
            return text
        return text[:137].rstrip() + '...'

    def _generation_failed_cb(self, error_text, job=None):
        self._detach_generation_job()
        display_error = _clean_generation_error_text(error_text)
        draft_source = ''
        if job is not None:
            draft_source = getattr(job, 'draft_activity_source', '') or ''
        if self._review_generation_context:
            self._review_generation_context['stage'] = 'failed'
            self._review_generation_context['progress'] = 1.0
            self._review_generation_context['message'] = display_error
            if draft_source:
                self._review_generation_context['draft_activity_source'] = \
                    draft_source
        self._stop_generation_animation()
        if self._prompt_status_label is not None:
            self._prompt_status_label.set_text(_('Generation failed'))
        if self._provider_status_label is not None:
            self._provider_status_label.set_text(
                _('API/generation failed: %s') %
                self._short_provider_status(display_error))
        if self._sidebar_refine_status_label is not None:
            self._sidebar_refine_status_label.set_text(
                _('Generation failed. Try a smaller refinement.'))
        if self._preview_empty_title is not None:
            self._preview_empty_title.set_text(
                _('Could not generate activity'))
        if self._preview_empty_note is not None:
            self._preview_empty_note.set_text(display_error)
        self._append_chat_status(
            _('Generation failed: %s') % display_error)
        self._append_sidebar_message(
            _('Generation failed: %s') % display_error)
        self._set_chat_entry_sensitive(True)
        self._set_review_file(self._current_review_file)
        if draft_source:
            self._select_studio_tab('review')
        return False

    def __review_and_install_cb(self, button):
        self._select_studio_tab('review')

    def __preview_fullscreen_toggle_cb(self, button):
        self._preview_is_fullscreen = not self._preview_is_fullscreen
        if self._preview_is_fullscreen:
            if self._studio_left_panel is not None:
                self._studio_left_panel.hide()
            if self._sidebar_revealer is not None:
                self._sidebar_revealer.set_transition_duration(0)
                self._sidebar_revealer.set_reveal_child(False)
                self._sidebar_revealer.set_transition_duration(260)
            if self._preview_fullscreen_button is not None:
                self._preview_fullscreen_button.set_label(
                    _('⛶ Exit Fullscreen'))
            if self._live_edit_panel is not None:
                self._live_edit_panel.hide()
            if self._ask_bar is not None:
                self._ask_bar.show()
                if self._ask_bar_entry is not None:
                    self._ask_bar_entry.grab_focus()
        else:
            if self._studio_left_panel is not None:
                self._studio_left_panel.show()
            if self._sidebar_revealer is not None:
                self._sidebar_revealer.set_transition_duration(0)
                self._sidebar_revealer.set_reveal_child(
                    self._sidebar_visible)
                self._sidebar_revealer.set_transition_duration(260)
            if self._preview_fullscreen_button is not None:
                self._preview_fullscreen_button.set_label(
                    _('⛶ Fullscreen'))
            if self._ask_bar is not None:
                self._ask_bar.hide()
            if self._live_edit_panel is not None:
                self._live_edit_panel.show()
            self._refresh_preview_layout()

    def __sidebar_toggle_cb(self, button):
        self._sidebar_visible = not self._sidebar_visible
        if self._sidebar_toggle_button is not None:
            self._sidebar_toggle_button.set_label(
                _('◀ Sidebar') if self._sidebar_visible else _('▶ Sidebar'))
        if self._sidebar_revealer is not None:
            self._sidebar_revealer.set_reveal_child(self._sidebar_visible)

    def __sidebar_reveal_done_cb(self, revealer, _param):
        self._refresh_preview_layout()

    def _refresh_preview_layout(self):
        GObject.idle_add(self.__do_refresh_preview_layout)
        GLib.timeout_add(200, self.__do_refresh_preview_layout)

    def __do_refresh_preview_layout(self):
        if self._studio_mode_stack is not None:
            self._studio_mode_stack.queue_resize()
            self._studio_mode_stack.queue_draw()
        if self._live_preview_canvas is not None:
            self._live_preview_canvas.queue_resize()
            self._live_preview_canvas.queue_draw()
        return False

    def _ensure_generation_bundle(self):
        if self._generation_result is None:
            raise ValueError('Generate first')

        bundle_path = self._generation_result.bundle_path
        if bundle_path and os.path.isfile(bundle_path):
            return bundle_path

        if self._prompt_status_label is not None:
            self._prompt_status_label.set_text(_('Packaging XO...'))
        self._append_chat_status(_('Packaging XO bundle...'))

        from jarabe.model.aodpipeline import package_generation_result

        bundle_path = package_generation_result(self._generation_result)
        self._append_chat_status(_('XO bundle packaged.'))
        if self._provider_status_label is not None:
            self._provider_status_label.set_text(
                _('XO packaged for export or install.'))
        return bundle_path

    def _prompt_and_apply_license(self, action_label):
        """Ask which license to bundle with, then apply it to the result.

        Returns True when the learner confirms and the license is applied,
        False when they cancel or the update fails.
        """
        if self._generation_result is None:
            return False

        options = self._get_license_options()
        current = self._selected_options.get('license', 'mit')

        dialog = Gtk.Dialog(
            title=_('Choose a license'),
            transient_for=self.get_toplevel(),
            modal=True,
        )
        dialog.add_button(_('Cancel'), Gtk.ResponseType.CANCEL)
        dialog.add_button(action_label, Gtk.ResponseType.ACCEPT)
        dialog.set_default_response(Gtk.ResponseType.ACCEPT)

        content = dialog.get_content_area()
        content.set_border_width(style.zoom(12))
        content.set_spacing(style.zoom(6))

        heading = Gtk.Label(
            _('Pick the license to bundle with this activity.'))
        heading.set_xalign(0)
        content.pack_start(heading, False, False, 0)
        heading.show()

        buttons = []
        group = None
        for option in options:
            radio = Gtk.RadioButton.new_with_label_from_widget(
                group, '%s — %s' % (option['label'], option['description']))
            if group is None:
                group = radio
            if option['value'] == current:
                radio.set_active(True)
            content.pack_start(radio, False, False, 0)
            radio.show()
            buttons.append((option['value'], radio))

        response = dialog.run()
        selected = current
        for value, radio in buttons:
            if radio.get_active():
                selected = value
                break
        dialog.destroy()

        if response != Gtk.ResponseType.ACCEPT:
            return False

        self._selected_options['license'] = selected

        from jarabe.model.aodpipeline import reapply_generation_license

        license_info = self._get_selected_license()
        try:
            reapply_generation_license(
                self._generation_result, license_info['spdx'])
        except Exception as error:
            logging.exception('Could not apply the selected license')
            if self._prompt_status_label is not None:
                self._prompt_status_label.set_text(_('License update failed'))
            self._append_chat_message(
                _('License update failed: %s') % error)
            return False

        self._refresh_generated_context()
        self._append_chat_status(
            _('License set to %s.') % license_info['label'])
        return True

    def __export_xo_cb(self, button):
        if self._generation_result is None:
            if self._prompt_status_label is not None:
                self._prompt_status_label.set_text(_('Generate first'))
            return

        if not self._prompt_and_apply_license(_('Export')):
            return

        try:
            bundle_path = self._ensure_generation_bundle()
        except Exception as error:
            logging.exception('Could not package generated XO bundle')
            if self._prompt_status_label is not None:
                self._prompt_status_label.set_text(_('Packaging failed'))
            self._append_chat_message(_('Packaging failed: %s') % error)
            return

        dialog = Gtk.FileChooserDialog(
            title=_('Export XO bundle'),
            parent=self.get_toplevel(),
            action=Gtk.FileChooserAction.SAVE,
        )
        dialog.add_buttons(
            _('Cancel'), Gtk.ResponseType.CANCEL,
            _('Export'), Gtk.ResponseType.ACCEPT,
        )
        dialog.set_do_overwrite_confirmation(True)
        dialog.set_current_name(os.path.basename(bundle_path))
        response = dialog.run()
        destination = dialog.get_filename()
        dialog.destroy()

        if response != Gtk.ResponseType.ACCEPT or not destination:
            return

        try:
            shutil.copy2(bundle_path, destination)
        except OSError as error:
            logging.exception('Could not export generated XO bundle')
            if self._prompt_status_label is not None:
                self._prompt_status_label.set_text(_('Export failed'))
            self._append_chat_message(_('Export failed: %s') % error)
            return

        if self._prompt_status_label is not None:
            self._prompt_status_label.set_text(_('Exported'))
        self._append_chat_message(
            _('XO bundle exported to %s') % destination)

    def __export_flatpak_cb(self, button):
        if self._generation_result is None:
            if self._prompt_status_label is not None:
                self._prompt_status_label.set_text(_('Generate first'))
            return

        if self._flatpak_export_running:
            if self._prompt_status_label is not None:
                self._prompt_status_label.set_text(_('Packaging Flatpak...'))
            return

        if not self._prompt_and_apply_license(_('Export')):
            return

        # Packaging can invoke flatpak-builder, which may run for many
        # minutes, so it must not block the Sugar shell's main loop.
        self._flatpak_export_running = True
        if self._prompt_status_label is not None:
            self._prompt_status_label.set_text(_('Packaging Flatpak...'))
        self._append_chat_status(_('Packaging Flatpak export...'))

        worker = threading.Thread(
            target=self._flatpak_export_worker,
            args=(self._generation_result,),
        )
        worker.daemon = True
        worker.start()

    def _flatpak_export_worker(self, result):
        from jarabe.model.aodflatpak import package_flatpak

        try:
            export = package_flatpak(result)
        except Exception as error:
            logging.exception('Could not package Flatpak export')
            GObject.idle_add(
                self._flatpak_export_finished_cb, None, str(error))
            return
        GObject.idle_add(self._flatpak_export_finished_cb, export, None)

    def _flatpak_export_finished_cb(self, export, error):
        # Hold the guard flag through the whole interaction, including the
        # (non-modal) save dialog's nested loop, so a second click cannot
        # start a concurrent export that collides on the staging paths.
        try:
            if error is not None or export is None:
                if self._prompt_status_label is not None:
                    self._prompt_status_label.set_text(_('Packaging failed'))
                self._append_chat_message(
                    _('Flatpak packaging failed: %s')
                    % (error or _('unknown')))
                return False

            artifact_path = export['path']
            if export['kind'] == 'flatpak':
                self._append_chat_status(
                    _('Built installable Flatpak bundle.'))
                title = _('Export Flatpak bundle')
            elif export.get('builder_available'):
                self._append_chat_status(
                    _('Flatpak build did not finish; exported buildable '
                      'Flatpak sources instead.'))
                title = _('Export Flatpak sources')
            else:
                self._append_chat_status(
                    _('flatpak-builder not found; exported buildable Flatpak '
                      'sources instead.'))
                title = _('Export Flatpak sources')

            dialog = Gtk.FileChooserDialog(
                title=title,
                parent=self.get_toplevel(),
                action=Gtk.FileChooserAction.SAVE,
            )
            dialog.add_buttons(
                _('Cancel'), Gtk.ResponseType.CANCEL,
                _('Export'), Gtk.ResponseType.ACCEPT,
            )
            dialog.set_do_overwrite_confirmation(True)
            dialog.set_current_name(os.path.basename(artifact_path))
            response = dialog.run()
            destination = dialog.get_filename()
            dialog.destroy()

            if response != Gtk.ResponseType.ACCEPT or not destination:
                return False

            try:
                shutil.copy2(artifact_path, destination)
            except OSError as copy_error:
                logging.exception('Could not export Flatpak artifact')
                if self._prompt_status_label is not None:
                    self._prompt_status_label.set_text(_('Export failed'))
                self._append_chat_message(
                    _('Export failed: %s') % copy_error)
                return False

            if self._prompt_status_label is not None:
                self._prompt_status_label.set_text(_('Exported'))
            if export['kind'] == 'flatpak':
                self._append_chat_message(
                    _('Flatpak bundle exported to %s') % destination)
            else:
                self._append_chat_message(
                    _('Flatpak sources exported to %s. Run flatpak-builder '
                      'to build the bundle.') % destination)
            return False
        finally:
            self._flatpak_export_running = False

    def __install_and_open_cb(self, button):
        if self._generation_result is None:
            if self._prompt_status_label is not None:
                self._prompt_status_label.set_text(_('Generate first'))
            return

        if not self._prompt_and_apply_license(_('Install & Open')):
            return

        from sugar3.bundle.activitybundle import ActivityBundle
        from sugar3.bundle.helpers import bundle_from_archive

        from jarabe.journal import misc
        from jarabe.model import bundleregistry

        try:
            bundle_path = self._ensure_generation_bundle()
            bundle = bundle_from_archive(
                bundle_path,
                mime_type=ActivityBundle.MIME_TYPE,
            )
            if bundle is None:
                raise ValueError('Sugar could not read the generated XO.')
            registry = bundleregistry.get_registry()
            registry.install(bundle, force_downgrade=True)
            installed = registry.get_bundle(
                self._generation_result.bundle_id)
            if installed is None:
                raise ValueError('Sugar did not register the activity.')
            misc.launch(installed)
        except Exception as error:
            logging.exception('Could not install generated activity')
            if self._prompt_status_label is not None:
                self._prompt_status_label.set_text(_('Install failed'))
            self._append_chat_message(_('Install failed: %s') % error)
            return

        if self._prompt_status_label is not None:
            self._prompt_status_label.set_text(_('Opening'))

    def __studio_back_cb(self, button):
        self._use_centered_layout()
        self._stack.set_visible_child_name('create')

    def __studio_rebuild_cb(self, button):
        self.__send_button_clicked_cb(button)

    def __live_edit_entry_activate_cb(self, entry):
        self.__live_edit_add_clicked_cb(entry)

    def __chat_entry_activate_cb(self, entry):
        self.__chat_send_clicked_cb(entry)

    def __chat_send_clicked_cb(self, button):
        if self._chat_entry is None:
            return

        text = self._chat_entry.get_text().strip()
        if not text:
            self._chat_entry.grab_focus()
            return

        self._chat_entry.set_text('')
        if self._generation_result is not None:
            self._submit_refinement_from_prompt(text, source='chat')
            return

        current_prompt = self._get_prompt_text()
        if current_prompt:
            prompt = _('%(prompt)s\n\nRefinement: %(refinement)s') % {
                'prompt': current_prompt,
                'refinement': text,
            }
        else:
            prompt = text
        self._set_prompt_text(prompt)
        self._submit_generation_from_prompt(prompt, chat_prompt=text)

    def __sidebar_refine_entry_activate_cb(self, entry):
        self.__sidebar_refine_send_clicked_cb(entry)

    def __sidebar_refine_send_clicked_cb(self, button):
        if self._sidebar_refine_entry is None:
            return

        text = self._sidebar_refine_entry.get_text().strip()
        if not text:
            self._sidebar_refine_entry.grab_focus()
            return

        self._sidebar_refine_entry.set_text('')
        if self._generation_result is None:
            if self._sidebar_refine_status_label is not None:
                self._sidebar_refine_status_label.set_text(
                    _('Generate an activity first.'))
            self._submit_generation_from_prompt(text, chat_prompt=text)
            return

        self._submit_refinement_from_prompt(text, source='sidebar')

    def __live_toggle_clicked_cb(self, button, enabled):
        self._live_edit_enabled = enabled
        self._select_start = None
        self._select_rect = None
        if self._preview_shell is not None:
            try:
                self._preview_shell.set_above_child(enabled)
                self._preview_shell.queue_draw()
            except Exception:
                pass
        if self._live_edit_on_button is not None:
            self._live_edit_on_button.get_style_context().remove_class(
                'create-ai-live-toggle-active')
        if self._live_edit_off_button is not None:
            self._live_edit_off_button.get_style_context().remove_class(
                'create-ai-live-toggle-active')

        if enabled and self._live_edit_on_button is not None:
            self._live_edit_on_button.get_style_context().add_class(
                'create-ai-live-toggle-active')
        elif self._live_edit_off_button is not None:
            self._live_edit_off_button.get_style_context().add_class(
                'create-ai-live-toggle-active')

        for mode_button, mode_enabled in (
                (self._ask_bar_edit_on, True),
                (self._ask_bar_edit_off, False)):
            if mode_button is None:
                continue
            mode_context = mode_button.get_style_context()
            if mode_enabled == enabled:
                mode_context.add_class('create-ai-ask-mode-active')
            else:
                mode_context.remove_class('create-ai-ask-mode-active')

        if self._ask_bar_plus is not None:
            self._ask_bar_plus.set_visible(enabled)
        if self._ask_bar_target_label is not None:
            self._ask_bar_target_label.set_visible(enabled)
        if self._ask_bar_entry is not None:
            self._ask_bar_entry.set_placeholder_text(
                _('Describe a change for the selected part')
                if enabled else _('Ask anything'))

        if self._live_edit_entry is not None:
            self._live_edit_entry.set_sensitive(enabled)
        if enabled:
            self._set_live_edit_status(
                _('Click or drag on the preview to pick a target.'))
        else:
            self._set_live_edit_status(
                _('Play mode: clicks go to the activity.'))

    def __live_edit_add_clicked_cb(self, button):
        if self._live_edit_entry is None:
            return

        if not self._live_edit_enabled:
            self._set_live_edit_status(
                _('Turn Live Edit on before adding changes.'))
            return

        text = self._live_edit_entry.get_text().strip()
        if not text:
            self._live_edit_entry.grab_focus()
            self._set_live_edit_status(
                _('Describe the preview change first.'))
            return

        self._live_edit_entry.set_text('')
        if self._generation_result is None:
            self._set_live_edit_status(
                _('Generate an activity before preview refinements.'))
            self._append_chat_message(
                _('Generate an activity first, then describe refinements.'))
            return

        self._submit_refinement_from_prompt(text, source='preview')

    def __stage_card_enter_notify_cb(self, card, event):
        if event.mode == Gdk.CrossingMode.NORMAL:
            card.get_style_context().add_class('create-ai-stage-card-hover')
        return False

    def __stage_card_leave_notify_cb(self, card, event):
        card.get_style_context().remove_class('create-ai-stage-card-hover')
        return False

    def __stage_card_button_release_cb(self, card, event, callback):
        if event.button != 1:
            return False
        alloc = card.get_allocation()
        if 0 < event.x < alloc.width and 0 < event.y < alloc.height:
            callback()
        return False

    def __open_create_view(self):
        self._use_centered_layout()
        self._stack.set_visible_child_name('create')
        self.focus_prompt()

    def __close_button_clicked_cb(self, button):
        self.emit('close-requested')

    def __focus_prompt_text(self):
        if self._prompt_text is not None and \
                not self._provider_control_has_focus():
            self._prompt_text.grab_focus()
        return False

    def _provider_control_has_focus(self):
        top_level = self.get_toplevel()
        if not isinstance(top_level, Gtk.Window):
            return False

        focused = top_level.get_focus()
        return focused in (
            self._provider_combo,
            self._provider_key_entry,
            self._provider_paste_button,
            self._provider_model_entry,
            self._provider_endpoint_entry,
            self._provider_apply_button,
            self._provider_remove_button,
        )


def _clean_generation_error_text(error_text):
    """Strip redundant pipeline prefixes so the learner sees the real
    validation reasons instead of a doubled-up error chain.

    The pipeline wraps validation failures as:
      Provider could not generate valid activity code:
        Provider generated code did not pass validation: <reasons>
    Both prefixes are implementation details; the learner only needs
    the <reasons> part.
    """
    text = str(error_text or '').strip()
    for prefix in (
            'Provider could not generate valid activity code: ',
            'Provider generated code did not pass validation: '):
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
    return text
