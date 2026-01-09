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
sudo dnf group install sugar-desktop
```

Then restart your computer.  At the *Sign in* select the *Sugar*
desktop.

See also [Fedora](docs/fedora.md).

Building
--------

Sugar follows the [GNU Coding
Standards](https://www.gnu.org/prep/standards/).

Install all dependencies, especially [`sugar-artwork`](https://github.com/sugarlabs/sugar-artwork), [`sugar-datastore`](https://github.com/sugarlabs/sugar-datastore),
and [`sugar-toolkit-gtk3`](https://github.com/sugarlabs/sugar-toolkit-gtk3).

Clone the repository, run `autogen.sh`, then `make` and `make
install`.

See also [Setup a development
environment](docs/development-environment.md).


## Running Sugar Shell on WSL / Ubuntu (Important Note)

Developers attempting to run Sugar Shell (`jarabe`) from source on **Ubuntu under WSL (Windows Subsystem for Linux)** may encounter a situation where the process exits silently without error output or a visible UI.

### Observed behavior
When running:
```bash
dbus-run-session -- python3 ./src/jarabe/main.py

on Ubuntu 20.04 (WSL2):
No traceback is shown
No jarabe process remains running
No Sugar UI window appears
This can give the impression that the setup is broken, even when all build steps completed successfully.

Explanation

Sugar Shell assumes a full Linux desktop environment with runtime data, session services, and system integration that are not fully available on WSL. While DBus can be started manually, other runtime expectations are unmet, causing Sugar Shell to exit quietly.
This is a platform limitation rather than a user setup error.
Recommended approach for contributors on Windows

Contributors working on Windows are encouraged to:
Focus on Sugar Activities
Contribute to sugar-toolkit-gtk3
Work on documentation, tests, or CI improvements

These components run reliably on WSL and do not require the full Sugar desktop runtime.
To run the Sugar Shell itself, a full Linux environment (for example, a virtual machine or native Linux installation) is recommended.

Why this note exists
This clarification is intended to save new contributors time and avoid confusion during initial setup.
