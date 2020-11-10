# MIT License
#
# Copyright The SCons Foundation
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
# KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Serial, Parallel, and ParallelV2 classes to execute build tasks.

The Jobs class provides a higher level interface to start,
stop, and wait on jobs.
"""

import SCons.compat
import SCons.Node
import SCons.Util

from collections import deque
import os
import signal

import SCons.Errors

# The default stack size (in kilobytes) of the threads used to execute
# jobs in parallel.
#
# We use a stack size of 256 kilobytes. The default on some platforms
# is too large and prevents us from creating enough threads to fully
# parallelized the build. For example, the default stack size on linux
# is 8 MBytes.

explicit_stack_size = None
default_stack_size = 256

interrupt_msg = 'Build interrupted.'

display = SCons.Util.display


class InterruptState:
    def __init__(self):
        self.interrupted = False

    def set(self):
        self.interrupted = True

    def __call__(self):
        return self.interrupted


class Jobs:
    """An instance of this class initializes N jobs, and provides
    methods for starting, stopping, and waiting on all N jobs.
    """

    def __init__(self, num, taskmaster, remote_cache=None,
                 use_scheduler_v2=False):
        """
        Create 'num' jobs using the given taskmaster.

        If 'num' is 1 or less, then a serial job will be used,
        otherwise a parallel job with 'num' worker threads will
        be used.

        The 'num_jobs' attribute will be set to the actual number of jobs
        allocated.  If more than one job is requested but the Parallel
        class can't do it, it gets reset to 1.  Wrapping interfaces that
        care should check the value of 'num_jobs' after initialization.

        'remote_cache' can be set to a RemoteCache.RemoteCache object.

        'use_scheduler_v2' can be set to True to opt into the newer and more
        aggressive scheduler.
        """

        self.job = None

        stack_size = explicit_stack_size
        if stack_size is None:
            stack_size = default_stack_size

        try:
            if ((remote_cache and remote_cache.fetch_enabled) or
                    use_scheduler_v2):
                self.job = ParallelV2(taskmaster, num, stack_size, remote_cache)
            elif num > 1:
                self.job = Parallel(taskmaster, num, stack_size)
            self.num_jobs = num
        except NameError:
            pass

        if self.job is None:
            self.job = Serial(taskmaster)
            self.num_jobs = 1

    def run(self, postfunc=lambda: None):
        """Run the jobs.

        postfunc() will be invoked after the jobs has run. It will be
        invoked even if the jobs are interrupted by a keyboard
        interrupt (well, in fact by a signal such as either SIGINT,
        SIGTERM or SIGHUP). The execution of postfunc() is protected
        against keyboard interrupts and is guaranteed to run to
        completion."""
        self._setup_sig_handler()
        try:
            self.job.start()
        finally:
            postfunc()
            self._reset_sig_handler()

    def were_interrupted(self):
        """Returns whether the jobs were interrupted by a signal."""
        return self.job.interrupted()

    def _setup_sig_handler(self):
        """Setup an interrupt handler so that SCons can shutdown cleanly in
        various conditions:

          a) SIGINT: Keyboard interrupt
          b) SIGTERM: kill or system shutdown
          c) SIGHUP: Controlling shell exiting

        We handle all of these cases by stopping the taskmaster. It
        turns out that it's very difficult to stop the build process
        by throwing asynchronously an exception such as
        KeyboardInterrupt. For example, the python Condition
        variables (threading.Condition) and queues do not seem to be
        asynchronous-exception-safe. It would require adding a whole
        bunch of try/finally block and except KeyboardInterrupt all
        over the place.

        Note also that we have to be careful to handle the case when
        SCons forks before executing another process. In that case, we
        want the child to exit immediately.
        """
        def handler(signum, stack, self=self, parentpid=os.getpid()):
            if os.getpid() == parentpid:
                self.job.taskmaster.stop()
                self.job.interrupted.set()
            else:
                os._exit(2)

        self.old_sigint  = signal.signal(signal.SIGINT, handler)
        self.old_sigterm = signal.signal(signal.SIGTERM, handler)
        try:
            self.old_sighup = signal.signal(signal.SIGHUP, handler)
        except AttributeError:
            pass

    def _reset_sig_handler(self):
        """Restore the signal handlers to their previous state (before the
         call to _setup_sig_handler()."""

        signal.signal(signal.SIGINT, self.old_sigint)
        signal.signal(signal.SIGTERM, self.old_sigterm)
        try:
            signal.signal(signal.SIGHUP, self.old_sighup)
        except AttributeError:
            pass

class Serial:
    """This class is used to execute tasks in series, and is more efficient
    than Parallel, but is only appropriate for non-parallel builds. Only
    one instance of this class should be in existence at a time.

    This class is not thread safe.
    """

    def __init__(self, taskmaster):
        """Create a new serial job given a taskmaster.

        The taskmaster's next_task() method should return the next task
        that needs to be executed, or None if there are no more tasks. The
        taskmaster's executed() method will be called for each task when it
        is successfully executed, or failed() will be called if it failed to
        execute (e.g. execute() raised an exception)."""

        self.taskmaster = taskmaster
        self.interrupted = InterruptState()

    def start(self):
        """Start the job. This will begin pulling tasks from the taskmaster
        and executing them, and return when there are no more tasks. If a task
        fails to execute (i.e. execute() raises an exception), then the job will
        stop."""

        while True:
            task = self.taskmaster.next_task()

            if task is None:
                break

            try:
                task.prepare()
                if task.needs_execute():
                    task.execute()
            except Exception:
                if self.interrupted():
                    try:
                        raise SCons.Errors.BuildError(
                            task.targets[0], errstr=interrupt_msg)
                    except:
                        task.exception_set()
                else:
                    task.exception_set()

                # Let the failed() callback function arrange for the
                # build to stop if that's appropriate.
                task.failed()
            else:
                task.executed()

            task.postprocess()
        self.taskmaster.cleanup()


# Trap import failure so that everything in the Job module but the
# Parallel class (and its dependent classes) will work if the interpreter
# doesn't support threads.
try:
    import queue
    import threading
except ImportError:
    pass
else:
    class Worker(threading.Thread):
        """A worker thread waits on a task to be posted to its request queue,
        dequeues the task, executes it, and posts a tuple including the task
        and a boolean indicating whether the task executed successfully. """

        def __init__(self, requestQueue, resultsQueue, interrupted):
            threading.Thread.__init__(self)
            self.setDaemon(1)
            self.requestQueue = requestQueue
            self.resultsQueue = resultsQueue
            self.interrupted = interrupted
            self.start()

        def run(self):
            while True:
                task = self.requestQueue.get()

                if task is None:
                    # The "None" value is used as a sentinel by
                    # ThreadPool.cleanup().  This indicates that there
                    # are no more tasks, so we should quit.
                    break

                try:
                    if self.interrupted():
                        raise SCons.Errors.BuildError(
                            task.targets[0], errstr=interrupt_msg)
                    task.execute()
                except:
                    task.exception_set()
                    ok = False
                else:
                    ok = True

                self.resultsQueue.put((task, ok))

    class ThreadPool:
        """This class is responsible for spawning and managing worker threads."""

        def __init__(self, num, stack_size, interrupted):
            """Create the request and reply queues, and 'num' worker threads.

            One must specify the stack size of the worker threads. The
            stack size is specified in kilobytes.
            """
            self.requestQueue = queue.Queue(0)
            self.resultsQueue = queue.Queue(0)

            try:
                prev_size = threading.stack_size(stack_size*1024)
            except AttributeError as e:
                # Only print a warning if the stack size has been
                # explicitly set.
                if explicit_stack_size is not None:
                    msg = "Setting stack size is unsupported by this version of Python:\n    " + \
                        e.args[0]
                    SCons.Warnings.warn(SCons.Warnings.StackSizeWarning, msg)
            except ValueError as e:
                msg = "Setting stack size failed:\n    " + str(e)
                SCons.Warnings.warn(SCons.Warnings.StackSizeWarning, msg)

            # Create worker threads
            self.workers = []
            for _ in range(num):
                worker = Worker(self.requestQueue, self.resultsQueue, interrupted)
                self.workers.append(worker)

            if 'prev_size' in locals():
                threading.stack_size(prev_size)

        def put(self, task):
            """Put task into request queue."""
            self.requestQueue.put(task)

        def get(self):
            """Remove and return a result tuple from the results queue."""
            return self.resultsQueue.get()

        def preparation_failed(self, task):
            self.resultsQueue.put((task, False))

        def cleanup(self):
            """
            Shuts down the thread pool, giving each worker thread a
            chance to shut down gracefully.
            """
            # For each worker thread, put a sentinel "None" value
            # on the requestQueue (indicating that there's no work
            # to be done) so that each worker thread will get one and
            # terminate gracefully.
            for _ in self.workers:
                self.requestQueue.put(None)

            # Wait for all of the workers to terminate.
            #
            # If we don't do this, later Python versions (2.4, 2.5) often
            # seem to raise exceptions during shutdown.  This happens
            # in requestQueue.get(), as an assertion failure that
            # requestQueue.not_full is notified while not acquired,
            # seemingly because the main thread has shut down (or is
            # in the process of doing so) while the workers are still
            # trying to pull sentinels off the requestQueue.
            #
            # Normally these terminations should happen fairly quickly,
            # but we'll stick a one-second timeout on here just in case
            # someone gets hung.
            for worker in self.workers:
                worker.join(1.0)
            self.workers = []

    class Parallel:
        """This class is used to execute tasks in parallel, and is somewhat
        less efficient than Serial, but is appropriate for parallel builds.

        This class is thread safe.
        """

        def __init__(self, taskmaster, num, stack_size):
            """Create a new parallel job given a taskmaster.

            The taskmaster's next_task() method should return the next
            task that needs to be executed, or None if there are no more
            tasks. The taskmaster's executed() method will be called
            for each task when it is successfully executed, or failed()
            will be called if the task failed to execute (i.e. execute()
            raised an exception).

            Note: calls to taskmaster are serialized, but calls to
            execute() on distinct tasks are not serialized, because
            that is the whole point of parallel jobs: they can execute
            multiple tasks simultaneously. """

            self.taskmaster = taskmaster
            self.interrupted = InterruptState()
            self.tp = ThreadPool(num, stack_size, self.interrupted)
            self.maxjobs = num

        def start(self):
            """Start the job. This will begin pulling tasks from the
            taskmaster and executing them, and return when there are no
            more tasks. If a task fails to execute (i.e. execute() raises
            an exception), then the job will stop."""

            jobs = 0

            while True:
                # Start up as many available tasks as we're
                # allowed to.
                while jobs < self.maxjobs:
                    task = self.taskmaster.next_task()
                    if task is None:
                        break

                    try:
                        # prepare task for execution
                        task.prepare()
                    except:
                        task.exception_set()
                        task.failed()
                        task.postprocess()
                    else:
                        if task.needs_execute():
                            # dispatch task
                            self.tp.put(task)
                            jobs = jobs + 1
                        else:
                            task.executed()
                            task.postprocess()

                if not task and not jobs: break

                # Let any/all completed tasks finish up before we go
                # back and put the next batch of tasks on the queue.
                while True:
                    self.process_result()
                    jobs = jobs - 1

                    if self.tp.resultsQueue.empty():
                        break

            self.tp.cleanup()
            self.taskmaster.cleanup()

        def process_result(self):
            task, ok = self.tp.get()

            if ok:
                task.executed()
            else:
                if self.interrupted():
                    try:
                        raise SCons.Errors.BuildError(
                            task.targets[0], errstr=interrupt_msg)
                    except:
                        task.exception_set()

                # Let the failed() callback function arrange
                # for the build to stop if that's appropriate.
                task.failed()

            task.postprocess()

    class ParallelV2(Parallel):
        """
        This class is an extension of the Parallel class that provides two main
        improvements:

        1. Minimizes time waiting for jobs by fetching tasks.
        2. Supports remote caching.
        """
        __slots__ = ['remote_cache']

        def __init__(self, taskmaster, num, stack_size, remote_cache):
            super(ParallelV2, self).__init__(taskmaster, num, stack_size)

            self.remote_cache = remote_cache

        def get_next_task_to_execute(self, limit):
            """
            Finds the next task that is ready for execution. If limit is 0,
            this function fetches until a task is found ready to execute.
            Otherwise, this function will fetch up to "limit" number of tasks.

            Returns tuple with:
                1. Task to execute.
                2. False if a call to next_task returned None, True otherwise.
            """
            count = 0
            while limit == 0 or count < limit:
                task = self.taskmaster.next_task()
                if task is None:
                    return None, False

                try:
                    # prepare task for execution
                    task.prepare()
                except:
                    task.exception_set()
                    task.failed()
                    task.postprocess()
                else:
                    if task.needs_execute():
                        return task, True
                    else:
                        task.executed()
                        task.postprocess()

                count = count + 1

            # We hit the limit of tasks to retrieve.
            return None, True

        def start(self):
            fetch_response_queue = queue.Queue(0)
            if self.remote_cache:
                self.remote_cache.set_fetch_response_queue(
                    fetch_response_queue)

            jobs = 0
            tasks_left = True
            pending_fetches = 0
            cache_hits = 0
            cache_misses = 0
            cache_skips = 0
            cache_suspended = 0

            while True:
                fetch_limit = 0 if jobs == 0 and pending_fetches == 0 else 1
                if tasks_left:
                    task, tasks_left = \
                        self.get_next_task_to_execute(fetch_limit)
                else:
                    task = None

                if not task and not tasks_left and jobs == 0 and \
                        pending_fetches == 0:
                    # No tasks left, no jobs, no cache fetches.
                    break

                while jobs > 0:
                    # Break if there are no results available and one of the
                    # following is true:
                    #   1. There are tasks left.
                    #   2. There is at least one job slot open and at least one
                    #      remote cache fetch pending.
                    # Otherwise we want to wait for jobs because the most
                    # important factor for build speed is keeping the job
                    # queue full.
                    if ((tasks_left or
                            (jobs < self.maxjobs and pending_fetches > 0))
                            and self.tp.resultsQueue.empty()):
                        break

                    self.process_result()
                    jobs = jobs - 1

                    # Tasks could have been unblocked, so we should check
                    # again.
                    tasks_left = True

                while pending_fetches > 0:
                    # Trimming the remote cache fetch queue is the least
                    # important job, so we only block if there are no responses
                    # available, no tasks left to fetch, and no active jobs.
                    if ((tasks_left or jobs > 0) and
                            fetch_response_queue.empty()):
                        break

                    cache_task, cache_hit, target_infos = \
                        fetch_response_queue.get()
                    pending_fetches = pending_fetches - 1

                    if cache_hit:
                        cache_hits = cache_hits + 1
                        cache_task.executed(target_infos=target_infos)
                        cache_task.postprocess()

                        # Tasks could have been unblocked, so we should check
                        # again.
                        tasks_left = True
                    else:
                        cache_misses = cache_misses + 1
                        self.tp.put(cache_task)
                        jobs = jobs + 1

                if task:
                    # Tasks should first go to the remote cache if enabled.
                    if self.remote_cache:
                        fetch_pending, task_cacheable = \
                            self.remote_cache.fetch_task(task)
                    else:
                        fetch_pending = task_cacheable = False

                    if fetch_pending:
                        pending_fetches = pending_fetches + 1
                    else:
                        # Fetch is not pending because remote cache is not
                        # being used or the task was not cacheable.
                        #
                        # Count the number of non-cacheable tasks but don't
                        # count tasks with 1 target that is an alias or a
                        # directory with '.' as the path, because they are not
                        # actually run.
                        if (len(task.targets) > 1 or
                                not isinstance(task.targets[0],
                                               SCons.Node.Alias.Alias)):
                            if task_cacheable:
                                cache_suspended = cache_suspended + 1
                            else:
                                cache_skips = cache_skips + 1
                        self.tp.put(task)
                        jobs = jobs + 1

            # Instruct the remote caching layer to log information about
            # the cache hit rate.
            cache_count = cache_hits + cache_misses + cache_suspended
            task_count = cache_count + cache_skips
            if self.remote_cache and task_count > 0:
                reset_count = self.remote_cache.reset_count
                total_failures = self.remote_cache.total_failure_count
                hit_pct = (cache_hits * 100.0 / cache_count if cache_count
                           else 0.0)
                cacheable_pct = cache_count * 100.0 / task_count
                self.remote_cache.log_stats(
                    hit_pct, cache_count, cache_hits, cache_misses,
                    cache_suspended, cacheable_pct, cache_skips, task_count,
                    total_failures, reset_count)

            self.tp.cleanup()
            self.taskmaster.cleanup()

# Local Variables:
# tab-width:4
# indent-tabs-mode:nil
# End:
# vim: set expandtab tabstop=4 shiftwidth=4:
