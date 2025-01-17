import os
import signal
import sys

import termcolor

import devtools.executor.proc_util.python.lib as proc_util


if sys.stderr.isatty():
    STOP_STR = termcolor.colored('\r' + chr(27) + '[2KStop\n', color='red', attrs=['bold'])
else:
    STOP_STR = 'Stop\n'


def create_sigint_exit_handler():
    if os.name == 'nt':
        # Become a subreaper on windows because os.kill(0, signal.SIGINT) doesn't work on this platform.
        subreaper_obj = proc_util.SubreaperApplicant()
    else:
        # Don't become subreaper on unix platforms, otherwise ya-tc won't outlast ya,
        # which is not expected for a caching daemon process.
        subreaper_obj = None

    def instant_sigint_exit_handler(*args):
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        try:
            os.kill(0, signal.SIGINT)
        except Exception:
            pass

        if subreaper_obj:
            try:
                subreaper_obj.close()
            except Exception:
                pass

        try:
            sys.stderr.write(STOP_STR)
        except Exception:
            pass

        # Force exit without processing exit handlers
        os._exit(-signal.SIGINT)

    return instant_sigint_exit_handler
