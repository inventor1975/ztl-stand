"""A stop asked from outside (the `timeout` command's SIGTERM), seen at SAFE points only.

The signal handler only sets the flag. Raising from inside the handler interrupted whatever code ran — inside
mpmath a bare `except:` swallowed the exception and turned it into a TypeError, a STAND ERROR instead of a partial
report (2026-10-11). The stand checks the flag between designs; the checker at each fast reading.
"""

STOP = [False]


class Stopped(BaseException):
    """BaseException, so no `except Exception` of ours or of ZTL swallows it on the way up."""


def check():
    if STOP[0]:
        raise Stopped()


# INTERRUPTIBLE WINDOWS (2026-10-12, the J4 test took 398 s under `timeout 45`): a SEARCH inside ZTL
# (zimplicit.search_certificate) runs for minutes with no safe point of ours, its every reading now a case reading.
# Inside such a window the handler raises at once: the code there is ZTL's pure computation (no bare `except:`, no
# mpmath on that path — checked 2026-10-12), with no state of the stand to leave half-written.
RAISE_NOW = [0]


class interruptible:
    def __enter__(self):
        check()
        RAISE_NOW[0] += 1
        return self

    def __exit__(self, *exc):
        RAISE_NOW[0] -= 1
        return False


def on_signal(signum=None, frame=None):
    STOP[0] = True
    if RAISE_NOW[0] > 0:
        raise Stopped()
