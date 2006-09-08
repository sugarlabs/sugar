Xephyr :50 -ac -screen 800x600 &

DISPLAY=:50
matchbox-window-manager &
exec $*
