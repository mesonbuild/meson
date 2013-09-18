#!/usr/bin/env python3

# Copyright 2013 Jussi Pakkanen

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow

class MesonGui():
    def __init__(self):
        uifile = 'mesonmain.ui'
        self.ui = uic.loadUi(uifile)
        self.ui.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    if len(sys.argv) != 2:
        print(sys.argv[0], "<build dir>")
        sys.exit(1)
    gui = MesonGui()
    sys.exit(app.exec_())
