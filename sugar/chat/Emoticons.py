emoticons_table = [						\
[ 'stock_smiley-10', [ ':P', ':p' ] ],	\
[ 'stock_smiley-19', None ],			\
[ 'stock_smiley-2', None ],				\
[ 'stock_smiley-11', None ],			\
[ 'stock_smiley-1', ':)' ],				\
[ 'stock_smiley-3', None ],				\
[ 'stock_smiley-12', None ],			\
[ 'stock_smiley-20', None ],			\
[ 'stock_smiley-4', ':(' ],				\
[ 'stock_smiley-13', None ],			\
[ 'stock_smiley-21', None ],			\
[ 'stock_smiley-5', None ],				\
[ 'stock_smiley-14', None ],			\
[ 'stock_smiley-22', None ],			\
[ 'stock_smiley-6', None ],				\
[ 'stock_smiley-15', None ],			\
[ 'stock_smiley-23', None ],			\
[ 'stock_smiley-7', None ],				\
[ 'stock_smiley-16', None ],			\
[ 'stock_smiley-24', None ],			\
[ 'stock_smiley-8', None ],				\
[ 'stock_smiley-17', None ],			\
[ 'stock_smiley-25', None ],			\
[ 'stock_smiley-9', None ],				\
[ 'stock_smiley-18', None ],			\
[ 'stock_smiley-26', None ],			\
]

class Emoticons:
	instance = None

	def get_instance():
		if not Emoticons.instance:
			Emoticons.instance = Emoticons()
		return Emoticons.instance

	get_instance = staticmethod(get_instance)

	def __init__(self):
		self._table = {}

		for emoticon in emoticons_table:		
			[ name, text_emts ] = emoticon
			self.add(name, text_emts)
	
	def add(self, icon_name, text=None):
		self._table[icon_name] = text
	
	def get_all(self):
		return self._table.keys()
	
	"""Replace emoticons text with the icon name.
	
	Parse the provided text to find emoticons (in
	textual form) and replace them with their xml
	representation in the form:
	<icon name="$EMOTICON_ICON_NAME"/>
	"""
	def replace(self, text):
		for icon_name in self._table.keys():
			text_emts = self._table[icon_name]
			if text_emts:
				for emoticon_text in text_emts: 
					xml = '<icon name="' + icon_name + '"/>'
					text = text.replace(emoticon_text, xml)
		return text
