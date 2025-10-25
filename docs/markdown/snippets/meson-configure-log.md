## Add a configure log in meson-logs

Add a second log file `meson-setup.txt` which contains the configure logs
displayed on stdout during the meson `setup` stage.
It allows user to navigate through the setup logs without searching in the terminal
or the extensive informations of `meson-log.txt`.