#include "sugar-marshal.h"
#include "sugar-download.h"
#include "sugar-download-manager.h"

enum {
  DOWNLOAD_STARTED,
  DOWNLOAD_COMPLETED,
  DOWNLOAD_CANCELLED,
  DOWNLOAD_PROGRESS,
  LAST_SIGNAL
};
static guint signals[LAST_SIGNAL] = { 0 };

static void	sugar_download_manager_finalize (GObject *object);
static void sugar_download_remove_download (gpointer key, gpointer value, gpointer user_data);

G_DEFINE_TYPE (SugarDownloadManager, sugar_download_manager, G_TYPE_OBJECT)

SugarDownloadManager *DownloadManager = NULL;

static void
sugar_download_manager_init (SugarDownloadManager *download_manager)
{
	download_manager->downloads = g_hash_table_new (g_str_hash, g_str_equal);
}

static void
sugar_download_manager_class_init (SugarDownloadManagerClass *download_manager_class)
{
	GObjectClass *gobject_class = G_OBJECT_CLASS (download_manager_class);

	gobject_class->finalize = sugar_download_manager_finalize;
  
	signals[DOWNLOAD_STARTED] =
		g_signal_new ("download-started",
					  G_OBJECT_CLASS_TYPE (download_manager_class),
		  			  G_SIGNAL_RUN_LAST,
		  			  G_STRUCT_OFFSET (SugarDownloadManagerClass, handle_content),
					  NULL, NULL,
					  sugar_marshal_VOID__OBJECT,
					  G_TYPE_NONE, 1,
					  G_TYPE_OBJECT);
					  
	signals[DOWNLOAD_COMPLETED] =
		g_signal_new ("download-completed",
					  G_OBJECT_CLASS_TYPE (download_manager_class),
		  			  G_SIGNAL_RUN_LAST,
		  			  G_STRUCT_OFFSET (SugarDownloadManagerClass, handle_content),
					  NULL, NULL,
					  sugar_marshal_VOID__OBJECT,
					  G_TYPE_NONE, 1,
					  G_TYPE_OBJECT);
					  
	signals[DOWNLOAD_CANCELLED] =
		g_signal_new ("download-cancelled",
					  G_OBJECT_CLASS_TYPE (download_manager_class),
		  			  G_SIGNAL_RUN_LAST,
		  			  G_STRUCT_OFFSET (SugarDownloadManagerClass, handle_content),
					  NULL, NULL,
					  sugar_marshal_VOID__OBJECT,
					  G_TYPE_NONE, 1,
					  G_TYPE_OBJECT);
					  
	signals[DOWNLOAD_PROGRESS] =
		g_signal_new ("download-progress",
					  G_OBJECT_CLASS_TYPE (download_manager_class),
		  			  G_SIGNAL_RUN_LAST,
		  			  G_STRUCT_OFFSET (SugarDownloadManagerClass, handle_content),
					  NULL, NULL,
					  sugar_marshal_VOID__OBJECT,
					  G_TYPE_NONE, 1,
					  G_TYPE_OBJECT);
}

static void
sugar_download_manager_finalize (GObject *object)
{
	SugarDownloadManager *download_manager = SUGAR_DOWNLOAD_MANAGER (object);
	g_hash_table_foreach (download_manager->downloads, sugar_download_remove_download, NULL);
	g_hash_table_destroy (download_manager->downloads);
}

static void
sugar_download_remove_download (gpointer key, gpointer value, gpointer user_data)
{
  g_free (value);
}

SugarDownloadManager *
sugar_get_download_manager ()
{  
	if (DownloadManager == NULL)
		DownloadManager = g_object_new (SUGAR_TYPE_DOWNLOAD_MANAGER, NULL);
 	
	return DownloadManager;
}

void
sugar_download_manager_download_started (SugarDownloadManager *download_manager,
										 const char *url,
										 const char *mime_type,
										 const char *file_name)
{
	SugarDownload *download = (SugarDownload *) g_hash_table_lookup (
			download_manager->downloads,
			file_name);

	g_return_if_fail (download == NULL);

	download = g_object_new (SUGAR_TYPE_DOWNLOAD, NULL);
	sugar_download_set_url (download, url);
	sugar_download_set_mime_type (download, mime_type);
	sugar_download_set_file_name (download, file_name);
	
	g_hash_table_insert (download_manager->downloads,
						 (gpointer)file_name,
						 download);

	g_signal_emit (download_manager, signals[DOWNLOAD_STARTED], 0, download);
}

void
sugar_download_manager_download_completed (SugarDownloadManager *download_manager,
										   const char *file_name)
{
	SugarDownload *download = (SugarDownload *) g_hash_table_lookup (
			download_manager->downloads,
			file_name);

	g_return_if_fail (download);
	
	g_signal_emit (download_manager, signals[DOWNLOAD_COMPLETED], 0, download);
	
	g_hash_table_remove (download_manager->downloads, file_name);
}

void sugar_download_manager_download_cancelled (SugarDownloadManager *download_manager,
												const char *file_name)
{
	SugarDownload *download = (SugarDownload *) g_hash_table_lookup (
			download_manager->downloads,
			file_name);

	g_return_if_fail (download);
	
	g_signal_emit (download_manager, signals[DOWNLOAD_CANCELLED], 0, download);

	g_hash_table_remove (download_manager->downloads, file_name);
}

void
sugar_download_manager_update_progress (SugarDownloadManager *download_manager,
										const char *file_name,
										const int percent)
{
	SugarDownload *download = (SugarDownload *) g_hash_table_lookup (
			download_manager->downloads,
			file_name);

	g_return_if_fail (download);
	
	sugar_download_set_percent (download, percent);

	g_signal_emit (download_manager, signals [DOWNLOAD_PROGRESS], 0, download);
}
