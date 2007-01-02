#!/usr/bin/env python

# Copyright (C) 2007, Eduardo Silva (edsiper@gmail.com).
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

import os
import gtk, gobject
import gtk.gdk
import cairo
import string
import drwarea


class CPU_Usage:
	
	CPU_HZ = 0
	last_jiffies = 0
	times = 0
	
	def __init__(self):
		self.CPU_hz = os.sysconf(2)
		
	def _get_CPU_data(self):
		# Uptime info
		stat_file = "/proc/stat"
		
		try:
			infile = file(stat_file, "r")
		except:
			print "Error trying uptime file"
			return -1
			
		stat_line = infile.readline()
		cpu_info = string.split(stat_line, ' ')
		infile.close()
					
		return cpu_info
	
	def _get_CPU_usage(self):
		
		cpu_info = self._get_CPU_data()
		
		used_jiffies = (int(cpu_info[2]) + int(cpu_info[3]) + int(cpu_info[4]))
		
		if self.times ==0:
			self.last_jiffies = used_jiffies
			self.times +=1
			return True
		
		new_ujiffies = (used_jiffies - self.last_jiffies)
		new_ajiffies = ((self.frequency/1000) * self.CPU_hz)

		if new_ajiffies <= 0:
			pcpu = 0.0
		else:
			pcpu = ((new_ujiffies*100)/new_ajiffies)

		if pcpu >100:
			pcpu = 100
			
		self.times +=1
		self.last_jiffies = used_jiffies
		
		return pcpu

class Interface:
    
    	context = None
	frequency_timer = 1
	graph_offset = 7
	
	def __init__(self):    

		self.drw_width = gtk.gdk.screen_width() * 90 / 100
		self.drw_height = gtk.gdk.screen_height() * 20 / 100
		self.y_cpu = self.drw_height - self.graph_offset
		self.drw_buffer = []
						
		drawingarea = gtk.DrawingArea()
		drawingarea.set_size_request(self.drw_width, self.drw_height)
		drawingarea.connect("expose-event", self.do_expose)

		self.dat = drwarea.Drawing_Area_Tools(drawingarea)
		
		fixed = gtk.Fixed();
		fixed.set_border_width(10)
		fixed.add(drawingarea)
		
		self.frame = gtk.Frame('System CPU Usage: 0%')
		self.frame.set_border_width(10)
		self.frame.add(fixed)
		
		self.widget = self.hbox = gtk.HBox(False, 3)
		self.hbox.pack_start(self.frame, True, True, 0)
		self.hbox.show_all()
		
		DRW_CPU = CPU_Usage()
		DRW_CPU.frequency = 1000 # 1 Second
		
		gobject.timeout_add(DRW_CPU.frequency, self._draw_cpu_usage, DRW_CPU, drawingarea)
		
	def _draw_cpu_usage(self, DRW_CPU, drwarea):
		# End of the graph ?
		if ((self.frequency_timer + 1)*self.graph_offset) >= (self.drw_width - self.graph_offset):
			self.frequency_timer = 1
			self.drw_buffer = []
			self.do_expose(drwarea, None)
			
		context = drwarea.window.cairo_create()
		
		from_x = self.frequency_timer * self.graph_offset
		from_y = self.y_cpu

		self.frequency_timer += 1
		
		pcpu = DRW_CPU._get_CPU_usage()
		
		self.drw_buffer.append(pcpu)
				
		to_x = self.frequency_timer * self.graph_offset
		self.y_cpu = to_y = self._get_y_cpu(pcpu)
			
		# Context properties
		context.set_line_width(2)
		context.set_source_rgb(0,1,0)
			
		cpu_label = str(round(pcpu, 4))
		self.frame.set_label('System CPU Usage: ' + cpu_label + ' %')
	
		self.dat.draw_line(context, from_x, from_y, to_x, to_y)
		context.stroke()
			
		return True
	
	def _get_y_cpu(self, pcpu):

		height = (self.dat.range_y['to']) - (self.dat.range_y['from'])
		
		# Get percent of cpu usage
		y_value	= (height - ((pcpu*height)/100) + 4)

		return int(y_value) 
	
	def do_expose(self, widget, event):
		
		self.context = widget.window.cairo_create()
		self.context.rectangle(0, 0, self.dat.width - 1, self.dat.height - 1)

		self.context.set_source_rgb (0,0,0)
		self.context.fill_preserve()

		# Drawing horizontal and vertical border lines
		self.dat.draw_border_lines(self.context)
		
		# Drawing grid
		line_margin = self.dat.margin
		self.context.set_source_rgb(1, 1, 1)
		self.context.set_line_width(1)
		self.dat.draw_grid(self.context, line_margin + 1, line_margin + 1, self.dat.width - line_margin - 2, self.dat.height - line_margin - 2)
		self.context.stroke()

		self._draw_buffer(widget)
		return False

	def _draw_buffer(self, drwarea):
		freq = 1 # Frequency timer
		last_y = self.drw_height - self.graph_offset
		
		context = drwarea.window.cairo_create()		
		for pcpu in self.drw_buffer:
			
			from_x = freq * self.graph_offset
			from_y = last_y
	
			freq+=1
			
			to_x = freq * self.graph_offset
			last_y = to_y = self._get_y_cpu(pcpu)
				
			# Context properties
			context.set_line_width(2)
			context.set_source_rgb(0,1,0)
				
			self.dat.draw_line(context, from_x, from_y, to_x, to_y)
			context.stroke()
			
