import hippo

from sugar.graphics.grid import Grid

class MenuStrategy:
	def _get_canvas(self, item):
		canvas = item
		while (not isinstance(canvas, hippo.Canvas)):
			canvas = canvas.get_context()
		return canvas

	def _get_item_origin(self, canvas, item):
		[x, y] = item.get_context().translate_to_widget(item)

		[origin_x, origin_y] = canvas.window.get_origin()
		x += origin_x
		y += origin_y

		return [x, y]

	def get_menu_position(self, menu, item):
		canvas = self._get_canvas(item)

		[x, y] = self._get_item_origin(canvas, item)
		[width, height] = item.get_allocation()

		[canvas_x, canvas_y] = canvas.window.get_origin()
		canvas_rect = canvas.get_allocation()
		[menu_w, menu_h] = menu.size_request()

		menu_x = x
		menu_y = y + height

		if (menu_x + menu_w > canvas_x) and \
		   (menu_y < canvas_y + canvas_rect.height):
			menu_x = x - menu_w
			menu_y = y

		return [menu_x, menu_y]
