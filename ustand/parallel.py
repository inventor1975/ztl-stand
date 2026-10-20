"""PARALLEL JUDGING (2026-10-11, the curator's "хорошо" — after blind test 5: four authors cut their design space
by hand; a design costs 0.4 s to minutes, the designs are independent, the machine has the cores).

The judging loops are NOT changed. What runs in parallel is the pure, per-design work the loop would do anyway,
computed AHEAD in the loop's own order by worker processes (fork), and handed to the loop in that order:

    for x in prefetch(fn, n):      # x == fn(i) for i = 0, 1, ..., n-1 — exactly what the loop would compute

With JOBS == 1 (the default) fn(i) is computed right here, lazily, as before. A loop that stops early (the first
EARNED design) closes the iterator and the workers are terminated; work they did beyond is thrown away. Workers
never start pools of their own (JOBS is 1 inside them).
"""
from __future__ import annotations

import multiprocessing as mp
import signal
from contextlib import contextmanager

JOBS = [1]
STATE = {}          # what the worker functions read: set by the loop before the pool forks


def _init():
    JOBS[0] = 1
    signal.signal(signal.SIGTERM, signal.SIG_DFL)      # a worker just dies; the stop belongs to the main process
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:                                                # and dies with it, even when the main process is killed
        import ctypes                                   # outright (2026-10-11: four orphans left after a kill -9)
        ctypes.CDLL("libc.so.6").prctl(1, signal.SIGTERM)          # PR_SET_PDEATHSIG
    except OSError:
        pass


@contextmanager
def prefetch(fn, n):
    """A context giving an iterator of fn(0), fn(1), ... fn(n-1) in order (see the module's text)."""
    if JOBS[0] <= 1 or n < 2:
        yield (fn(i) for i in range(n))
        return
    pool = mp.get_context("fork").Pool(min(JOBS[0], n), initializer=_init)
    try:
        yield pool.imap(fn, range(n), chunksize=1)
    finally:
        pool.terminate()
        pool.join()


def iterate(fn, n):
    """prefetch as a plain generator: the loop takes next() per design; closing it (or dropping it) ends the pool."""
    with prefetch(fn, n) as it:
        yield from it
