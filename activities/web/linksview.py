# Copyright (C) 2006, Red Hat, Inc.
#
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

import gtk
import hippo

from sugar.graphics.menu import Menu
from sugar.graphics.menushell import MenuShell
from sugar.graphics.menuicon import MenuIcon
from sugar.graphics.iconcolor import IconColor
from sugar.graphics import style

class LinkIcon(MenuIcon):
	def __init__(self, menu_shell, link):
		color = IconColor(link.buddy.get_color())
		MenuIcon.__init__(self, menu_shell, color=color,
						  icon_name='activity-web')

		self._link = link

	def create_menu(self):
		menu = Menu(self._link.title)
		return menu

class LinksView(hippo.Canvas):
	def __init__(self, model, browser):
		hippo.Canvas.__init__(self)

		self._icons = {}
		self._browser = browser
		self._menu_shell = MenuShell(self)

		self._box = hippo.CanvasBox()
		style.apply_stylesheet(self._box, 'links.Box')
		self.set_root(self._box)

		for link in model:
			self._add_link(link)

		model.connect('link_added', self._link_added_cb)
		model.connect('link_removed', self._link_removed_cb)

	def _add_link(self, link):
		if len(self._icons) == 0:
			self.show()

		icon = LinkIcon(self._menu_shell, link)
		icon.connect('activated', self._link_activated_cb, link)
		style.apply_stylesheet(icon, 'links.Icon')
		self._box.append(icon)

		self._icons[link] = icon

	def _remove_link(self, link):
		icon = self._icons[link]
		self._box.remove(icon)

		del self._icons[link]

		if len(self._icons) == 0:
			self.hide()

	def _link_added_cb(self, model, link):
		self._add_link(link)

	def _link_removed_cb(self, model, link):
		self._remove_link(link)

	def _link_activated_cb(self, link_item, link):
		self._browser.load_url(link.url)
