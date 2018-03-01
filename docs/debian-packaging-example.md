Debian Local Packaging Example
-------------------------------

An example of local packaging of the `sugar-artwork` module on Debian.  Also applicable to Ubuntu.

*Warning: this is not Debian packaging.*  For more information on Debian, and becoming a Debian Developer, please see [debian.org](https://debian.org).


Add or enable `deb-src` lines in your `/etc/apt/sources.list`.

Install build dependencies;

```
sudo apt update
sudo apt build-dep sugar-artwork
```

Create a directory for this work and change to it;

```
mkdir /tmp/test
cd /tmp/test
```

Clone your repository, and change to it;

```
git clone https://github.com/quozl/sugar-artwork.git
cd sugar-artwork
```

Set the version number by adding a developer suffix to `configure.ac`, using your GitHub username and a release number:

```
AC_INIT([sugar-artwork],[0.112~quozl.0],[],[sugar-artwork])
```

Configure the source code.

```
./autogen.sh
```

Make a local release tarball.

```
make dist
```

As an optional check, compare `sugar-artwork-0.112~quozl.0.tar.xz` with the most recent release `sugar-artwork-0.112.tar.xz` at [download.laptop.org sugar-artwork](http://download.sugarlabs.org/sources/sucrose/glucose/sugar-artwork/?C=M;O=D).  You should see changes consistent with the git commits since the git tag of the release.

Copy the `tar.xz` file into the directory above with a special name expected by the Debian tools, and return to that directory.

```
mv sugar-artwork-0.112~quozl.0.tar.xz ../sugar-artwork_0.112~quozl.0.orig.tar.xz
cd ..
```

Download the latest distribution source package

```
sudo apt source sugar-artwork
```

A set of files will be created;

* `.dsc` describes the source package,
* `.orig.tar.xz` is the original release tarball,
* `.debian.tar.xz` is the delta, or set of changes, for packaging.

These files will be automatically extracted by `apt`.

A directory `sugar-artwork-0.112` will be created.  Below we will use the `debian` subdirectory only.  Familiarise yourself with the directory and subdirectory; they can be used to rebuild the distribution package.

Unpack your local release tarball and copy the `debian` subdirectory into it;

```
tar xf sugar-artwork_0.112~quozl.0.orig.tar.xz
cp -rl sugar-artwork-0.112/debian sugar-artwork-0.112~quozl.0/
cd sugar-artwork-0.112~quozl.0
```

Install the `devscripts` package.  It contains tools `dch` and `debuild` we will use below.

```
sudo apt install devscripts
```

Increment the package version number.

```
dch -b -v 0.112~quozl.0-1 -D bionic new local test version
```

Package version in this form will be _lower than_ the official package.

Optionally confirm the version number has changed by reading the `debian/changelog` file.  Familiarise yourself with the format and previous entries.

Build the package, without signing.

```
debuild -us -uc
```

Result should be a set of files in the directory above.

* a debian source package set;

    * `sugar-artwork_0.112~quozl.0.orig.tar.xz` - your local release tarball, made by `make dist` above,
    * `sugar-artwork_0.112~quozl.0-1.debian.tar.xz` - the debian directory,
    * `sugar-artwork_0.112~quozl.0-1.dsc` - the source package description,

* a debian binary package set, each of which can be installed;

    * `sugar-themes_0.112~quozl.0-1_all.deb` - the artwork, in architecture independent form,
    * `sugar-icon-theme_0.112~quozl.0-1_all.deb` - the icon theme, in architecture independent form,
    * `gtk2-engines-sugar_0.112~quozl.0-1_amd64.deb` - the GTK+ 2 theme engine, in amd64 architecture,
    * `gtk2-engines-sugar-dbgsym_0.112~quozl.0-1_amd64.ddeb` - debug symbols for above, usually not needed.

* build and changes descriptions;

    * `sugar-artwork_0.112~quozl.0-1_amd64.buildinfo`
    * `sugar-artwork_0.112~quozl.0-1_amd64.changes`
    * `sugar-artwork_0.112~quozl.0-1_amd64.build`

Install the three packages needed, and test Sugar.

References:

* [GNU Coding Standards](https://www.gnu.org/prep/standards/)

* [Native Sugar - Setting up a Development Environment](https://github.com/sugarlabs/sugar/blob/master/docs/development-environment.md) has details on how to install build dependencies for all modules.

* [Development Team - Release - Modules - Glucose Base](https://wiki.sugarlabs.org/go/Development_Team/Release#Glucose_.28base.29_modules) is a process used by release manager for making a release.
