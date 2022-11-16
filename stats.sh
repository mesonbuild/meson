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
        rounds=0
        while :; do
                python meson.py fmt_unstable ../$1 -R >/dev/null 2>&1 || exit
                cd ../$1 || exit
                if [[ $(git diff --stat) != '' ]]; then
                        git commit -a -m "FOO" --no-verify >/dev/null 2>&1 || exit
                        ((rounds++))
                else
                        break
                fi
                cd ../meson || exit
        done
        echo "$1 needed $rounds formatting passes to be stable"
        git reset --hard HEAD~$rounds >/dev/null 2>&1 || exit
        cd ../meson || exit
}
if [ -z "$YES_THIS_WILL_OVERWRITE_MY_CHANGES_TO_THESE_PROJECTS" ]; then
        echo "No confirmation given. This uses git reset --hard and may destroy your changes,"
        echo "if any of those projects has uncommitted changes"
        exit 1
fi
check_it systemd
check_it mesa
check_it gnome-builder
check_it gstreamer
check_it gtk
check_it glib

