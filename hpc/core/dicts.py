"""
dicts.py
--------

core module holding specific dictionaries for Job environment settings and a default dict specific
"""
# - import Python modules ----------------------------------------------------------------------------------------------
from sys import version_info
from os import unlink, environ
from os.path import exists
from simplejson import dump, load
from six import iteritems, PY2

if PY2:
    from types import StringTypes
else:
    StringTypes = (str,)

# - import HPC modules -------------------------------------------------------------------------------------------------
from .md5 import create_from_string
from ..version import VERSION

# - defines ------------------------------------------------------------------------------------------------------------
WRAP_EXE, BSIG_CHK, CNCL_CMD, USR_EXMAP = "wrapexe", "bsig_check", "cncl_cmd", "exit_map"
NOTIFY_START, NOTIFY_STOP = "notify_on_start", "notify_on_completion"
TOUT_DIR, TLOG_DIR = "out_dir", "log_dir"

TASK_DEFAULTS = {NOTIFY_START: False, NOTIFY_STOP: False, WRAP_EXE: [], TOUT_DIR: None, TLOG_DIR: None,
                 BSIG_CHK: True, CNCL_CMD: None, USR_EXMAP: {}}


# - classes / functions ------------------------------------------------------------------------------------------------
class JobDict(object):  # pylint: disable=R0902
    """interfacing local HPC sqlite DB"""

    def __init__(self, **kwargs):
        """
        init essentials

        :param kwargs: optional arguments
        """
        self._task = None
        self._sub_idx, self._sub_lst = 0, []
        self._fname = kwargs.get("fp")

        self._mode = kwargs.pop('mode', 'r')
        if self._mode == 'r':
            with open(self._fname) as fp:
                json = load(fp)

            self._job = json["job"]  # job dict
            self._cfg = json["cfg"]  # config dict
            self._tsk = json["tsk"]  # task dict
            self._stk = json["stk"]  # sub task dict
            self._wrp = json.get("wrp")  # wrap dict
            self._pri = json.get("prios")  # priority dict

            if self._wrp:
                for v in self._tsk.values():
                    if v.get("wrapexe") is not None:
                        v["wrapexe"] = self._wrp[v["wrapexe"]]

                for v in self._stk.values():
                    if v.get("wrapexe") is not None:
                        v["wrapexe"] = self._wrp[v["wrapexe"]]
        else:
            self._mode = 'w'

            self._job = dict(kwargs)
            self._job.update({"masterid": environ.get("MASTERID"), "orig_loc": environ.get("ORIG_LOC")})
            self._cfg = {}  # config dict
            self._tsk = {}  # task dict
            self._stk = {}  # sub task dict
            self._sth = {}  # sub task hashed lookup
            self._wrp = []  # wrapper's list
            self._pri = {}  # priority dict

    def __len__(self):
        """
        :return: number of tasks we have
        :rtype: int
        """
        return len(self._tsk)

    @property
    def subtask_len(self):
        """
        :return: length of subtasks
        :rtype: int
        """
        return len(self._stk)

    def __enter__(self):
        """with JobEnv(...) as job"""
        return self

    def __exit__(self, *args):
        """close db at least"""
        if len(args) == 3:  # an exception never happens :), well, maybe when testing intended
            return

        fname = args[0] if len(args) == 1 else self._fname
        if self._mode == 'w':
            if exists(fname):
                unlink(fname)
            with open(fname, 'w') as fp:
                dump({"job": self._job, "cfg": self._cfg, "tsk": self._tsk, "stk": self._stk, "wrp": self._wrp,
                      "ver": VERSION, "prios": self._pri}, fp, indent=2)

    close = __exit__

    def __getitem__(self, task):
        """
        support a call, so that we could set the task and iterate, e.g.

        with JobEnv(...) as job:
            for item in job(1):  # iterate over all subtasks of taskid 1
                print item.taskid, item.subtaskid

            for item in job:  # iterate over all tasks and subtasks
                print item.taskid, item.subtaskid

        :param int task: set the task to iterate over
        :return: self
        :rtype: self
        :raises IndexError: once task item is not found
        """
        if task is not None and 0 < int(task) <= len(self._tsk):
            self._task = task
            return self

        raise IndexError("no such task: {}".format(task))

    def __iter__(self):
        """iterate over subtasks"""
        self._sub_idx, self._sub_lst = 0, self._tsk[self._task]['stk']
        return self

    def next(self):
        """
        :return: next subtask information
        :rtype: dict
        :raises StopIteration: once iteration is at its end
        """
        if self._sub_idx >= len(self._sub_lst):
            self._task = None  # reset when iteration finishes
            raise StopIteration

        subid = self._sub_lst[self._sub_idx]
        stk = self._stk[str(subid)]
        space = DefDict(subid=subid, **stk)
        space.simcfg = self._cfg.get(stk["cfg"])  # pylint: disable=W0201
        self._sub_idx += 1
        return space

    if version_info >= (3, 0):
        __next__ = next

    def append(self, **kwargs):
        """
        append a subtask

        :keyword kwargs: details about the subtask
        :return: index of subtask and re-usage flag
        :rtype: tuple
        """
        cfg, hsh = kwargs.pop("simcfg", None), None
        if cfg:
            cfg = dict(cfg)
            hsh = create_from_string(str(cfg))
            self._cfg[hsh] = cfg
        wrp = kwargs.pop("wrapexe", None)
        if wrp:
            kwargs["wrapexe"] = self._add_wrap(wrp)

        kwargs["cfg"] = hsh
        hsh = create_from_string(str(kwargs))
        if hsh in self._sth:
            return self._sth[hsh], True

        stno = len(self._stk)
        self._stk[stno] = kwargs
        self._sth[hsh] = stno

        return stno, False

    def add(self, **kwargs):
        """
        add a task

        :keyword kwargs: details about the task
        """
        taskno = kwargs.pop("taskno")
        wrp = kwargs.pop("wrapexe", None)
        if wrp:
            kwargs["wrapexe"] = self._add_wrap(wrp)
        self._tsk[taskno] = kwargs

    def _add_wrap(self, wrap):
        """add a wrap item"""
        try:
            return self._wrp.index(wrap)
        except ValueError:
            self._wrp.append(wrap)
            return len(self._wrp) - 1

    def task(self, task, item, default=None):
        """get task items"""
        if default is None and item in TASK_DEFAULTS:
            default = TASK_DEFAULTS[item]

        return self._tsk[task].get(item, default)

    def __getattr__(self, item):
        """get job attribute"""
        try:
            return self._job[item]
        except KeyError:
            raise AttributeError

    @property
    def prios(self):
        """return priorities"""
        return self._pri

    @prios.setter
    def prios(self, value):
        """set the prio dict"""
        self._pri = value

    def job_rel(self, value):
        """set job release command"""
        self._job["job_rel_cmd"] = value


class DefDict(dict):
    """I'm a default space dict, but with my own getattr method."""

    __defs__ = ['_default', '_hasdflt', '_nondef']

    def __init__(self, *args, **kwargs):
        """
        init with any parameter

        :param args: only default name is supported as first unnamed argument
        :param kwargs: *default*: value if not specified, *nondef*: value returned not for those withing here
        """
        if args:
            dict.__setattr__(self, "_default", args[0])
            dict.__setattr__(self, "_hasdflt", True)
        elif "default" in kwargs:
            dict.__setattr__(self, "_default", kwargs.pop("default"))
            dict.__setattr__(self, "_hasdflt", True)
        else:
            dict.__setattr__(self, "_default", None)
            dict.__setattr__(self, "_hasdflt", False)

        dict.__setattr__(self, "_nondef", kwargs.pop("nondef", []))
        dict.__init__(self, **kwargs)
        if len(args) == 2 and isinstance(args[1], dict):  # args must be strings, but also allow e.g. int as keys
            for k, v in iteritems(args[1]):
                self[k] = v

    def __str__(self):
        """
        my formated representation

        :return: string representation
        :rtype: str
        """
        return "<{} default: {}, dict={}>"\
            .format(self.__class__.__name__, self._default if self._hasdflt else "(none)",
                    ", ".join(["{}={}".format(k, v) for k, v in self.items()]))

    __repr__ = __str__

    def __getattr__(self, value):
        """
        get the value from item

        :param object value: item to find
        :return: value for item
        :rtype: object
        """
        return self[value]

    def __setattr__(self, key, value):
        """
        set an inner attribute

        :param object key: key
        :param object value: value
        """
        self[key] = value

    def __missing__(self, item):
        """
        in case a key is missing, return default

        :param object item: item to find inside _nondef
        :return: default if in _default
        :rtype: object
        :raises AttributeError: in case item is not in _nondef
        """
        if self._hasdflt and item not in DefDict.__defs__:
            return self._default

        raise AttributeError

    def get(self, item, default=None):
        """get an item"""
        if item in self and self[item] is not None:
            return self[item]

        if default is not None:
            return default

        return self[item]

    def items(self):
        """
        iterate over my items, except internals

        :return: iterator
        :rtype: iterator
        """
        for i in self.keys():
            yield i, self[i]

    iteritems = items

    def keys(self):
        """
        implement keys not to return

        :return: keys
        :rtype: dict_keys
        """
        for i in dict.__iter__(self):
            if i not in DefDict.__defs__:
                yield i

    __iter__ = keys


def toint(text):
    """
    convert text to int, take only starting numbers

    :param str text: input text
    :return: int from text
    :rtype: int
    """
    number = None
    if text == "min":
        return -2 ** 31
    if text == "max":
        return 2 ** 31 - 1

    mul = 1
    for i, k in enumerate(text):
        try:
            if i == 0 and k in ['-', '+']:
                mul = -1 if k == '-' else 1
                v = 0
            else:
                v = int(k)
            number = v if i == 0 else (10 * number + v)
        except ValueError:
            break
    return None if number is None else (mul * number)


def tointlist(x):
    """
    flatten inter array

    :param list x: e.g. [min..-10,0,5,10..max]
    :return: integer values from
    :rtype: list[int] | iterable
    """
    if isinstance(x, StringTypes):
        if ',' in x:
            return [toint(i) for i in x.split(',')]
        if ".." in x:
            i, k = x.split('..')
            if PY2:
                return xrange(toint(i), toint(k) + 1)  # pylint: disable=E0602
            return range(toint(i), toint(k) + 1)
        return [toint(x)]
    if hasattr(x, "__iter__"):
        return [toint(i) for i in x]

    return x


# def memoize(func):
#     """memorize a functions output from input => https://www.python-course.eu/python3_memoization.php"""
#     memo = {}
#
#     def helper(x):
#         """help"""
#         if x not in memo:
#             memo[x] = func(x)
#         return memo[x]
#     return helper
