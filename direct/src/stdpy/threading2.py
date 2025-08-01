""" This module reimplements Python's native threading module using Panda
threading constructs.  It's designed as a drop-in replacement for the
threading module for code that works with Panda; it is necessary because
in some compilation models, Panda's threading constructs are
incompatible with the OS-provided threads used by Python's thread
module.

Unlike threading.py, this module is a more explicit implementation of
Python's threading model, designed to more precisely emulate Python's
standard threading semantics.  In fact, this is a bald-face copy of
Python's threading module from Python 2.5, with a few lines at the top
to import Panda's thread reimplementation instead of the system thread
module, and so it is therefore layered on top of Panda's thread
implementation. """

from __future__ import annotations

import sys as _sys
import atexit as _atexit

from direct.stdpy import thread as _thread
from direct.stdpy.thread import stack_size, _newname, _local as local
from panda3d import core
_sleep = core.Thread.sleep

from collections.abc import Callable, Iterable, Mapping
from time import time as _time
from traceback import format_exc as _format_exc
from typing import Any

__all__ = ['get_ident', 'active_count', 'Condition', 'current_thread',
           'enumerate', 'main_thread', 'TIMEOUT_MAX',
           'Event', 'Lock', 'RLock', 'Semaphore', 'BoundedSemaphore', 'Thread',
           'Timer', 'ThreadError',
           'setprofile', 'settrace', 'local', 'stack_size']

# Rename some stuff so "from threading import *" is safe
_start_new_thread = _thread.start_new_thread
_allocate_lock = _thread.allocate_lock
get_ident = _thread.get_ident
ThreadError = _thread.error
TIMEOUT_MAX = _thread.TIMEOUT_MAX
del _thread


# Debug support (adapted from ihooks.py).
# All the major classes here derive from _Verbose.  We force that to
# be a new-style class so that all the major classes here are new-style.
# This helps debugging (type(instance) is more revealing for instances
# of new-style classes).

_VERBOSE = False

if __debug__:

    class _Verbose(object):

        def __init__(self, verbose: bool | None = None) -> None:
            if verbose is None:
                verbose = _VERBOSE
            self.__verbose = verbose

        def _note(self, format: str, *args: Any) -> None:
            if self.__verbose:
                format = format % args
                format = "%s: %s\n" % (
                    currentThread().getName(), format)
                _sys.stderr.write(format)

else:
    # Disable this when using "python -O"
    class _Verbose(object):  # type: ignore[no-redef]
        def __init__(self, verbose: bool | None = None) -> None:
            pass
        def _note(self, *args) -> None:
            pass

# Support for profile and trace hooks

_profile_hook = None
_trace_hook = None

def setprofile(func):
    global _profile_hook
    _profile_hook = func

def settrace(func):
    global _trace_hook
    _trace_hook = func

# Synchronization classes

Lock = _allocate_lock

def RLock(verbose: bool | None = None) -> _RLock:
    return _RLock(verbose)

class _RLock(_Verbose):

    def __init__(self, verbose: bool | None = None) -> None:
        _Verbose.__init__(self, verbose)
        self.__block = _allocate_lock()
        self.__owner: Thread | None = None
        self.__count = 0

    def __repr__(self):
        return "<%s(%s, %d)>" % (
                self.__class__.__name__,
                self.__owner and self.__owner.getName(),
                self.__count)

    def acquire(self, blocking: bool = True) -> bool:
        me = currentThread()
        if self.__owner is me:
            self.__count = self.__count + 1
            if __debug__:
                self._note("%s.acquire(%s): recursive success", self, blocking)
            return True
        rc = self.__block.acquire(blocking)
        if rc:
            self.__owner = me
            self.__count = 1
            if __debug__:
                self._note("%s.acquire(%s): initial success", self, blocking)
        else:
            if __debug__:
                self._note("%s.acquire(%s): failure", self, blocking)
        return rc

    __enter__ = acquire

    def release(self) -> None:
        me = currentThread()
        assert self.__owner is me, "release() of un-acquire()d lock"
        self.__count = count = self.__count - 1
        if not count:
            self.__owner = None
            self.__block.release()
            if __debug__:
                self._note("%s.release(): final release", self)
        else:
            if __debug__:
                self._note("%s.release(): non-final release", self)

    def __exit__(self, t, v, tb):
        self.release()

    # Internal methods used by condition variables

    def _acquire_restore(self, state):
        self.__block.acquire()
        self.__count, self.__owner = state
        if __debug__:
            self._note("%s._acquire_restore()", self)

    def _release_save(self):
        if __debug__:
            self._note("%s._release_save()", self)
        count = self.__count
        self.__count = 0
        owner = self.__owner
        self.__owner = None
        self.__block.release()
        return (count, owner)

    def _is_owned(self):
        return self.__owner is currentThread()


def Condition(lock: _thread.LockType | _RLock | None = None, verbose: bool | None = None) -> _Condition:
    return _Condition(lock, verbose)

class _Condition(_Verbose):

    def __init__(self, lock: _thread.LockType | _RLock | None = None, verbose: bool | None = None) -> None:
        _Verbose.__init__(self, verbose)
        if lock is None:
            lock = RLock()
        self.__lock = lock
        # Export the lock's acquire() and release() methods
        self.acquire = lock.acquire
        self.release = lock.release
        # If the lock defines _release_save() and/or _acquire_restore(),
        # these override the default implementations (which just call
        # release() and acquire() on the lock).  Ditto for _is_owned().
        try:
            self._release_save = lock._release_save  # type: ignore[method-assign, union-attr]
        except AttributeError:
            pass
        try:
            self._acquire_restore = lock._acquire_restore  # type: ignore[method-assign, union-attr]
        except AttributeError:
            pass
        try:
            self._is_owned = lock._is_owned  # type: ignore[method-assign, union-attr]
        except AttributeError:
            pass
        self.__waiters: list[_thread.LockType] = []

    def __enter__(self):
        return self.__lock.__enter__()

    def __exit__(self, *args):
        return self.__lock.__exit__(*args)

    def __repr__(self):
        return "<Condition(%s, %d)>" % (self.__lock, len(self.__waiters))

    def _release_save(self) -> Any: # pylint: disable=method-hidden
        self.__lock.release()           # No state to save

    def _acquire_restore(self, x) -> None: # pylint: disable=method-hidden
        self.__lock.acquire()           # Ignore saved state

    def _is_owned(self) -> bool: # pylint: disable=method-hidden
        # Return True if lock is owned by currentThread.
        # This method is called only if __lock doesn't have _is_owned().
        if self.__lock.acquire(False):
            self.__lock.release()
            return False
        else:
            return True

    def wait(self, timeout: float | None = None) -> None:
        assert self._is_owned(), "wait() of un-acquire()d lock"
        waiter = _allocate_lock()
        waiter.acquire()
        self.__waiters.append(waiter)
        saved_state = self._release_save()
        try:    # restore state no matter what (e.g., KeyboardInterrupt)
            if timeout is None:
                waiter.acquire()
                if __debug__:
                    self._note("%s.wait(): got it", self)
            else:
                # Balancing act:  We can't afford a pure busy loop, so we
                # have to sleep; but if we sleep the whole timeout time,
                # we'll be unresponsive.  The scheme here sleeps very
                # little at first, longer as time goes on, but never longer
                # than 20 times per second (or the timeout time remaining).
                endtime = _time() + timeout
                delay = 0.0005 # 500 us -> initial delay of 1 ms
                while True:
                    gotit = waiter.acquire(False)
                    if gotit:
                        break
                    remaining = endtime - _time()
                    if remaining <= 0:
                        break
                    delay = min(delay * 2, remaining, .05)
                    _sleep(delay)
                if not gotit:
                    if __debug__:
                        self._note("%s.wait(%s): timed out", self, timeout)
                    try:
                        self.__waiters.remove(waiter)
                    except ValueError:
                        pass
                else:
                    if __debug__:
                        self._note("%s.wait(%s): got it", self, timeout)
        finally:
            self._acquire_restore(saved_state)

    def notify(self, n: int = 1) -> None:
        assert self._is_owned(), "notify() of un-acquire()d lock"
        __waiters = self.__waiters
        waiters = __waiters[:n]
        if not waiters:
            if __debug__:
                self._note("%s.notify(): no waiters", self)
            return
        self._note("%s.notify(): notifying %d waiter%s", self, n,
                   n!=1 and "s" or "")
        for waiter in waiters:
            waiter.release()
            try:
                __waiters.remove(waiter)
            except ValueError:
                pass

    def notifyAll(self) -> None:
        self.notify(len(self.__waiters))


def Semaphore(*args, **kwargs):
    return _Semaphore(*args, **kwargs)

class _Semaphore(_Verbose):

    # After Tim Peters' semaphore class, but not quite the same (no maximum)

    def __init__(self, value=1, verbose=None):
        assert value >= 0, "Semaphore initial value must be >= 0"
        _Verbose.__init__(self, verbose)
        self.__cond = Condition(Lock())
        self.__value = value

    def acquire(self, blocking=1):
        rc = False
        self.__cond.acquire()
        while self.__value == 0:
            if not blocking:
                break
            if __debug__:
                self._note("%s.acquire(%s): blocked waiting, value=%s",
                           self, blocking, self.__value)
            self.__cond.wait()
        else:
            self.__value = self.__value - 1
            if __debug__:
                self._note("%s.acquire: success, value=%s",
                           self, self.__value)
            rc = True
        self.__cond.release()
        return rc

    __enter__ = acquire

    def release(self):
        self.__cond.acquire()
        self.__value = self.__value + 1
        if __debug__:
            self._note("%s.release: success, value=%s",
                       self, self.__value)
        self.__cond.notify()
        self.__cond.release()

    def __exit__(self, t, v, tb):
        self.release()


def BoundedSemaphore(*args, **kwargs):
    return _BoundedSemaphore(*args, **kwargs)

class _BoundedSemaphore(_Semaphore):
    """Semaphore that checks that # releases is <= # acquires"""
    def __init__(self, value=1, verbose=None):
        _Semaphore.__init__(self, value, verbose)
        self._initial_value = value

    def release(self):
        if self._Semaphore__value >= self._initial_value:
            raise ValueError("Semaphore released too many times")
        return _Semaphore.release(self)


def Event(*args, **kwargs):
    return _Event(*args, **kwargs)

class _Event(_Verbose):

    # After Tim Peters' event class (without is_posted())

    def __init__(self, verbose=None):
        _Verbose.__init__(self, verbose)
        self.__cond = Condition(Lock())
        self.__flag = False

    def isSet(self):
        return self.__flag

    def set(self):
        self.__cond.acquire()
        try:
            self.__flag = True
            self.__cond.notifyAll()
        finally:
            self.__cond.release()

    def clear(self):
        self.__cond.acquire()
        try:
            self.__flag = False
        finally:
            self.__cond.release()

    def wait(self, timeout=None):
        self.__cond.acquire()
        try:
            if not self.__flag:
                self.__cond.wait(timeout)
        finally:
            self.__cond.release()

# Active thread administration
_active_limbo_lock = _allocate_lock()
_active: dict[int, Thread] = {}    # maps thread id to Thread object
_limbo = {}


# Main class for threads

class Thread(_Verbose):

    __initialized = False
    # Need to store a reference to sys.exc_info for printing
    # out exceptions when a thread tries to use a global var. during interp.
    # shutdown and thus raises an exception about trying to perform some
    # operation on/with a NoneType
    __exc_info = _sys.exc_info

    # Set to True when the _shutdown handler is registered as atexit function.
    # Protected by _active_limbo_lock.
    __registered_atexit = False

    def __init__(
        self,
        group: None = None,
        target: Callable[..., object] | None = None,
        name: object = None,
        args: Iterable[Any] = (),
        kwargs: Mapping[str, Any] | None = None,
        verbose: bool | None = None,
        daemon: bool | None = None,
    ) -> None:
        assert group is None, "group argument must be None for now"
        _Verbose.__init__(self, verbose)
        if kwargs is None:
            kwargs = {}
        self.__target = target
        self.__name = str(name or _newname())
        self.__args = args
        self.__kwargs = kwargs
        if daemon is not None:
            self.__daemonic = daemon
        else:
            self.__daemonic = self._set_daemon()
        self.__started = False
        self.__stopped = False
        self.__block = Condition(Lock())
        self.__initialized = True
        # sys.stderr is not stored in the class like
        # sys.exc_info since it can be changed between instances
        self.__stderr = _sys.stderr

    def _set_daemon(self) -> bool:
        # Overridden in _MainThread and _DummyThread
        return currentThread().isDaemon()

    def __repr__(self):
        assert self.__initialized, "Thread.__init__() was not called"
        status = "initial"
        if self.__started:
            status = "started"
        if self.__stopped:
            status = "stopped"
        if self.__daemonic:
            status = status + " daemon"
        return "<%s(%s, %s)>" % (self.__class__.__name__, self.__name, status)

    def start(self) -> None:
        assert self.__initialized, "Thread.__init__() not called"
        assert not self.__started, "thread already started"
        if __debug__:
            self._note("%s.start(): starting thread", self)
        _active_limbo_lock.acquire()
        _limbo[self] = self

        # If we are starting a non-daemon thread, we need to call join() on it
        # when the interpreter exits.  Python will call _shutdown() on the
        # built-in threading module automatically, but not on our module.
        if not self.__daemonic and not Thread.__registered_atexit:
            _atexit.register(_shutdown)
            Thread.__registered_atexit = True

        _active_limbo_lock.release()
        _start_new_thread(self.__bootstrap, ())
        self.__started = True
        _sleep(0.000001)    # 1 usec, to let the thread run (Solaris hack)

    def run(self) -> None:
        if self.__target:
            self.__target(*self.__args, **self.__kwargs)

    def __bootstrap(self) -> None:
        try:
            self.__started = True
            _active_limbo_lock.acquire()
            _active[get_ident()] = self
            del _limbo[self]
            _active_limbo_lock.release()
            if __debug__:
                self._note("%s.__bootstrap(): thread started", self)

            if _trace_hook:
                self._note("%s.__bootstrap(): registering trace hook", self)
                _sys.settrace(_trace_hook)
            if _profile_hook:
                self._note("%s.__bootstrap(): registering profile hook", self)
                _sys.setprofile(_profile_hook)

            try:
                self.run()
            except SystemExit:
                if __debug__:
                    self._note("%s.__bootstrap(): raised SystemExit", self)
            except:
                if __debug__:
                    self._note("%s.__bootstrap(): unhandled exception", self)
                # If sys.stderr is no more (most likely from interpreter
                # shutdown) use self.__stderr.  Otherwise still use sys (as in
                # _sys) in case sys.stderr was redefined since the creation of
                # self.
                if _sys:
                    _sys.stderr.write("Exception in thread %s:\n%s\n" %
                                      (self.getName(), _format_exc()))
                else:
                    # Do the best job possible w/o a huge amt. of code to
                    # approximate a traceback (code ideas from
                    # Lib/traceback.py)
                    exc_type, exc_value, exc_tb = self.__exc_info()  # type: ignore[misc]
                    try:
                        self.__stderr.write("Exception in thread " + self.getName() +
                            " (most likely raised during interpreter shutdown):\n")
                        self.__stderr.write("Traceback (most recent call last):\n")
                        while exc_tb:
                            self.__stderr.write('  File "%s", line %s, in %s\n' %
                                (exc_tb.tb_frame.f_code.co_filename,
                                    exc_tb.tb_lineno,
                                    exc_tb.tb_frame.f_code.co_name))
                            exc_tb = exc_tb.tb_next
                        self.__stderr.write("%s: %s\n" % (exc_type, exc_value))
                    # Make sure that exc_tb gets deleted since it is a memory
                    # hog; deleting everything else is just for thoroughness
                    finally:
                        del exc_type, exc_value, exc_tb
            else:
                if __debug__:
                    self._note("%s.__bootstrap(): normal return", self)
        finally:
            self.__stop()
            try:
                self.__delete()
            except:
                pass

    def __stop(self) -> None:
        self.__block.acquire()
        self.__stopped = True
        self.__block.notifyAll()
        self.__block.release()

    def __delete(self) -> None:
        "Remove current thread from the dict of currently running threads."

        # Notes about running with dummy_thread:
        #
        # Must take care to not raise an exception if dummy_thread is being
        # used (and thus this module is being used as an instance of
        # dummy_threading).  dummy_thread.get_ident() always returns -1 since
        # there is only one thread if dummy_thread is being used.  Thus
        # len(_active) is always <= 1 here, and any Thread instance created
        # overwrites the (if any) thread currently registered in _active.
        #
        # An instance of _MainThread is always created by 'threading'.  This
        # gets overwritten the instant an instance of Thread is created; both
        # threads return -1 from dummy_thread.get_ident() and thus have the
        # same key in the dict.  So when the _MainThread instance created by
        # 'threading' tries to clean itself up when atexit calls this method
        # it gets a KeyError if another Thread instance was created.
        #
        # This all means that KeyError from trying to delete something from
        # _active if dummy_threading is being used is a red herring.  But
        # since it isn't if dummy_threading is *not* being used then don't
        # hide the exception.

        _active_limbo_lock.acquire()
        try:
            try:
                del _active[get_ident()]
            except KeyError:
                if 'dummy_threading' not in _sys.modules:
                    raise
        finally:
            _active_limbo_lock.release()

    def join(self, timeout: float | None = None) -> None:
        assert self.__initialized, "Thread.__init__() not called"
        assert self.__started, "cannot join thread before it is started"
        assert self is not currentThread(), "cannot join current thread"
        if __debug__:
            if not self.__stopped:
                self._note("%s.join(): waiting until thread stops", self)
        self.__block.acquire()
        try:
            if timeout is None:
                while not self.__stopped:
                    self.__block.wait()
                if __debug__:
                    self._note("%s.join(): thread stopped", self)
            else:
                deadline = _time() + timeout
                while not self.__stopped:
                    delay = deadline - _time()
                    if delay <= 0:
                        if __debug__:
                            self._note("%s.join(): timed out", self)
                        break
                    self.__block.wait(delay)
                else:
                    if __debug__:
                        self._note("%s.join(): thread stopped", self)
        finally:
            self.__block.release()

    def getName(self) -> str:
        assert self.__initialized, "Thread.__init__() not called"
        return self.__name

    def setName(self, name: object) -> None:
        assert self.__initialized, "Thread.__init__() not called"
        self.__name = str(name)

    def is_alive(self):
        assert self.__initialized, "Thread.__init__() not called"
        return self.__started and not self.__stopped

    isAlive = is_alive

    def isDaemon(self) -> bool:
        assert self.__initialized, "Thread.__init__() not called"
        return self.__daemonic

    def setDaemon(self, daemonic):
        assert self.__initialized, "Thread.__init__() not called"
        assert not self.__started, "cannot set daemon status of active thread"
        self.__daemonic = daemonic

    name = property(getName, setName)
    daemon = property(isDaemon, setDaemon)

# The timer class was contributed by Itamar Shtull-Trauring

def Timer(*args, **kwargs):
    return _Timer(*args, **kwargs)

class _Timer(Thread):
    """Call a function after a specified number of seconds:

    t = Timer(30.0, f, args=[], kwargs={})
    t.start()
    t.cancel() # stop the timer's action if it's still waiting
    """

    def __init__(self, interval, function, args=[], kwargs={}):
        Thread.__init__(self)
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.finished = Event()

    def cancel(self):
        """Stop the timer if it hasn't finished yet"""
        self.finished.set()

    def run(self):
        self.finished.wait(self.interval)
        if not self.finished.isSet():
            self.function(*self.args, **self.kwargs)
        self.finished.set()

# Special thread class to represent the main thread
# This is garbage collected through an exit handler

class _MainThread(Thread):

    def __init__(self) -> None:
        Thread.__init__(self, name="MainThread")
        self._Thread__started = True
        _active_limbo_lock.acquire()
        _active[get_ident()] = self
        _active_limbo_lock.release()

    def _set_daemon(self):
        return False

    def _exitfunc(self):
        self._Thread__stop()
        t = _pickSomeNonDaemonThread()
        if t:
            if __debug__:
                self._note("%s: waiting for other threads", self)
        while t:
            t.join()
            t = _pickSomeNonDaemonThread()
        if __debug__:
            self._note("%s: exiting", self)
        self._Thread__delete()


# Dummy thread class to represent threads not started here.
# These aren't garbage collected when they die, nor can they be waited for.
# If they invoke anything in threading.py that calls currentThread(), they
# leave an entry in the _active dict forever after.
# Their purpose is to return *something* from currentThread().
# They are marked as daemon threads so we won't wait for them
# when we exit (conform previous semantics).

class _DummyThread(Thread):

    def __init__(self) -> None:
        Thread.__init__(self, name=_newname("Dummy-%d"), daemon=True)

        # Thread.__block consumes an OS-level locking primitive, which
        # can never be used by a _DummyThread.  Since a _DummyThread
        # instance is immortal, that's bad, so release this resource.
        del self._Thread__block  # type: ignore[attr-defined]

        self._Thread__started = True
        _active_limbo_lock.acquire()
        _active[get_ident()] = self
        _active_limbo_lock.release()

    def _set_daemon(self):
        return True

    def join(self, timeout=None):
        assert False, "cannot join a dummy thread"


# Global API functions

def current_thread() -> Thread:
    try:
        return _active[get_ident()]
    except KeyError:
        ##print "current_thread(): no current thread for", get_ident()
        return _DummyThread()

currentThread = current_thread

def active_count():
    _active_limbo_lock.acquire()
    count = len(_active) + len(_limbo)
    _active_limbo_lock.release()
    return count

activeCount = active_count

def enumerate():
    _active_limbo_lock.acquire()
    active = list(_active.values()) + list(_limbo.values())
    _active_limbo_lock.release()
    return active

#from thread import stack_size

# Create the main thread object,
# and make it available for the interpreter
# (Py_Main) as threading._shutdown.

_main_thread = _MainThread()
_shutdown = _main_thread._exitfunc

def _pickSomeNonDaemonThread():
    for t in enumerate():
        if not t.isDaemon() and t.isAlive():
            return t
    return None

def main_thread():
    """Return the main thread object.
    In normal conditions, the main thread is the thread from which the
    Python interpreter was started.
    """
    return _main_thread

# get thread-local implementation, either from the thread
# module, or from the python fallback

## try:
##     from thread import _local as local
## except ImportError:
##     from _threading_local import local
