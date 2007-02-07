import gobject
import hippo

from canvasicon import CanvasIcon
from iconcolor import IconColor
from grid import Grid
from sugar import profile

class Button(hippo.CanvasBox):
    __gtype_name__ = 'Button'

    __gproperties__ = {
        'icon-name': (str, None, None, None,
                      gobject.PARAM_READWRITE),
        'active': (bool, None, None, True,
                      gobject.PARAM_READWRITE)
    }

    def __init__(self, icon_name):
        hippo.CanvasBox.__init__(self)
        
        self._active = True
        self._normal_color = IconColor('white')
        self._prelight_color = profile.get_color()
        self._inactive_color = IconColor('#808080,#424242')
                       
        grid = Grid()
        self.props.box_width = grid.dimension(1)
        self.props.box_height = grid.dimension(1)

        self._icon = CanvasIcon(icon_name=icon_name, cache=True,
                                color=self._normal_color)
        self.append(self._icon, hippo.PACK_EXPAND)
        self._connect_signals(self._icon)

    def do_set_property(self, pspec, value):
        if pspec.name == 'icon-name':
            self._icon.props.icon_name = value
        elif pspec.name == 'active':
            self._active = value
            if self._active:
                self._icon.props.color = self._normal_color
            else:
                self._icon.props.color = self._inactive_color            
        else:
            hippo.CanvasBox.do_set_property(self, pspec, value)

    def do_get_property(self, pspec):
        if pspec.name == 'icon-name':
            return self._icon.get_property('icon-name')
        elif pspec.name == 'active':
            return self._active
        else:
            return hippo.CanvasBox.get_property(self, pspec)

    def _connect_signals(self, item):
        item.connect('button-release-event', self._button_release_event_cb)
        # TODO: Prelighting is disabled by now. Need to figure how we want it to behave.
        #item.connect('motion-notify-event', self._motion_notify_event_cb)

    def _button_release_event_cb(self, widget, event):
        if self._active:
            self.emit_activated()

    def _motion_notify_event_cb(self, widget, event):
        if self._active and event.detail == hippo.MOTION_DETAIL_ENTER:
            self._icon.props.color = self._prelight_color
        elif self._active and event.detail == hippo.MOTION_DETAIL_LEAVE:
            self._icon.props.color = self._normal_color
