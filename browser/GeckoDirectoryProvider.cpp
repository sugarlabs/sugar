#include "GeckoDirectoryProvider.h"

#include <nsCOMPtr.h>
#include <nsIIOService.h>
#include <nsNetUtil.h>
#include <nsArrayEnumerator.h>
#include <nsILocalFile.h>
#include <nsDirectoryServiceDefs.h>
#include <nsIToolkitChromeRegistry.h>
#include <nsIDirectoryService.h>
#include <nsCOMArray.h>

#include <glib.h>

NS_IMPL_ISUPPORTS2 (GeckoDirectoryProvider,
                    nsIDirectoryServiceProvider,
                    nsIDirectoryServiceProvider2)

GeckoDirectoryProvider::GeckoDirectoryProvider(const char *sugar_path,
                                               const char *profile_path)
{
    mComponentPath = g_build_filename
            (sugar_path, "mozilla", "components", NULL);
    mCompregPath = g_build_filename
            (profile_path, "compreg.dat", NULL);
}

GeckoDirectoryProvider::~GeckoDirectoryProvider()
{
    if(mComponentPath)
        g_free(mComponentPath);
    if(mCompregPath)
        g_free(mCompregPath);
}

/* nsIFile getFile (in string prop, out PRBool persistent); */
NS_IMETHODIMP
GeckoDirectoryProvider::GetFile (const char *prop,
                                 PRBool *persistent,
                                 nsIFile **_retval)
{
    nsresult rv = NS_ERROR_FAILURE;
    nsCOMPtr<nsILocalFile> file;

    if (!strcmp(prop, NS_XPCOM_COMPONENT_REGISTRY_FILE)) {
        rv = NS_NewNativeLocalFile(nsDependentCString(mCompregPath),
                                   PR_TRUE,
                                   getter_AddRefs(file));
    }

    if (NS_SUCCEEDED(rv) && file) {
        NS_ADDREF(*_retval = file);
        return NS_OK;
    }

    return NS_ERROR_FAILURE;
}

/* nsISimpleEnumerator getFiles (in string aProperty); */
NS_IMETHODIMP
GeckoDirectoryProvider::GetFiles (const char *aProperty, nsISimpleEnumerator **aResult)
{
    nsresult rv = NS_ERROR_FAILURE;

    if (!strcmp(aProperty, NS_XPCOM_COMPONENT_DIR_LIST)) {
        if (mComponentPath) {
            nsCOMPtr<nsILocalFile> componentDir;
            rv = NS_NewNativeLocalFile(nsDependentCString(mComponentPath),
                                       PR_TRUE,
                                       getter_AddRefs(componentDir));
            NS_ENSURE_SUCCESS (rv, rv);

            nsCOMArray<nsIFile> array;

            rv = array.AppendObject (componentDir);
            NS_ENSURE_SUCCESS (rv, rv);

            rv = NS_NewArrayEnumerator (aResult, array);
            NS_ENSURE_SUCCESS (rv, rv);

            rv = NS_SUCCESS_AGGREGATE_RESULT;
        }
    }
    
    return rv;
}
