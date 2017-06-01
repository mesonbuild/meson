# Copyright 2017 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from . import mlog
from . import coredata
from .mesonlib import version_compare

# This is the oldest version we can possibly be compatible with. To remove
# compatibility code for an unsupported version, bump this, run the tests,
# and look for assertion errors.
oldest_version = '0.40.0'
current_version = coredata.version

def check_compat_needed(meson_version, change_version, warn_msg):
    '''
    Check whether minimum version required by the current (sub)project is older
    than the @change_version in which the change was made. If it is, we need to
    maintain backwards-compatibility by using the old behaviour and printing
    a warning. Else, the compatibility code is not needed.

    @warn_msg is the warning message to use. Must not end in a period.
    '''
    if not version_compare(change_version, '>=' + oldest_version):
        raise AssertionError('BUG: Support for version {!r} should have been removed')
    if version_compare(meson_version, '>=' + change_version):
        return False
    msg = '(in {}) '.format(change_version) + warn_msg + \
          '. Using compatibility code which will be removed in a future version.'
    mlog.deprecated(msg)
    return True
