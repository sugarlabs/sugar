#ifndef __SUGAR_DOWNLOAD_MANAGER_H__
#define __SUGAR_DOWNLOAD_MANAGER_H__

#include <glib-object.h>
#include <glib.h>

G_BEGIN_DECLS

typedef struct _SugarDownloadManager SugarDownloadManager;
typedef struct _SugarDownloadManagerClass SugarDownloadManagerClass;

#define SUGAR_TYPE_DOWNLOAD_MANAGER				 (sugar_download_manager_get_type())
#define SUGAR_DOWNLOAD_MANAGER(object)			 (G_TYPE_CHECK_INSTANCE_CAST((object), SUGAR_TYPE_DOWNLOAD_MANAGER, SugarDownloadManager))
#define SUGAR_DOWNLOAD_MANAGER_CLASS(klass) 	 (G_TYPE_CHECK_CLASS_CAST((klass), SUGAR_TYPE_DOWNLOAD_MANAGER, SugarDownloadManagerClass))
#define SUGAR_IS_DOWNLOAD_MANAGER(object)		 (G_TYPE_CHECK_INSTANCE_TYPE((object), SUGAR_TYPE_DOWNLOAD_MANAGER))
#define SUGAR_IS_DOWNLOAD_MANAGER_CLASS(klass) 	 (G_TYPE_CHECK_CLASS_TYPE((klass), SUGAR_TYPE_DOWNLOAD_MANAGER))
#define SUGAR_DOWNLOAD_MANAGER_GET_CLASS(object) (G_TYPE_INSTANCE_GET_CLASS((object), SUGAR_TYPE_DOWNLOAD_MANAGER, SugarDownloadManagerClass))

struct _SugarDownloadManager {
	GObject base_instance;
};

struct _SugarDownloadManagerClass {
	GObjectClass base_class;
	
	void (* handle_content) (char *url, char *tmp_file_name);
	
};

GType sugar_download_manager_get_type(void);

SugarDownloadManager *sugar_get_download_manager(void);

void sugar_download_manager_download_started(
	SugarDownloadManager *download_manager,
	const char *url,
	const char *mime_type,
	const char *tmp_file_name);

void sugar_download_manager_download_completed(
	SugarDownloadManager *download_manager,
	const char *tmp_file_name);
	
void sugar_download_manager_download_cancelled(
	SugarDownloadManager *download_manager,
	const char *tmp_file_name);

void sugar_download_manager_update_progress(
	SugarDownloadManager *download_manager,
	const char *tmp_file_name,
	const int percent);

G_END_DECLS

#endif
