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

from optparse import OptionParser
import sys

parser = OptionParser()

parser.add_option('--prefix', default='/usr/local', dest='prefix')
parser.add_option('--libdir', default='lib', dest='libdir')
parser.add_option('--includedir', default='include', dest='includedir')
parser.add_option('--datadir', default='share', dest='datadir')

if __name__ == '__main__':
    (options, args) = parser.parse_args(sys.argv)
    print (len(args))
    if len(args) == 1 or len(args) > 3:
        print('Invalid arguments')