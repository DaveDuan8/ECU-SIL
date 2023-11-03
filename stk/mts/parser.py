"""
stk/mts/parser.py
-----------------

Classes for checking the mts output.

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.2 $
:contact:       $Author: Mertens, Sven (uidv7805) $ (last change)
:date:          $Date: 2015/12/07 13:48:12CET $
"""
# - import Python modules ---------------------------------------------------------------------------------------------
from xml.sax.handler import ContentHandler
from xml.dom.minidom import parse
from xml.parsers.expat import ExpatError
from re import match
from collections import OrderedDict
from hashlib import sha256
from warnings import warn

# - import STK modules ------------------------------------------------------------------------------------------------
from stk.util.helper import deprecated


# - classes -----------------------------------------------------------------------------------------------------------
class XlogHandler(ContentHandler):
    """handles xml LogEntries and extracts its data"""

    # define levels, counters and attributes
    levels = ["debug", "information", "warning", "error", "alert", "exception", "crash"]

    def __init__(self):
        """local saves for the entry
        """
        ContentHandler.__init__(self)

        self._active = -1
        self._tags = ["LogEntry", "general", "symbol"]
        self._stage = 0
        self._sdata = {}
        self._elem = None

        self._results = OrderedDict()

        self._severity = None
        self._code = None
        self._reporter = None
        self._content = None

        self._parsing_err = 0

    def startElement(self, name, attrs):
        """entry starts, we extract severity, code, reporter and content

        :param name: name of element which starts here
        :param attrs: additional attributes for element
        """
        if name == self._tags[0]:
            self._severity = XlogHandler.levels.index(attrs['Severity'].lower())
            self._content = ""
            if self._severity != 5:
                self._code = attrs['Code']
                self._reporter = attrs['Reporter']
            self._active = 0
        elif name == self._tags[1]:
            self._severity = 6
            self._content = ""
            self._active = 1
        elif self._active == 1:
            self._content = ""
            self._elem = name
        elif name == self._tags[2] and self._active != 2:
            if "srcfile" and "srcline" in attrs:
                self._severity = 6
                self._sdata["fault_module"] += (" (%s: %s)" % (attrs["srcfile"], attrs["srcline"]))
                self._active = 2
                self._stage += 1

    def endElement(self, name):
        """end of entry, in case of exception, we parse it's content

        :param name: element name which is to be checked at end tag
        """
        if self._active < 0:
            return

        if self._active == 0:
            if self._severity == 5:  # exception
                try:
                    msg = match(r"\[(.*)\][,:]\s?Exception:\s?(0x[0-9A-F]*)\s?\((.*)\)\s?at\sAddress:\s?(0x[0-9A-F]*)$",
                                self._content)
                    if msg is None:
                        msg = match(r"\[(.*)\][,:]\s?(.*)", self._content)
                        msg = [0, msg.group(2), msg.group(1)]
                    else:
                        msg = [int(msg.group(2), 16), msg.group(3), msg.group(1)]

                    eit = type('ErrorItem', (object,), {'severity': self._severity, 'err_code': msg[0],
                                                        'err_desc': msg[1], 'err_src': msg[2], 'count': 1})
                except:
                    self._parsing_err += 1
            else:
                eit = type('ErrorItem', (object,), {'severity': self._severity, 'err_code': int(self._code, 16),
                                                    'err_desc': self._content, 'err_src': self._reporter, 'count': 1})

            self._insert(eit)
            self._active = -1

        elif self._active == 1:
            if name != self._tags[1]:
                self._sdata[self._elem] = self._content
            else:
                self._stage += 1
                self._active = -1

    @property
    def parsing_problem(self):
        return self._parsing_err

    def characters(self, content):
        """save content

        :param content: content of entry we need to prepare
        """
        if self._active >= 0:
            self._content += content.strip('" \n').replace("'", r"''")

    def endDocument(self):
        """end of document"""
        if self._stage > 0:
            self._insert(type('ErrorItem', (object,), {'severity': self._severity,
                                                       'err_code': int(self._sdata.get("except_code", "-1"), 16),
                                                       'err_desc': self._sdata.get("except_descr", ""),
                                                       'err_src': self._sdata.get("fault_module", ""), 'count': 1}))

    def _insert(self, eit):
        """insert element"""
        hasher = sha256()
        hasher.update(str(eit.severity) + str(eit.err_code) + eit.err_desc + eit.err_src)
        ehash = hasher.hexdigest()

        if ehash in self._results:
            self._results[ehash].count += 1
        else:
            self._results[ehash] = eit

    def results(self, type_):
        """returns result entries of a certain type

        :param type_:    type of results to return
        :return:         list[ErrorItem, ...]
        :rtype:          list
        """
        return [r for r in self._results.values() if r.severity in (type_, -1)]

    @property
    def crash(self):
        """returns only crashs

        :return:    exceptions
        :rtype:     list[ErrorItem,...]
        """
        try:
            return self.results(6)[0]
        except:
            return None

    @property
    def exceptions(self):
        """returns only exceptions

        :return:    exceptions
        :rtype:     list[ErrorItem,...]
        """
        return self.results(5)

    @property
    def errors(self):
        """returns only errors

        :return:    found errors
        :rtype:     list[ErrorItem,...]
        """
        return self.results(3)


class ErrorItem(object):
    """Error Item Element

    :author:        Robert Hecker
    :date:          10.12.2013
    """
    def __init__(self, severity, err_code, err_desc, err_src):
        self.severity = severity
        self.err_code = err_code
        self.err_desc = err_desc
        self.err_src = err_src


class Crash(object):
    """
    Parse Crashdumps files created by MTS and provide the information due the
    ErrorItem interface.

    :author:        Robert Hecker
    :date:          10.12.2013
    """

    # define levels, counters and attributes
    levels = ["debug", "information", "warning", "error", "alert", "exception", "crash"]

    def __init__(self, filepath):
        """
        Do the Parsing of the given Chrashdump file.

        :param filepath: Url to the File to be used.
        :type filepath:  string
        :author:         Robert Hecker
        :date:           10.12.2013
        """
        self._results = []
        data = {}

        try:
            xml = parse(filepath)
            for elem in xml.getElementsByTagName("general")[0].childNodes:
                if elem is not None and elem.firstChild is not None and elem.nodeType == elem.ELEMENT_NODE:
                    data[elem.nodeName] = str(elem.firstChild.data).strip(' \r\n')

            for elem in xml.getElementsByTagName("symbol"):
                if "srcfile" and "srcline" in list(elem.attributes.keys()):
                    data["fault_module"] += (" (%s: %s)" % (elem.attributes["srcfile"].value,
                                                            elem.attributes["srcline"].value))
                    break

            self._results.append(ErrorItem(len(self.levels) - 1, int(data.get("except_code", "-1"), 16),
                                           data.get("except_descr", ""),
                                           data.get("fault_module", "")))
        except ExpatError:
            self._results.append(ErrorItem(len(self.levels) - 1, -1, "Unreadable Crashdump", filepath))

    def get_crash_info(self):
        """
        Do the real Parsing of the given file.

        :return:         the found crash information
        :rtype:          list[ErrorItem,...]
        :author:         Robert Hecker
        :date:           10.12.2013
        """
        return self._results

    @deprecated('get_crash_info')
    def GetChrashInfo(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_crash_info()


class Xlog(object):
    """
    Parse xlog files created by MTS and provide the information due the
    ErrorItem interface.

    :author:        Robert Hecker
    :date:          10.12.2013
    """

    # define levels, counters and attributes
    levels = ["debug", "information", "warning", "error", "alert", "exception", "crash"]

    def __init__(self, filepath):
        """
        Do the Parsing of the given *.xlog file.

        :param filepath: Url to the File to be used.
        :type filepath:  string
        :author:         Robert Hecker
        :date:           10.12.2013
        """
        self._results = []  # level, ErrorCode, ErrorDesc, ErrorSource

        try:
            for elem in parse(filepath).getElementsByTagName("LogEntry"):
                lev = self.levels.index(elem.getAttribute("Severity").lower())
                if lev == 5:  # exception
                    try:
                        msg = match(
                            r"\[(.*)\][,:]\s?Exception:\s?(0x[0-9A-F]*)\s?\((.*)\)\s?at\sAddress:\s?(0x[0-9A-F]*)$",
                            elem.firstChild.data.strip('" ').replace("'", r"''")).groups()
                        self._results.append(ErrorItem(lev, int(msg[1], 16), msg[3], msg[0]))
                    except:
                        msg = match(r"\[(.*)\][,:]\s?(.*)",
                                    elem.firstChild.data.strip('" ').replace("'", r"''")).groups()
                        self._results.append(ErrorItem(lev, 0, msg[1], msg[0]))
                else:
                    self._results.append(ErrorItem(lev, int(elem.getAttribute("Code"), 16),
                                                   elem.firstChild.data.strip('" ').replace("'", r"''"),
                                                   elem.getAttribute("Reporter")))
        except ExpatError:
            self._results.append(ErrorItem(-1, -1, "Unreadable xlog", filepath))

    def get_exceptions(self):
        """
        Return all found exceptions in the xlog file.

        :return:         the found exceptions
        :rtype:          list[ErrorItem,...]
        :author:         Robert Hecker
        :date:           10.12.2013
        """
        return [r for r in self._results if r.severity in (5, -1)]

    def get_errors(self):
        """
        Return all found errors in the xlog file.

        :return:         the found errors
        :rtype:          list[ErrorItem,...]
        :author:         Robert Hecker
        :date:           10.12.2013
        """
        return [r for r in self._results if r.severity in (3, -1)]

    @deprecated('get_errors')
    def GetErrors(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_errors()

    @deprecated('get_exceptions')
    def GetExceptions(self):  # pylint: disable=C0103
        """deprecated"""
        warn('Method GetExceptions() is deprecated, please use get_exceptions() instead', stacklevel=2)
        return self.get_exceptions()


"""
CHANGE LOG:
-----------
$Log: parser.py  $
Revision 1.2 2015/12/07 13:48:12CET Mertens, Sven (uidv7805) 
adding more docu and renicing scanner
Revision 1.1 2015/04/23 19:04:37CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/mts/project.pj
Revision 1.13 2015/02/09 18:26:59CET Ellero, Stefano (uidw8660)
Removed all mts based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Feb 9, 2015 6:27:00 PM CET]
Change Package : 301800:1 http://mks-psad:7002/im/viewissue?selection=301800
Revision 1.12 2015/01/13 16:29:43CET Mertens, Sven (uidv7805)
renice
--- Added comments ---  uidv7805 [Jan 13, 2015 4:29:44 PM CET]
Change Package : 294954:1 http://mks-psad:7002/im/viewissue?selection=294954
Revision 1.11 2015/01/13 15:14:40CET Mertens, Sven (uidv7805)
fix for changed measapp output
--- Added comments ---  uidv7805 [Jan 13, 2015 3:14:41 PM CET]
Change Package : 294954:1 http://mks-psad:7002/im/viewissue?selection=294954
Revision 1.10 2014/11/12 12:18:36CET Mertens, Sven (uidv7805)
update for hex numbers a bit a more exact
Revision 1.9 2014/10/09 17:21:25CEST Mertens, Sven (uidv7805)
extension exception parsing by a comma (new format?)
--- Added comments ---  uidv7805 [Oct 9, 2014 5:21:27 PM CEST]
Change Package : 270505:1 http://mks-psad:7002/im/viewissue?selection=270505
Revision 1.8 2014/06/27 14:19:51CEST Mertens, Sven (uidv7805)
reverting Xlog class
--- Added comments ---  uidv7805 [Jun 27, 2014 2:19:51 PM CEST]
Change Package : 244394:1 http://mks-psad:7002/im/viewissue?selection=244394
Revision 1.7 2014/06/27 13:30:35CEST Mertens, Sven (uidv7805)
add new XlogHandler class based on sax
--- Added comments ---  uidv7805 [Jun 27, 2014 1:30:35 PM CEST]
Change Package : 244394:1 http://mks-psad:7002/im/viewissue?selection=244394
Revision 1.6 2014/03/24 21:08:09CET Hecker, Robert (heckerr)
Adapted code to python 3.
--- Added comments ---  heckerr [Mar 24, 2014 9:08:09 PM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.5 2014/03/20 17:04:53CET Hecker, Robert (heckerr)
Removed Typing Error.
Revision 1.4 2014/03/16 21:55:53CET Hecker, Robert (heckerr)
added pylintrc.
--- Added comments ---  heckerr [Mar 16, 2014 9:55:54 PM CET]
Change Package : 225494:1 http://mks-psad:7002/im/viewissue?selection=225494
Revision 1.3 2014/02/24 16:05:12CET Mertens, Sven (uidv7805)
check for data and firstChild adapted because there could be missing infos...
--- Added comments ---  uidv7805 [Feb 24, 2014 4:05:13 PM CET]
Change Package : 219925:1 http://mks-psad:7002/im/viewissue?selection=219925
Revision 1.2 2014/02/13 16:46:54CET Hecker, Robert (heckerr)
catching Attribute Error Exception.
--- Added comments ---  heckerr [Feb 13, 2014 4:46:54 PM CET]
Change Package : 218906:1 http://mks-psad:7002/im/viewissue?selection=218906
Revision 1.1 2013/12/10 19:37:12CET Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/04_Engineering/
    stk/mts/project.pj
"""
