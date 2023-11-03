"""
logger.py
---------

DummyLogger: uses just print / stderr
get_logger: wrapper for Python's logger for HPC stuff
"""
# - import Python modules ----------------------------------------------------------------------------------------------
from __future__ import print_function
import sys
from os import environ
from logging import getLogger, StreamHandler, Formatter, DEBUG, WARN
from warnings import warn, filterwarnings
from time import time, gmtime, ctime
from re import compile as recmp
from functools import wraps
from keyring import get_password, set_password, delete_password, errors
from six import PY2
if PY2:
    from types import StringTypes
else:
    StringTypes = (str,)

# - HPC imports --------------------------------------------------------------------------------------------------------
from .dicts import DefDict

# - defines ------------------------------------------------------------------------------------------------------------
DATEFORMAT = '%Y-%m-%d %H:%M:%S'
Formatter.converter = gmtime


# - classes and functions ----------------------------------------------------------------------------------------------
class DummyLogger(object):  # pylint: disable=R0903
    """dummy logger"""

    def __init__(self, use_print=False):
        """use real print or not"""
        self._use_print = False if hasattr(use_print, "__call__") else use_print
        self._store = use_print if hasattr(use_print, "__call__") else None

    def _dummy(self, data, *xtra):
        """if store, store!"""
        if self._store:
            if xtra:  # sometimes the ducks are stupid and we need to ignore E1102
                self._store(str(data) % xtra)  # pylint: disable=E1102
            else:
                self._store(str(data))  # pylint: disable=E1102

    @staticmethod
    def _print(text, *args):
        """print text"""
        print(str(text) % args)

    @staticmethod
    def _perr(text, *args):
        """print to stderr"""
        sys.stderr.write(str(text) % args + "\n")

    def flush(self):
        """flush me dummily"""

    def __getattr__(self, which):
        """for each missing, return dummy"""
        if self._use_print:
            return self._perr if which == "error" else self._print

        return self._dummy


class ListStream(object):
    """grab stdout from a call"""

    def __init__(self, **kwargs):
        """additional dict to take over"""
        self.data = []
        self._read = False
        self._kwargs = kwargs

    def write(self, txt):
        """grab text into internal data"""
        for i in txt.split('\n'):
            if i:
                self.data.append(i)

    def read(self, *_):
        """return read in data"""
        data = "\n".join(str(i) for i in self.data) if not self._read else None
        self._read = True
        return data

    def seek(self, _):
        """rewind"""
        self._read = False

    def flush(self):
        """flush me"""

    def __enter__(self):
        """go"""
        sys.stdout = self
        sys.stderr = self
        return self

    @staticmethod
    def __exit__(*_):
        """stop and reset"""
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

    close = __exit__

    def __getattr__(self, item):
        """whatever we gave"""
        return self._kwargs[item]


class StdFormatter(Formatter):
    """colorize the format for HTML output"""

    LEVEL_FRMT = '{:^8}'
    COLORS = DefDict("DEBUG",
                     {40: LEVEL_FRMT.format("ERROR"),
                      30: LEVEL_FRMT.format("WARNING"),
                      20: LEVEL_FRMT.format("INFO")})

    def format(self, record):
        """overwrite default"""
        record.levelname = self.COLORS[record.levelno]

        return Formatter.format(self, record)


class ColoredFormatter(StdFormatter):
    """colorize the format for HTML output"""

    LEVEL_FRMT = '<span style="background-color: {}">{:^8}</span>'
    LOG_COLOR = '<span style="color: {}">{}</span>'
    COLORS = DefDict(LEVEL_FRMT.format("blue", "DEBUG"),
                     {40: LEVEL_FRMT.format("red", "ERROR"),
                      30: LEVEL_FRMT.format("orange", "WARNING"),
                      20: LEVEL_FRMT.format("yellow", "INFO")})

    def __init__(self, *args, **kwargs):
        """init the Formatter"""
        StdFormatter.__init__(self, *args, **kwargs)

        self._cmpl = recmp(r"starting\ssubtask\s(\d+)\s\(id \d+\)")
        self._http = recmp(r"(.*)(https?:\/\/[-a-zA-Z0-9:%._\+~#?&\//=()]{1,256})(\b.*)")

    def format(self, record):
        """overwrite default"""
        msg = StdFormatter.format(self, record)

        if hasattr(record, "color"):
            msg = msg.replace(record.message, self.LOG_COLOR.format(record.color, record.message))
        else:
            mtc = self._cmpl.search(msg)
            if mtc:
                msg = '{}<span style="background-color: LINEN" id="stid{}">{}</span>{}'\
                    .format(msg[:mtc.start()], int(mtc.groups()[0]) - 1, msg[mtc.start():mtc.end()],
                            msg[mtc.end():])
            else:
                mtc = self._http.search(msg)
                if mtc:
                    msg = '{0}<a href="{1}">{1}</a>{2}'.format(*mtc.groups())

        return msg


def get_logger(name, strms=None, prefix="", level=2):
    """
    provide a logger with a specific name

    :param str name:   name, which should appear in the log
    :param list strms: streams to log to
    :param str prefix: prefix each message
    :param int level: log level
    :return:  object of type `logger`
    :rtype: `logger`
    """
    # Create a Logger with the specified name
    logger = getLogger(name)
    logger.propagate = False
    logger.setLevel(DEBUG if level >= 2 else WARN)

    # this is for module tests, log handlers are not cleaned up, but left behind,
    # so we initialize every time anew, but doesn't matter, as for each logger needed,
    # we're not calling get_logger frequently
    while logger.handlers:
        logger.removeHandler(logger.handlers[0])

    fmt = '%%(asctime)s.%%(msecs)03d %%(name)-15s %%(levelname)-8s %s%%(message)s' % prefix

    frmter = [StdFormatter(fmt=fmt, datefmt=DATEFORMAT), ColoredFormatter(fmt=fmt, datefmt=DATEFORMAT)]

    if strms is None:
        strms = [[sys.stdout, False]]

    for strm, frmt in strms:
        hdl = StreamHandler(strm)
        hdl.setFormatter(frmter[int(frmt)])
        logger.addHandler(hdl)

    return logger


def timeit(method):
    """
    decorate a method / function to measure execution time
    idea from https://medium.com/pythonhive/python-decorator-to-measure-the-execution-time-of-methods-fa04cb6bb36d
    """
    def timed(*args, **kwargs):
        ts = time()
        result = method(*args, **kwargs)
        te = time()
        msg = "{!s}: {:.3f} ms".format(method.__name__, (te - ts) * 1000)
        if 'logger' in kwargs:
            kwargs['logger'](msg)
        else:
            print(msg)

        return result
    return timed


def deprecated(replacement=None):
    """
    decorate functions being deprecated soon.
    It will result in a warning being emitted when function is used.

    python ::

        @deprecated  # if you just want to state that it's deprecated
        def foo():
            pass

        # or

        @deprecated('bar')  # if you want to tell a replacement (bar)
        def foo():
            pass

    :param str|property replacement: name of function / method / property to replace decorated one
    :return: inner function
    :rtype: property
    """
    def outer(func):  # pragma: no cover
        """outer call wraps message output"""
        if PY2:
            msg = "'{}' is deprecated".format(func.fget.func_name if isinstance(func, property) else func.__name__)
        else:
            msg = "'{}' is deprecated".format(func.fget.__name__ if isinstance(func, property) else func.__name__)

        if replacement is not None:
            msg += ", {}".format(replacement if isinstance(replacement, StringTypes) else replacement.__name__)
        if func.__doc__ is None:
            func.__doc__ = msg

        @wraps(func)
        def inner(*args, **kwargs):
            """inner call outputs message"""
            warn(msg, stacklevel=2)
            return func(*args, **kwargs)

        return inner

    return outer


def suppress_warnings(func):
    """
    suppress python warnings
    https://stackoverflow.com/questions/14463277/how-to-disable-python-warnings
    """

    def call_fnc(*args, **kwargs):
        """
        check and return the instance of class (already being instantiated) to suppress warnings

        :param args: std arguments to pass
        :param kwargs: xtra args to pass
        :return: function
        :rtype: object
        """
        filterwarnings("ignore")
        try:
            return func(*args, **kwargs)
        finally:
            filterwarnings("default")

    return call_fnc


class HpcPassword(object):
    """wrapper to get all users stored password"""

    def __init__(self, service="HPC"):
        """init me"""
        self._sid = service

    def __enter__(self):
        """provide with statement support"""
        return self

    def __exit__(self, *_):
        """exit"""

    def __getitem__(self, key):
        """get the secret for given key"""
        return get_password(self._sid, key)

    def __setitem__(self, key, sec):
        """set a certain secret"""
        set_password(self._sid, key, sec)

    def __delitem__(self, key):
        """delete a certain secret"""
        try:
            delete_password(self._sid, key)
        except errors.PasswordDeleteError:
            pass


def dlog(text):
    """log some debug info"""
    with open(r"\\lufs009x.li.de.conti.de\hpc\HPC_submit\sven\dlog.txt", 'a') as fp:
        fp.write("[{} @ {}] {}\n".format(ctime(), environ["COMPUTERNAME"], text))
