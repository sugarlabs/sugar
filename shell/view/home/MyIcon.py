from sugar.graphics.canvasicon import CanvasIcon
from sugar.graphics.iconcolor import IconColor
import conf

class MyIcon(CanvasIcon):
	def __init__(self, size):
		profile = conf.get_profile()

		CanvasIcon.__init__(self, icon_name='stock-buddy',
					  	    color=profile.get_color(), size=size)
