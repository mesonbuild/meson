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
        self._tokens_available = max_workers

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

    # Tokens are the mechanism to limit the number of workers.

    def deposit_token(self):
        with self._lock:
            self._tokens_available += 1
            self._ready_cv.notify()

    def wait_for_token(self):
        with self._lock:
            while not self._tokens_available:
                self._ready_cv.wait()
            self._tokens_available -= 1

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
                        if self._idle_threads == 0 and self._tokens_available and not spawned_worker:
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
