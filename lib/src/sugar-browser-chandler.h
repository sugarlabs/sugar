#ifndef __SUGAR_BROWSER_CHANDLER_H__
#define __SUGAR_BROWSER_CHANDLER_H__

#include <glib-object.h>
#include <glib.h>

G_BEGIN_DECLS

typedef struct _SugarBrowserChandler SugarBrowserChandler;
typedef struct _SugarBrowserChandlerClass SugarBrowserChandlerClass;

#define SUGAR_TYPE_BROWSER_CHANDLER				 (sugar_browser_chandler_get_type())
#define SUGAR_BROWSER_CHANDLER(object)			 (G_TYPE_CHECK_INSTANCE_CAST((object), SUGAR_TYPE_BROWSER_CHANDLER, SugarBrowserChandler))
#define SUGAR_BROWSER_CHANDLER_CLASS(klass) 	 (G_TYPE_CHECK_CLASS_CAST((klass), SUGAR_TYPE_BROWSER_CHANDLER, SugarBrowserChandlerClass))
#define SUGAR_IS_BROWSER_CHANDLER(object)		 (G_TYPE_CHECK_INSTANCE_TYPE((object), SUGAR_TYPE_BROWSER_CHANDLER))
#define SUGAR_IS_BROWSER_CHANDLER_CLASS(klass) 	 (G_TYPE_CHECK_CLASS_TYPE((klass), SUGAR_TYPE_BROWSER_CHANDLER))
#define SUGAR_BROWSER_CHANDLER_GET_CLASS(object) (G_TYPE_INSTANCE_GET_CLASS((object), SUGAR_TYPE_BROWSER_CHANDLER, SugarBrowserChandlerClass))

struct _SugarBrowserChandler {
	GObject base_instance;
};

struct _SugarBrowserChandlerClass {
	GObjectClass base_class;
	
	void (* handle_content) (char *url, char *tmp_file_name);
	
};

GType				  sugar_browser_chandler_get_type	    (void);
SugarBrowserChandler *sugar_get_browser_chandler		    (void);
void            	  sugar_browser_chandler_handle_content (SugarBrowserChandler *chandler,
															 const char *url, 
															 const char *suggested_file_name, 
															 const char *mime_type,
															 const char *tmp_file_name);

G_END_DECLS

#endif
