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

Installing on Debian or Ubuntu
------------------------------

```
sudo apt install sucrose
```

Then log out, and log in with the Sugar desktop selected.

See also [Debian](docs/debian.md) or [Ubuntu](docs/ubuntu.md).

Installing on Fedora
--------------------

```
sudo dnf groupinstall sugar-desktop
```

Then restart your computer.  At the *Sign in* select the *Sugar*
desktop.

See also [Fedora](docs/fedora.md).

Building
--------

Sugar follows the [GNU Coding
Standards](https://www.gnu.org/prep/standards/).

Install all dependencies, especially [`sugar-artwork`](https://github.com/sugarlabs/sugar-artwork), `sugar-datastore` (automatically installed) ,
and [`sugar-toolkit-gtk3`](https://github.com/sugarlabs/sugar-toolkit-gtk3).

Clone the repository, run `autogen.sh`, then `make` and `make
install`.

See also [Setup a development
environment](docs/development-environment.md).
