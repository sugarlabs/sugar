// Disable onload popups
user_pref("dom.disable_open_during_load", true);

// Disable usless security warnings
user_pref("security.warn_entering_secure", false);
user_pref("security.warn_entering_secure.show_once", true);
user_pref("security.warn_leaving_secure", false);
user_pref("security.warn_leaving_secure.show_once", false);
user_pref("security.warn_submit_insecure", false);
user_pref("security.warn_submit_insecure.show_once", false);
user_pref("security.warn_viewing_mixed", true);
user_pref("security.warn_viewing_mixed.show_once", false);
user_pref("security.warn_entering_weak", true);
user_pref("security.warn_entering_weak.show_once", false);

// Set some style properties to not follow our dark gtk theme
user_pref("ui.-moz-field", "#FFFFFF");
user_pref("ui.-moz-fieldtext", "#000000");
user_pref("ui.buttonface", "#D3D3DD");
user_pref("ui.buttontext", "#000000");

// Fonts
user_pref("font.size.unit", "pt");

// Layout:
// 1024x768 -> (96 * 6) / 1024 * 201 = 113 dpi
// 800x600  -> (96 * 6) /  800 * 201 = 144 dpi
//
// Fonts:
// 7  pt ->  7 / 12 * 201 = 117 dpi
// 8  pt ->  8 / 12 * 201 = 134 dpi
// 9  pt ->  9 / 12 * 201 = 150 dpi

user_pref("layout.css.dpi", 134);

user_pref("font.name.cursive.ar", "KacstQurn");
user_pref("font.name.fantasy.ar", "KacstDecorative");
user_pref("font.name.monospace.ar", "KacstDigital");
user_pref("font.name.sans-serif.ar", "KacstQurn");
user_pref("font.name.serif.ar", "KacstBook");
user_pref("font.default.ar", "sans-serif");
user_pref("font.size.variable.ar", 12);
user_pref("font.size.fixed.ar", 9);

user_pref("font.default.el", "serif");
user_pref("font.size.variable.el", 12);
user_pref("font.size.fixed.el", 9);

user_pref("font.default.he", "sans-serif");
user_pref("font.size.variable.he", 12);
user_pref("font.size.fixed.he", 9);

user_pref("font.default.ja", "sans-serif");
user_pref("font.size.variable.ja", 12);
user_pref("font.size.fixed.ja", 12);

user_pref("font.default.ko", "sans-serif");
user_pref("font.size.variable.ko", 12);
user_pref("font.size.fixed.ko", 12);

user_pref("font.default.th", "serif");
user_pref("font.size.variable.th", 12);
user_pref("font.size.fixed.th", 9);

user_pref("font.default.tr", "serif");
user_pref("font.size.variable.tr", 12);
user_pref("font.size.fixed.tr", 9);

user_pref("font.default.x-baltic", "serif");
user_pref("font.size.variable.x-baltic", 12);
user_pref("font.size.fixed.x-baltic", 9);

user_pref("font.default.x-central-euro", "serif");
user_pref("font.size.variable.x-central-euro", 12);
user_pref("font.size.fixed.x-central-euro", 9);

user_pref("font.default.x-cyrillic", "serif");
user_pref("font.size.variable.x-cyrillic", 12);
user_pref("font.size.fixed.x-cyrillic", 9);

user_pref("font.default.x-unicode", "serif");
user_pref("font.size.variable.x-unicode", 12);
user_pref("font.size.fixed.x-unicode", 9);

user_pref("font.default.x-western", "serif");
user_pref("font.size.variable.x-western", 12);
user_pref("font.size.fixed.x-western", 9);

user_pref("font.default.zh-CN", "sans-serif");
user_pref("font.size.variable.zh-CN", 12);
user_pref("font.size.fixed.zh-CN", 12);

user_pref("font.default.zh-TW", "sans-serif");
user_pref("font.size.variable.zh-TW", 12);
user_pref("font.size.fixed.zh-TW", 12);

user_pref("font.default.zh-HK", "sans-serif");
user_pref("font.size.variable.zh-HK", 12);
user_pref("font.size.fixed.zh-HK", 12);

// Enable error pages (xulrunner is missing this pref)
user_pref("browser.xul.error_pages.enabled", true);
