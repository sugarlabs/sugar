Sugar
=====

Sugar is the desktop environment component of a worldwide effort to
provide every child with an equal opportunity for a quality
education. Available in more than twenty-five languages, Sugar
Activities are used every school day by children in more than forty
countries.

Originally developed for the One Laptop per Child XO-1 netbook, Sugar
can run on most computers.

Sugar is free/libre and open-source software.

https://www.sugarlabs.org/

https://wiki.sugarlabs.org/

Installing on Debian or Ubuntu
------------------------------

```
sudo apt install sucrose
```

Then log out, and log in with the Sugar desktop selected.

See also [Debian](http://wiki.sugarlabs.org/go/Debian) and
[Ubuntu](http://wiki.sugarlabs.org/go/Ubuntu) on the Wiki.

Installing on Fedora
--------------------

```
sudo dnf groupinstall sugar-desktop
sudo dnf install python2-decorator webkitgtk3
```

Then restart your computer.  At the *Sign in* select the *Sugar*
desktop.

See also [Fedora](http://wiki.sugarlabs.org/go/Fedora) on the Wiki.

Building
--------

Sugar follows the [GNU Coding
Standards](https://www.gnu.org/prep/standards/).

Install all dependencies, especially sugar-artwork, sugar-datastore,
and sugar-toolkit-gtk3.

Clone the repository, run `autogen.sh`, then `make` and `make
install`.

Hacking
-------

For hacking you can use the
[sugar-build](https://github.com/sugarlabs/sugar-build) tool.

Sugar is made of several modules and depends on libraries with
different names in GNU/Linux distributions.  To make it easier for
developers to build from sources, we developed a set of scripts that
automates builds and other common development tasks.

See also [Setup a development
environment](https://developer.sugarlabs.org/dev-environment.md.html)

