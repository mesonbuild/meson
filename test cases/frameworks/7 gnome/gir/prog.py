#!/usr/bin/env python3
from gi.repository import Meson

if __name__ == "__main__":
    s = Meson.Sample.new("Hello, meson/py!")
    s.print_message()
