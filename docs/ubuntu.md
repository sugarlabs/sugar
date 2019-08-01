Using Sugar on Ubuntu
=====================

*Ubuntu is a [Debian](debian.md)-based Linux operating system, with Gnome as its default desktop environment.* -- [wikipedia.org](http://en.wikipedia.org/wiki/Ubuntu_%28operating_system%29)

In relation to Sugar, Ubuntu is a downstream distribution project that can be used to run Sugar.

Ubuntu 18.04 (Bionic Beaver) and 18.10 (Cosmic Cuttlefish)
-------------------

Sugar 0.112 is in the universe repository of Ubuntu 18.04, (Bionic Beaver) as well as 18.10 (Cosmic Cuttlefish), and can be installed by executing the following commands:


    sudo add-apt-repository universe
    sudo apt-get update
    sudo apt install sucrose

-   log out,
-   log in with the Sugar desktop selected,
-   press the F3 key to switch to the home view, see below.

Known problems

-   Sugar starts in Journal, fixed by [258235c](https://github.com/sugarlabs/sugar/commit/258235c4da3e019ee667b6cd8adf1ede7100a9da) or [Metacity 074af8f](https://github.com/GNOME/metacity/commit/074af8f87ef89b13ff326fb5d04ee424bbfd4ced),
-   My Settings, Network, may hang, requires reboot or forced logout to escape, fixed by [04c63f6](https://github.com/sugarlabs/sugar/commit/04c63f6dd2b6f10a80376a43c735822f5283bda7).
