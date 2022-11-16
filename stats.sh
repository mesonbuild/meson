#!/usr/bin/env bash
check_it() {
        cd ../$1 || exit
        git stash >/dev/null 2>&1
        cd ../meson || exit
        n_comments=$(python meson.py fmt_unstable ../$1 -R -v |& grep Found.*comments | cut -d ' ' -f2 | paste -sd+ | bc)
        cd ../$1 || exit
        git stash >/dev/null 2>&1
        cd ../meson || exit
        n_lost_comments=$(python meson.py fmt_unstable ../$1 -R |& grep Unable.to.readd | cut -d ' ' -f4 | paste -sd+ | bc)
        if [ -z "$n_lost_comments" ]; then
                n_lost_comments=0
        fi
        cd ../$1 || exit
        git stash >/dev/null 2>&1
        cd ../meson || exit
        percentage=$(echo "print(str(round(($n_lost_comments/$n_comments) * 100, 3)) + '%')" | python /dev/stdin)
        echo "$1 has $n_comments, lost $n_lost_comments during formatting ($percentage)"
}

check_it systemd
check_it mesa
check_it gnome-builder
check_it gstreamer
check_it gtk
check_it glib

