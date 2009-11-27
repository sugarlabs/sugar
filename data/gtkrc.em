@{
if scaling == '72':
    icon_sizes = 'gtk-large-toolbar=40,40'
else:
    icon_sizes = 'gtk-large-toolbar=55,55'
}@
gtk-theme-name = "sugar-@scaling"
gtk-icon-theme-name = "sugar"
gtk-cursor-theme-name = "sugar"
gtk-toolbar-style = GTK_TOOLBAR_ICONS
gtk-icon-sizes = "@icon_sizes"
gtk-cursor-blink-timeout = 3
