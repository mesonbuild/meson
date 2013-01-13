#!/usr/bin/python3 -tt

# Copyright 2012 Jussi Pakkanen

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

class Build:
    """A class that holds the status of one build including
    all dependencies and so on.
    """

    def __init__(self, environment):
        self.environment = environment
        self.project = None
        self.targets = {}
        self.compilers = []
        self.tests = []
        self.headers = []
        self.man = []
        self.data = []
        self.static_linker = self.environment.detect_static_linker()
        self.configure_files = []

    def get_project(self):
        return self.project

    def get_targets(self):
        return self.targets

    def get_tests(self):
        return self.tests

    def get_headers(self):
        return self.headers

    def get_man(self):
        return self.man

    def get_data(self):
        return self.data

    def get_configure_files(self):
        return self.configure_files
