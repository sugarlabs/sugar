How to use Sugar on a Stick on a Raspberry Pi;

-   on another computer, visit [arm.fedoraproject.org](https://arm.fedoraproject.org/) and download the Sugar on a Stick image,
-   write the image to a microSD card, using software such as Fedora Media Writer, Etcher.io, or the [Fedora Raspberry Pi Documentation](https://fedoraproject.org/wiki/Architectures/ARM/Raspberry_Pi),
-   insert the microSD card into the Raspberry Pi, and turn it on,
-   answer the post-install questions; time zone, root password, and add a user,
-   at the login prompt log in with the added user, and Sugar will start.

Security Warning
----------------

Remote access is pre-enabled through SSH, for both root and any user accounts. Risk can be reduced by choosing strong passwords in the post-install setup questions. Can be fixed after install with Terminal command;

`sudo chkconfig sshd off`

Security Updates
----------------

Security updates can be downloaded with Terminal command;

`sudo dnf update`

Fedora Media Writer
-------------------

How to write an image to microSD card using [Fedora Media Writer](https://github.com/MartinBriza/MediaWriter/releases) (FMW), which is available for Mac OS X, Microsoft Windows, Fedora Linux, and Ubuntu Linux as a flatpak, or from source.

-   download the raw.xz file
-   select and extract, result is a raw file
-   start Fedora Media Writer
-   select "Custom"
-   select the raw file
-   Insert microSD in Mini Card Reader and insert in USB port
-   Choose rpi3 from drop-down in Fedora Media Writer
-   Write microSD
