#ifndef __SUGAR_DOWNLOAD_H__
#define __SUGAR_DOWNLOAD_H__

#include <glib-object.h>
#include <glib.h>

G_BEGIN_DECLS

typedef struct _SugarDownload SugarDownload;
typedef struct _SugarDownloadClass SugarDownloadClass;

#define SUGAR_TYPE_DOWNLOAD				 (sugar_download_get_type())
#define SUGAR_DOWNLOAD(object)			 (G_TYPE_CHECK_INSTANCE_CAST((object), SUGAR_TYPE_DOWNLOAD, SugarDownload))
#define SUGAR_DOWNLOAD_CLASS(klass) 	 (G_TYPE_CHECK_CLASS_CAST((klass), SUGAR_TYPE_DOWNLOAD, SugarDownloadClass))
#define SUGAR_IS_DOWNLOAD(object)		 (G_TYPE_CHECK_INSTANCE_TYPE((object), SUGAR_TYPE_DOWNLOAD))
#define SUGAR_IS_DOWNLOAD_CLASS(klass) 	 (G_TYPE_CHECK_CLASS_TYPE((klass), SUGAR_TYPE_DOWNLOAD))
#define SUGAR_DOWNLOAD_GET_CLASS(object) (G_TYPE_INSTANCE_GET_CLASS((object), SUGAR_TYPE_DOWNLOAD, SugarDownloadClass))

struct _SugarDownload {
	GObject	base_instance;
	
	gchar	*file_name;
	gchar	*url;
	gchar	*mime_type;
	gint	 percent;
};

struct _SugarDownloadClass {
	GObjectClass base_class;
};

GType sugar_download_get_type(void);

void	sugar_download_set_file_name	(SugarDownload	*download,
										 const gchar	*file_name);
void	sugar_download_set_url			(SugarDownload	*download,
										 const gchar	*url);
void	sugar_download_set_mime_type	(SugarDownload	*download,
										 const gchar	*mime_type);
void	sugar_download_set_percent		(SugarDownload	*download,
										 const gint		 percent);

const gchar *sugar_download_get_file_name	(SugarDownload	*download);
const gchar *sugar_download_get_url			(SugarDownload	*download);
const gchar *sugar_download_get_mime_type	(SugarDownload	*download);
gint		 sugar_download_get_percent		(SugarDownload	*download);

G_END_DECLS

#endif /* __SUGAR_DOWNLOAD_H__ */
