from sugar.graphics.canvasicon import CanvasIcon
import conf

class MyIcon(CanvasIcon):
	def __init__(self):
		profile = conf.get_profile()
		CanvasIcon.__init__(self, icon_name='stock-buddy',
					  	    color=profile.get_color())
