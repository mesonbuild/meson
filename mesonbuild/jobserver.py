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

"""An Executor that can act as a GNU Make jobserver client."""

# Based on ThreadPoolExecutor,
# Copyright 2009 Brian Quinlan. All Rights Reserved.
# Licensed to PSF under a Contributor Agreement.

import atexit
import concurrent.futures as conc
import queue
import threading
import weakref
import errno
import os
from mesonbuild.mesonlib import is_windows
import re

# Workers are created as daemon threads. This is done to allow the interpreter
# to exit when there are still idle threads in a ThreadPoolExecutor's thread
# pool (i.e. shutdown() was not called). However, allowing workers to die with
# the interpreter has two undesirable properties:
#   - The workers would still be running during interpreter shutdown,
#     meaning that they would fail in unpredictable ways.
#   - The workers could be killed while evaluating a work item, which could
#     be bad if the callable being evaluated has external side-effects e.g.
#     writing to a file.
#
# To work around this problem, an exit handler is installed which tells all
# pools to shutdown immediately, and then waits until their threads finish.

_pools = weakref.WeakSet()

def _python_exit():
    for p in _pools:
        p.shutdown = True
    for p in _pools:
        p.join_all()

atexit.register(_python_exit)

# For now only POSIX is supported.  On Windows, you would need to use the
# Win32 API modules from PyPI, but Meson is not supposed to use anything
# but the Python standard library.
class _POSIXJobserver(object):
    def __init__(self, rfd, wfd):
        super().__init__()
        self._rfd = rfd
        self._wfd = wfd

    def deposit_token(self):
        os.write(self._wfd, b'+')

    def wait_for_token(self):
        while True:
            try:
                os.read(self._rfd, 1)
                break
            except IOError as e:
                if e.errno != errno.EINTR:
                    raise
                # another iteration


# When Make starts us, one token is already given to this process.
# We wrap _POSIXJobserver with this class to track it.
class _Jobserver(object):
    def __init__(self, inner):
        self._inner = inner
        self._lock = threading.Lock()
        # The number of tokens taken from the pipe, or -1 if we are not
        # even using the token that Make assigns to the process.
        self._taken = -1

    def deposit_token(self):
        with self._lock:
            self._taken -= 1
            if self._taken == -1:
                return
        self._inner.deposit_token()

    def wait_for_token(self):
        with self._lock:
            self._taken += 1
            if self._taken == 0:
                return
        self._inner.wait_for_token()


def _get_jobserver():
    if is_windows():
        return None
    else:
        makeflags = os.environ.get('MAKEFLAGS', '')
        match = re.search(r'(?:^|\s)--jobserver-(?:fds|auth)=([0-9]+),([0-9]+)', makeflags)
        if not match:
            return None
        rfd = int(match.group(1))
        wfd = int(match.group(2))
        jobserver = _POSIXJobserver(rfd, wfd)
    return _Jobserver(jobserver)

_jobserver = _get_jobserver()


# The actual workhorse for ThreadPoolExecutor is this class.  The executor
# is just a facade for TokenPool.  This simplifies finalization of
# ThreadPoolExecutors.

class _TokenPool(object):
    @staticmethod
    def finalize_cb(pool):
        pool.shutdown = True

    def __init__(self, max_workers):
        if max_workers <= 0:
            raise ValueError("max_workers must be greater than 0")

        self._lock = threading.Lock()
        self._ready_cv = threading.Condition(self._lock)
        self._threads = []
        self._idle_threads = 0
        self._shutdown = False
        self._queue = queue.Queue()

        global _jobserver
        self._tokens_available = 0 if _jobserver else max_workers

        global _pools
        _pools.add(self)

        with self._lock:
            self._create_worker_thread()

    @property
    def shutdown(self):
        return self._shutdown

    @shutdown.setter
    def shutdown(self, value):
        with self._lock:
            if self._shutdown and not value:
                raise RuntimeError('cannot un-shutdown')
            elif not self._shutdown and value:
                self._shutdown = True
                self._queue.put(None)

    # Tokens are the mechanism to limit the number of workers.  When
    # the jobserver is not in use, we use a simple counting semaphore
    # based on condition variables.  This avoids problems such as
    # filling the pipe's buffer when a high max_workers is requested,
    # and is more portable too.

    def deposit_local_token(self):
        with self._lock:
            self._tokens_available += 1
            self._ready_cv.notify()

    def deposit_token(self):
        global _jobserver
        if _jobserver:
            _jobserver.deposit_token()
        else:
            self.deposit_local_token()

    def wait_for_local_token(self):
        with self._lock:
            while not self._tokens_available:
                self._ready_cv.wait()
            self._tokens_available -= 1

    def wait_for_token(self):
        global _jobserver
        if _jobserver:
            _jobserver.wait_for_token()
        else:
            self.wait_for_local_token()

    # Wrappers around queue.Queue that handle shutdown

    def get(self):
        work_fn = self._queue.get(block=True)
        if work_fn is None:
            # Put back the sentinel so that other workers are notified
            self._queue.put(None)

        return work_fn

    def put(self, value):
        with self._lock:
            if self._shutdown:
                raise RuntimeError('cannot schedule new futures after shutdown')

            self._queue.put(value)

    # Thread management

    def _worker(self):
        spawned_worker = False
        try:
            while True:
                work_fn = self.get()
                if work_fn is None:
                    assert self._shutdown
                    break

                # It is important to grab the token last, because tokens are a
                # shared system resource when using a jobserver!
                self.wait_for_token()

                try:
                    with self._lock:
                        self._idle_threads -= 1
                        # If all threads are busy, create another worker thread.  However,
                        # only do so once to avoid an explosion in the number of threads.
                        # Note that we cannot know in advance the maximum number of threads
                        # if running under a jobserver, so if running under a jobserver we
                        # spawn a new thread if there is some work to do.  As a result, for
                        # "make -jN" there will be up to N+1 worker threads (of which one will
                        # always be idle).
                        global _jobserver
                        if self._idle_threads == 0 and not spawned_worker and \
                                (not self._queue.empty() if _jobserver else self._tokens_available):
                            self._create_worker_thread()
                            spawned_worker = True
                    work_fn()
                    del work_fn
                finally:
                    with self._lock:
                        self._idle_threads += 1
                    self.deposit_token()
        except:
            # Create another worker thread to replace us, and die
            with self._lock:
                self._create_worker_thread()
            raise

        # Balance the increment in self._create_worker_thread
        with self._lock:
            self._idle_threads -= 1

    def _create_worker_thread(self):
        # Called with self._lock taken.
        t = threading.Thread(target=self._worker)
        t.daemon = True
        t.start()
        self._idle_threads += 1
        self._threads.append(t)

    def join_all(self):
        with self._lock:
            assert self._shutdown
            while self._threads:
                t = self._threads[-1]
                del self._threads[-1]
                self._lock.release()
                t.join()
                del t
                self._lock.acquire()


class ThreadPoolExecutor(conc.Executor):
    def __init__(self, max_workers):
        """Initializes a new ThreadPoolExecutor instance.

        Args:
            max_workers: The maximum number of threads that can be used to
                execute the given calls.
        """
        pool = _TokenPool(max_workers)
        self._pool = pool
        weakref.finalize(self, pool.finalize_cb, pool)

    def submit(self, fn, *args, **kwargs):
        f = conc.Future()

        def run():
            if f.set_running_or_notify_cancel():
                try:
                    result = fn(*args, **kwargs)
                except BaseException as e:
                    f.set_exception(e)
                else:
                    f.set_result(result)

        self._pool.put(run)
        return f

    submit.__doc__ = conc.Executor.submit.__doc__

    def shutdown(self, wait=True):
        self._pool.shutdown = True
        if wait:
            self._pool.join_all()

    shutdown.__doc__ = conc.Executor.shutdown.__doc__


if __name__ == '__main__':
    import time, random

    lock = threading.Lock()
    concurrent = 0

    def long_running(i):
        global concurrent
        with lock:
            concurrent += 1
            print('Started job %d, %d concurrent jobs running.' % (i, concurrent))
        sleep_time = random.random() / 4.0 + 0.25
        time.sleep(sleep_time)
        with lock:
            concurrent -= 1

    ex = ThreadPoolExecutor(4)
    futures = [ex.submit(long_running, i) for i in range(10)]
    print('1. Waiting on futures')
    for f in futures:
        f.result()
    ex.shutdown(True)

    ex = ThreadPoolExecutor(4)
    futures = [ex.submit(long_running, i) for i in range(10)]
    print('2. Waiting on futures')
    for f in futures:
        f.result()
    ex.shutdown(True)
