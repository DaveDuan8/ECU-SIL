"""
exitcodes.py
------------

This Module contains ExitCodes class.
"""
# - import Python modules ----------------------------------------------------------------------------------------------
from datetime import datetime

# - import HPC modules -------------------------------------------------------------------------------------------------
from .error import ERR_OK, ERR_APPLICATION_UNSPECIFIED_ERROR_FOUND, ERR_HPC_USER_CANCEL_TASK_DETECTED
from ..rdb.base import BaseDB


# - classes ------------------------------------------------------------------------------------------------------------
class ExitCodes(object):  # pylint: disable=R0902
    """exit code class"""

    def __init__(self, other=None, **kwargs):
        """retrieve exit codes"""
        self._strings = {}
        self._prios = {}
        self._error, self._warn = kwargs.get("init_code", ERR_OK), ERR_OK
        self._canceled = False
        self._skipon = []
        self._hist = []
        self._unfail = kwargs.get("unfailing", [])
        self._ignore = kwargs.get("ignore_codes", [])
        self._suppress = []

        if other is None:
            if "prio" in kwargs:
                for exc, pri, des in kwargs["prios"]:
                    self._prios[exc] = pri
                    self._strings[exc] = des
            else:
                with BaseDB(kwargs.get('db', 'HPC')) as bdb:
                    for i in bdb("SELECT EXITCODE, PRIO, DESCR FROM HPC_EXITCODES"):
                        self._prios[i[0]] = i[1]
                        self._strings[i[0]] = i[2]
        elif isinstance(other, ExitCodes):
            self._strings, self._prios, self._skipon, self._unfail, self._ignore, self._suppress = other.internals
            # take over if specified explicitly
            self._unfail = kwargs.get("unfailing", self._unfail)
            self._ignore = kwargs.get("ignore_codes", self._ignore)
        else:
            raise ValueError("not of same class!")

    def __str__(self):
        """
        :return: code and desc
        :rtype: str
        """
        return "{}: {}".format(self.error, self.desc)

    @property
    def error(self):
        """
        :return: error code
        :rtype: int
        """
        return self._error if self._error != ERR_OK else self._warn

    @property
    def state(self):
        """
        :return: state of ecode
        :rtype: str
        """
        return "Canceled" if self._canceled else ("Finished" if self._error in self._unfail else "Failed")

    @property
    def lasterror(self):
        """
        :return: last error code
        :rtype: int
        """
        if self._hist:
            return self._hist[-1][0]

        return self.error

    @property
    def history(self):
        """
        :return: error code history
        :rtype: list
        """
        return self._hist

    @property
    def desc(self):
        """
        :return: description of exitcode
        :rtype: str
        """
        return self.explain(self.error)

    def explain(self, ecode):
        """
        :param int ecode: exitcode
        :return: string representation of it
        :rtype: str
        """
        return self._strings.get(ecode, "-")

    def __call__(self, ecode):  # pylint: disable=R1260
        """
        do a repriorization

        :param int ecode: new exitcode
        """
        if ecode is None:
            self._error = ERR_OK
            self._hist = []
            return

        if isinstance(ecode, ExitCodes):
            for exc, dtm in ecode.history:
                self._priorize(exc, dtm)
        else:
            self._priorize(ecode, datetime.utcnow())

    def _priorize(self, ecode, dtime):
        """priorize the code"""
        if ecode == ERR_HPC_USER_CANCEL_TASK_DETECTED:
            self._canceled = True

        if ecode in self._ignore:
            return

        if ecode not in self._prios:
            ecode = ERR_APPLICATION_UNSPECIFIED_ERROR_FOUND
        if ecode != ERR_OK:
            self._hist.append([ecode, dtime])

        self._set_code(ecode)

    def _set_code(self, ecode):
        """set the final code to be either a warning or error"""
        if ecode in self._suppress:
            return

        if ecode in self._unfail and self.prio(ecode) <= self.prio(self._warn):
            self._warn = ecode
        elif ecode not in self._unfail and self.prio(ecode) <= self.prio(self._error):
            self._error = ecode

    def prio(self, ecode=None):
        """priority of exit code"""
        return self._prios.get(ecode, self._prios[ERR_OK])

    def reprioritize(self, ecode):
        """remove or suppress a certain exit code"""
        self._suppress.append(ecode)
        self._error, self._warn = ERR_OK, ERR_OK

        for code, _ in self._hist:
            self._set_code(code)

    @property
    def internals(self):
        """
        :return: db queried stuff to parents
        :rtype: tuple
        """
        return self._strings, self._prios, self._skipon, self._unfail, self._ignore, self._suppress

    def clear(self):
        """reset history"""
        self._hist = []
        self._error, self._warn = ERR_OK, ERR_OK
