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
