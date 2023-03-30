Using Sugar on Debian
=====================

*Debian is a free operating system (OS) for your computer. An operating system is the set of basic programs and utilities that make your computer run.* -- [debian.org](https://www.debian.org/)

In relation to Sugar, Debian is a downstream distribution project that can be used to run Sugar.

Using Sugar on Debian
---------------------

Sugar is available in Debian:

-   install Debian in the usual way, see [debian.org](https://www.debian.org/), and [debian-installer](https://www.debian.org/releases/stretch/debian-installer/),
-   when the install has completed, log in, install Sugar, a display manager, and reboot,

```
sudo apt install sucrose lightdm
exec sudo reboot
```

-   in the graphical login screen, [change from the default X session to Sugar](https://github.com/sugarlabs/sugar-docs/blob/master/src/sugar-logging-in.md),
-   log in as the non-root user, which you will have created during install.

Known bugs include;

-   Sugar starts in Journal, workaround is to press F3 button, fixed by [Metacity 074af8f](https://github.com/GNOME/metacity/commit/074af8f87ef89b13ff326fb5d04ee424bbfd4ced),

Update activities using My Settings, Software Update.  Updated activities as at 2020-03-07 are Calculate, Chat, Image Viewer, Jukebox, Log, Pippy, Terminal, and Write.

Packaging
---------

Packaging of Sugar on Debian is done by a team:

-   [pkg-sugar-team project](https://salsa.debian.org/pkg-sugar-team),
-   [pkg-sugar-devel mailing list](https://lists.alioth.debian.org/mailman/listinfo/pkg-sugar-devel),
-   [pkg-sugar git repositories](https://salsa.debian.org/pkg-sugar-team/sugar)
-   [package archive of Jonas Smedegaard](http://debian.jones.dk/pkg/sugar_/),

Sucrose packages are usually updated in the unstable release. These packages migrate to the testing release after a while. You can see the current package versions [here](http://packages.debian.org/search?keywords=sugar&searchon=names&suite=all&section=all).

Interested in developing Sugar software?  Visit our [developer documentation website](http://developer.sugarlabs.org/).

See also [local packaging example](debian-packaging-example.md).

Derivatives
-----------

Derivatives of Debian include:

-   [Ubuntu](ubuntu.md),
-   [Raspberry Pi OS](rpi.md) .

See Also
--------

-   [Sugar page on the Debian Wiki](https://wiki.debian.org/Sugar),
-   the Debian Edu product [Skolelinux](http://wiki.sugarlabs.org/go/Skolelinux).
