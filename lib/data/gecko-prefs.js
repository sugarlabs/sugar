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

// Define our font size in points (to adapt to resolution)
user_pref("font.size.unit", "pt");

user_pref("font.size.variable.ar", 12);
user_pref("font.size.fixed.ar", 10);

user_pref("font.size.variable.el", 12);
user_pref("font.size.fixed.el", 10);

user_pref("font.size.variable.he", 12);
user_pref("font.size.fixed.he", 10);

user_pref("font.size.variable.ja", 12);
user_pref("font.size.fixed.ja", 12);

user_pref("font.size.variable.ko", 12);
user_pref("font.size.fixed.ko", 12);

user_pref("font.size.variable.th", 12);
user_pref("font.size.fixed.th", 10);

user_pref("font.size.variable.tr", 12);
user_pref("font.size.fixed.tr", 10);

user_pref("font.size.variable.x-baltic", 12);
user_pref("font.size.fixed.x-baltic", 10);

user_pref("font.size.variable.x-central-euro", 9);
user_pref("font.size.fixed.x-central-euro", 10);

user_pref("font.size.variable.x-cyrillic", 12);
user_pref("font.size.fixed.x-cyrillic", 10);

user_pref("font.size.variable.x-devanagari", 12);
user_pref("font.size.fixed.x-devanagari", 10);

user_pref("font.size.variable.x-tamil", 12);
user_pref("font.size.fixed.x-tamil", 10);

user_pref("font.size.variable.x-armn", 12);
user_pref("font.size.fixed.x-armn", 10);

user_pref("font.size.variable.x-beng", 12);
user_pref("font.size.fixed.x-beng", 10);

user_pref("font.size.variable.x-cans", 12);
user_pref("font.size.fixed.x-cans", 10);

user_pref("font.size.variable.x-ethi", 12);
user_pref("font.size.fixed.x-ethi", 10);

user_pref("font.size.variable.x-geor", 12);
user_pref("font.size.fixed.x-geor", 10);

user_pref("font.size.variable.x-gujr", 12);
user_pref("font.size.fixed.x-gujr", 10);

user_pref("font.size.variable.x-guru", 12);
user_pref("font.size.fixed.x-guru", 10);

user_pref("font.size.variable.x-khmr", 12);
user_pref("font.size.fixed.x-khmr", 10);

user_pref("font.size.variable.x-mlym", 12);
user_pref("font.size.fixed.x-mlym", 10);

user_pref("font.size.variable.x-unicode", 9);
user_pref("font.size.fixed.x-unicode", 10);

user_pref("font.size.variable.x-western", 9);
user_pref("font.size.fixed.x-western", 10);

user_pref("font.size.variable.zh-CN", 12);
user_pref("font.size.fixed.zh-CN", 12);

user_pref("font.size.variable.zh-TW", 12);
user_pref("font.size.fixed.zh-TW", 12);

user_pref("font.size.variable.zh-HK", 12);
user_pref("font.size.fixed.zh-HK", 12);

// Font families for Arabic

user_pref("font.name.cursive.ar", "KacstQurn");
user_pref("font.name.fantasy.ar", "KacstDecorative");
user_pref("font.name.monospace.ar", "KacstDigital");
user_pref("font.name.sans-serif.ar", "KacstQurn");
user_pref("font.name.serif.ar", "KacstBook");

// Enable error pages (xulrunner is missing this pref)
user_pref("browser.xul.error_pages.enabled", true);
