# Copyright 2019 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This class contains the basic functionality needed to run any interpreter
# or an interpreter-based tool.

from .common import CMakeException
from ..environment import Environment
from ..dependencies.base import CMakeDependency, ExternalProgram
from .. import mlog
from contextlib import contextmanager
from subprocess import Popen, PIPE, TimeoutExpired
from typing import List, Optional
import json

CMAKE_SERVER_BEGIN_STR = '[== "CMake Server" ==['
CMAKE_SERVER_END_STR = ']== "CMake Server" ==]'

CMAKE_MESSAGE_TYPES = {
    'error': ['cookie', 'errorMessage'],
    'hello': ['supportedProtocolVersions'],
    'reply': ['cookie', 'inReplyTo'],
}

CMAKE_REPLY_TYPES = {
    'handshake': [],
}

# Base CMake server message classes

class MessageBase:
    def __init__(self, type: str, cookie: str):
        self.type = type
        self.cookie = cookie

    def to_dict(self) -> dict:
        return {'type': self.type, 'cookie': self.cookie}

    def log(self) -> None:
        mlog.warning('CMake server message of type', mlog.bold(type(self).__name__), 'has no log function')

class RequestBase(MessageBase):
    cookie_counter = 0

    def __init__(self, type: str):
        super().__init__(type, self.gen_cookie())

    @staticmethod
    def gen_cookie():
        RequestBase.cookie_counter += 1
        return 'meson_{}'.format(RequestBase.cookie_counter)

class ReplyBase(MessageBase):
    def __init__(self, cookie: str, in_reply_to: str):
        super().__init__('reply', cookie)
        self.in_reply_to = in_reply_to

# Special Message classes

class Error(MessageBase):
    def __init__(self, cookie: str, message: str):
        super().__init__('error', cookie)
        self.message = message

    def log(self) -> None:
        mlog.error(mlog.bold('CMake server error:'), mlog.red(self.message))

class MessageHello(MessageBase):
    def __init__(self, supported_protocol_versions: List[dict]):
        super().__init__('hello', '')
        self.supported_protocol_versions = supported_protocol_versions

    def supports(self, major: int, minor: Optional[int] = None) -> bool:
        for i in self.supported_protocol_versions:
            if major == i['major']:
                if minor is None or minor == i['minor']:
                    return True
        return False

# Request classes

class RequestHandShake(RequestBase):
    def __init__(self, src_dir: str, build_dir: str, generator: str, vers_major: int, vers_minor: Optional[int] = None):
        super().__init__('handshake')
        self.src_dir = src_dir
        self.build_dir = build_dir
        self.generator = generator
        self.vers_major = vers_major
        self.vers_minor = vers_minor

    def to_dict(self) -> dict:
        vers = {'major': self.vers_major}
        if self.vers_minor is not None:
            vers['minor'] = self.vers_minor
        return {
            **super().to_dict(),
            'sourceDirectory': self.src_dir,
            'buildDirectory': self.build_dir,
            'generator': self.generator,
            'protocolVersion': vers
        }

# Reply classes

class ReplyHandShake(ReplyBase):
    def __init__(self, cookie: str):
        super().__init__(cookie, 'handshake')

class CMakeClient:
    def __init__(self, env: Environment):
        self.env = env
        self.proc = None
        self.type_map = {
            'hello': self.resolve_type_hello,
            'error': self.resolve_type_error,
            'reply': self.resolve_type_reply,
        }

        self.reply_map = {
            'handshake': self.resolve_reply_handshake,
        }

    def readMessageRaw(self) -> dict:
        assert(self.proc is not None)
        rawData = []
        begin = False
        while self.proc.poll() is None:
            line = self.proc.stdout.readline()
            if not line:
                break
            line = line.decode('utf-8')
            line = line.strip()

            if begin and line == CMAKE_SERVER_END_STR:
                break # End of the message
            elif begin:
                rawData += [line]
            elif line == CMAKE_SERVER_BEGIN_STR:
                begin = True # Begin of the message

        if rawData:
            return json.loads('\n'.join(rawData))
        raise CMakeException('Failed to read data from the CMake server')

    def readMessage(self) -> MessageBase:
        raw_data = self.readMessageRaw()
        if 'type' not in raw_data:
            raise CMakeException('The "type" attribute is missing from the message')
        type = raw_data['type']
        func = self.type_map.get(type, None)
        if not func:
            raise CMakeException('Recieved unknown message type "{}"'.format(type))
        for i in CMAKE_MESSAGE_TYPES[type]:
            if i not in raw_data:
                raise CMakeException('Key "{}" is missing from CMake server message type {}'.format(i, type))
        return func(raw_data)

    def writeMessage(self, msg: MessageBase) -> None:
        raw_data = '\n{}\n{}\n{}\n'.format(CMAKE_SERVER_BEGIN_STR, json.dumps(msg.to_dict(), indent=2), CMAKE_SERVER_END_STR)
        self.proc.stdin.write(raw_data.encode('ascii'))
        self.proc.stdin.flush()

    def query(self, request: RequestBase) -> MessageBase:
        self.writeMessage(request)
        while True:
            reply = self.readMessage()
            if reply.cookie == request.cookie:
                return reply

            reply.log()

    def do_handshake(self, src_dir: str, build_dir: str, generator: str, vers_major: int, vers_minor: Optional[int] = None) -> None:
        # CMake prints the hello message on startup
        msg = self.readMessage()
        if not isinstance(msg, MessageHello):
            raise CMakeException('Recieved an unexpected message from the CMake server')

        request = RequestHandShake(src_dir, build_dir, generator, vers_major, vers_minor)
        reply = self.query(request)
        if not isinstance(reply, ReplyHandShake):
            reply.log()
            mlog.log('CMake server handshake:', mlog.red('FAILED'))
            raise CMakeException('Failed to perform the handshake with the CMake server')
        mlog.log('CMake server handshake:', mlog.green('OK'))

    def resolve_type_error(self, data: dict) -> Error:
        return Error(data['cookie'], data['errorMessage'])

    def resolve_type_hello(self, data: dict) -> MessageHello:
        return MessageHello(data['supportedProtocolVersions'])

    def resolve_type_reply(self, data: dict) -> ReplyBase:
        reply_type = data['inReplyTo']
        func = self.reply_map.get(reply_type, None)
        if not func:
            raise CMakeException('Recieved unknown reply type "{}"'.format(reply_type))
        for i in ['cookie'] + CMAKE_REPLY_TYPES[reply_type]:
            if i not in data:
                raise CMakeException('Key "{}" is missing from CMake server message type {}'.format(i, type))
        return func(data)

    def resolve_reply_handshake(self, data: dict) -> ReplyHandShake:
        return ReplyHandShake(data['cookie'])

    @contextmanager
    def connect(self):
        self.startup()
        try:
            yield
        finally:
            self.shutdown()

    def startup(self) -> None:
        if self.proc is not None:
            raise CMakeException('The CMake server was already started')

        cmake_exe, cmake_vers, _ = CMakeDependency.find_cmake_binary(self.env)
        if cmake_exe is None or cmake_exe is False:
            raise CMakeException('Unable to find CMake')
        assert(isinstance(cmake_exe, ExternalProgram))
        if not cmake_exe.found():
            raise CMakeException('Unable to find CMake')

        mlog.log('Starting CMake server with CMake', mlog.bold(' '.join(cmake_exe.get_command())), 'version', mlog.cyan(cmake_vers))
        self.proc = Popen(cmake_exe.get_command() + ['-E', 'server', '--experimental', '--debug'], stdin=PIPE, stdout=PIPE)

    def shutdown(self) -> None:
        if self.proc is None:
            return

        mlog.log('Shutting down the CMake server')

        # Close the pipes to exit
        self.proc.stdin.close()
        self.proc.stdout.close()

        # Wait for CMake to finish
        try:
            self.proc.wait(timeout=2)
        except TimeoutExpired:
            self.proc.terminate()

        self.proc = None
