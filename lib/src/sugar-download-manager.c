#include "sugar-marshal.h"
#include "sugar-download-manager.h"

enum {
  DOWNLOAD_STARTED,
  DOWNLOAD_COMPLETED,
  DOWNLOAD_CANCELLED,
  DOWNLOAD_PROGRESS,
  LAST_SIGNAL
};
static guint signals[LAST_SIGNAL] = { 0 };

G_DEFINE_TYPE(SugarDownloadManager, sugar_download_manager, G_TYPE_OBJECT)

SugarDownloadManager *DownloadManager = NULL;

static void
sugar_download_manager_init(SugarDownloadManager *DownloadManager)
{
}

static void
sugar_download_manager_class_init(SugarDownloadManagerClass *download_manager_class)
{
	signals[DOWNLOAD_STARTED] =
		g_signal_new ("download-started",
					  G_OBJECT_CLASS_TYPE (download_manager_class),
		  			  G_SIGNAL_RUN_LAST,
		  			  G_STRUCT_OFFSET (SugarDownloadManagerClass, handle_content),
					  NULL, NULL,
					  sugar_marshal_VOID__STRING_STRING_STRING,
					  G_TYPE_NONE, 3,
					  G_TYPE_STRING,
					  G_TYPE_STRING,
					  G_TYPE_STRING);
					  
	signals[DOWNLOAD_COMPLETED] =
		g_signal_new ("download-completed",
					  G_OBJECT_CLASS_TYPE (download_manager_class),
		  			  G_SIGNAL_RUN_LAST,
		  			  G_STRUCT_OFFSET (SugarDownloadManagerClass, handle_content),
					  NULL, NULL,
					  sugar_marshal_VOID__STRING,
					  G_TYPE_NONE, 1,
					  G_TYPE_STRING);
					  
	signals[DOWNLOAD_CANCELLED] =
		g_signal_new ("download-cancelled",
					  G_OBJECT_CLASS_TYPE (download_manager_class),
		  			  G_SIGNAL_RUN_LAST,
		  			  G_STRUCT_OFFSET (SugarDownloadManagerClass, handle_content),
					  NULL, NULL,
					  sugar_marshal_VOID__STRING,
					  G_TYPE_NONE, 1,
					  G_TYPE_STRING);
					  
	signals[DOWNLOAD_PROGRESS] =
		g_signal_new ("download-progress",
					  G_OBJECT_CLASS_TYPE (download_manager_class),
		  			  G_SIGNAL_RUN_LAST,
		  			  G_STRUCT_OFFSET (SugarDownloadManagerClass, handle_content),
					  NULL, NULL,
					  sugar_marshal_VOID__STRING_INT,
					  G_TYPE_NONE, 2,
					  G_TYPE_STRING,
					  G_TYPE_INT);
}

SugarDownloadManager *
sugar_get_download_manager()
{  
	if(DownloadManager == NULL)
		DownloadManager = g_object_new(SUGAR_TYPE_DOWNLOAD_MANAGER, NULL);
 	
	return DownloadManager;
}

void
sugar_download_manager_download_started (SugarDownloadManager *download_manager,
										 const char *url,
										 const char *mime_type,
										 const char *tmp_file_name)
{
	g_signal_emit(download_manager, 
				  signals[DOWNLOAD_STARTED],
                  0 /* details */, 
                  url,
                  mime_type,
                  tmp_file_name);
}

void
sugar_download_manager_download_completed (SugarDownloadManager *download_manager,
										   const char *tmp_file_name)
{
	g_signal_emit(download_manager, 
				  signals[DOWNLOAD_COMPLETED],
                  0 /* details */, 
                  tmp_file_name);
}

void sugar_download_manager_download_cancelled (SugarDownloadManager *download_manager,
												const char *tmp_file_name)
{
	g_signal_emit(download_manager, 
				  signals[DOWNLOAD_CANCELLED],
                  0 /* details */, 
                  tmp_file_name);
}

void
sugar_download_manager_update_progress (SugarDownloadManager *download_manager,
										const char *tmp_file_name,
										const int percent)
{
	g_signal_emit(download_manager, 
				  signals[DOWNLOAD_PROGRESS],
                  0 /* details */, 
                  tmp_file_name,
                  percent);
}
