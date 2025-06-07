cmake_minimum_required(VERSION 3.12)

project("configure file test" LANGUAGES C)

set("var1" "foo")
set("var2" "bar")
configure_file("config7.h.in" "config7.h")

set("var" "foo")
configure_file("config10.h.in" "config10.h")
