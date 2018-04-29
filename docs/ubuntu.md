Using Sugar on Ubuntu
=====================

*Ubuntu is a [Debian](debian.md)-based Linux operating system, with Gnome as its default desktop environment.* -- [wikipedia.org](http://en.wikipedia.org/wiki/Ubuntu_%28operating_system%29)

In relation to Sugar, Ubuntu is a downstream distribution project that can be used to run Sugar.

Ubuntu 18.04 Bionic
-------------------

Sugar 0.112 is in the archive for Ubuntu 18.04 Bionic, and can be installed by typing

    sudo apt install sucrose

-   log out,
-   log in with the Sugar desktop selected,
-   press the F3 button to switch to the home view ([issue #769](https://github.com/sugarlabs/sugar/issues/769)).


Ubuntu 17.10 Artful
-------------------

Sugar 0.110 is in the archive for Ubuntu 17.10 Artful, and can be installed by typing

    sudo apt install sucrose gir1.2-webkit-3.0

-   log out,
-   log in with the Sugar desktop selected.

Installing the package `gir1.2-webkit-3.0` is a workaround for [Debian bug \#877812](https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=877812), which affects only Ubuntu 17.10.

Using Sugar inside another desktop environment on Ubuntu
--------------------------------------------------------

Sugar is a desktop environment. For developers who use Ubuntu Unity, Gnome or another desktop environment, Sugar can be run inside that environment as a window.

Install the Remote Desktop packages:

    sudo apt install xrdp rdesktop

Create a user for Sugar and set a default desktop environment:

    sudo adduser sugar
    sudo su - sugar -c 'echo sugar >> .xsession'

Start a session:

    rdesktop -g 1200x900 -u sugar -p sugar 0

Ubuntu 17.04 Zesty
------------------

Sugar 0.110 is in the archive for Ubuntu 17.04 Zesty, and can be installed by typing

    sudo apt install sucrose

-   log out,
-   log in with the Sugar desktop selected.

Ubuntu 16.04 Xenial LTS
-----------------------

Sugar 0.106 is in the archive for Ubuntu 16.04 Xenial, and can be installed by typing

    sudo apt install sucrose

Sugar 0.112 can be installed by careful addition of the Ubuntu 18.04 Bionic packages; temporarily change sources.list, update, and install the Sugar packages again, then restore sources.list.

Organisations that require Ubuntu 16.04 support for Sugar may consider getting involved in the Ubuntu [Stable Release Updates](https://wiki.ubuntu.com/StableReleaseUpdates) process.
