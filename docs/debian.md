Using Sugar on Debian
=====================

*Debian is a free operating system (OS) for your computer. An operating system is the set of basic programs and utilities that make your computer run.* -- [debian.org](https://www.debian.org/)

In relation to Sugar, Debian is a downstream distribution project that can be used to run Sugar.

Using Sugar 0.112 on Debian
---------------------------

Sugar 0.112 will be available in Debian *Buster*.

Using Sugar 0.110 on Debian
---------------------------

Sugar 0.110 is available in Debian *Stretch*:

-   install Debian *Stretch* in the usual way, see [debian.org](https://www.debian.org/), and [debian-installer](https://www.debian.org/releases/stretch/debian-installer/),
-   when asked mid-way through install what to include, deselect all,
-   when the install has completed, log in, install Sugar, a display manager, and reboot,

```
sudo apt install sucrose lightdm
exec sudo reboot
```

-   in the graphical login screen, change from the default X session to Sugar,
-   log in as your non-root user, created during install.

Known bugs include;

-   [848841](https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=848841) journal view multiple select does not show actions toolbar,
-   Browse busy cursor may get stuck on.

Pre-built Images
----------------

There are pre-built Debian images for Sugar, and the tools available in Debian make this easy for any integration or deployment team. There's no need for us to duplicate documentation here.

See also [0.112\#Testing](http://wiki.sugarlabs.org/go/0.112#Testing "wikilink") for Sugar [Live Build](http://wiki.sugarlabs.org/go/Live_Build "wikilink"), an image for testing a new release of Sugar, or for certain development tasks.

Packaging
---------

Packaging of Sugar on Debian is done by a team:

-   [pkg-sugar-team project](https://https://salsa.debian.org/pkg-sugar-team),
-   [pkg-sugar-devel mailing list](https://lists.alioth.debian.org/mailman/listinfo/pkg-sugar-devel),
-   [package archive of Jonas Smedegaard](http://debian.jones.dk/pkg/sugar_/),

Sucrose packages are usually updated in the unstable release. These packages migrate to the testing release after a while. You can see the current package versions [here](http://packages.debian.org/search?keywords=sugar&searchon=names&suite=all&section=all).

Interested in developing Sugar software?  Visit our [developer documentation website](http://developer.sugarlabs.org/).

See also [local packaging example](debian-packaging-example.md).

Derivatives
-----------

Derivatives of Debian include:

-   [Ubuntu](ubuntu.md),
-   [Raspbian](raspbian.md) for the Raspberry Pi.

See Also
--------

-   [Sugar page on the Debian Wiki](https://wiki.debian.org/Sugar),
-   the Debian Edu product [Skolelinux](http://wiki.sugarlabs.org/go/Skolelinux).
