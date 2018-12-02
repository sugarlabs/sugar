Using Sugar on Ubuntu
=====================

*Ubuntu is a [Debian](debian.md)-based Linux operating system, with Gnome as its default desktop environment.* -- [wikipedia.org](http://en.wikipedia.org/wiki/Ubuntu_%28operating_system%29)

In relation to Sugar, Ubuntu is a downstream distribution project that can be used to run Sugar.

Ubuntu 18.04 Bionic
-------------------

Sugar 0.112 is in the archive for Ubuntu 18.04 Bionic, and can be installed by typing

    sudo add-apt-repository universe
    sudo apt install sucrose

-   log out,
-   log in with the Sugar desktop selected,
-   press the F3 button to switch to the home view ([issue #769](https://github.com/sugarlabs/sugar/issues/769)).

Known problems

-   Sugar starts in Journal, fixed by [258235c](https://github.com/sugarlabs/sugar/commit/258235c4da3e019ee667b6cd8adf1ede7100a9da) or [Metacity 074af8f](https://github.com/GNOME/metacity/commit/074af8f87ef89b13ff326fb5d04ee424bbfd4ced),
-   My Settings, Network, may hang, requires reboot or forced logout to escape, fixed by (04c63f6)[https://github.com/sugarlabs/sugar/commit/04c63f6dd2b6f10a80376a43c735822f5283bda7].

Using Sugar inside another desktop environment on Ubuntu
--------------------------------------------------------

Sugar is a desktop environment. For developers who use Ubuntu Unity, Gnome or another desktop environment, Sugar can be run inside that environment as a window.

Install the Remote Desktop packages:

    sudo apt install xrdp rdesktop

Create a user for Sugar and set a default desktop environment:

    sudo adduser sugar
    sudo su - sugar -c 'echo sugar >> .xsession'

Start a session:

    rdesktop -g 1200x900 -u sugar -p sugar 0
