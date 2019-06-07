Setup a development environment
===============================

Sugar is made of several modules and depends on many other libraries.

There are several ways to set up a Sugar environment for doing Sugar development, choose one at a time only;

-   for testing or changing Sugar or a Sugar activity, install a [live build](#sugar-live-build), which has all dependencies and source code included, but is nearly 1GB of downloads;

-   for writing or changing a Sugar activity, install a [packaged Sugar environment](#packaged-sugar), which will install dependencies automatically; or,

-   for packaging Sugar, downstream developers create a [native Sugar build](#native-sugar) and install the necessary dependencies by hand, but Sugar is difficult to remove.

Sugar Live Build
----------------

Sugar Live Build is a complete bootable image containing Sugar, the toolkits, and the demonstration activities;

-   can be booted from hard drive, flash drive, and optical media, automatically starting Sugar without persistence,

-   can be installed as a virtual machine, with persistence and password protection,

-   contains all build dependencies, configured source trees (git clones in `/usr/src`), and binaries (`make install`) for Sugar modules and the demonstration activity set.

See [downloads](http://people.sugarlabs.org/~quozl/sugar-live-build/) for the ISO9660 image file.

Once installed, Sugar Live Build can be used to make changes to Sugar, the toolkits, the demonstration activities, or to write new activities.

-   changes to Sugar or the toolkits can be done by editing files in the module source trees in `/usr/src`, followed by `sudo make install` for each changed module.

-   changes to demonstration activities can be done in the activity source trees in `/usr/src/sugar-activities`, and are immediately effective; just start a new instance of the activity in Sugar.

-   writing new activities can be done in the `~/Activities/` directory, and the new activity can be started using `sugar-activity` command in Terminal, or by restarting Sugar so that the new `activity/activity.info` file is read to regenerate the [Home View](https://help.sugarlabs.org/en/home_view.html).

See [sugar-live-build](https://github.com/sugarlabs/sugar-live-build) on GitHub for configuration files to make your own Sugar Live Build using the Debian Live Build software.

Packaged Sugar
--------------

For development of activities without making changes to Sugar desktop.

For Fedora users, see [Using Sugar on Fedora](fedora.md). Once Sugar is installed, development of activities can begin.

For Debian users, see also [Using Sugar on Debian](debian.md), or see how to install `sucrose` below.

For Ubuntu users, see also [Using Sugar on Ubuntu](ubuntu.md), or see how to install `sucrose` below.

Install the `sucrose` package;

    sudo apt install sucrose

Log out, then log in with the Sugar desktop selected.

Once Sugar is installed, development of activities can begin.

Native Sugar
------------

For experts.

Clone each of the module repositories;

    for module in sugar{-datastore,-artwork,-toolkit,-toolkit-gtk3,}; do
        git clone https://github.com/sugarlabs/$module.git
    done

Install the build dependencies. There are many, and their package
names vary by distribution. A first start is in the Debian or Fedora
packaging files. From 0.113, add Six.

On Debian or Ubuntu, ensure `deb-src` lines are present and enabled in `/etc/apt/sources.list`, and then;

    sudo apt update
    for module in sugar{-datastore,-artwork,-toolkit,-toolkit-gtk3,}; do
        sudo apt build-dep $module
    done
    sudo apt install python{,3}-six python-empy

On Fedora, use [dnf builddep](http://dnf-plugins-core.readthedocs.io/en/latest/builddep.html), like this;

    for module in sugar{-datastore,-artwork,-toolkit,-toolkit-gtk3,}; do
        sudo dnf builddep $module
    done
    sudo dnf install python{2,3}-six python2-empy

Autogen, configure, make, and install each module for Python 2;

    for module in sugar{-datastore,-artwork,-toolkit,-toolkit-gtk3,}; do
        cd $module
        ./autogen.sh
        make
        sudo make install
        cd ..
    done

When support is required for both versions of Python, build the `sugar-toolkit-gtk3` module again with the `--with-python3` option;

    for module in sugar-toolkit-gtk3; do
        cd $module
        ./autogen.sh --with-python3
        make
        sudo make install
        cd ..
    done

On Debian or Ubuntu, try `python3 -c 'import sugar3'` if fails move the `sugar3` directory from `/usr/local/lib/python3.6/site-packages/` to `/usr/local/lib/python3.6/dist-packages/`.

On Fedora, add `/usr/local/lib/python2.7/site-packages/` to `sys.path` for any Python 2 programs, especially `/usr/local/bin/sugar`;

    export PYTHONPATH=/usr/local/lib/python2.7/site-packages
    export GI_TYPELIB_PATH=/usr/local/lib/girepository-1.0
    export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

Install the run-time dependencies. There are many, and their package
names vary by distribution. A first start is in the Debian or Fedora
packaging files.

On Debian or Ubuntu, install the Sugar packages;

    sudo apt install sucrose

On Fedora, use `dnf deplist` and filter by architecture;

    for module in sugar{-datastore,-artwork,-toolkit,-toolkit-gtk3,}; do
        echo
        echo $module
        sudo dnf deplist $module | \
            awk '/provider:/ {print $2}' | \
            grep -v i686 | \
            sort -u | sudo xargs dnf -y install
    done

Add the PolicyKit files to the system-wide directory;

    sudo ln -sf /usr/local/share/polkit-1/actions/org.sugar.* \
        /usr/share/polkit-1/actions/

Sugar is now installed in `/usr/local`.  Remove any Sugar or Toolkit packages you installed from Fedora or Debian, otherwise then you start Sugar the packaged files in `/usr/` will be run.

Clone the Browse and Terminal activities;

    mkdir -p ~/Activities
    cd ~/Activities
    git clone https://github.com/sugarlabs/browse-activity.git Browse.activity
    git clone https://github.com/sugarlabs/terminal-activity.git Terminal.activity

Log out and log in again with the Sugar desktop selected, or use the remote desktop feature described earlier on this page.

After making changes in a Sugar module, repeat the `sudo make install` step, and log in again.


Change Debugging Level
--------------------

You can enable debugging in Sugar by uncommenting the line
```shell
#export SUGAR_LOGGER_LEVEL=debug
```
present in  `~/.sugar/default/debug`
The debug file also allows the enabling of debugging for other parts of the stack, such as collaboration.
