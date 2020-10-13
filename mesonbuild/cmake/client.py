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

from .common import CMakeException, CMakeConfiguration, CMakeBuildFile
from .. import mlog
from contextlib import contextmanager
from subprocess import Popen, PIPE, TimeoutExpired
from .._pathlib import Path
import typing as T
import json

if T.TYPE_CHECKING:
    from ..environment import Environment
    from .executor import CMakeExecutor

CMAKE_SERVER_BEGIN_STR = '[== "CMake Server" ==['
CMAKE_SERVER_END_STR = ']== "CMake Server" ==]'

CMAKE_MESSAGE_TYPES = {
    'error': ['cookie', 'errorMessage'],
    'hello': ['supportedProtocolVersions'],
    'message': ['cookie', 'message'],
    'progress': ['cookie'],
    'reply': ['cookie', 'inReplyTo'],
    'signal': ['cookie', 'name'],
}  # type: T.Dict[str, T.List[str]]

CMAKE_REPLY_TYPES = {
    'handshake': [],
    'configure': [],
    'compute': [],
    'cmakeInputs': ['buildFiles', 'cmakeRootDirectory', 'sourceDirectory'],
    'codemodel': ['configurations']
}  # type: T.Dict[str, T.List[str]]

# Base CMake server message classes

class MessageBase:
    def __init__(self, msg_type: str, cookie: str) -> None:
        self.type = msg_type
        self.cookie = cookie

    def to_dict(self) -> T.Dict[str, T.Union[str, T.List[str], T.Dict[str, int]]]:
        return {'type': self.type, 'cookie': self.cookie}

    def log(self) -> None:
        mlog.warning('CMake server message of type', mlog.bold(type(self).__name__), 'has no log function')

class RequestBase(MessageBase):
    cookie_counter = 0

    def __init__(self, msg_type: str) -> None:
        super().__init__(msg_type, self.gen_cookie())

    @staticmethod
    def gen_cookie() -> str:
        RequestBase.cookie_counter += 1
        return 'meson_{}'.format(RequestBase.cookie_counter)

class ReplyBase(MessageBase):
    def __init__(self, cookie: str, in_reply_to: str) -> None:
        super().__init__('reply', cookie)
        self.in_reply_to = in_reply_to

class SignalBase(MessageBase):
    def __init__(self, cookie: str, signal_name: str) -> None:
        super().__init__('signal', cookie)
        self.signal_name = signal_name

    def log(self) -> None:
        mlog.log(mlog.bold('CMake signal:'), mlog.yellow(self.signal_name))

# Special Message classes

class Error(MessageBase):
    def __init__(self, cookie: str, message: str) -> None:
        super().__init__('error', cookie)
        self.message = message

    def log(self) -> None:
        mlog.error(mlog.bold('CMake server error:'), mlog.red(self.message))

class Message(MessageBase):
    def __init__(self, cookie: str, message: str) -> None:
        super().__init__('message', cookie)
        self.message = message

    def log(self) -> None:
        #mlog.log(mlog.bold('CMake:'), self.message)
        pass

class Progress(MessageBase):
    def __init__(self, cookie: str) -> None:
        super().__init__('progress', cookie)

    def log(self) -> None:
        pass

class MessageHello(MessageBase):
    def __init__(self, supported_protocol_versions: T.List[T.Dict[str, int]]) -> None:
        super().__init__('hello', '')
        self.supported_protocol_versions = supported_protocol_versions

    def supports(self, major: int, minor: T.Optional[int] = None) -> bool:
        for i in self.supported_protocol_versions:
            assert 'major' in i
            assert 'minor' in i
            if major == i['major']:
                if minor is None or minor == i['minor']:
                    return True
        return False

# Request classes

class RequestHandShake(RequestBase):
    def __init__(self, src_dir: Path, build_dir: Path, generator: str, vers_major: int, vers_minor: T.Optional[int] = None) -> None:
        super().__init__('handshake')
        self.src_dir = src_dir
        self.build_dir = build_dir
        self.generator = generator
        self.vers_major = vers_major
        self.vers_minor = vers_minor

    def to_dict(self) -> T.Dict[str, T.Union[str, T.List[str], T.Dict[str, int]]]:
        vers = {'major': self.vers_major}
        if self.vers_minor is not None:
            vers['minor'] = self.vers_minor

        # Old CMake versions (3.7) want '/' even on Windows
        self.src_dir   = self.src_dir.resolve()
        self.build_dir = self.build_dir.resolve()

        return {
            **super().to_dict(),
            'sourceDirectory': self.src_dir.as_posix(),
            'buildDirectory': self.build_dir.as_posix(),
            'generator': self.generator,
            'protocolVersion': vers
        }

class RequestConfigure(RequestBase):
    def __init__(self, args: T.Optional[T.List[str]] = None):
        super().__init__('configure')
        self.args = args

    def to_dict(self) -> T.Dict[str, T.Union[str, T.List[str], T.Dict[str, int]]]:
        res = super().to_dict()
        if self.args:
            res['cacheArguments'] = self.args
        return res

class RequestCompute(RequestBase):
    def __init__(self) -> None:
        super().__init__('compute')

class RequestCMakeInputs(RequestBase):
    def __init__(self) -> None:
        super().__init__('cmakeInputs')

class RequestCodeModel(RequestBase):
    def __init__(self) -> None:
        super().__init__('codemodel')

# Reply classes

class ReplyHandShake(ReplyBase):
    def __init__(self, cookie: str) -> None:
        super().__init__(cookie, 'handshake')

class ReplyConfigure(ReplyBase):
    def __init__(self, cookie: str) -> None:
        super().__init__(cookie, 'configure')

class ReplyCompute(ReplyBase):
    def __init__(self, cookie: str) -> None:
        super().__init__(cookie, 'compute')

class ReplyCMakeInputs(ReplyBase):
    def __init__(self, cookie: str, cmake_root: Path, src_dir: Path, build_files: T.List[CMakeBuildFile]) -> None:
        super().__init__(cookie, 'cmakeInputs')
        self.cmake_root = cmake_root
        self.src_dir = src_dir
        self.build_files = build_files

    def log(self) -> None:
        mlog.log('CMake root: ', mlog.bold(self.cmake_root.as_posix()))
        mlog.log('Source dir: ', mlog.bold(self.src_dir.as_posix()))
        mlog.log('Build files:', mlog.bold(str(len(self.build_files))))
        with mlog.nested():
            for i in self.build_files:
                mlog.log(str(i))

class ReplyCodeModel(ReplyBase):
    def __init__(self, data: T.Dict[str, T.Any]) -> None:
        super().__init__(data['cookie'], 'codemodel')
        self.configs = []
        for i in data['configurations']:
            self.configs += [CMakeConfiguration(i)]

    def log(self) -> None:
        mlog.log('CMake code mode:')
        for idx, i in enumerate(self.configs):
            mlog.log('Configuration {}:'.format(idx))
            with mlog.nested():
                i.log()

# Main client class

class CMakeClient:
    def __init__(self, env: 'Environment') -> None:
        self.env = env
        self.proc = None  # type: T.Optional[Popen]
        self.type_map = {
            'error': lambda data: Error(data['cookie'], data['errorMessage']),
            'hello': lambda data: MessageHello(data['supportedProtocolVersions']),
            'message': lambda data: Message(data['cookie'], data['message']),
            'progress': lambda data: Progress(data['cookie']),
            'reply': self.resolve_type_reply,
            'signal': lambda data: SignalBase(data['cookie'], data['name'])
        }  # type: T.Dict[str, T.Callable[[T.Dict[str, T.Any]], MessageBase]]

        self.reply_map = {
            'handshake': lambda data: ReplyHandShake(data['cookie']),
            'configure': lambda data: ReplyConfigure(data['cookie']),
            'compute': lambda data: ReplyCompute(data['cookie']),
            'cmakeInputs': self.resolve_reply_cmakeInputs,
            'codemodel': lambda data: ReplyCodeModel(data),
        }  # type: T.Dict[str, T.Callable[[T.Dict[str, T.Any]], ReplyBase]]

    def readMessageRaw(self) -> T.Dict[str, T.Any]:
        assert self.proc is not None
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
            res = json.loads('\n'.join(rawData))
            assert isinstance(res, dict)
            for i in res.keys():
                assert isinstance(i, str)
            return res
        raise CMakeException('Failed to read data from the CMake server')

    def readMessage(self) -> MessageBase:
        raw_data = self.readMessageRaw()
        if 'type' not in raw_data:
            raise CMakeException('The "type" attribute is missing from the message')
        msg_type = raw_data['type']
        func = self.type_map.get(msg_type, None)
        if not func:
            raise CMakeException('Recieved unknown message type "{}"'.format(msg_type))
        for i in CMAKE_MESSAGE_TYPES[msg_type]:
            if i not in raw_data:
                raise CMakeException('Key "{}" is missing from CMake server message type {}'.format(i, msg_type))
        return func(raw_data)

    def writeMessage(self, msg: MessageBase) -> None:
        raw_data = '\n{}\n{}\n{}\n'.format(CMAKE_SERVER_BEGIN_STR, json.dumps(msg.to_dict(), indent=2), CMAKE_SERVER_END_STR)
        self.proc.stdin.write(raw_data.encode('ascii'))
        self.proc.stdin.flush()

    def query(self, request: RequestBase) -> MessageBase:
        self.writeMessage(request)
        while True:
            reply = self.readMessage()
            if reply.cookie == request.cookie and reply.type in ['reply', 'error']:
                return reply

            reply.log()

    def query_checked(self, request: RequestBase, message: str) -> MessageBase:
        reply = self.query(request)
        h = mlog.green('SUCCEEDED') if reply.type == 'reply' else mlog.red('FAILED')
        mlog.log(message + ':', h)
        if reply.type != 'reply':
            reply.log()
            raise CMakeException('CMake server query failed')
        return reply

    def do_handshake(self, src_dir: Path, build_dir: Path, generator: str, vers_major: int, vers_minor: T.Optional[int] = None) -> None:
        # CMake prints the hello message on startup
        msg = self.readMessage()
        if not isinstance(msg, MessageHello):
            raise CMakeException('Recieved an unexpected message from the CMake server')

        request = RequestHandShake(src_dir, build_dir, generator, vers_major, vers_minor)
        self.query_checked(request, 'CMake server handshake')

    def resolve_type_reply(self, data: T.Dict[str, T.Any]) -> ReplyBase:
        reply_type = data['inReplyTo']
        func = self.reply_map.get(reply_type, None)
        if not func:
            raise CMakeException('Recieved unknown reply type "{}"'.format(reply_type))
        for i in ['cookie'] + CMAKE_REPLY_TYPES[reply_type]:
            if i not in data:
                raise CMakeException('Key "{}" is missing from CMake server message type {}'.format(i, type))
        return func(data)

    def resolve_reply_cmakeInputs(self, data: T.Dict[str, T.Any]) -> ReplyCMakeInputs:
        files = []
        for i in data['buildFiles']:
            for j in i['sources']:
                files += [CMakeBuildFile(Path(j), i['isCMake'], i['isTemporary'])]
        return ReplyCMakeInputs(data['cookie'], Path(data['cmakeRootDirectory']), Path(data['sourceDirectory']), files)

    @contextmanager
    def connect(self, cmake_exe: 'CMakeExecutor') -> T.Generator[None, None, None]:
        self.startup(cmake_exe)
        try:
            yield
        finally:
            self.shutdown()

    def startup(self, cmake_exe: 'CMakeExecutor') -> None:
        if self.proc is not None:
            raise CMakeException('The CMake server was already started')
        assert cmake_exe.found()

        mlog.debug('Starting CMake server with CMake', mlog.bold(' '.join(cmake_exe.get_command())), 'version', mlog.cyan(cmake_exe.version()))
        self.proc = Popen(cmake_exe.get_command() + ['-E', 'server', '--experimental', '--debug'], stdin=PIPE, stdout=PIPE)

    def shutdown(self) -> None:
        if self.proc is None:
            return

        mlog.debug('Shutting down the CMake server')

        # Close the pipes to exit
        self.proc.stdin.close()
        self.proc.stdout.close()

        # Wait for CMake to finish
        try:
            self.proc.wait(timeout=2)
        except TimeoutExpired:
            # Terminate CMake if there is a timeout
            # terminate() may throw a platform specific exception if the process has already
            # terminated. This may be the case if there is a race condition (CMake exited after
            # the timeout but before the terminate() call). Additionally, this behavior can
            # also be triggered on cygwin if CMake crashes.
            # See https://github.com/mesonbuild/meson/pull/4969#issuecomment-499413233
            try:
                self.proc.terminate()
            except Exception:
                pass

        self.proc = None
