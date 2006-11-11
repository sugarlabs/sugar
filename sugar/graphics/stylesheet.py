from sugar.graphics import style

menu = {
	'background_color' : 0x000000FF,
	'spacing'		   : style.space_unit,
	'padding'		   : style.space_unit
}

menu_Title = {
	'color'	: 0xFFFFFFFF,
	'font'	: style.get_font_description('Bold', 1.2)
}

menu_Separator = {
	'background_color' : 0xFFFFFFFF,
	'box_height'       : style.separator_thickness
}

menu_ActionIcon = {
	'size' : style.standard_icon_size
}

menu_Item = {
	'color'	: 0xFFFFFFFF,
	'font'  : style.get_font_description('Plain', 1.1)
}

menu_Text = {
	'color'	: 0xFFFFFFFF,
	'font'  : style.get_font_description('Plain', 1.2)
}
