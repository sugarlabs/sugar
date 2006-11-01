#include "sugar-marshal.h"
#include "sugar-browser-chandler.h"

enum {
  DOWNLOAD_STARTED,
  DOWNLOAD_COMPLETED,
  DOWNLOAD_CANCELLED,
  DOWNLOAD_PROGRESS,
  LAST_SIGNAL
};
static guint signals[LAST_SIGNAL] = { 0 };

G_DEFINE_TYPE(SugarBrowserChandler, sugar_browser_chandler, G_TYPE_OBJECT)

SugarBrowserChandler *browserChandler = NULL;

static void
sugar_browser_chandler_init(SugarBrowserChandler *browserChandler)
{
}

static void
sugar_browser_chandler_class_init(SugarBrowserChandlerClass *browser_chandler_class)
{
	signals[DOWNLOAD_STARTED] =
		g_signal_new ("download-started",
					  G_OBJECT_CLASS_TYPE (browser_chandler_class),
		  			  G_SIGNAL_RUN_LAST,
		  			  G_STRUCT_OFFSET (SugarBrowserChandlerClass, handle_content),
					  NULL, NULL,
					  sugar_marshal_VOID__STRING_STRING_STRING,
					  G_TYPE_NONE, 3,
					  G_TYPE_STRING,
					  G_TYPE_STRING,
					  G_TYPE_STRING);
					  
	signals[DOWNLOAD_COMPLETED] =
		g_signal_new ("download-completed",
					  G_OBJECT_CLASS_TYPE (browser_chandler_class),
		  			  G_SIGNAL_RUN_LAST,
		  			  G_STRUCT_OFFSET (SugarBrowserChandlerClass, handle_content),
					  NULL, NULL,
					  sugar_marshal_VOID__STRING,
					  G_TYPE_NONE, 1,
					  G_TYPE_STRING);
					  
	signals[DOWNLOAD_CANCELLED] =
		g_signal_new ("download-cancelled",
					  G_OBJECT_CLASS_TYPE (browser_chandler_class),
		  			  G_SIGNAL_RUN_LAST,
		  			  G_STRUCT_OFFSET (SugarBrowserChandlerClass, handle_content),
					  NULL, NULL,
					  sugar_marshal_VOID__STRING,
					  G_TYPE_NONE, 1,
					  G_TYPE_STRING);
					  
	signals[DOWNLOAD_PROGRESS] =
		g_signal_new ("download-progress",
					  G_OBJECT_CLASS_TYPE (browser_chandler_class),
		  			  G_SIGNAL_RUN_LAST,
		  			  G_STRUCT_OFFSET (SugarBrowserChandlerClass, handle_content),
					  NULL, NULL,
					  sugar_marshal_VOID__STRING_INT,
					  G_TYPE_NONE, 2,
					  G_TYPE_STRING,
					  G_TYPE_INT);
}

SugarBrowserChandler *
sugar_get_browser_chandler()
{  
	if(browserChandler == NULL)
		browserChandler = g_object_new(SUGAR_TYPE_BROWSER_CHANDLER, NULL);
 	
	return browserChandler;
}

void
sugar_browser_chandler_download_started (SugarBrowserChandler *browser_chandler,
										 const char *url,
										 const char *mime_type,
										 const char *tmp_file_name)
{
	g_signal_emit(browser_chandler, 
				  signals[DOWNLOAD_STARTED],
                  0 /* details */, 
                  url,
                  mime_type,
                  tmp_file_name);
}

void
sugar_browser_chandler_download_completed (SugarBrowserChandler *browser_chandler,
										   const char *tmp_file_name)
{
	g_signal_emit(browser_chandler, 
				  signals[DOWNLOAD_COMPLETED],
                  0 /* details */, 
                  tmp_file_name);
}

void sugar_browser_chandler_download_cancelled (SugarBrowserChandler *browser_chandler,
												const char *tmp_file_name)
{
	g_signal_emit(browser_chandler, 
				  signals[DOWNLOAD_CANCELLED],
                  0 /* details */, 
                  tmp_file_name);
}

void
sugar_browser_chandler_update_progress (SugarBrowserChandler *browser_chandler,
										const char *tmp_file_name,
										const int percent)
{
	g_signal_emit(browser_chandler, 
				  signals[DOWNLOAD_PROGRESS],
                  0 /* details */, 
                  tmp_file_name,
                  percent);
}
