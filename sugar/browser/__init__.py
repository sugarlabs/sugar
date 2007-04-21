"""Sugar's web-browser activity

XUL Runner and gtkmozembed and is produced by the PyGTK
.defs system.
"""

try:
    from sugar.browser._sugarbrowser import *
except ImportError:
    from sugar import ltihooks
    from sugar.browser._sugarbrowser import *
