Using Sugar on Fedora
=====================

*Fedora is an operating system based on the Linux kernel, developed by the community-supported Fedora Project and sponsored by Red Hat.* -- [wikipedia.org](https://en.wikipedia.org/wiki/Fedora_(operating_system))

In relation to Sugar, Fedora is a downstream distribution project that can be used to run Sugar.

Using Sugar as a Desktop Environment
------------------------------------

Install Fedora. Then, in a Terminal, type:

    sudo dnf groupinstall sugar-desktop

Then restart your computer. At the *Sign in* select the *Sugar* desktop.

Using Sugar with another Desktop Environment
--------------------------------------------

Select the *GNOME on Xorg* or *GNOME Classic* desktop, then in a Terminal, type:

    sudo dnf groupinstall sugar-desktop
    sudo dnf install sugar-runner
    sugar-runner

Sugar will start. *Logout* from Sugar to return to the desktop environment you were previously using.

Sugar is also available from *Activities* search in GNOME.

Using Sugar from a USB drive - Sugar on a Stick
-----------------------------------------------

Sugar on a Stick (SoaS) is a Fedora spin, made from Fedora and Sugar together.

SoaS starts from a USB drive ("stick"), and can be installed with the [Fedora installation process](http://docs.fedoraproject.org/en-US/Fedora/20/html/Installation_Guide/). Or, the Fedora installer may be started from the Sugar Terminal activity, with the command , or using a [tutorial](http://wiki.sugarlabs.org/go/Tutorials/Installation/Install_with_liveinst "wikilink").
