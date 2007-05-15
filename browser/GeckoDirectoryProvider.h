/*
 * Copyright (C) 2007, One Laptop Per Child
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the
 * Free Software Foundation, Inc., 59 Temple Place - Suite 330,
 * Boston, MA 02111-1307, USA.
 */
#ifndef GECKO_DIRECTORY_PROVIDER_H
#define GECKO_DIRECTORY_PROVIDER_H
    
#include <nsIDirectoryService.h>

class GeckoDirectoryProvider : public nsIDirectoryServiceProvider2
{
    public:
        NS_DECL_ISUPPORTS
        NS_DECL_NSIDIRECTORYSERVICEPROVIDER
        NS_DECL_NSIDIRECTORYSERVICEPROVIDER2

        GeckoDirectoryProvider(const char *sugar_path,
                               const char *profile_path);
        virtual ~GeckoDirectoryProvider();

    private:
        char *mComponentPath;
        char *mCompregPath;
};

#endif /* GECKO_DIRECTORY_PROVIDER_H */
