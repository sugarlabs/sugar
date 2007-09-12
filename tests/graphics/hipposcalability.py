import hippo
import gtk
import gobject

from sugar.graphics.icon import CanvasIcon
from sugar.graphics.roundbox import CanvasRoundBox

import common

test = common.Test()

canvas = hippo.Canvas()
test.pack_start(canvas)
canvas.show()

scrollbars = hippo.CanvasScrollbars()
canvas.set_root(scrollbars)

box = hippo.CanvasBox(padding=10, spacing=10)
scrollbars.set_root(box)

def idle_cb():
    global countdown

    for i in range(0, 100):
        entry = hippo.CanvasBox(border=2, border_color=0x000000ff,
                                orientation=hippo.ORIENTATION_HORIZONTAL,
                                padding=10, spacing=10)

        for j in range(0, 3):
            icon = CanvasIcon(icon_name='go-left')
            entry.append(icon)

        for j in range(0, 2):
            text = hippo.CanvasText(text='Text %s %s' % (countdown, j))
            entry.append(text)

        box.append(entry)

        countdown -= 1

    return countdown > 0

countdown = 1000
gobject.idle_add(idle_cb)

test.show()

if __name__ == "__main__":
    common.main(test)
