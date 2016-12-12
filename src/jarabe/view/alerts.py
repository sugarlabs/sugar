# Copyright (C) 2013 Sugar Labs
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

import logging
from gettext import gettext as _

from sugar3.graphics.alert import ErrorAlert


class BaseErrorAlert(ErrorAlert):

    def __init__(self, title, message):
        ErrorAlert.__init__(self)

        logging.error('%s: %s' % (title, message))
        self.props.title = title
        self.props.msg = message


class MultipleInstanceAlert(BaseErrorAlert):

    def __init__(self, name):
        BaseErrorAlert.__init__(
            self,
            _('Activity launcher'),
            _('%s is already running. \
Please stop %s before launching it again.' % (name, name)))


class MaxOpenActivitiesAlert(BaseErrorAlert):

    def __init__(self):
        BaseErrorAlert.__init__(
            self,
            _('Activity launcher'),
            _('The maximum number of open activities has been reached. \
Please close an activity before launching a new one.'))


def _alert_response_cb(alert, response_id, window):
    window.remove_alert(alert)


def show_multiple_instance_alert(window, activity_name):
    alert = MultipleInstanceAlert(activity_name)
    alert.connect('response', _alert_response_cb, window)
    window.add_alert(alert)
    alert.show()


def show_max_open_activities_alert(window):
    alert = MaxOpenActivitiesAlert()
    alert.connect('response', _alert_response_cb, window)
    window.add_alert(alert)
    alert.show()
