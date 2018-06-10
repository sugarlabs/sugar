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
sudo dnf install python2-decorator webkitgtk3
```

Then restart your computer.  At the *Sign in* select the *Sugar*
desktop.

See also [Fedora](docs/fedora.md).

Building
--------

Sugar follows the [GNU Coding
Standards](https://www.gnu.org/prep/standards/).

Install all dependencies, especially `sugar-artwork`, `sugar-datastore`,
and `sugar-toolkit-gtk3`.

Clone the repository, run `autogen.sh`, then `make` and `make
install`.

See also [Setup a development
environment](docs/development-environment.md).

[![alt text][1.1]][1]
[![alt text][2.1]][2]
[![alt text][3.1]][3]
[![alt text][4.1]][4]


<!-- icons with padding -->

[1.1]: https://svgshare.com/i/708.svg (twitter icon with padding)
[2.1]: https://svgshare.com/i/70R.svg (instagram icon with padding)
[3.1]: https://svgshare.com/i/6yt.svg (facebook icon with padding)
[4.1]: https://svgshare.com/i/70a.svg (youtube icon with padding)


<!-- update these accordingly -->

[1]: https://twitter.com/sugar_labs
[2]: https://www.instagram.com/sugarlabsforall/
[3]: https://www.facebook.com/SugarLabs-187845102582/timeline/
[4]: https://www.youtube.com/channel/UCfsR9AEb7HuPRAc14jfiI6g/featured