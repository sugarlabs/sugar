import hippo
import math

from sugar.graphics.canvasicon import CanvasIcon

class ActivitiesDonut(hippo.CanvasBox, hippo.CanvasItem):
	__gtype_name__ = 'SugarActivitiesDonut'
	def __init__(self, shell, **kwargs):
		hippo.CanvasBox.__init__(self, **kwargs)

		self._activities = {}

		shell.connect('activity_opened', self.__activity_opened_cb)
		shell.connect('activity_closed', self.__activity_closed_cb)

	def __activity_opened_cb(self, model, activity):
		self._add_activity(activity)

	def __activity_closed_cb(self, model, activity):
		self._remove_activity(activity)
	
	def _remove_activity(self, activity):
		icon = self._activities[activity.get_id()]
		self.remove(icon)
		del self._activities[activity.get_id()]

	def _add_activity(self, activity):
		icon_name = activity.get_icon_name()
		icon_color = activity.get_icon_color()

		icon = CanvasIcon(icon_name=icon_name, color=icon_color, size=75)
		icon.connect('activated', self.__activity_icon_clicked_cb, activity)
		self.append(icon, hippo.PACK_FIXED)

		self._activities[activity.get_id()] = icon

		self.emit_paint_needed(0, 0, -1, -1)

	def __activity_icon_clicked_cb(self, item, activity):
		activity.present()

	def _get_angles(self, index):
		angle = 2 * math.pi / 8
		return [index * angle, (index + 1) * angle]

	def _get_radius(self):
		[width, height] = self.get_allocation()
		return min(width, height) / 2

	def _get_inner_radius(self):
		return self._get_radius() * 0.5

	def do_paint_below_children(self, cr, damaged_box):
		[width, height] = self.get_allocation()

		cr.translate(width / 2, height / 2)

		radius = self._get_radius()

		cr.set_source_rgb(0xf1 / 255.0, 0xf1 / 255.0, 0xf1 / 255.0)
		cr.arc(0, 0, radius, 0, 2 * math.pi)
		cr.fill()

		angle_end = 0
		for i in range(0, len(self._activities)):
			[angle_start, angle_end] = self._get_angles(i)

			cr.new_path()
			cr.move_to(0, 0)
			cr.line_to(radius * math.cos(angle_start),
					   radius * math.sin(angle_start))
			cr.arc(0, 0, radius, angle_start, angle_end)
			cr.line_to(0, 0)

			cr.set_source_rgb(0xe2 / 255.0, 0xe2 / 255.0, 0xe2 / 255.0)
			cr.set_line_width(4)
			cr.stroke_preserve()

			cr.set_source_rgb(1, 1, 1)
			cr.fill()

		cr.set_source_rgb(0xe2 / 255.0, 0xe2 / 255.0, 0xe2 / 255.0)
		cr.arc(0, 0, self._get_inner_radius(), 0, 2 * math.pi)
		cr.fill()

	def do_allocate(self, width, height):
		hippo.CanvasBox.do_allocate(self, width, height)

		radius = (self._get_inner_radius() + self._get_radius()) / 2

		i = 0
		for icon in self._activities.values():
			[angle_start, angle_end] = self._get_angles(i)
			angle = angle_start + (angle_end - angle_start) / 2

			[icon_width, icon_height] = icon.get_allocation()

			x = int(radius * math.cos(angle)) - icon_width / 2
			y = int(radius * math.sin(angle)) - icon_height / 2
			self.move(icon, x + width / 2, y + height / 2)

			i += 1
