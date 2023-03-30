Using Sugar on Ubuntu
=====================

*Ubuntu is a [Debian](debian.md)-based Linux operating system, with Gnome as its default desktop environment.* -- [wikipedia.org](http://en.wikipedia.org/wiki/Ubuntu_%28operating_system%29)

In relation to Sugar, Ubuntu is a downstream distribution project that can be used to run Sugar.

Ubuntu 22.04 (Jammy Jellyfish)
-------------------

Sugar 0.118 can be installed with the following commands:

    sudo apt update
    sudo apt install sucrose

-   log out,
-   [log in with the Sugar desktop selected](https://github.com/sugarlabs/sugar-docs/blob/master/src/sugar-logging-in.md),

Known Problems:

-   no datastore entries are created [sugar-datastore #23](https://github.com/sugarlabs/sugar-datastore/pull/23), and;
-   [Browse does not visit web sites](https://github.com/sugarlabs/browse-activity/issues/119).

Ubuntu 20.10 (Groovy Gorilla)
-------------------

Sugar 0.117 can be installed with the following commands:

    sudo apt update
    sudo apt install sucrose

-   log out,
-   [log in with the Sugar desktop selected](https://github.com/sugarlabs/sugar-docs/blob/master/src/sugar-logging-in.md),

Ubuntu 19.10 (Eoan Ermine)
-------------------

Sugar 0.112 can be installed with the following commands:

    sudo apt update
    sudo apt install sucrose

-   log out,
-   [log in with the Sugar desktop selected](https://github.com/sugarlabs/sugar-docs/blob/master/src/sugar-logging-in.md),

Known Problems:

-   Sugar 0.112 does not start because of [ImportError: No module named popwindow](https://github.com/sugarlabs/sugar/issues/822), in turn because the Sugar Toolkit 0.116 is not compatible with Sugar 0.112,

Ubuntu 19.04 (Disco Dingo)
-------------------

Sugar 0.112 is in the universe repository, and can be installed with the following commands:


    sudo add-apt-repository universe
    sudo apt update
    sudo apt install sucrose

-   log out,
-   [log in with the Sugar desktop selected](https://github.com/sugarlabs/sugar-docs/blob/master/src/sugar-logging-in.md),
