from sugar.graphics.grid import Grid

class MenuStrategy:
	def get_menu_position(self, menu, x, y, width, height):
		grid = Grid()

		[grid_x1, grid_y1] = grid.fit_point(x, y)
		[grid_x2, grid_y2] = grid.fit_point(x + width, y + height)

		menu_grid_x = grid_x1
		menu_grid_y = grid_y2

		[menu_x, menu_y] = grid.point(menu_grid_x, menu_grid_y)

		return [menu_x, menu_y]
