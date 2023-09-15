@echo off
REM This script generates the expected files
REM Please double-check the contents of those files before commiting them!!!

python ../../../meson.py format -o default.expected.meson source.meson
python ../../../meson.py format -c muon.ini -o muon.expected.meson source.meson
python ../../../meson.py format -c options.ini -o options.expected.meson source.meson
