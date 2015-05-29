#!/usr/bin/env python3
#
# Copyright 2015 The Meson development team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import requests

import mlog

API_URL = "http://wrapdb.mesonbuild.com/v1"

parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group()
group.add_argument("--list-wraps", action="store_true", dest="list_projects", default=True,
                    help="List all available projects with wraps.")

def list_projects():
    j = requests.get("%s/projects" % API_URL).json()
    mlog.log("Available projects:")
    for p in j["projects"]:
        mlog.log("-", mlog.bold(p))

if __name__ == "__main__":
    options = parser.parse_args()
    if options.list_projects:
        list_projects()
