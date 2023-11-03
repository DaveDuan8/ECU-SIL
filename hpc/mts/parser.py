"""
parser.py
---------

class for checking the mts output.
"""
# pylint: disable=W0702,C0103
# - import Python modules ---------------------------------------------------------------------------------------------
from xml.sax.handler import ContentHandler
from re import match, search
from collections import OrderedDict
from hashlib import sha256
from datetime import datetime as dt, timedelta
from time import gmtime, mktime, strptime
from six import PY2

# - import HPC modules ------------------------------------------------------------------------------------------------
from ..core.error import ERR_MTS_CRASH_DUMP_FOUND, ERR_MTS_LOG_EXCEPTION_FOUND, ERR_MTS_LOG_ALERT_FOUND, \
    ERR_MTS_LOG_ERROR_FOUND, ERR_MTS_LOG_WARNING_FOUND, ERR_MTS_LOG_INFO_FOUND, ERR_MTS_LOG_DEBUG_FOUND
from ..core.dicts import DefDict


# - classes -----------------------------------------------------------------------------------------------------------
class XlogHandler(ContentHandler):  # pylint: disable=R0902
    """handles xml LogEntries and extracts its data"""

    # define levels, counters and attributes
    levels = ["crash", "exception", "error", "alert", "warning", "information", "debug"]
    codes = [ERR_MTS_CRASH_DUMP_FOUND, ERR_MTS_LOG_EXCEPTION_FOUND, ERR_MTS_LOG_ERROR_FOUND, ERR_MTS_LOG_ALERT_FOUND,
             ERR_MTS_LOG_WARNING_FOUND, ERR_MTS_LOG_INFO_FOUND, ERR_MTS_LOG_DEBUG_FOUND]

    def __init__(self, logger, **kwargs):
        """local saves for the entry"""
        ContentHandler.__init__(self)
        self._logger = logger
        self._tags = ["LogEntry", "general", "symbol"]
        self._results = OrderedDict()
        self._active = -1

        self._stage = 0
        self._sdata = {}
        self._elem = None

        self._severity = None
        self._code = None
        self._reporter = None
        self._time = None
        self._content = None
        self._mts_ts = 0
        self._tm_frmt = "%d/%m/%Y-%H:%M:%S:%f"
        self._gpu, self._gpu_err = kwargs.get("gpu", False), None

    def reset(self):
        """set to default"""
        self._active = -1
        self._stage = 0
        self._sdata = {}
        self._elem = None

        self._severity = None
        self._code = None
        self._reporter = None
        self._time = None
        self._content = None
        self._mts_ts = 0

    def startElement(self, name, attrs):
        """entry starts"""
        if name == self._tags[0]:  # LogEntry
            self._severity = XlogHandler.levels.index(attrs['Severity'].lower())
            self._content = ""
            try:
                self._code = attrs['Code']
                self._reporter = str(attrs['Reporter'])
            except Exception:  # pragma: no cover
                self._code = self._reporter = ""
            self._time = (dt(*gmtime(mktime(strptime(attrs['SystemTime'], self._tm_frmt)))[:6]) +
                          timedelta(microseconds=dt.strptime(attrs['SystemTime'], self._tm_frmt).microsecond))
            self._mts_ts = int(attrs['Timestamp'])
            self._active = 0
        elif name == self._tags[1]:  # general
            self._severity = 0  # crash
            self._content = ""
            self._active = 1
        elif self._active == 1:
            self._content = ""
            self._elem = name
        elif name == self._tags[2] and self._active != 2:  # symbol
            if "srcfile" and "srcline" in attrs:
                self._severity = 0  # crash
                self._sdata["fault_module"] += (" ({}: {})".format(attrs["srcfile"], attrs["srcline"]))
                self._active = 2
                self._stage += 1

    def endElement(self, name):  # pylint: disable=R0912,R1260
        """end of entry"""
        if self._active < 0:
            return

        if self._active == 0:
            # care about special GPU message:
            if self._gpu:
                if match(r"Opened file .*\.MF4", self._content):
                    if self._gpu_err:  # raise up severity as there wasn't any GPU success before!
                        self._severity = 1
                        self._content = "No GPU success msg after '{}!'".format(self._content)
                    self._gpu_err = self._content
                elif self._gpu_err and search(r"SRepro_Reprocessing_Debug: GPU Success RTT", self._content):
                    self._gpu_err = None

            eit = DefDict(severity=self._severity, time=self._time, count=1, mts_ts=self._mts_ts)

            if self._severity > 0:  # exception and lower
                msg = search(r"\sTs:\s(\d+)\s", self._content)
                if msg is not None and len(msg.regs) > 0:  # pragma: no cover
                    eit.mts_ts = int(msg.group(1))  # update MTS timestamp if Ts given

                # Try to read xml format 1
                msg = match(r"\[(.*)\][,:]\s?Exception:\s?(0x[0-9A-F]*)\s?\((.*)\)\s?at\sAddress:\s?(0x[0-9A-F]*)$",
                            self._content)
                if msg is not None and len(msg.regs) == 4:  # pragma: no cover
                    msg = msg.groups()
                    eit.update({'err_code': int(msg[1], 16), 'err_desc': msg[2], 'err_src': msg[0]})
                else:
                    # Reading of xml format one crashed
                    # Try to read format 2
                    msg = match(r"\[(.*)\][,:]\s?(.*)", self._content)
                    if msg is not None and len(msg.regs) == 3:
                        msg = msg.groups()
                        eit.update({'err_code': 0, 'err_desc': msg[1], 'err_src': msg[0]})
                    else:
                        eit.update({'err_code': int(self._code, 16), 'err_desc': self._content,
                                    'err_src': self._reporter})
            else:  # pragma: no cover
                eit.update({'err_code': int(self._code, 16), 'err_desc': self._content, 'err_src': self._reporter})

            self._insert(eit)

            self._active = -1

        elif self._active == 1:
            if name != self._tags[1]:
                self._sdata[self._elem] = self._content
            else:
                self._stage += 1
                self._active = -1

    def characters(self, content):
        """save content"""
        if self._active >= 0:
            if PY2:
                self._content += str(content.encode('utf-8').strip('" \n').replace("'", r"''"))
            else:
                self._content += str(content.strip('" \n').replace("'", r"''"))

    def endDocument(self):
        """end of document"""
        if self._stage > 0:
            dfrmt = "%d/%m/%Y %H:%M"
            time = dt.strptime(self._sdata.get("crash_time", dt.utcnow().strftime(dfrmt)), dfrmt)
            self._insert(DefDict(severity=self._severity, err_code=int(self._sdata.get("except_code", "-1"), 16),
                                 err_desc=self._sdata.get("except_descr", ""),
                                 err_src=self._sdata.get("fault_module", ""), time=time, mts_ts=0, count=1))
            self._stage = 0

    def _insert(self, eit):
        """insert element"""
        hasher = sha256()
        key = str(eit.severity) + str(eit.err_code) + eit.err_desc + eit.err_src
        if PY2:
            hasher.update(key.decode('utf-8').encode('latin1'))
        else:
            hasher.update(key.encode())
        ehash = hasher.hexdigest()

        if ehash in self._results:
            self._results[ehash].count += 1
        else:
            self._results[ehash] = eit

    def results(self, type_):
        """
        return result entries of a certain type

        :param int type_: type of results to return
        :return: list[ErrorItem, ...]
        :rtype: list
        """
        return [r for r in list(self._results.values()) if r.severity in (type_, -1)]

    def __getattr__(self, item):
        """handle those attributes defined in levels' list"""
        item = item.rstrip('s')
        if item in XlogHandler.levels:
            try:
                return self.results(XlogHandler.levels.index(item))
            except Exception:  # pragma: no cover
                return []
        else:  # pragma: no cover
            raise AttributeError

    # those methods are taken from xml.sax.handler.ErrorHandler, they are called by the parser on problems
    @staticmethod
    def error(exception):  # pragma: no cover
        """Handle a recoverable error."""
        raise exception

    def fatalError(self, exception):
        """Handle a non-recoverable error."""
        # let's call the endDocument, as otherwise we loose data taken until now
        self.endDocument()
        raise exception

    def warning(self, exception):  # pragma: no cover
        """Handle a warning."""
        self._logger.warning(exception)
