# Components of a Software Bill Of Materials (SBOM)

## Primary Components

* maintained by Sugar Labs,

| Component | Description | Repository |
| :-------- | :---------- | :--------- |
| Sugar | Activity Menu, Journal, Network View and Control Panel | https://github.com/sugarlabs/sugar |
| Toolkit | Activity, Journal, and Plaform library | https://github.com/sugarlabs/sugar-toolkit-gtk3 |
| Datastore | Journal Storage API | https://github.com/sugarlabs/sugar-datastore |
| Artwork | Icons, Themes and Cursors | https://github.com/sugarlabs/sugar-artwork |
| Browse Activity | Web Browser | https://github.com/sugarlabs/browse-activity |
| Calculate Activity | Calculator | https://github.com/sugarlabs/calculate-activity |
| Chat Activity | Messaging Client | https://github.com/sugarlabs/chat |
| Image Viewer Activity | Image Viewer | https://github.com/sugarlabs/imageviewer-activity |
| Jukebox Activity | Audio and Video Viewer | https://github.com/sugarlabs/jukebox-activity |
| Log Activity | System Log Viewer | https://github.com/sugarlabs/log-activity |
| Pippy Activity | Python Development Environment | https://github.com/sugarlabs/Pippy |
| Read Activity | Document Reader | https://github.com/sugarlabs/read-activity |
| Terminal Activity | Terminal Emulator | https://github.com/sugarlabs/terminal-activity |
| Turtle Art Activity | Block Programming Language | https://github.com/sugarlabs/turtleart-activity |
| Write Activity | Document Editor | https://github.com/sugarlabs/write-activity |

<details><summary>source of data</summary>

1. Sugar, Toolkit, Datastore and Artwork are the core Sugar components,
1. Fructose activities are the core Sugar activites, as listed in http://download.sugarlabs.org/sources/sucrose/fructose/

</details>

## Dependencies of Primary Components

<details><summary>source of data</summary>

1. `git grep "import "`
1. `git grep "#include "`
1. dependencies of downstream packages of Sugar,

</details>

## Secondary Components

* dependencies of primary components, and;
* maintained by Sugar Labs,

| Component | Description | Repository |
| :-------- | :---------- | :--------- |
| gwebsockets | Python websocket server integrated with GIO and GLib | https://github.com/sugarlabs/gwebsockets
| gst-plugins-espeak | GStreamer espeak plugin | https://github.com/sugarlabs/gst-plugins-espeak |
| sugar-web | Sugar activity components for JavaScript | https://github.com/sugarlabs/sugar-web |

<details><summary>source of data</summary>

1. search of https://github.com/sugarlabs repositories,

</details>

## Dependencies of Secondary Components

## Embedded Components

* copied into code of other components,
* maintained by Sugar Labs,

| Component | Description | Repository |
| :-------- | :---------- | :--------- |
| collabwrapper | Telepathy wrapper for Sugar activities | https://github.com/sugarlabs/collabwrapper |
| sugargame | Pygame and GTK wrapper for Sugar activities | https://github.com/sugarlabs/sugargame |

<details><summary>source of data</summary>

1. search of https://github.com/sugarlabs repositories,

</details>

