# Copyright (C) 2007, Red Hat, Inc.
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

import hippo
import random, math
import gobject

from sugar.graphics.canvasicon import CanvasIcon
from sugar.graphics import color
from sugar.graphics import units
from sugar.graphics.xocolor import XoColor

# Ported from a JavaScript implementation (C) 2007 Jacob Rus
# http://www.hcs.harvard.edu/~jrus/olpc/colorpicker.svg


# An array of arrays with value 1-9 for each of 40 different hues,
# starting with 5R, and going all the way around to 2.5R.

munsell_colors = [
      #   1         2         3         4         5         6         7         8         9
      ["#40011d","#640d28","#8e172e","#bf1837","#f50141","#fc5f68","#f49599","#f1bdc3","#f8dfe9"], #  5   R
      ["#410117","#630f1f","#8d1c21","#bd2024","#f21d22","#fc6252","#f5968d","#f2bdbe","#f9dfe7"], #  7.5 R
      ["#410210","#631214","#940c00","#b03716","#d84b18","#f96735","#f49781","#f3bdb8","#fadfe5"], # 10   R
      ["#410405","#611601","#7c3111","#a14614","#c85b15","#f07015","#fd9465","#f2beb2","#fbdfe1"], #  2.5 YR
      ["#381001","#542305","#763601","#944f1f","#ba651f","#e07b1d","#f69955","#febc98","#fcdfdc"], #  5   YR
      ["#2b180e","#492a14","#6b3e14","#8e5313","#b26a0a","#d1832b","#f69b26","#f9be91","#fbe0d7"], #  7.5 YR
      ["#2a190b","#462c0f","#66400c","#885703","#a67020","#c9881a","#eba004","#fcbf6f","#f9e1d3"], # 10   YR
      ["#271a09","#422e09","#614303","#7c5c1e","#9e7415","#bb8e32","#dda72c","#ffc01e","#f6e2d0"], #  2.5 Y
      ["#251b09","#3f2f06","#574621","#775e19","#967709","#b2922a","#d2ac1d","#edc73f","#fae3b2"], #  5   Y
      ["#221c0a","#3b3105","#534820","#706116","#8b7b2e","#a99525","#c8af13","#e3ca3a","#fde676"], #  7.5 Y
      ["#1f1d0d","#363207","#4e4920","#6a6316","#857d2f","#a19825","#beb30e","#dacd39","#f8ea20"], # 10   Y
      ["#1c1e11","#31340e","#474c02","#61651c","#7b810b","#959b2b","#b0b71b","#ccd23f","#e8ee25"], #  2.5 GY
      ["#1a1e13","#2b3515","#3e4e0f","#576824","#6e841e","#85a007","#a1ba30","#b9d719","#d6f337"], #  5   GY
      ["#082205","#18390a","#255301","#3e6d19","#508914","#61a704","#7ec22e","#90e01a","#abfc39"], #  7.5 GY
      ["#01230d","#0b3a18","#0a541b","#2a6f2d","#048f1e","#0bad21","#15cb23","#0cea1c","#91fe81"], # 10   GY
      ["#141f1a","#183728","#115336","#2b6d4c","#2e8b5b","#2ba96a","#20c877","#4be48e","#83feaf"], #  2.5 G
      ["#131f1b","#15382c","#285041","#226d54","#138c68","#3ea681","#33c695","#54e2ae","#8afbcc"], #  5   G
      ["#121f1c","#11382f","#245045","#176e5a","#3c8874","#33a78a","#1ac6a0","#46e2b9","#81fbd6"], #  7.5 G
      ["#111f1e","#0d3832","#205049","#0a6e60","#38887a","#26a792","#4ec2ac","#38e2c4","#79fbe0"], # 10   G
      ["#0f1f1f","#083836","#1c504d","#366a66","#338880","#13a79a","#45c2b4","#24e2ce","#72fbe9"], #  2.5 BG
      ["#0e1f22","#03383b","#185053","#34696c","#2d8788","#49a3a2","#3cc2be","#5addd9","#6afbf4"], #  5   BG
      ["#0c1f24","#00373e","#155057","#336970","#28878f","#46a2aa","#37c1c8","#55dde4","#92f5fb"], #  7.5 BG
      ["#0c1f26","#23343b","#154f5c","#336975","#278697","#46a1b1","#34c0d2","#52dced","#b5effd"], # 10   BG
      ["#0c1f27","#23343c","#154f60","#356879","#2b859d","#49a0b8","#3bbedb","#55dbf7","#d5e8f8"], #  2.5 B
      ["#0c1f29","#023649","#1a4e64","#076988","#3584a2","#19a1ca","#49bce4","#88d4f5","#d8e7f9"], #  5   B
      ["#0e1e2a","#0a354c","#224d66","#21688b","#0284b3","#3a9fce","#58baea","#90d2f9","#dbe6fa"], #  7.5 B
      ["#101e2c","#13344d","#294b68","#2f668d","#2d82b6","#1f9edf","#43b9fe","#9bd0fd","#dee5fa"], # 10   B
      ["#021e38","#1c334f","#1d4b77","#23649e","#277fc7","#159bf3","#7eb3f0","#b8cbee","#e2e4fa"], #  2.5 PB
      ["#0d1c38","#14315d","#1a4885","#2661ac","#2e7cd6","#4f96f4","#8eb0f1","#bec9ef","#e4e4fa"], #  5   PB
      ["#1c0560","#2c089c","#3b0ddf","#3f45f7","#566ff1","#7d8ef2","#a2abf2","#c7c7ee","#e8e3fa"], #  7.5 PB
      ["#290652","#45018a","#5f0fbf","#7d16fe","#8261f3","#9784fb","#b0a4fe","#ccc3fe","#eae2f9"], # 10   PB
      ["#2e0945","#510079","#7103ab","#911ddb","#a945fd","#b577fd","#c1a0f7","#d5c1fa","#ece1f9"], #  2.5 P
      ["#340541","#54086b","#79079a","#9d18c8","#c226f9","#ca6bfc","#d397fc","#dcbff5","#ede1f8"], #  5   P
      ["#37023f","#55115e","#7e0e8a","#a519b3","#d11ee0","#f045ff","#ee8af6","#f2b6f7","#f1e0f5"], #  7.5 P
      ["#340a36","#5a0c59","#7f177a","#a9229e","#d822c6","#f749e2","#fa86e8","#fab4ee","#f2e0f3"], # 10   P
      ["#360833","#600450","#880c6d","#b3128e","#e401b2","#fa4fc6","#fa8ad2","#f4b9de","#f4e0f2"], #  2.5 RP
      ["#39062f","#5b1344","#8d0060","#b32078","#e71994","#fb56aa","#f68fbd","#f9b8d5","#f5dff0"], #  5   RP
      ["#3b052b","#5e113e","#881951","#b81a69","#ec0c82","#f56099","#fa8eb3","#fcb7cf","#f6dfee"], #  7.5 RP
      ["#3d0427","#600f38","#8c1645","#bd145a","#e72a6f","#f95f88","#fe8ea7","#ffb7c8","#f7dfed"], # 10   RP
      ["#3f0222","#620d31","#8d153a","#bf124b","#e92a5e","#fb5f79","#f295a1","#efbdc8","#f6dfeb"], #  2.5 R
]
    
# neutral values from 0 to 10.  Not sure these are completely
# accurate; my method was a bit of a guesstimate.
munsell_neutrals = [
  '#000000', '#1d1d1d', '#323232', '#494949', '#626262', '#7c7c7c',
  '#969696', '#b1b1b1', '#cbcbcb', '#e7e7e7', '#ffffff'
]


def _hex_color(hue, value):
    # hue ranges from 0 (5R) to 39 (2.5R).  value ranges from 1 to 9
    return munsell_colors[hue][value-1]

def rand(n):
    return int(math.floor(random.random() * n))


class ColorPicker(hippo.CanvasBox, hippo.CanvasItem):
    __gsignals__ = {
        'color': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT])),
    }

    def __init__(self, **kwargs):
        hippo.CanvasBox.__init__(self, **kwargs)
        self.props.orientation = hippo.ORIENTATION_HORIZONTAL

        # 5YR7: #f69955
        # 5BP3: #1a4885
        self._fg_hue = 4
        self._fg_value = 7
        self._bg_hue = 28
        self._bg_value = 3
        
        self._fg_hex = _hex_color(self._fg_hue, self._fg_value)
        self._bg_hex = _hex_color(self._bg_hue, self._bg_value)
        
        self._pie_hues = 10
        self._slider_values = 9

        self._xo = CanvasIcon(scale=units.XLARGE_ICON_SCALE,
                            icon_name='theme:stock-buddy',
                            stroke_color=color.HTMLColor(self._fg_hex),
                            fill_color=color.HTMLColor(self._bg_hex))
        self._set_random_colors()
        self._emit_color()
        self._xo.connect('activated', self._xo_activated_cb)
        self.append(self._xo)

    def _xo_activated_cb(self, item):
        self._set_random_colors()
        self._emit_color()

    def _emit_color(self):
        xo_color = XoColor('%s,%s' % (self._xo.props.stroke_color.get_html(), 
                                        self._xo.props.fill_color.get_html()))
        self.emit('color', xo_color)

    def _update_xo_hex(self, fg=None, bg=None):
        """set the colors of the XO man"""
        if fg:
            self._xo.props.stroke_color = color.HTMLColor(fg)
        if bg:
            self._xo.props.fill_color = color.HTMLColor(bg)

    def _update_fg_hue(self, pie_fg_hue):
        """change foreground (fill) hue"""
        self._fg_hue = pie_fg_hue * (40 / self._pie_hues)
        self._fg_hex = _hex_color(self._fg_hue, self._fg_value)
      
        self._update_xo_hex(fg=self._fg_hex)
      
        # set value slider
        #for i in range(1, 10):
        #    setFill("fgv" + i, _hex_color(self._fg_hue, i))  
      
        # rotate selection dingus
        #svgDocument.getElementById("fgHueSelect").setAttribute(
        #  "transform",
        #  "rotate(" + (360/self._pie_hues) * pie_fg_hue + ")"
        #)
    
    def _update_bg_hue(self, pie_bg_hue):
        """change background (stroke) hue"""
        self._bg_hue = pie_bg_hue * (40 / self._pie_hues)
        self._bg_hex = _hex_color(self._bg_hue, self._bg_value)
      
        self._update_xo_hex(bg=self._bg_hex)
      
        # set value slider
        #for i in range(1, self._slider_values + 1):
        #    setFill("bgv" + i, _hex_color(self._bg_hue, i))
      
        # rotate selection dingus
        #svgDocument.getElementById("bgHueSelect").setAttribute(
        #  "transform",
        #  "rotate(" + (360/self._pie_hues) * pie_bg_hue + ")"
        #)
    
    def _update_fg_value(self, slider_fg_value):
        self._fg_value = slider_fg_value
        self._fg_hex = _hex_color(self._fg_hue, self._fg_value)
      
        self._update_xo_hex(fg=self._fg_hex)
      
        # set hue pie
        #for i in range(0, self._pie_hues):
        #    cur_hue = i * (40 / self._pie_hues)
        #    setFill("fgh" + i, _hex_color(cur_hue, self._fg_value))  
      
        # move selection dingus
        #svgDocument.getElementById("fgValueSelect").setAttribute(
        #  "transform",
        #  "translate(0 -" + 22 * slider_fg_value + ")"
        #)
    
    def _update_bg_value(self, slider_bg_value):
        self._bg_value = slider_bg_value
        self._bg_hex = _hex_color(self._bg_hue, self._bg_value)
      
        self._update_xo_hex(bg=self._bg_hex)
      
        # set hue pie
        #for i in range(0, self._pie_hues):
        #    cur_hue = i * (40 / self._pie_hues)
        #    setFill("bgh" + i, _hex_color(cur_hue, self._bg_value))  
      
        # move selection dingus
        #svgDocument.getElementById("bgValueSelect").setAttribute(
        #  "transform",
        #  "translate(0 -" + 22 * slider_bg_value + ")"
        #)

    def _set_random_colors(self):
        self._update_fg_hue(rand(self._pie_hues))
        self._update_fg_value(rand(self._slider_values)+1)
        self._update_bg_hue(rand(self._pie_hues))
        self._update_bg_value(rand(self._slider_values)+1)

