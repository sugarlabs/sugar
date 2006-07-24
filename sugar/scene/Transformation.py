import copy

class Transformation:
	def __init__(self):
		self._translation_x = 0
		self._translation_y = 0

	def set_translation(self, x, y):
		self._translation_x = x
		self._translation_y = y

	def get_position(self, x, y):
		translated_x = x + self._translation_x
		translated_y = y + self._translation_y
		return (translated_x, translated_y)

	def compose(self, transf):
		composed = copy.copy(transf)
		composed._translation_x += transf._translation_x
		composed._translation_y += transf._translation_y
		return composed
