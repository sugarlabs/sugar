import random

import goocanvas

from sugar.canvas.IconItem import IconItem

class ActivityItem(IconItem):
	def __init__(self, activity, registry):
		info = registry.get_activity(activity.get_type())
		icon_name = info.get_icon()

		IconItem.__init__(self, icon_name, 'green', 48)

		self._activity = activity

	def get_service(self):
		return self._activity.get_service()

class Model(goocanvas.CanvasModelSimple):
	def __init__(self, data_model, registry):
		goocanvas.CanvasModelSimple.__init__(self)
		self._registry = registry

		root = self.get_root_item()

		item = goocanvas.Rect(width=1200, height=900,
							  fill_color="#d8d8d8")
		root.add_child(item)

		for activity in data_model:
			self.add_activity(activity)

		data_model.connect('activity-added', self.__activity_added_cb)

	def add_activity(self, activity):
		root = self.get_root_item()

		item = ActivityItem(activity, self._registry)
		item.set_property('x', random.random() * 1100)
		item.set_property('y', random.random() * 800)
		root.add_child(item)

	def __activity_added_cb(self, data_model, activity):
		self.add_activity(activity)	

class MeshView(goocanvas.CanvasView):
	def __init__(self, shell, data_model):
		goocanvas.CanvasView.__init__(self)
		self._shell = shell

		self.connect("item_view_created", self.__item_view_created_cb)

		canvas_model = Model(data_model, shell.get_registry())
		self.set_model(canvas_model)

	def __activity_button_press_cb(self, view, target, event, service):
		self._shell.join_activity(service)

	def __item_view_created_cb(self, view, item_view, item):
		if isinstance(item, ActivityItem):
			item_view.connect("button_press_event",
							  self.__activity_button_press_cb,
							  item.get_service())
