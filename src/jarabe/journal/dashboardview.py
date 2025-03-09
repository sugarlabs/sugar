# Copyright (C) 2019 Hrishi Patel
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, Pango, GObject, GdkPixbuf
import logging

from gettext import gettext as _

from sugar3.activity.activity import launch_bundle
from sugar3.activity.activity import get_activity_root
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.graphics.icon import CellRendererIcon
from sugar3.graphics import style
from sugar3.activity.widgets import ActivityToolbarButton
from sugar3.activity.widgets import StopButton
from sugar3.graphics.toolbutton import ToolButton
from sugar3.datastore import datastore
from sugar3 import profile

from jarabe.model import bundleregistry
from jarabe.journal import misc

from jarabe.util.charts import Chart
from jarabe.util.readers import JournalReader
from jarabe.util.utils import get_user_fill_color

import os
import datetime
import locale


COLOR1 = get_user_fill_color('str')


class DashboardView(Gtk.ScrolledWindow):

    def __init__(self, **kwargs):

        Gtk.ScrolledWindow.__init__(self)

        self.current_chart = None
        self.x_label = ""
        self.y_label = ""
        self.chart_data = []
        self.mime_types = ['image/bmp', 'image/gif', 'image/jpeg',
                           'image/png', 'image/tiff',
                           'application/pdf',
                           'application/vnd.olpc-sugar',
                           'application/rtf', 'text/rtf',
                           'application/epub+zip', 'text/html',
                           'application/x-pdf']

        # Detect if device is a XO
        if os.path.exists('/etc/olpc-release') or \
           os.path.exists('/sys/power/olpc-pm'):
            COLUMN_SPACING = 1
            STATS_WIDTH = 30
            TP_WIDTH = 45
            HMAP_WIDTH = 90
        else:
            COLUMN_SPACING = 2
            STATS_WIDTH = 50
            TP_WIDTH = 75
            HMAP_WIDTH = 150

        # ScrolledWindow as the main container
        self.set_can_focus(False)
        self.set_policy(Gtk.PolicyType.AUTOMATIC,
                        Gtk.PolicyType.AUTOMATIC)
        self.set_shadow_type(Gtk.ShadowType.NONE)
        self.show_all()

        grid = Gtk.Grid(column_spacing=6, row_spacing=3.5)
        grid.set_border_width(20)
        grid.set_halign(Gtk.Align.CENTER)
        self.add_with_viewport(grid)

        # VBoxes for total activities, journal entries and total files
        vbox_total_activities = Gtk.VBox()
        vbox_journal_entries = Gtk.VBox()
        vbox_total_contribs = Gtk.VBox()
        vbox_tree = Gtk.VBox()
        vbox_heatmap = Gtk.VBox()
        self.vbox_pie = Gtk.VBox()

        eb_total_activities = Gtk.EventBox()
        eb_journal_entries = Gtk.EventBox()
        eb_total_contribs = Gtk.EventBox()
        eb_heatmap = Gtk.EventBox()
        eb_tree = Gtk.EventBox()
        eb_pie = Gtk.EventBox()

        eb_total_activities.add(vbox_total_activities)
        eb_journal_entries.add(vbox_journal_entries)
        eb_total_contribs.add(vbox_total_contribs)
        eb_heatmap.add(vbox_heatmap)
        eb_pie.add(self.vbox_pie)
        eb_tree.add(vbox_tree)

        # change eventbox color
        eb_total_activities.modify_bg(Gtk.StateType.NORMAL,
                                      Gdk.color_parse("#ffffff"))
        eb_journal_entries.modify_bg(Gtk.StateType.NORMAL,
                                     Gdk.color_parse("#ffffff"))
        eb_total_contribs.modify_bg(Gtk.StateType.NORMAL,
                                    Gdk.color_parse("#ffffff"))
        eb_heatmap.modify_bg(Gtk.StateType.NORMAL,
                             Gdk.color_parse("#ffffff"))
        eb_pie.modify_bg(Gtk.StateType.NORMAL,
                         Gdk.color_parse("#ffffff"))
        eb_tree.modify_bg(Gtk.StateType.NORMAL,
                          Gdk.color_parse("#ffffff"))

        label_dashboard = Gtk.Label()
        text_dashboard = "<b>{0}</b>".format(_("Dashboard"))
        label_dashboard.set_markup(text_dashboard)

        # label for total activities
        label_TA = Gtk.Label()
        text_TA = "<b>{0}</b>".format(_("Activities Installed"))
        label_TA.set_markup(text_TA)
        vbox_total_activities.add(label_TA)

        self.label_total_activities = Gtk.Label()
        vbox_total_activities.add(self.label_total_activities)

        # label for total journal entries
        label_JE = Gtk.Label()
        text_JE = "<b>{0}</b>".format(_("Journal Entries"))
        label_JE.set_markup(text_JE)
        vbox_journal_entries.add(label_JE)

        self.label_journal_entries = Gtk.Label()
        vbox_journal_entries.add(self.label_journal_entries)

        # label for files
        label_CE = Gtk.Label()
        text_CE = "<b>{0}</b>".format(_("Total Files"))
        label_CE.set_markup(text_CE)
        vbox_total_contribs.add(label_CE)

        # label for pie
        label_PIE = Gtk.Label()
        text_PIE = "<b>{0}</b>".format(_("Most used activities"))
        label_PIE.set_markup(text_PIE)
        self.vbox_pie.pack_start(label_PIE, False, True, 5)

        self.label_contribs = Gtk.Label()
        vbox_total_contribs.add(self.label_contribs)

        # pie chart
        self.labels_and_values = ChartData(self)
        self.eventbox = Gtk.EventBox()
        self.charts_area = ChartArea(self)
        self.charts_area.connect('size-allocate', self._chart_size_allocate_cb)
        self.eventbox.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("white"))
        self.eventbox.add(self.charts_area)
        self.vbox_pie.pack_start(self.eventbox, True, True, 0)
        self.eventbox.connect('button-press-event', self._pie_opened)
        self.charts_area.set_tooltip_text(_("Click for more information"))

        # pie chart window
        self.window = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        self.window.set_border_width(2)
        self.window.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.window.set_decorated(True)
        self.window.set_resizable(False)
        self.window.set_modal(True)
        self.window.set_keep_above(True)
        self.window.set_size_request(800, 600)
        self.window.set_title("Pie Chart")
        self.window.connect('delete-event', self._hide_window)

        eb_image_holder = Gtk.EventBox()
        eb_image_holder.modify_bg(Gtk.StateType.NORMAL,
                                  Gdk.color_parse("ffffff"))
        self.window.modify_bg(Gtk.StateType.NORMAL,
                              Gdk.color_parse("#282828"))

        vbox_image = Gtk.VBox()
        eb_image_holder.add(vbox_image)

        # scrolled window for details window
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_can_focus(False)
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC,
                                   Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_shadow_type(Gtk.ShadowType.NONE)
        scrolled_window.show()

        # load pie image
        # not using get_activity_root for now
        self.image = Gtk.Image()
        self.image.set_from_file("/tmp/screenshot.png")
        vbox_image.add(self.image)

        self.vbox_holder = Gtk.VBox()
        self.vbox_holder.pack_start(eb_image_holder, True, True, 0)
        self.vbox_holder.pack_start(self.labels_and_values, False, False, 0)
        self.window.add(scrolled_window)
        scrolled_window.add_with_viewport(self.vbox_holder)

        reader = JournalReader()
        self._graph_from_reader(reader)
        self.current_chart = Chart("pie")
        self.update_chart()

        # font
        font_main = Pango.FontDescription("Granada 12")
        label_JE.modify_font(font_main)
        label_CE.modify_font(font_main)
        label_TA.modify_font(font_main)

        font_actual = Pango.FontDescription("12")
        self.label_journal_entries.modify_font(font_actual)
        self.label_total_activities.modify_font(font_actual)
        self.label_contribs.modify_font(font_actual)
        label_dashboard.modify_font(font_actual)

        self.treeview_list = []
        self.files_list = []
        self.old_list = []
        self.heatmap_list = []
        self.journal_entries = 0

        # treeview for Journal entries
        self.liststore = Gtk.ListStore(str, str, str, object, str,
                                       datastore.DSMetadata, str, str)
        self.treeview = Gtk.TreeView(self.liststore)
        self.treeview.set_headers_visible(False)
        self.treeview.set_grid_lines(Gtk.TreeViewGridLines.HORIZONTAL)
        self._load_data()

        for i, col_title in enumerate(["Recently Opened Activities"]):

            renderer_title = Gtk.CellRendererText()
            renderer_time = Gtk.CellRendererText()
            icon_renderer = CellRendererActivityIcon()

            renderer_title.set_property('ellipsize', Pango.EllipsizeMode.END)
            renderer_title.set_property('ellipsize-set', True)

            column1 = Gtk.TreeViewColumn("Icon")
            column1.pack_start(icon_renderer, True)
            column1.add_attribute(icon_renderer, 'file-name',
                                  1)
            column1.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
            column1.add_attribute(icon_renderer, 'xo-color',
                                  3)
            column2 = Gtk.TreeViewColumn(col_title, renderer_title, text=0)
            column2.set_min_width(200)
            column3 = Gtk.TreeViewColumn(col_title, renderer_time, text=6)

            self.treeview.set_tooltip_column(0)
            self.treeview.append_column(column1)
            self.treeview.append_column(column2)
            self.treeview.append_column(column3)

        # combobox for sort selection
        cbox_store = Gtk.ListStore(str)
        cbox_entries = [_("Newest"), _("Files"), _("Oldest")]

        for item in cbox_entries:
            cbox_store.append([item])

        combobox = Gtk.ComboBox.new_with_model(cbox_store)
        combobox.set_halign(Gtk.Align.END)
        combobox.connect('changed', self._on_name_combo_changed_cb)
        renderer_text = Gtk.CellRendererText()
        combobox.pack_start(renderer_text, True)
        combobox.add_attribute(renderer_text, "text", 0)
        combobox.set_active(0)

        self._add_to_treeview(self.treeview_list)

        selected_row = self.treeview.get_selection()
        selected_row.connect('changed', self._item_select_cb)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_can_focus(False)
        scrolled_window.set_policy(Gtk.PolicyType.NEVER,
                                   Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_shadow_type(Gtk.ShadowType.NONE)
        scrolled_window.show()

        hbox_tree2 = Gtk.HBox()
        text_treeview = "{0}".format(_("Journal Entries"))
        self.label_treeview = Gtk.Label(text_treeview)
        hbox_tree2.pack_start(self.label_treeview, False, True, 10)
        hbox_tree2.pack_start(combobox, True, True, 10)

        vbox_tree.pack_start(hbox_tree2, False, False, 5)
        scrolled_window.add_with_viewport(self.treeview)

        # label for recent activities
        label_rec = Gtk.Label(expand=False)
        text_treeview = "{0}".format(_("Recently Opened Activities"))
        label_rec.set_markup(text_treeview)

        vbox_tree.add(scrolled_window)

        # heatmap
        label_heatmap = Gtk.Label(_("User Activity"))
        grid_heatmap = Gtk.Grid(column_spacing=COLUMN_SPACING,
                                row_spacing=2)
        grid_heatmap.set_halign(Gtk.Align.CENTER)
        vbox_heatmap.pack_start(label_heatmap, False, True, 5)
        vbox_heatmap.pack_start(grid_heatmap, False, True, 5)

        self.dates, self.dates_a, months = self._generate_dates()
        self._build_heatmap(grid_heatmap, self.dates, self.dates_a, months)

        self.heatmap_liststore = Gtk.ListStore(str, str, str, object, str,
                                               datastore.DSMetadata, str, str)
        heatmap_treeview = Gtk.TreeView(self.heatmap_liststore)
        heatmap_treeview.set_headers_visible(False)
        heatmap_treeview.set_grid_lines(Gtk.TreeViewGridLines.HORIZONTAL)

        for i, col_title in enumerate(["Activity"]):
            renderer_title = Gtk.CellRendererText()
            icon_renderer = CellRendererActivityIcon()
            renderer_time = Gtk.CellRendererText()

            column1 = Gtk.TreeViewColumn("Icon")
            column1.pack_start(icon_renderer, True)
            column1.add_attribute(icon_renderer, 'file-name',
                                  1)
            column1.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
            column1.add_attribute(icon_renderer, 'xo-color',
                                  3)
            column2 = Gtk.TreeViewColumn(col_title, renderer_title, text=0)
            column3 = Gtk.TreeViewColumn(col_title, renderer_time, text=6)

            heatmap_treeview.append_column(column1)
            heatmap_treeview.append_column(column2)
            heatmap_treeview.append_column(column3)

        vbox_heatmap.pack_start(heatmap_treeview, False, True, 5)

        selected_row_heatmap = heatmap_treeview.get_selection()
        selected_row_heatmap.connect('changed', self._item_select_cb)

        # add views to grid
        grid.attach(label_dashboard, 1, 2, 1, 1)
        grid.attach_next_to(eb_total_activities, label_dashboard,
                            Gtk.PositionType.BOTTOM, STATS_WIDTH, 35)
        grid.attach_next_to(eb_journal_entries, eb_total_activities,
                            Gtk.PositionType.RIGHT, STATS_WIDTH, 35)
        grid.attach_next_to(eb_total_contribs, eb_journal_entries,
                            Gtk.PositionType.RIGHT, STATS_WIDTH, 35)
        grid.attach_next_to(eb_tree, eb_total_activities,
                            Gtk.PositionType.BOTTOM, TP_WIDTH, 90)
        grid.attach_next_to(eb_pie, eb_tree,
                            Gtk.PositionType.RIGHT, TP_WIDTH, 90)
        grid.attach_next_to(eb_heatmap, eb_tree,
                            Gtk.PositionType.BOTTOM, HMAP_WIDTH, 75)
        grid.show_all()

    def _load_data(self, widget=None):
        del self.treeview_list[:]
        del self.files_list[:]
        del self.old_list[:]
        del self.heatmap_list[:]

        dsobjects, journal_entries = datastore.find({})
        for dsobject in dsobjects:
            new = []
            new.append(dsobject.metadata['title'])
            new.append(misc.get_icon_name(dsobject.metadata))
            new.append(dsobject.metadata['activity_id'])
            new.append(profile.get_color())
            new.append(dsobject.get_object_id())
            new.append(dsobject.metadata)
            new.append(misc.get_date(dsobject.metadata))
            new.append(dsobject.metadata['mtime'])
            self.treeview_list.append(new)
            self.old_list.append(new)

            # determine if a file
            if dsobject.metadata['mime_type'] in self.mime_types:
                new2 = []
                new2.append(dsobject.metadata['title'])
                new2.append(misc.get_icon_name(dsobject.metadata))
                new2.append(dsobject.metadata['activity_id'])
                new2.append(profile.get_color())
                new2.append(dsobject.get_object_id())
                new2.append(dsobject.metadata)
                new2.append(misc.get_date(dsobject.metadata))
                new2.append(dsobject.metadata['mtime'])
                self.files_list.append(new2)

            self.old_list = sorted(self.old_list, key=lambda x: x[7])
            self.journal_entries = journal_entries
            self._add_to_treeview(self.treeview_list)

            # get number of activities installed
            registry = bundleregistry.get_registry()

            self.label_total_activities.set_text(str(len(registry)))
            self.label_journal_entries.set_text(str(self.journal_entries))
            self.label_contribs.set_text(str(len(self.files_list)))

    def _pie_opened(self, widget, event):
        self.update_chart(300)
        self.vbox_holder.pack_start(self.labels_and_values, False, False, 0)
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale("/tmp/screenshot.png",
                                                         800, 550, True)
        self.image.set_from_pixbuf(pixbuf)
        self.window.show()
        self.window.show_all()

    def _hide_window(self, *args):
        self.vbox_holder.remove(self.labels_and_values)
        self.window.hide()
        self.update_chart(0)
        return Gtk.true

    def _build_heatmap(self, grid, dates, dates_a, months):
        j = 1
        k = 1
        counter_days = 0
        counter_weeks = 0
        week_list = [0, 5, 9, 13, 18, 22, 26, 31, 35, 39, 44, 49]
        months_dict = {}

        # populate dictionary
        for i, item in enumerate(week_list):
            months_dict[item] = months[i]

        for i in range(0, 365):
            if (i % 7 == 0):
                j = j + 1
                k = 0
            k = k + 1
            count = 0
            for x in range(0, len(self.old_list)):
                date = self.old_list[x][7][:-16]
                if date == dates[i]:
                    count = count + 1
            box = HeatMapBlock(dates_a[i], count, i)
            box.connect('on-clicked', self._on_clicked_cb)
            lab_days = Gtk.Label()
            lab_months = Gtk.Label()

            # for weekdays
            if(k % 2 == 0 and counter_days < 3):
                day = ''
                if(counter_days == 0):
                    day = dates_a[8][:-13]
                    lab_days.set_text(_(day))
                if(counter_days == 1):
                    day = dates_a[10][:-13]
                    lab_days.set_text(_(day))
                if(counter_days == 2):
                    day = dates_a[12][:-13]
                    lab_days.set_text(_(day))

                grid.attach(lab_days, 0, k, 1, 1)
                counter_days = counter_days + 1

            # for months
            if(k % 4 == 0 and counter_weeks < 54):
                for key, value in months_dict.items():
                    if counter_weeks == key:
                        lab_months.set_text(str(value))

                if counter_weeks in week_list:
                    grid.attach(lab_months, j, 0, 2, 1)

                counter_weeks = counter_weeks + 1

            grid.attach(box, j, k, 1, 1)

    def _on_clicked_cb(self, i, index):
        self.heatmap_liststore.clear()
        del self.heatmap_list[:]

        for y in range(0, len(self.old_list)):
            date = self.old_list[y][7][:-16]
            if date == self.dates[index]:
                self.heatmap_list.append(self.old_list[y])

        for item in self.heatmap_list:
            self.heatmap_liststore.append(item)

    def _generate_dates(self):
        year = datetime.date.today().year

        dt = datetime.datetime(year, 1, 1)
        end = datetime.datetime(year, 12, 31, 23, 59, 59)
        step = datetime.timedelta(days=1)

        result = []
        result_a = []
        months = []

        while dt < end:
            result_a.append(dt.strftime('%a, %b %d %Y'))
            result.append(dt.strftime('%Y-%m-%d'))
            dt += step

        for i in range(1, 13):
            month_abre = datetime.date(year, i, 1).strftime('%b')
            months.append(month_abre)

        return result, result_a, months

    def _add_to_treeview(self, tlist):
        self.liststore.clear()
        for item in tlist:
            self.liststore.append(item)

    def _on_name_combo_changed_cb(self, combo):
        tree_iter = combo.get_active_iter()
        if tree_iter is not None:
            model = combo.get_model()
            selected_item = model[tree_iter][0]
            if selected_item == "Files":
                self._add_to_treeview(self.files_list)
            elif selected_item == "Newest":
                self._add_to_treeview(self.treeview_list)
            elif selected_item == "Oldest":
                self._add_to_treeview(self.old_list)

    def _item_select_cb(self, selection):
        model, row = selection.get_selected()

        if row is not None:
            metadata = model[row][5]
            bundle_id = metadata.get('activity', '')
            launch_bundle(bundle_id, model[row][4])

    def _chart_size_allocate_cb(self, widget, allocation):
        self._render_chart()

    def _render_chart(self, extra_size=0):
        if self.current_chart is None or self.charts_area is None:
            return

        # Resize the chart for all the screen sizes
        alloc = self.vbox_pie.get_allocation()
        new_width = alloc.width + extra_size
        new_height = alloc.height + extra_size

        self.current_chart.width = new_width
        self.current_chart.height = new_height

        try:
            if self.current_chart.type == "pie":
                self.current_chart.render(self)
            else:
                self.current_chart.render()
            self.charts_area.queue_draw()
            surface = self.charts_area.get_surface()
            surface.write_to_png('/tmp/screenshot.png')
        except (ZeroDivisionError, ValueError):
            pass

        return False

    def _graph_from_reader(self, reader):
        self.labels_and_values.model.clear()
        self.chart_data = []

        chart_data = reader.get_chart_data()

        # Load the data
        for row in chart_data:
            self._add_value(None,
                            label=row[0], value=float(row[1]))

            self.update_chart()

    def _add_value(self, widget, label="", value="0.0"):
        data = (label, float(value))
        if data not in self.chart_data:
            pos = self.labels_and_values.add_value(label, value)
            self.chart_data.insert(pos, data)
            self._update_chart_data()

    def update_chart(self, extra_size=0):
        if self.current_chart:
            self.current_chart.data_set(self.chart_data)
            self.current_chart.set_x_label(self.x_label)
            self.current_chart.set_y_label(self.y_label)
            self._render_chart(extra_size)

    def _update_chart_data(self):
        if self.current_chart is None:
            return
        self.current_chart.data_set(self.chart_data)
        self._update_chart_labels()

    def _update_chart_labels(self, title=""):
        if self.current_chart is None:
            return
        self.current_chart.set_title(title)
        self.current_chart.set_x_label(self.x_label)
        self.current_chart.set_y_label(self.y_label)
        self._render_chart()


class ChartArea(Gtk.DrawingArea):

    def __init__(self, parent):
        """A class for Draw the chart"""
        super(ChartArea, self).__init__()
        self._parent = parent
        self.add_events(Gdk.EventMask.EXPOSURE_MASK |
                        Gdk.EventMask.VISIBILITY_NOTIFY_MASK)
        self.connect('draw', self._draw_cb)

    def _draw_cb(self, widget, context):
        alloc = self.get_allocation()

        # White Background:
        context.rectangle(0, 0, alloc.width, alloc.height)
        context.set_source_rgb(255, 255, 255)
        context.fill()

        # Paint the chart:
        chart_width = self._parent.current_chart.width
        chart_height = self._parent.current_chart.height

        cxpos = alloc.width / 2 - chart_width / 2
        cypos = alloc.height / 2 - chart_height / 2

        context.set_source_surface(self._parent.current_chart.surface,
                                   cxpos,
                                   cypos)
        context.paint()

    def get_surface(self):
        return self._parent.current_chart.surface


class ChartData(Gtk.TreeView):

    def __init__(self, activity):
        GObject.GObject.__init__(self)

        self.model = Gtk.ListStore(str, str)
        self.set_model(self.model)

        self._selection = self.get_selection()
        self._selection.set_mode(Gtk.SelectionMode.SINGLE)

        # Label column
        column = Gtk.TreeViewColumn(_("Activities"))
        label = Gtk.CellRendererText()

        column.pack_start(label, True)
        column.add_attribute(label, 'text', 0)
        self.append_column(column)

        # Value column
        column = Gtk.TreeViewColumn(_("Number of Instances"))
        value = Gtk.CellRendererText()

        column.pack_start(value, True)
        column.add_attribute(value, 'text', 1)

        self.append_column(column)
        self.set_enable_search(False)

        self.show_all()

    def add_value(self, label, value):
        treestore, selected = self._selection.get_selected()
        if not selected:
            path = 0

        elif selected:
            path = int(str(self.model.get_path(selected))) + 1
        try:
            _iter = self.model.insert(path, [label, str(value)])
        except ValueError:
            _iter = self.model.append([label, str(value)])

        self.set_cursor(self.model.get_path(_iter),
                        self.get_column(1),
                        True)

        return path


class CellRendererActivityIcon(CellRendererIcon):
    __gtype_name__ = 'DashboardCellRendererActivityIcon'

    def __init__(self):
        CellRendererIcon.__init__(self)

        self.props.width = style.GRID_CELL_SIZE
        self.props.height = style.GRID_CELL_SIZE
        self.props.size = style.STANDARD_ICON_SIZE
        self.props.mode = Gtk.CellRendererMode.ACTIVATABLE


class HeatMapBlock(Gtk.EventBox):

    __gsignals__ = {
        'on-clicked': (GObject.SignalFlags.RUN_FIRST, None,
                       (int,)),
    }

    def __init__(self, date, contribs, index):
        Gtk.EventBox.__init__(self)

        self._i = index

        label = Gtk.Label("   ")
        tooltip = date + "\nContributions: " + str(contribs)
        label.set_tooltip_text(tooltip)

        if contribs == 0:
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#cdcfd3"))
        elif contribs <= 2 and contribs > 0:
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#5fce68"))
        elif contribs <= 5 and contribs > 2:
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#47a94f"))
        elif contribs >= 6:
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#38853e"))

        self.add(label)
        self.set_events(Gdk.EventType.BUTTON_PRESS)
        self.connect('button-press-event', self._on_mouse_cb)

    def _on_mouse_cb(self, widget, event):
        self.emit('on-clicked', self._i)
