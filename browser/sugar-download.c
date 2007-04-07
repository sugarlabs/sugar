#include "sugar-download.h"

static void	sugar_download_finalize (GObject *object);

G_DEFINE_TYPE (SugarDownload, sugar_download, G_TYPE_OBJECT)

static void
sugar_download_init (SugarDownload *download)
{
	download->file_name = NULL;
	download->url = NULL;
	download->mime_type = NULL;
	download->percent = 0;
}

static void
sugar_download_class_init (SugarDownloadClass *download_class)
{
	GObjectClass *gobject_class = G_OBJECT_CLASS (download_class);

	gobject_class->finalize = sugar_download_finalize;
}

void
sugar_download_set_file_name (SugarDownload *download, const gchar *file_name)
{
	gchar *new_file_name;
  
	g_return_if_fail (SUGAR_IS_DOWNLOAD (download));

	new_file_name = g_strdup (file_name);
	g_free (download->file_name);
	download->file_name = new_file_name;
}

void
sugar_download_set_url (SugarDownload *download, const gchar *url)
{
	gchar *new_url;
  
	g_return_if_fail (SUGAR_IS_DOWNLOAD (download));

	new_url = g_strdup (url);
	g_free (download->url);
	download->url = new_url;
}

void
sugar_download_set_mime_type (SugarDownload *download, const gchar *mime_type)
{
	gchar *new_mime_type;
  
	g_return_if_fail (SUGAR_IS_DOWNLOAD (download));

	new_mime_type = g_strdup (mime_type);
	g_free (download->mime_type);
	download->mime_type = new_mime_type;
}

void
sugar_download_set_percent (SugarDownload *download, const gint percent)
{
	g_return_if_fail (SUGAR_IS_DOWNLOAD (download));

	download->percent = percent;
}

const gchar *
sugar_download_get_file_name (SugarDownload *download)
{
	g_return_val_if_fail (SUGAR_IS_DOWNLOAD (download), NULL);
  
	return download->file_name;
}

const gchar *
sugar_download_get_url (SugarDownload *download)
{
	g_return_val_if_fail (SUGAR_IS_DOWNLOAD (download), NULL);
  
	return download->url;
}

const gchar *
sugar_download_get_mime_type (SugarDownload *download)
{
	g_return_val_if_fail (SUGAR_IS_DOWNLOAD (download), NULL);
  
	return download->mime_type;
}

gint
sugar_download_get_percent (SugarDownload *download)
{
	g_return_val_if_fail (SUGAR_IS_DOWNLOAD (download), -1);
  
	return download->percent;
}

static void
sugar_download_finalize (GObject *object)
{
	SugarDownload *download = SUGAR_DOWNLOAD (object);
	
	g_free (download->file_name);
	g_free (download->url);
	g_free (download->mime_type);
}
