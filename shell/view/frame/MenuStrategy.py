class MenuStrategy:
	def get_menu_position(self, menu, grid_x1, grid_y1, grid_x2, grid_y2):
		grid = menu.get_grid()

		[x1, y1] = grid.micro_to_macro(grid_x1, grid_y1)
		[x2, y2] = grid.micro_to_macro(grid_x2, grid_y2)

		if x1 == 0:
			x = x2
			y = y1
		elif x2 == grid.get_macro_cols():
			x = x1
			y = y1
		elif y2 == grid.get_macro_rows():
			x = x1
			y = y1
		else:
			x = x1
			y = y2

		[grid_x, grid_y] = grid.macro_to_micro(x, y)

		if x2 == grid.get_macro_cols():
			grid_x -= menu.get_width()
		elif y2 == grid.get_macro_rows():
			grid_y -= menu.get_height()

		return [grid_x, grid_y]
