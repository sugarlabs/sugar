#!/bin/bash
# Launch Sugar inside a nested Xephyr window for safe testing.

set -e

# Find a free display number
DISPLAY_NUM=2
while [ -e /tmp/.X11-unix/X${DISPLAY_NUM} ]; do
    DISPLAY_NUM=$((DISPLAY_NUM + 1))
done

X_DISPLAY=":${DISPLAY_NUM}"
SUGAR_TEST_HOME="/tmp/sugar_test_home_$$"
LOG_FILE="/tmp/sugar_xephyr_$$.log"

echo "Starting Xephyr on display ${X_DISPLAY}..."
Xephyr ${X_DISPLAY} -screen 1200x900 -ac -br -noreset > "${LOG_FILE}.xephyr" 2>&1 &
XEPHYR_PID=$!
disown ${XEPHYR_PID}
sleep 2

SUGAR_DATA_DIR="/usr/share/sugar/data"

# Clean snap-polluted environment variables (e.g. from the VS Code snap) that
# point gdk-pixbuf, GTK, GIO and GLib at snap-specific loader/library paths.
# These cause incompatible snap libraries (libpthread from snap core20) to be
# loaded, resulting in fatal symbol lookup errors. We reset to system defaults.
unset GDK_PIXBUF_MODULE_FILE
unset GDK_PIXBUF_MODULEDIR
unset GIO_MODULE_DIR
unset GTK_PATH
unset GTK_EXE_PREFIX
unset GTK_IM_MODULE_FILE
unset GSETTINGS_SCHEMA_DIR
unset XDG_DATA_HOME
unset LOCPATH
unset SNAP SNAP_NAME SNAP_VERSION SNAP_REVISION SNAP_ARCH SNAP_COMMON SNAP_DATA
unset SNAP_USER_COMMON SNAP_USER_DATA SNAP_INSTANCE_NAME SNAP_CONTEXT SNAP_COOKIE
unset SNAP_EUID SNAP_LAUNCHER_ARCH_TRIPLET SNAP_LIBRARY_PATH SNAP_REAL_HOME
export XDG_DATA_DIRS="/usr/local/share:/usr/share:/var/lib/snapd/desktop"
export XDG_CONFIG_DIRS="/etc/xdg"
export XDG_CACHE_HOME="${SUGAR_TEST_HOME}/.cache"

mkdir -p "${SUGAR_TEST_HOME}/default" "${SUGAR_TEST_HOME}/.cache"
export SUGAR_HOME="${SUGAR_TEST_HOME}"
export SUGAR_PROFILE="default"
export SUGAR_SCALING="72"
export DISPLAY="${X_DISPLAY}"
export GTK2_RC_FILES="${SUGAR_DATA_DIR}/sugar-${SUGAR_SCALING}.gtkrc"
export SUGAR_GROUP_LABELS="${SUGAR_DATA_DIR}/group-labels.defaults"
export SUGAR_MIME_DEFAULTS="${SUGAR_DATA_DIR}/mime.defaults"
export SUGAR_ACTIVITIES_HIDDEN="${SUGAR_DATA_DIR}/activities.hidden"
export MC_ACCOUNT_DIR="${SUGAR_TEST_HOME}/default/accounts"
export LANG="${LANG:-en_US.utf8}"
export LANGUAGE="${LANGUAGE:-${LANG}}"
export HOME="${SUGAR_TEST_HOME}"

# Use the local source tree
export PYTHONPATH="/home/ashutoshx7/sugar/src:${PYTHONPATH}"

echo "Starting Sugar on ${X_DISPLAY}..."
echo "Logs: ${LOG_FILE}"
dbus-launch --exit-with-session python3 -m jarabe.main > "${LOG_FILE}" 2>&1 &
SUGAR_PID=$!
disown ${SUGAR_PID}

echo "Xephyr PID: ${XEPHYR_PID}"
echo "Sugar PID: ${SUGAR_PID}"
echo ""
echo "Sugar is running in Xephyr on display ${X_DISPLAY}"
echo "To stop, run: kill ${XEPHYR_PID} ${SUGAR_PID}"
echo ""

# Keep script alive but detached
sleep 3
echo "Sugar startup complete. PIDs: Xephyr=${XEPHYR_PID} Sugar=${SUGAR_PID}"
