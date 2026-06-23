# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

import json
from textwrap import dedent


def render_activity_source(spec, plan):
    template = plan['template']
    render = _TEMPLATE_RENDERERS[template]
    body = render(spec, plan)
    return _render_shell(spec, plan, body)


def _render_shell(spec, plan, body):
    return dedent(
        '''\
        # SPDX-License-Identifier: {license_id}

        import json

        import gi
        gi.require_version('Gdk', '3.0')
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gdk
        from gi.repository import GLib
        from gi.repository import Gtk

        from sugar3.activity import activity
        from sugar3.activity.widgets import ActivityToolbarButton
        from sugar3.activity.widgets import StopButton
        from sugar3.graphics.toolbarbox import ToolbarBox


        ACTIVITY_TITLE = {title}
        LEARNER_GOAL = {goal}


        class GeneratedActivity(activity.Activity):
            def __init__(self, handle):
                activity.Activity.__init__(self, handle)
                self.max_participants = 1
                self._build_toolbar()
                self._build_canvas()

            def _build_toolbar(self):
                toolbar_box = ToolbarBox()
                toolbar = toolbar_box.toolbar
                toolbar.insert(ActivityToolbarButton(self), 0)
                toolbar.insert(StopButton(self), -1)
                self.set_toolbar_box(toolbar_box)
                toolbar_box.show_all()

        {body}
        '''
    ).format(
        license_id=spec.license_id,
        title=json.dumps(spec.name),
        goal=json.dumps(spec.learner_goal or plan['learner_goal']),
        body=_indent(body.rstrip(), 4),
    )


def _render_canvas(spec, plan):
    return dedent(
        '''\
        def _build_canvas(self):
            self._points = []
            canvas = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            canvas.set_border_width(24)

            goal = Gtk.Label(label=LEARNER_GOAL)
            goal.set_line_wrap(True)
            canvas.pack_start(goal, False, False, 0)

            self._drawing = Gtk.DrawingArea()
            self._drawing.set_size_request(640, 420)
            self._drawing.add_events(
                Gdk.EventMask.BUTTON_PRESS_MASK |
                Gdk.EventMask.BUTTON_MOTION_MASK)
            self._drawing.connect('button-press-event', self._draw_point)
            self._drawing.connect('motion-notify-event', self._draw_point)
            self._drawing.connect('draw', self._draw_canvas)
            canvas.pack_start(self._drawing, True, True, 0)

            clear_button = Gtk.Button(label='Clear drawing')
            clear_button.connect('clicked', self._clear_drawing)
            canvas.pack_start(clear_button, False, False, 0)

            self.set_canvas(canvas)
            canvas.show_all()

        def _draw_point(self, widget, event):
            if event.type == Gdk.EventType.MOTION_NOTIFY and \
                    not event.state & Gdk.ModifierType.BUTTON1_MASK:
                return False
            self._points.append([event.x, event.y])
            self._drawing.queue_draw()
            return True

        def _draw_canvas(self, widget, context):
            context.set_source_rgb(0.15, 0.35, 0.75)
            for x, y in self._points:
                context.rectangle(x - 2, y - 2, 4, 4)
            context.fill()
            return False

        def _clear_drawing(self, button):
            self._points = []
            self._drawing.queue_draw()

        def write_file(self, file_path):
            with open(file_path, 'w', encoding='utf-8') as output:
                json.dump({'points': self._points}, output)

        def read_file(self, file_path):
            try:
                with open(file_path, encoding='utf-8') as source:
                    self._points = json.load(source).get('points', [])
            except (OSError, ValueError):
                self._points = []
            if hasattr(self, '_drawing'):
                self._drawing.queue_draw()
        '''
    )


def _render_grid(spec, plan):
    return dedent(
        '''\
        def _build_canvas(self):
            self._grid_state = [False] * 16
            canvas = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            canvas.set_border_width(24)

            goal = Gtk.Label(label=LEARNER_GOAL)
            goal.set_line_wrap(True)
            canvas.pack_start(goal, False, False, 0)

            grid = Gtk.Grid(row_spacing=8, column_spacing=8)
            self._grid_buttons = []
            for index in range(16):
                button = Gtk.ToggleButton(label=str(index + 1))
                button.connect('toggled', self._grid_toggled, index)
                grid.attach(button, index % 4, index // 4, 1, 1)
                self._grid_buttons.append(button)
            canvas.pack_start(grid, True, False, 0)

            self._grid_status = Gtk.Label(label='Find or create a pattern.')
            canvas.pack_start(self._grid_status, False, False, 0)

            self.set_canvas(canvas)
            canvas.show_all()

        def _grid_toggled(self, button, index):
            self._grid_state[index] = button.get_active()
            selected = sum(1 for value in self._grid_state if value)
            self._grid_status.set_text(
                '%d squares are part of your pattern.' % selected)

        def write_file(self, file_path):
            with open(file_path, 'w', encoding='utf-8') as output:
                json.dump({'grid': self._grid_state}, output)

        def read_file(self, file_path):
            try:
                with open(file_path, encoding='utf-8') as source:
                    values = json.load(source).get('grid', [])
            except (OSError, ValueError):
                values = []
            for index, value in enumerate(values[:16]):
                self._grid_state[index] = bool(value)
                if hasattr(self, '_grid_buttons'):
                    self._grid_buttons[index].set_active(bool(value))
        '''
    )


def _render_chess(spec, plan):
    body = dedent(
        '''\
        def _build_canvas(self):
            self._selected_square = None
            self._turn = 'w'
            self._move_log = []
            self._captured = {'w': [], 'b': []}
            self._move_log_view = None
            self._buttons = []
            self._board = self._starting_board()

            canvas = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            canvas.set_border_width(16)

            goal = Gtk.Label(label=LEARNER_GOAL)
            goal.set_line_wrap(True)
            canvas.pack_start(goal, False, False, 0)

            self._status = Gtk.Label()
            self._status.set_line_wrap(True)
            canvas.pack_start(self._status, False, False, 0)

            play_area = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                                spacing=18)
            canvas.pack_start(play_area, True, True, 0)

            board_frame = Gtk.Alignment(xalign=0.5, yalign=0.5,
                                        xscale=0, yscale=0)
            board_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                spacing=6)
            board_frame.add(board_box)

            files_top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                                spacing=1)
            files_top.set_halign(Gtk.Align.CENTER)
            files_top.pack_start(Gtk.Label(label='  '), False, False, 0)
            for file_name in 'abcdefgh':
                label = Gtk.Label(label=file_name)
                label.set_size_request(64, 18)
                files_top.pack_start(label, False, False, 0)
            board_box.pack_start(files_top, False, False, 0)

            board_rows = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                                 spacing=6)
            board_box.pack_start(board_rows, False, False, 0)
            ranks = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            board_rows.pack_start(ranks, False, False, 0)
            self._grid = Gtk.Grid(row_spacing=1, column_spacing=1)
            board_rows.pack_start(self._grid, False, False, 0)

            for row in range(8):
                ranks.pack_start(
                    Gtk.Label(label=str(8 - row)), False, False, 0)
                button_row = []
                for col in range(8):
                    button = Gtk.Button()
                    button.set_size_request(64, 58)
                    button.connect('clicked', self._square_clicked, row, col)
                    self._grid.attach(button, col, row, 1, 1)
                    button_row.append(button)
                self._buttons.append(button_row)
            play_area.pack_start(board_frame, True, True, 0)

            side_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                 spacing=10)
            side_panel.set_size_request(320, -1)
            play_area.pack_start(side_panel, False, False, 0)

            prompt = Gtk.Label(
                label='Before each move, say your idea out loud or type it '
                      'below.')
            prompt.set_line_wrap(True)
            side_panel.pack_start(prompt, False, False, 0)

            self._lesson_steps_label = Gtk.Label()
            self._lesson_steps_label.set_xalign(0)
            self._lesson_steps_label.set_line_wrap(True)
            side_panel.pack_start(self._lesson_steps_label, False, False, 0)

            self._move_idea = Gtk.Entry()
            self._move_idea.set_placeholder_text(
                'Move idea, plan, or teamwork note')
            side_panel.pack_start(self._move_idea, False, False, 0)

            self._captured_white = Gtk.Label()
            self._captured_white.set_xalign(0)
            side_panel.pack_start(self._captured_white, False, False, 0)

            self._captured_black = Gtk.Label()
            self._captured_black.set_xalign(0)
            side_panel.pack_start(self._captured_black, False, False, 0)

            if self._show_move_log:
                scroll = Gtk.ScrolledWindow()
                scroll.set_size_request(320, 210)
                self._move_log_view = Gtk.TextView()
                self._move_log_view.set_editable(False)
                self._move_log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
                scroll.add(self._move_log_view)
                side_panel.pack_start(scroll, True, True, 0)
            else:
                clean_note = Gtk.Label(
                    label='Clean board mode: move history is hidden.')
                clean_note.set_xalign(0)
                clean_note.set_line_wrap(True)
                side_panel.pack_start(clean_note, False, False, 0)

            controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                               spacing=8)
            reset_button = Gtk.Button(label='Reset board')
            reset_button.connect('clicked', self._reset_board)
            controls.pack_start(reset_button, False, False, 0)
            controls.pack_start(
                Gtk.Label(label='Click a piece, then its destination.'),
                False, False, 0)
            side_panel.pack_start(controls, False, False, 0)

            self.set_canvas(canvas)
            self._update_lesson_steps()
            self._refresh_board()
            canvas.show_all()

        def _starting_board(self):
            return [
                ['br', 'bn', 'bb', 'bq', 'bk', 'bb', 'bn', 'br'],
                ['bp', 'bp', 'bp', 'bp', 'bp', 'bp', 'bp', 'bp'],
                ['', '', '', '', '', '', '', ''],
                ['', '', '', '', '', '', '', ''],
                ['', '', '', '', '', '', '', ''],
                ['', '', '', '', '', '', '', ''],
                ['wp', 'wp', 'wp', 'wp', 'wp', 'wp', 'wp', 'wp'],
                ['wr', 'wn', 'wb', 'wq', 'wk', 'wb', 'wn', 'wr'],
            ]

        def _piece_labels(self):
            return {
                'wk': '\\u2654', 'wq': '\\u2655', 'wr': '\\u2656',
                'wb': '\\u2657', 'wn': '\\u2658', 'wp': '\\u2659',
                'bk': '\\u265a', 'bq': '\\u265b', 'br': '\\u265c',
                'bb': '\\u265d', 'bn': '\\u265e', 'bp': '\\u265f',
            }

        def _square_clicked(self, button, row, col):
            piece = self._board[row][col]
            if self._selected_square is None:
                if not piece:
                    self._set_status('Choose a %s piece to move.' %
                                     self._turn_name())
                    return
                if piece[0] != self._turn:
                    self._set_status('It is %s turn.' % self._turn_name())
                    return
                self._selected_square = (row, col)
                self._set_status('Selected %s at %s.' %
                                 (self._piece_name(piece),
                                  self._square_name(row, col)))
                self._refresh_board()
                return

            start_row, start_col = self._selected_square
            moving = self._board[start_row][start_col]
            if (row, col) == self._selected_square:
                self._selected_square = None
                self._set_status('Selection cleared.')
                self._refresh_board()
                return
            if piece and piece[0] == self._turn:
                self._selected_square = (row, col)
                self._set_status('Selected %s at %s.' %
                                 (self._piece_name(piece),
                                  self._square_name(row, col)))
                self._refresh_board()
                return
            if not self._can_move(moving, start_row, start_col, row, col):
                self._set_status('%s cannot move to %s.' %
                                 (self._piece_name(moving),
                                  self._square_name(row, col)))
                return

            capture = self._board[row][col]
            self._board[row][col] = moving
            self._board[start_row][start_col] = ''
            move_text = '%s %s to %s' % (
                self._piece_name(moving),
                self._square_name(start_row, start_col),
                self._square_name(row, col),
            )
            if capture:
                move_text += ' captures %s' % self._piece_name(capture)
                self._captured[self._turn].append(capture)
            idea = self._move_idea.get_text().strip()
            if idea:
                move_text += ' - idea: %s' % idea
                self._move_idea.set_text('')
            if self._show_move_log:
                self._move_log.append(move_text)
            self._turn = 'b' if self._turn == 'w' else 'w'
            self._selected_square = None
            self._set_status('%s. %s to move.' %
                             (move_text, self._turn_name()))
            self._refresh_board()

        def _can_move(self, piece, start_row, start_col, row, col):
            if not piece or piece[0] != self._turn:
                return False
            target = self._board[row][col]
            if target and target[0] == piece[0]:
                return False

            dr = row - start_row
            dc = col - start_col
            abs_dr = abs(dr)
            abs_dc = abs(dc)
            kind = piece[1]

            if kind == 'p':
                direction = -1 if piece[0] == 'w' else 1
                home_row = 6 if piece[0] == 'w' else 1
                if dc == 0 and not target:
                    if dr == direction:
                        return True
                    if start_row == home_row and dr == 2 * direction:
                        mid_row = start_row + direction
                        return not self._board[mid_row][start_col]
                if abs_dc == 1 and dr == direction and target:
                    return True
                return False
            if kind == 'n':
                return (abs_dr, abs_dc) in ((1, 2), (2, 1))
            if kind == 'k':
                return max(abs_dr, abs_dc) == 1
            if kind == 'b':
                return abs_dr == abs_dc and self._path_clear(
                    start_row, start_col, row, col)
            if kind == 'r':
                return (dr == 0 or dc == 0) and self._path_clear(
                    start_row, start_col, row, col)
            if kind == 'q':
                diagonal = abs_dr == abs_dc
                straight = dr == 0 or dc == 0
                return (diagonal or straight) and self._path_clear(
                    start_row, start_col, row, col)
            return False

        def _path_clear(self, start_row, start_col, row, col):
            step_row = self._step(row - start_row)
            step_col = self._step(col - start_col)
            current_row = start_row + step_row
            current_col = start_col + step_col
            while (current_row, current_col) != (row, col):
                if self._board[current_row][current_col]:
                    return False
                current_row += step_row
                current_col += step_col
            return True

        def _step(self, value):
            if value < 0:
                return -1
            if value > 0:
                return 1
            return 0

        def _refresh_board(self):
            labels = self._piece_labels()
            for row in range(8):
                for col in range(8):
                    piece = self._board[row][col]
                    label = labels.get(piece, ' ')
                    self._buttons[row][col].set_label(label)
                    self._style_square(
                        self._buttons[row][col],
                        row,
                        col,
                        self._selected_square == (row, col),
                    )
                    self._buttons[row][col].set_tooltip_text(
                        '%s %s' % (self._square_name(row, col),
                                   self._piece_name(piece) if piece else
                                   'empty'))
            if not self._move_log:
                self._set_status('%s to move. Select a piece.' %
                                 self._turn_name())
            self._update_captured()
            self._update_move_log()

        def _style_square(self, button, row, col, selected):
            color = Gdk.RGBA()
            if selected:
                color.parse('#f4d06f')
            elif (row + col) % 2:
                color.parse('#c9c9c9')
            else:
                color.parse('#f2f2f2')
            button.override_background_color(Gtk.StateFlags.NORMAL, color)

        def _update_captured(self):
            labels = self._piece_labels()
            white = ' '.join(labels.get(piece, '') for piece in
                             self._captured.get('w', [])) or 'none'
            black = ' '.join(labels.get(piece, '') for piece in
                             self._captured.get('b', [])) or 'none'
            self._captured_white.set_text('White captured: %s' % white)
            self._captured_black.set_text('Black captured: %s' % black)

        def _update_lesson_steps(self):
            text = '\\n'.join(
                '%d. %s' % (index, step)
                for index, step in enumerate(self._lesson_steps, 1)
            )
            self._lesson_steps_label.set_text(
                text or 'Take turns, explain moves, then save to Journal.')

        def _update_move_log(self):
            if self._move_log_view is None:
                return
            text = '\\n'.join(
                '%d. %s' % (index, move)
                for index, move in enumerate(self._move_log, 1)
            )
            self._move_log_view.get_buffer().set_text(
                text or 'Move log will appear here.')

        def _set_status(self, text):
            self._status.set_text(text)

        def _turn_name(self):
            return 'White' if self._turn == 'w' else 'Black'

        def _square_name(self, row, col):
            return '%s%d' % ('abcdefgh'[col], 8 - row)

        def _piece_name(self, piece):
            names = {
                'k': 'king',
                'q': 'queen',
                'r': 'rook',
                'b': 'bishop',
                'n': 'knight',
                'p': 'pawn',
            }
            if not piece:
                return 'empty square'
            color = 'White' if piece[0] == 'w' else 'Black'
            return '%s %s' % (color, names.get(piece[1], 'piece'))

        def _reset_board(self, button):
            self._board = self._starting_board()
            self._selected_square = None
            self._turn = 'w'
            self._move_log = []
            self._captured = {'w': [], 'b': []}
            self._set_status('Board reset. White to move.')
            self._refresh_board()

        def write_file(self, file_path):
            state = {
                'board': self._board,
                'turn': self._turn,
                'move_log': self._move_log if self._show_move_log else [],
                'captured': self._captured,
            }
            with open(file_path, 'w', encoding='utf-8') as output:
                json.dump(state, output)

        def read_file(self, file_path):
            try:
                with open(file_path, encoding='utf-8') as source:
                    state = json.load(source)
            except (OSError, ValueError):
                state = {}
            board = state.get('board')
            if isinstance(board, list) and len(board) == 8:
                self._board = board
            self._turn = state.get('turn', 'w')
            if self._turn not in ('w', 'b'):
                self._turn = 'w'
            if self._show_move_log:
                move_log = state.get('move_log', [])
                self._move_log = [
                    str(move) for move in move_log
                    if isinstance(move, str)
                ][:200]
            else:
                self._move_log = []
            captured = state.get('captured')
            if isinstance(captured, dict):
                self._captured = {
                    'w': [
                        str(piece) for piece in captured.get('w', [])
                        if isinstance(piece, str)
                    ][:32],
                    'b': [
                        str(piece) for piece in captured.get('b', [])
                        if isinstance(piece, str)
                    ][:32],
                }
            if hasattr(self, '_buttons'):
                self._selected_square = None
                self._refresh_board()
        '''
    )
    return body.replace(
        "    self._captured = {'w': [], 'b': []}\n",
        "    self._captured = {'w': [], 'b': []}\n"
        "    self._show_move_log = %s\n" %
        ('True' if plan.get('chess_show_move_log', True) else 'False') +
        "    self._lesson_steps = %s\n" %
        json.dumps(plan.get('learner_steps') or []),
        1,
    )


def _render_carrom(spec, plan):
    return dedent(
        '''\
        def _build_canvas(self):
            self._active_player = 'A'
            self._scores = {'A': 0, 'B': 0}
            self._fouls = {'A': 0, 'B': 0}
            self._coins = {'white': 9, 'black': 9, 'queen': 1}
            self._shot_log = []
            self._aim_point = [0.5, 0.82]

            canvas = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            canvas.set_border_width(18)

            goal = Gtk.Label(label=LEARNER_GOAL)
            goal.set_line_wrap(True)
            goal.set_xalign(0)
            canvas.pack_start(goal, False, False, 0)

            play_area = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                                spacing=18)
            canvas.pack_start(play_area, True, True, 0)

            self._board = Gtk.DrawingArea()
            self._board.set_size_request(560, 560)
            self._board.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            self._board.connect('draw', self._draw_carrom_board)
            self._board.connect('button-press-event',
                                self._board_clicked)
            play_area.pack_start(self._board, True, True, 0)

            side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            side.set_size_request(330, -1)
            play_area.pack_start(side, False, False, 0)

            self._turn_label = Gtk.Label()
            self._turn_label.set_xalign(0)
            self._turn_label.set_line_wrap(True)
            side.pack_start(self._turn_label, False, False, 0)

            self._score_label = Gtk.Label()
            self._score_label.set_xalign(0)
            self._score_label.set_line_wrap(True)
            side.pack_start(self._score_label, False, False, 0)

            self._aim_label = Gtk.Label()
            self._aim_label.set_xalign(0)
            self._aim_label.set_line_wrap(True)
            side.pack_start(self._aim_label, False, False, 0)

            self._shot_note = Gtk.Entry()
            self._shot_note.set_placeholder_text(
                'Shot idea, rebound plan, or partner note')
            side.pack_start(self._shot_note, False, False, 0)

            controls = Gtk.Grid(row_spacing=6, column_spacing=6)
            side.pack_start(controls, False, False, 0)

            buttons = (
                ('Pocket white', self._record_pocket, 'white'),
                ('Pocket black', self._record_pocket, 'black'),
                ('Pocket queen', self._record_pocket, 'queen'),
                ('Foul', self._record_foul, None),
                ('Switch turn', self._switch_turn, None),
                ('Reset match', self._reset_match, None),
            )
            for index, item in enumerate(buttons):
                label, callback, value = item
                button = Gtk.Button(label=label)
                if value is None:
                    button.connect('clicked', callback)
                else:
                    button.connect('clicked', callback, value)
                controls.attach(button, index % 2, index // 2, 1, 1)

            log_label = Gtk.Label(label='Shot log')
            log_label.set_xalign(0)
            side.pack_start(log_label, False, False, 0)

            scroll = Gtk.ScrolledWindow()
            scroll.set_size_request(300, 180)
            self._log_view = Gtk.TextView()
            self._log_view.set_editable(False)
            self._log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
            scroll.add(self._log_view)
            side.pack_start(scroll, True, True, 0)

            help_text = Gtk.Label(
                label='Click the board to place the striker aim marker, '
                      'record the shot result, then switch turns. The match '
                      'state is saved in the Journal.')
            help_text.set_xalign(0)
            help_text.set_line_wrap(True)
            side.pack_start(help_text, False, False, 0)

            self.set_canvas(canvas)
            self._update_carrom_panel()
            canvas.show_all()

        def _board_geometry(self, allocation):
            size = min(allocation.width, allocation.height) - 18
            if size < 240:
                size = min(allocation.width, allocation.height)
            left = (allocation.width - size) / 2.0
            top = (allocation.height - size) / 2.0
            return left, top, size

        def _board_clicked(self, widget, event):
            left, top, size = self._board_geometry(widget.get_allocation())
            if event.x < left or event.y < top or \
                    event.x > left + size or event.y > top + size:
                return False
            self._aim_point = [
                (event.x - left) / size,
                (event.y - top) / size,
            ]
            self._set_carrom_status(
                '%s set an aim point. Add a note, then record the result.' %
                self._player_name())
            self._board.queue_draw()
            self._update_carrom_panel()
            return True

        def _draw_carrom_board(self, widget, context):
            left, top, size = self._board_geometry(widget.get_allocation())
            context.set_source_rgb(0.92, 0.80, 0.58)
            context.rectangle(left, top, size, size)
            context.fill()

            border = max(8, size * 0.035)
            context.set_source_rgb(0.45, 0.22, 0.09)
            context.set_line_width(border)
            context.rectangle(left + border / 2.0, top + border / 2.0,
                              size - border, size - border)
            context.stroke()

            context.set_source_rgb(0.66, 0.36, 0.17)
            context.set_line_width(max(2, size * 0.006))
            context.rectangle(left + size * 0.12, top + size * 0.12,
                              size * 0.76, size * 0.76)
            context.stroke()

            pocket_radius = size * 0.052
            for nx, ny in ((0.08, 0.08), (0.92, 0.08),
                           (0.08, 0.92), (0.92, 0.92)):
                self._draw_disc(context, left + nx * size, top + ny * size,
                                pocket_radius, (0.05, 0.05, 0.05),
                                (0.35, 0.18, 0.08))

            context.set_source_rgb(0.52, 0.22, 0.12)
            context.set_line_width(max(2, size * 0.006))
            context.arc(left + size * 0.5, top + size * 0.5,
                        size * 0.16, 0, 6.28318)
            context.stroke()
            context.arc(left + size * 0.5, top + size * 0.5,
                        size * 0.045, 0, 6.28318)
            context.stroke()

            self._draw_remaining_coins(context, left, top, size)

            aim_x = left + self._aim_point[0] * size
            aim_y = top + self._aim_point[1] * size
            center_x = left + size * 0.5
            center_y = top + size * 0.5
            context.set_source_rgb(0.20, 0.35, 0.75)
            context.set_line_width(max(2, size * 0.006))
            context.move_to(aim_x, aim_y)
            context.line_to(center_x, center_y)
            context.stroke()
            self._draw_disc(context, aim_x, aim_y, size * 0.04,
                            (0.93, 0.93, 0.98), (0.20, 0.35, 0.75))
            return False

        def _draw_remaining_coins(self, context, left, top, size):
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
                    (self._coins.get('white', 0),
                     (0.96, 0.94, 0.86), (0.55, 0.48, 0.38)),
                    (self._coins.get('black', 0),
                     (0.08, 0.08, 0.08), (0.35, 0.35, 0.35))):
                for unused in range(max(0, min(9, count))):
                    dx, dy = positions[index % len(positions)]
                    self._draw_disc(context, left + size * (0.5 + dx),
                                    top + size * (0.5 + dy), radius,
                                    fill, stroke)
                    index += 1
            if self._coins.get('queen', 0):
                self._draw_disc(context, left + size * 0.5,
                                top + size * 0.5, radius * 1.05,
                                (0.72, 0.05, 0.08), (0.40, 0.02, 0.04))

        def _draw_disc(self, context, x, y, radius, fill, stroke):
            context.set_source_rgb(fill[0], fill[1], fill[2])
            context.arc(x, y, radius, 0, 6.28318)
            context.fill_preserve()
            context.set_source_rgb(stroke[0], stroke[1], stroke[2])
            context.set_line_width(max(1, radius * 0.16))
            context.stroke()

        def _record_pocket(self, button, coin_type):
            if self._coins.get(coin_type, 0) <= 0:
                self._set_carrom_status('No %s coins remain.' % coin_type)
                return
            self._coins[coin_type] -= 1
            points = 3 if coin_type == 'queen' else 1
            self._scores[self._active_player] += points
            note = self._consume_shot_note()
            self._append_shot_log(
                '%s pocketed %s for %d point%s%s' % (
                    self._player_name(),
                    coin_type,
                    points,
                    '' if points == 1 else 's',
                    note,
                ))
            self._set_carrom_status(
                'Recorded %s. Switch turns or let the same player continue.' %
                coin_type)
            self._update_carrom_panel()

        def _record_foul(self, button):
            self._fouls[self._active_player] += 1
            if self._scores[self._active_player] > 0:
                self._scores[self._active_player] -= 1
            note = self._consume_shot_note()
            self._append_shot_log('%s made a foul%s' % (
                self._player_name(), note))
            self._set_carrom_status('Foul recorded. Switch turns.')
            self._update_carrom_panel()

        def _switch_turn(self, button):
            self._active_player = 'B' if self._active_player == 'A' else 'A'
            self._set_carrom_status('%s to shoot next.' %
                                    self._player_name())
            self._update_carrom_panel()

        def _reset_match(self, button):
            self._active_player = 'A'
            self._scores = {'A': 0, 'B': 0}
            self._fouls = {'A': 0, 'B': 0}
            self._coins = {'white': 9, 'black': 9, 'queen': 1}
            self._shot_log = []
            self._aim_point = [0.5, 0.82]
            self._set_carrom_status('New carrom match ready.')
            self._update_carrom_panel()

        def _consume_shot_note(self):
            if not hasattr(self, '_shot_note'):
                return ''
            note = self._shot_note.get_text().strip()
            self._shot_note.set_text('')
            if note:
                return ' - %s' % note
            return ''

        def _append_shot_log(self, text):
            self._shot_log.append(text)
            self._shot_log = self._shot_log[-80:]

        def _player_name(self):
            return 'Student A' if self._active_player == 'A' else 'Student B'

        def _set_carrom_status(self, text):
            self._carrom_status = text

        def _update_carrom_panel(self):
            status = getattr(
                self,
                '_carrom_status',
                'Student A to shoot. Click the board to set an aim point.')
            if hasattr(self, '_turn_label'):
                self._turn_label.set_text('%s\\n%s' %
                                          (self._player_name(), status))
            if hasattr(self, '_score_label'):
                self._score_label.set_text(
                    'Score - Student A: %d  Student B: %d\\n'
                    'Fouls - Student A: %d  Student B: %d\\n'
                    'Coins left - white: %d  black: %d  queen: %d' % (
                        self._scores.get('A', 0),
                        self._scores.get('B', 0),
                        self._fouls.get('A', 0),
                        self._fouls.get('B', 0),
                        self._coins.get('white', 0),
                        self._coins.get('black', 0),
                        self._coins.get('queen', 0),
                    ))
            if hasattr(self, '_aim_label'):
                self._aim_label.set_text(
                    'Aim marker: %.0f%% across, %.0f%% down' % (
                        self._aim_point[0] * 100,
                        self._aim_point[1] * 100,
                    ))
            if hasattr(self, '_log_view'):
                text = '\\n'.join(
                    '%d. %s' % (index + 1, item)
                    for index, item in enumerate(self._shot_log)
                )
                if not text:
                    text = 'No shots recorded yet.'
                self._log_view.get_buffer().set_text(text)
            if hasattr(self, '_board'):
                self._board.queue_draw()

        def write_file(self, file_path):
            state = {
                'active_player': self._active_player,
                'scores': self._scores,
                'fouls': self._fouls,
                'coins': self._coins,
                'shot_log': self._shot_log,
                'aim_point': self._aim_point,
            }
            with open(file_path, 'w', encoding='utf-8') as output:
                json.dump(state, output)

        def read_file(self, file_path):
            try:
                with open(file_path, encoding='utf-8') as source:
                    state = json.load(source)
            except (OSError, ValueError):
                state = {}
            self._active_player = (
                'B' if state.get('active_player') == 'B' else 'A')
            self._scores = self._clean_score_dict(state.get('scores'))
            self._fouls = self._clean_score_dict(state.get('fouls'))
            self._coins = self._clean_coin_dict(state.get('coins'))
            self._shot_log = [
                str(item) for item in state.get('shot_log', [])
                if isinstance(item, str)
            ][:80]
            aim = state.get('aim_point')
            if isinstance(aim, list) and len(aim) == 2:
                self._aim_point = [
                    max(0.0, min(1.0, float(aim[0]))),
                    max(0.0, min(1.0, float(aim[1]))),
                ]
            else:
                self._aim_point = [0.5, 0.82]
            if hasattr(self, '_turn_label'):
                self._set_carrom_status('%s restored from the Journal.' %
                                        self._player_name())
                self._update_carrom_panel()

        def _clean_score_dict(self, value):
            if not isinstance(value, dict):
                return {'A': 0, 'B': 0}
            return {
                'A': max(0, int(value.get('A', 0))),
                'B': max(0, int(value.get('B', 0))),
            }

        def _clean_coin_dict(self, value):
            if not isinstance(value, dict):
                return {'white': 9, 'black': 9, 'queen': 1}
            return {
                'white': max(0, min(9, int(value.get('white', 9)))),
                'black': max(0, min(9, int(value.get('black', 9)))),
                'queen': max(0, min(1, int(value.get('queen', 1)))),
            }
        '''
    )


def _render_narrative(spec, plan):
    starter = plan.get('starter_text', spec.prompt)
    return dedent(
        '''\
        def _build_canvas(self):
            canvas = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            canvas.set_border_width(24)

            goal = Gtk.Label(label=LEARNER_GOAL)
            goal.set_line_wrap(True)
            canvas.pack_start(goal, False, False, 0)

            scroll = Gtk.ScrolledWindow()
            self._editor = Gtk.TextView()
            self._editor.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
            self._editor.get_buffer().set_text({starter})
            scroll.add(self._editor)
            canvas.pack_start(scroll, True, True, 0)

            self.set_canvas(canvas)
            canvas.show_all()

        def write_file(self, file_path):
            text_buffer = self._editor.get_buffer()
            start, end = text_buffer.get_bounds()
            text = text_buffer.get_text(start, end, True)
            with open(file_path, 'w', encoding='utf-8') as output:
                output.write(text)

        def read_file(self, file_path):
            try:
                with open(file_path, encoding='utf-8') as source:
                    text = source.read()
            except OSError:
                text = ''
            if hasattr(self, '_editor'):
                self._editor.get_buffer().set_text(text)
        '''
    ).format(starter=json.dumps(starter))


def _render_quiz(spec, plan):
    questions = plan.get('questions') or [
        {
            'question': 'What is one thing you want to learn?',
            'answer': 'anything',
        },
        {
            'question': 'How could you explain your idea to a friend?',
            'answer': 'anything',
        },
        {
            'question': 'What would you change after testing it?',
            'answer': 'anything',
        },
    ]
    return dedent(
        '''\
        def _build_canvas(self):
            self._questions = __QUESTIONS__
            self._question_index = 0
            self._score = 0

            canvas = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
            canvas.set_border_width(24)

            self._question_label = Gtk.Label()
            self._question_label.set_line_wrap(True)
            canvas.pack_start(self._question_label, True, True, 0)

            self._answer_entry = Gtk.Entry()
            self._answer_entry.connect('activate', self._check_answer)
            canvas.pack_start(self._answer_entry, False, False, 0)

            check_button = Gtk.Button(label='Check answer')
            check_button.connect('clicked', self._check_answer)
            canvas.pack_start(check_button, False, False, 0)

            self._feedback = Gtk.Label(label=LEARNER_GOAL)
            canvas.pack_start(self._feedback, False, False, 0)
            self._show_question()

            self.set_canvas(canvas)
            canvas.show_all()

        def _show_question(self):
            item = self._questions[self._question_index]
            self._question_label.set_text(item['question'])
            self._answer_entry.set_text('')
            self._answer_entry.grab_focus()

        def _check_answer(self, widget):
            item = self._questions[self._question_index]
            expected = item.get('answer', 'anything').strip().lower()
            answer = self._answer_entry.get_text().strip().lower()
            if expected == 'anything' or answer == expected:
                self._score += 1
                message = 'Good thinking!'
            else:
                message = 'Try comparing your answer with: %s' % expected
            self._question_index = (
                self._question_index + 1) % len(self._questions)
            self._feedback.set_text(
                '%s Score: %d' % (message, self._score))
            self._show_question()

        def write_file(self, file_path):
            state = {
                'question_index': self._question_index,
                'score': self._score,
            }
            with open(file_path, 'w', encoding='utf-8') as output:
                json.dump(state, output)

        def read_file(self, file_path):
            try:
                with open(file_path, encoding='utf-8') as source:
                    state = json.load(source)
            except (OSError, ValueError):
                state = {}
            self._score = int(state.get('score', 0))
            self._question_index = int(
                state.get('question_index', 0)) % len(self._questions)
            if hasattr(self, '_question_label'):
                self._show_question()
        '''
    ).replace('__QUESTIONS__', repr(questions))


def _render_utility(spec, plan):
    mode = plan.get('utility_mode', 'word_counter')
    if mode == 'counter':
        return _render_counter_utility()
    if mode == 'timer':
        return _render_timer_utility()
    return _render_word_counter_utility()


def _render_word_counter_utility():
    return dedent(
        '''\
        def _build_canvas(self):
            canvas = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            canvas.set_border_width(24)

            goal = Gtk.Label(label=LEARNER_GOAL)
            goal.set_line_wrap(True)
            canvas.pack_start(goal, False, False, 0)

            self._utility_input = Gtk.TextView()
            self._utility_input.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
            self._utility_input.get_buffer().connect(
                'changed', self._update_count)
            scroll = Gtk.ScrolledWindow()
            scroll.add(self._utility_input)
            canvas.pack_start(scroll, True, True, 0)

            self._utility_result = Gtk.Label(label='0 words, 0 characters')
            canvas.pack_start(self._utility_result, False, False, 0)

            self.set_canvas(canvas)
            canvas.show_all()

        def _get_utility_text(self):
            text_buffer = self._utility_input.get_buffer()
            start, end = text_buffer.get_bounds()
            return text_buffer.get_text(start, end, True)

        def _update_count(self, text_buffer):
            text = self._get_utility_text()
            words = len(text.split())
            self._utility_result.set_text(
                '%d words, %d characters' % (words, len(text)))

        def write_file(self, file_path):
            with open(file_path, 'w', encoding='utf-8') as output:
                output.write(self._get_utility_text())

        def read_file(self, file_path):
            try:
                with open(file_path, encoding='utf-8') as source:
                    text = source.read()
            except OSError:
                text = ''
            if hasattr(self, '_utility_input'):
                self._utility_input.get_buffer().set_text(text)
        '''
    )


def _render_counter_utility():
    return dedent(
        '''\
        def _build_canvas(self):
            self._count = 0
            canvas = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
            canvas.set_border_width(24)

            goal = Gtk.Label(label=LEARNER_GOAL)
            goal.set_line_wrap(True)
            canvas.pack_start(goal, False, False, 0)

            self._counter_label = Gtk.Label(label='0')
            canvas.pack_start(self._counter_label, True, True, 0)

            controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                               spacing=10)
            controls.set_halign(Gtk.Align.CENTER)
            canvas.pack_start(controls, False, False, 0)

            minus_button = Gtk.Button(label='-1')
            minus_button.connect('clicked', self._change_count, -1)
            controls.pack_start(minus_button, False, False, 0)

            plus_button = Gtk.Button(label='+1')
            plus_button.connect('clicked', self._change_count, 1)
            controls.pack_start(plus_button, False, False, 0)

            reset_button = Gtk.Button(label='Reset')
            reset_button.connect('clicked', self._reset_count)
            controls.pack_start(reset_button, False, False, 0)

            self._counter_note = Gtk.Label(
                label='Use the count, then explain what it means.')
            self._counter_note.set_line_wrap(True)
            canvas.pack_start(self._counter_note, False, False, 0)

            self.set_canvas(canvas)
            canvas.show_all()

        def _change_count(self, button, amount):
            self._count += amount
            self._update_counter()

        def _reset_count(self, button):
            self._count = 0
            self._update_counter()

        def _update_counter(self):
            self._counter_label.set_text(str(self._count))

        def write_file(self, file_path):
            with open(file_path, 'w', encoding='utf-8') as output:
                json.dump({'count': self._count}, output)

        def read_file(self, file_path):
            try:
                with open(file_path, encoding='utf-8') as source:
                    state = json.load(source)
            except (OSError, ValueError):
                state = {}
            self._count = int(state.get('count', 0))
            if hasattr(self, '_counter_label'):
                self._update_counter()
        '''
    )


def _render_timer_utility():
    return dedent(
        '''\
        def _build_canvas(self):
            self._elapsed_seconds = 0
            self._timer_running = False
            self._timer_id = 0

            canvas = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
            canvas.set_border_width(24)

            goal = Gtk.Label(label=LEARNER_GOAL)
            goal.set_line_wrap(True)
            canvas.pack_start(goal, False, False, 0)

            self._timer_label = Gtk.Label(label='00:00')
            canvas.pack_start(self._timer_label, True, True, 0)

            controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                               spacing=10)
            controls.set_halign(Gtk.Align.CENTER)
            canvas.pack_start(controls, False, False, 0)

            self._timer_toggle = Gtk.Button(label='Start')
            self._timer_toggle.connect('clicked', self._toggle_timer)
            controls.pack_start(self._timer_toggle, False, False, 0)

            reset_button = Gtk.Button(label='Reset')
            reset_button.connect('clicked', self._reset_timer)
            controls.pack_start(reset_button, False, False, 0)

            self._timer_note = Gtk.Label(
                label='Use elapsed time as evidence for your reflection.')
            self._timer_note.set_line_wrap(True)
            canvas.pack_start(self._timer_note, False, False, 0)

            self.set_canvas(canvas)
            canvas.show_all()

        def _toggle_timer(self, button):
            self._timer_running = not self._timer_running
            if self._timer_running:
                self._timer_toggle.set_label('Pause')
                if not self._timer_id:
                    self._timer_id = GLib.timeout_add_seconds(
                        1, self._tick_timer)
            else:
                self._timer_toggle.set_label('Start')

        def _tick_timer(self):
            if not self._timer_running:
                self._timer_id = 0
                return False
            self._elapsed_seconds += 1
            self._update_timer()
            return True

        def _reset_timer(self, button):
            self._elapsed_seconds = 0
            self._timer_running = False
            self._timer_toggle.set_label('Start')
            self._update_timer()

        def _update_timer(self):
            minutes = self._elapsed_seconds // 60
            seconds = self._elapsed_seconds % 60
            self._timer_label.set_text('%02d:%02d' % (minutes, seconds))

        def write_file(self, file_path):
            with open(file_path, 'w', encoding='utf-8') as output:
                json.dump({'elapsed_seconds': self._elapsed_seconds}, output)

        def read_file(self, file_path):
            try:
                with open(file_path, encoding='utf-8') as source:
                    state = json.load(source)
            except (OSError, ValueError):
                state = {}
            self._elapsed_seconds = int(state.get('elapsed_seconds', 0))
            if hasattr(self, '_timer_label'):
                self._update_timer()
        '''
    )


def _indent(text, spaces):
    prefix = ' ' * spaces
    return '\n'.join(
        prefix + line if line else '' for line in text.splitlines()
    )


_TEMPLATE_RENDERERS = {
    'canvas': _render_canvas,
    'carrom': _render_carrom,
    'chess': _render_chess,
    'grid': _render_grid,
    'narrative': _render_narrative,
    'quiz': _render_quiz,
    'utility': _render_utility,
}
