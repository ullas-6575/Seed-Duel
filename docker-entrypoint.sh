#!/bin/sh
set -eu

display_num="${DISPLAY#:}"
rm -f "/tmp/.X${display_num}-lock" "/tmp/.X11-unix/X${display_num}"

Xvfb "$DISPLAY" -screen 0 1100x720x24 -ac -nolisten tcp &
xvfb_pid=$!
x11vnc_pid=
websockify_pid=
app_pid=

stop_services() {
    [ -z "$app_pid" ] || kill "$app_pid" 2>/dev/null || true
    [ -z "$websockify_pid" ] || kill "$websockify_pid" 2>/dev/null || true
    [ -z "$x11vnc_pid" ] || kill "$x11vnc_pid" 2>/dev/null || true
    kill "$xvfb_pid" 2>/dev/null || true
}
trap stop_services EXIT INT TERM

attempt=0
while [ ! -S "/tmp/.X11-unix/X${display_num}" ]; do
    if ! kill -0 "$xvfb_pid" 2>/dev/null; then
        echo "Xvfb failed to start" >&2
        exit 1
    fi
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 50 ]; then
        echo "Timed out waiting for Xvfb" >&2
        exit 1
    fi
    sleep 0.1
done

x11vnc \
    -display "$DISPLAY" \
    -forever \
    -shared \
    -nopw \
    -localhost \
    -rfbport 5900 \
    -noxdamage \
    -xkb \
    -cursor most \
    -quiet &
x11vnc_pid=$!

websockify --web=/usr/share/novnc 0.0.0.0:6080 localhost:5900 &
websockify_pid=$!

echo "Seed Duel is ready at http://localhost:6080 (or http://localhost:6080/vnc.html?autoconnect=1&resize=scale)"

python main.py &
app_pid=$!
wait "$app_pid"
