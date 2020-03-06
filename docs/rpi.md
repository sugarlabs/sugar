Raspberry Pi are a series of small, low cost, low power computers.

Sugar can be run on a Raspberry Pi. You will need a display, keyboard and mouse.

Raspbian Buster
---------------

Sugar 0.112 can be loaded using [Instructions for Debian Buster](debian.md),

Sugar 0.116 can be loaded using our package archive;

- add to `/etc/apt/sources.list` file this line;

```
deb [arch=armhf trusted=yes] http://people.sugarlabs.org/~quozl/rb buster main
```

- update the package lists;

```
sudo apt update
```

- install Sugar 0.116;

```
sudo apt install sucrose
```

- install sample activities;

```
sudo apt install sugar-{abacus,browse,calculate,chart,chat,clock,\
  develop,finance,findwords,fototoon,fractionbounce,gears,\
  imageviewer,implode,jukebox,letters,log,maze,measure,memorize,\
  moon,music-keyboard,paint,physics,pippy,poll,portfolio,read,\
  record,speak,stopwatch,story,terminal,words,write}-activity
```

- choose Sugar for restart by adding a file, like this;

```
echo sugar > .xsession
```

- restart the Raspberry pi;

```
sudo reboot
```

Sugar on a Stick
----------------

As of August 2017, the best to use was Sugar on a Stick, as it had many activities and regular security updates. See [Sugar on a Stick](rpi-soas.md) for how to download and install it. Sugar on a Stick is a spin of Fedora.

Other methods are;

-   using [Fedora](fedora.md),
-   using [Debian](debian.md),
-   using [Ubuntu](ubuntu.md).

Developers may focus on either Fedora or Debian when [setting up a development environment](development-environment.md) for Sugar on Raspberry Pi, because Sugar development on generic computers is focused on those operating systems.
