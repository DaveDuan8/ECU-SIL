r"""
mts_check.py
------------

**Checks after MTS Crashdumps, Errors and Exception in \*.xlog files.**

**Features:**
    - Printing of Error Statistic Output from HPCErrorDB (Oracle)
    - Scanning of a given Folder for Chrashdumps and xlog-Error File Entries.
    - Scanning xlog-Error files for MTS Errors, Exceptions and ...
    - Writing all found errors into the Oracle Error DB.

**UseCase:**
    Typically used as SubTask in the MTSTaskFactory for error checking.

**Usage:**

    - `C:\\>python mts_check.py check \\\\LIFS010\\hpc\\liss006\\3511_MFC3B0_JointSim\\2_Output\\T00008`
    - `C:\\>python mts_check.py stat 3511`
    - |  scan for db file and add rec file mapping entries:
      | `C:\\>python mts_check.py check \\\\LIFS010\\hpc\\liss006\\3511_MFC3B0_JointSim -d`

Parameters
----------
    check \<folder\>
        The given Input Folder URL which is used to scan after some errornous stuff.
    stat \<jobid\>
        JobId which must be used for getting the Error info out from the Oracle DB.

"""
# pylint: disable=C0413
# - import Python modules ---------------------------------------------------------------------------------------------
from __future__ import print_function
from os import walk, listdir, chmod, unlink
from os.path import join, isdir, expandvars, basename
from fnmatch import fnmatch
from stat import S_IWRITE
from re import search as research, match
from tempfile import mktemp
from xml.sax import make_parser, SAXParseException
from collections import OrderedDict, defaultdict
from hashlib import sha256
from configparser import ConfigParser
from six import iteritems, PY2
try:
    from pefile import PE, DIRECTORY_ENTRY
except Exception:
    PE = None

# - import HPC modules ------------------------------------------------------------------------------------------------
from ..rdb.error_db import ErrorDB
from ..rdb.sqlite_defs import create_sqlite
from ..core.exitcodes import ExitCodes
from ..core.dicts import DefDict
from ..core.logger import DummyLogger, get_logger
from ..core.tds import HPC_STORAGE_MAP, DEFAULT_HEAD_NODE
from ..core import error
from .parser import XlogHandler

# - defines -----------------------------------------------------------------------------------------------------------
LOGGER_NAME = 'MTSCheck:'
CORRUPT_FIX = "<!--appended by HPC -->\n</LogEntryList>\n</ErrorLog>\n"

# treat following (regex) log entries with a specific exit code and map to an error level (-> XlogHandler.levels)
# fallback for other levels
ERR_MAPPING = DefDict({})
# crash mappings
ERR_MAPPING[0] = OrderedDict((  # Exceptions are misspelled same way, with a singleton S !!!
    (r'^ACCESS_VIOLATION$', (error.ERR_APP_CRASH_ACCESS_VIOLATION, 0)),
    (r'^ARRAY_BOUNDS_EXCEEDED', (error.ERR_APP_CRASH_ARRAY_BOUNDS_EXCEEDED, 0)),
    (r'^BREAKPOINT', (error.ERR_APP_CRASH_BREAKPOINT, 0)),
    (r'^FLT_DIVIDE_BY_ZERO', (error.ERR_APP_CRASH_FLT_DIVIDE_BY_ZERO, 0)),
    (r'^FLT_INVALID_OPERATION', (error.ERR_APP_CRASH_FLT_INVALID_OPERATION, 0)),
    (r'^GUARD_PAGE', (error.ERR_APP_CRASH_GUARD_PAGE, 0)),
    (r'^ILLEGAL_INSTRUCTION', (error.ERR_APP_CRASH_ILLEGAL_INSTRUCTION, 0)),
    (r'^INT_DIVIDE_BY_ZERO', (error.ERR_APP_CRASH_INT_DIVIDE_BY_ZERO, 0)),
    (r'^INT_OVERFLOW', (error.ERR_APP_CRASH_INT_OVERFLOW, 0)),
    (r'^INVALID_HANDLE', (error.ERR_APP_CRASH_INVALID_HANDLE, 0)),
    (r'^PRIV_INSTRUCTION', (error.ERR_APP_CRASH_PRIV_INSTRUCTION, 0)),
    (r'^SINGLE_STEP', (error.ERR_APP_CRASH_SINGLE_STEP, 0)),

    # basst: using multiple lines for the same error in different languages is done by intend
    #        as lines get too long using a single statement
    (r'^An invalid parameter was passed to a C runtime function.', (error.ERR_APP_CRASH_INVALID_PARAMETER, 0)),
    (r'^An invalid parameter was passed to a service or function.', (error.ERR_APP_CRASH_INVALID_PARAMETER, 0)),
    (r'^An eine C-Laufzeitfunktion wurde ein ung', (error.ERR_APP_CRASH_INVALID_PARAMETER, 0)),
    (r'^Un param.*tre non valide', (error.ERR_APP_CRASH_INVALID_PARAMETER, 0)),
    (r'^The system detected an overrun of a stack-based buffer', (error.ERR_APP_CRASH_STACK_BUFFER_OVERRUN, 0)),
    (r'Fatal Application Exit', (error.ERR_APP_CRASH_FATAL_APP_EXIT, 0)),
    (r'Sortie d_application irr', (error.ERR_APP_CRASH_FATAL_APP_EXIT, 0)),
    (r'Anwendungsbeendung', (error.ERR_APP_CRASH_FATAL_APP_EXIT, 0)),
    (r'The activation context being deactivated', (error.ERR_APP_CRASH_THREAD_ACTIVATION_CONTEXT, 0)),
    # can also be used for empty error messages
    (r'.*', (error.ERR_MTS_CRASH_DUMP_FOUND, 0)),
))

# exception mappings
ERR_MAPPING[1] = OrderedDict((
    (r'InvalidOperation', (error.ERR_APP_FP_EXCEPTION_INVALID_OP, 1)),
    (r'DivisionByZero|Zero Divide', (error.ERR_APP_FP_EXCEPTION_DIVISION_BY_ZERO, 1)),
    (r'Overflow', (error.ERR_APP_FP_EXCEPTION_OVERFLOW, 1)),

    # following definitions have not yet been seen by the time now
    # basst: no unit test cases available as real examples not found
    (r'Underflow', (error.ERR_APP_FP_EXCEPTION_UNDERFLOW, 1)),
    (r'Inexact', (error.ERR_APP_FP_EXCEPTION_INEXACT, 1)),
    (r'DenormalOperation', (error.ERR_APP_FP_EXCEPTION_DENORMAL_OP, 1)),
    (r'StackCheck', (error.ERR_APP_FP_EXCEPTION_STACK_CHECK, 1)),

    # basst: following found in different error logs during a search on results
    (r'Far scan peak lists are different', (error.ERR_APP_EXC_FAR_SCAN_PEAK_ERROR, 1)),
    (r'Near scan peak lists are different', (error.ERR_APP_EXC_NEAR_SCAN_PEAK_ERROR, 1)),
    (r'Peak error block=.*index=.*', (error.ERR_APP_EXC_PEAK_ERROR_AT_POSITION, 1)),
    (r'0xC0000005|Acces.*Violation', (error.ERR_APP_EXC_ACCESS_VIOLATION, 1)),
    (r'Inconsistent data structure. The following performance counters will be skipped.',
     (error.ERR_APP_EXC_INCONSISTENT_DATA_STRUCTURE, 1)),
    (r'Configuration file:.*does not exist', (error.ERR_APP_EXC_CONFIG_OF_MO_MISSING, 1)),
    (r'error.*assert', (error.ERR_APP_EXC_MO_CODE_ERROR, 1)),
    (r'A BMW Radome correction is done in this Simulation', (error.ERR_APP_EXC_BMW_RADOME_CORRECTION, 1)),
    # ('An exception occured and a crash report', (error.ERR_APP_EXC_UNKNOWN, 1)),
    (r'An unhandled exception occured', (error.ERR_APP_EXC_UNHANDLED_EXCEPTION, 1)),
    (r'No GPU success msg after ', (error.ERR_MTS_GPU_EXEC, 1)),

    # basst modified this to a known state
    (r'0x80000003|Unknown', (error.ERR_APP_EXC_UNKNOWN_EXCEPTION, 1)),

    (r'.*', (error.ERR_APP_EXC_UNKNOWN, 1))
))

# error mappings
ERR_MAPPING[2] = OrderedDict((
    (r'0x00000040 The specified network name is no longer available\.', (error.ERR_APP_ERR_NETWORK_UNAVAILABLE, 1)),
    (r'(Recording is corrupted, offset = \d+)|(Read request beyond the end of the file)|'
     r'(Found \d+ corrupted record-package\(s\) starting at)|'
     r'(The recording contains a corrupted control section at offset: )', (error.ERR_APP_ERR_RECORDING_CORRUPT, 1)),
    (r'(Recording reader plugin failed to open file)|(No matching reader plugin found for file: )|'
     r'(Failed to open [A-Za-z0-9]+ file )', (error.ERR_MTS_READ_REC_FAILED, 1)),
    (r'(Connection to GPU server could not be established)|(Error in GPU model execution)',
     (error.ERR_INFRASTRUCTURE_GPU_EXEC, 1)),
    (r'format error: not a valid MDF block', (error.ERR_MTS_INVALID_BLOCK, 1)),
    (r'MTS will exit due to lack of memory', (error.ERR_MTS_LOW_VIRT_MEM, 1)),
    (r'Failed to add merge candidate recording', (error.ERR_MTS_MERGE_REC, 1)),
))

# warning mappings
ERR_MAPPING[4] = OrderedDict((
    (r'Cannot open or read configuration from file .*', (error.ERR_MTS_READ_CONFIG, 1)),
))

# information mappings
ERR_MAPPING[5] = OrderedDict((
    (r'Recovering navigation data and data source information from recording file\.',
     (error.ERR_MTS_RECOVERING_DATA, 1)),
    (r'Output file was created successfully.', (error.ERR_MTS_OUTPUT_CREATED, 1)),
))

# debug mappings
ERR_MAPPING[6] = OrderedDict((
    (r'The application has failed to start because its side-by-side configuration is incorrect',
     (error.ERR_MTS_ERR_SIDE_BY_SIDE, 1)),  # Please see the application event log for more detail
))

IGNORE_MAPPING = DefDict({})
# ignore certain errors in case other things happen
IGNORE_MAPPING[4] = OrderedDict((
    (r'Output file was created successfully', [error.ERR_APPLICATION_IO_IDLE, error.ERR_MTS_UNSPECIFIED_ERROR_FOUND],),
))


# - functions ---------------------------------------------------------------------------------------------------------
def mts_log_check(**kwargs):  # pylint: disable=R0912,R0914,R0915,R1260
    r"""
    scan given Input Folder for MTS Chrashdumps and xlog-Files.
    Analyse the Files, and return dedicated infos.
    => used by the starter

    :keyword \**kwargs:
        * *folder* (``str``): input folder to check crash xml or xlog files
        * *exitcodes* (``ExitCodes``): exit code object
        * *level* (``int``): limit reporting to certain level
        * *log_corrupts* (``bool``): log corrupt log files, default: True

    :return: error code
    :rtype: int
    """
    cmdcall = kwargs.get("cmdline", False)
    logger = kwargs["logger"] = kwargs.get("logger", DummyLogger(cmdcall))

    if "exitcodes" not in kwargs:
        dbase, created = kwargs.get("db", None), False
        if dbase is None:
            dbase = create_sqlite(mktemp(".sqlite", "hpc_"))
            created = True
        xcodes = ExitCodes(db=dbase)
        if created:
            unlink(dbase)
    else:
        xcodes = kwargs["exitcodes"]

    err_items, err_cnt = {}, {}
    founds = defaultdict(lambda: 0)
    try:
        xfiles = []
        fldr = expandvars(kwargs["folder"])
        if isdir(fldr):
            for (path_, _, files) in walk(kwargs["folder"]):
                xfiles.extend([join(path_, f) for f in files
                               if match(r"(?i)((.*crash.*|\d{2}(\d{2}_){3}(_\d{2}){3}'\d{3}\-\d{3})\.xml|.*\.xlog)$",
                                        f)])
        else:
            xfiles.append(fldr)

        if not xfiles:
            xcodes(error.ERR_MTS_NO_XLOG_AVAILABLE)
            if cmdcall:
                print("no x-files found")
                return xcodes.error
            logger.error("no xlog found! -> %d", error.ERR_MTS_NO_XLOG_AVAILABLE)
            return {}, DefDict(0), False

        if cmdcall:
            print("{} x-files found".format(len(xfiles)))

        xlog = XlogHandler(**kwargs)
        parser = make_parser()
        parser.setContentHandler(xlog)
        parser.setErrorHandler(xlog)  # we have all in one
        old_prio = 999

        for fname in xfiles:
            for i in range(2):
                xlog.reset()
                if i == 0:
                    logger.info("parsing %s", basename(fname))
                try:
                    with open(fname, "rb") as xfl:
                        parser.parse(xfl)
                except SAXParseException as sex:
                    if i == 0 and fnmatch(basename(fname), "errmon_*.xlog"):
                        with open(fname, "a") as xfl:
                            xfl.write(CORRUPT_FIX)
                        logger.info("needed to fix xml footer.")
                        continue
                    if kwargs.get("log_corrupts", True):
                        logger.error("corrupt XML %s: %s @ line: %d:%d", fname, sex.getMessage(),
                                     sex.getLineNumber(), sex.getColumnNumber())
                        xcodes(error.ERR_MTS_CORRUPT_CRASH_FOUND)
                break

        # pre-add level counters (defaults to 0 at start)
        for lev in range(len(XlogHandler.levels)):
            err_cnt[lev] = 0

        # iterate finally
        for lev, lname in enumerate(XlogHandler.levels):  # pylint: disable=R1702
            for res in getattr(xlog, lname + 's'):
                # we're mapping the logs here, the lower the code, the more important
                nerror, nlev, rep = _filter_desc(res.err_desc, lev)
                if rep:
                    msg = "found {}: {}".format(nerror, xcodes.explain(nerror))
                    founds[msg] += 1
                    if founds[msg] <= 1:
                        logger.warning(msg)
                        xcodes(nerror)
                if nlev <= kwargs.get("level", 1):
                    if not rep:
                        xcodes(XlogHandler.codes[nlev])
                    if not cmdcall:
                        chk = sha256()
                        chk.update("{}{}{}{}".format(nlev, res.err_code, res.err_desc, res.err_src).encode())
                        if chk.hexdigest() in err_items:
                            err_items[chk.hexdigest()]['cnt'] += res.count
                        else:
                            err_items[chk.hexdigest()] = {'type': nlev, 'code': res.err_code, 'desc': res.err_desc,
                                                          'src': res.err_src, 'time': res.time, 'mts': res.mts_ts,
                                                          'cnt': 1}
                    elif xcodes.prio() < old_prio:
                        print("found higher prio'ed error: {} ({})".format(xcodes.error, xcodes.desc))
                        old_prio = xcodes.prio()
                err_cnt[nlev] += 1

                # todo: rewind / remove it once MTS solved the exe-hang....
                for pat, ignerr in iteritems(IGNORE_MAPPING[lev]):
                    if xcodes.error in ignerr and research(pat, res.err_desc):
                        for code in ignerr:
                            xcodes.reprioritize(code)
                            logger.info("suppressing exitcode %d as related %s at TS %s found: %s.", code,
                                        XlogHandler.levels[lev], str(res.time), res.err_desc)
    except Exception as _ex:
        pass

    for msg, cnt in iteritems(founds):
        if cnt > 1:
            logger.warning("message '%s' repeated %d times.", msg, cnt)

    if cmdcall:
        logger.info("returning error {} ({})".format(xcodes.error, xcodes.desc))
        return xcodes.error

    return list(err_items.values()), err_cnt, True


def mts_check(**kwargs):  # pylint: disable=R0912,R0914,R0915,R1260
    r"""
    Scan given Input Folder for MTS Chrashdumps and xlog-Files.
    Analyse the Files, and store dedicated infos inside the DB.

    :keyword \**kwargs:
        * *headnode* (``str``): HPC head node name, default: DEFAULT_HEAD_NODE
        * *folder* (``str``): input folder to check crash xml or xlog files
        * *use_print* (``bool``): checker should use print instead of logger
        * *logger* (``Logger``): use logger given if given
        * *level* (``int``): limit reporting to certain level
        * *log_corrupts* (``bool``): log corrupt log files, default: True
        * *verbose* (``bool``): print logs additionally (be a bit more verbose)

    :return: error code
    :rtype: int
    """
    input_folder = kwargs["folder"]
    if "logger" in kwargs:
        logger = get_logger(LOGGER_NAME, [kwargs["logger"].handlers[-1].stream, True])
    else:
        logger = DummyLogger(kwargs.get("use_print", False))\
            if kwargs.get("use_print", False) else get_logger(LOGGER_NAME)

    try:
        mtc = research(r'(?i)(.*\\(\d*)_.*\\0?(1_Input|2_Output))\\T(\d+)', input_folder)
        if mtc is None or len(mtc.groups()) < 4:
            logger.error('Path %s does not fit into path pattern!', input_folder)
            return error.ERR_HPC_WRONG_ARG

        jobid = int(mtc.group(2))
        taskid = int(mtc.group(4))
        head_node = kwargs.get("head_node", DEFAULT_HEAD_NODE)
        logger.debug('headnode: %s, jobid: %d, taskid: %d', head_node, jobid, taskid)

        db = kwargs.get("db", HPC_STORAGE_MAP[head_node][3])
        err_db = ErrorDB(head_node, jobid=jobid, mode='w', logger=logger, db=db)
        xcodes = ExitCodes(db=db)

        xfiles = []
        for (path_, _, files) in walk(input_folder):
            xfiles.extend([join(path_, f) for f in files
                           if match(r"(?i)((.*crash.*|\d{2}(\d{2}_){3}(_\d{2}){3}'\d{3}\-\d{3})\.xml|.*\.xlog)$", f)])

        if len(xfiles) == 0:
            logger.error("no xlogs found!")
            xcodes(error.ERR_MTS_NO_XLOG_AVAILABLE)

        xlog = XlogHandler(logger)
        parser = make_parser()
        parser.setContentHandler(xlog)
        parser.setErrorHandler(xlog)  # we have all in one

        for fname in xfiles:
            for i in range(2):
                xlog.reset()

                logger.debug('Parsing File: %s', fname)
                try:
                    args = {"mode": "rb"} if PY2 else {"mode": "r", "encoding": 'utf-8-sig'}
                    with open(fname, **args) as xfl:
                        parser.parse(xfl)
                except SAXParseException as sex:
                    if i == 0 and fnmatch(basename(fname), "errmon_*.xlog"):
                        with open(fname, "a") as xfl:
                            xfl.write(CORRUPT_FIX)
                        logger.info("needed to fix xml footer.")
                        continue

                    logger.error("XML File Corrupt: %s @ line %d, column %d!",
                                 sex.getMessage(), sex.getLineNumber(), sex.getColumnNumber())
                    if kwargs.get("log_corrupts", True):
                        xcodes(error.ERR_MTS_CORRUPT_CRASH_FOUND)
                break

        # pre-add level counters (defaults to 0 at start)
        for lev in range(len(XlogHandler.levels)):
            err_db.add_count(taskid, lev, 0)

        # iterate finally
        for lev, lname in enumerate(XlogHandler.levels):
            scnt, fcnt = 0, -1
            for fcnt, res in enumerate(getattr(xlog, lname + 's')):
                # we're mapping the logs here, the lower the code, the more important
                nerror, nlev, rep = _filter_desc(res.err_desc, lev)
                if rep:
                    xcodes(nerror)
                if nlev <= kwargs.get("level", 1):
                    if not rep:
                        xcodes(XlogHandler.codes[nlev])
                    err_db.add_item(taskid, nlev, res.err_code, res.err_desc, res.err_src, 0,
                                    res.time, res.mts_ts, res.count)
                    scnt += 1
                else:  # just add the count
                    err_db.add_count(taskid, nlev)
            if fcnt >= 0:
                msg, log = 'found %d %s(s)' % (fcnt + 1, lname), logger.debug
                if scnt > 0:
                    msg += (' and saving %d to HPC DB' % scnt)
                    log = logger.info
                log(msg)

        if len(xfiles) == 0:
            logger.info("Scully, no x-files in folder: %s", input_folder)
        elif kwargs.get("verbose", False):
            logger.info("Logs:")
            logger.info("type / count / code / desc / src / mts")
            logger.info("=" * 100)
            frmt = "%s / %5d / %10s / %s / %s / %d"
            err_items = err_db.items(taskid)
            for i in err_items:
                logger.info(frmt, i)
            if len(err_items) == 0:
                logger.info("no item details available!")
        if not kwargs.get("dry_run", False):
            err_db.commit_items(kwargs.get("purge", False))

    except Exception as exc:
        logger.error(str(exc))
        return error.ERR_HPC_DATABASE

    if err_db:
        err_db.close()

    logger.debug("returning %d to OS", xcodes.error)
    return xcodes.error


def _filter_desc(desc, lev):
    """
    check if desc is one of those we need to care about

    :param str desc: description
    :param int lev: level of mapping

    :return: error code, level and success state
    :rtype: tuple
    """
    for pat, emap in iteritems(ERR_MAPPING[lev]):
        if research(pat, desc):
            return emap[0], emap[1], True
    return error.ERR_OK, lev, False


def mts_recheck(**kwargs):
    r"""
    scan given Input Folder for MTS Chrashdumps and xlog-Files.
    Analyse the Files, and store dedicated infos inside the DB.

    :keyword \**kwargs:
        * *headnode* (``str``): HPC head node name, default: DEFAULT_HEAD_NODE
        * *jobrange* (``str``): range of jobid's to take care of

    :return: always 0
    :rtype: int
    """
    jobs = []
    for i in kwargs["jobrange"].split(','):
        if '-' in i:
            rng = i.split('-')
            jobs.extend([str(k) for k in range(int(rng[0]), 1 + int(rng[-1]))])
        else:
            jobs.append(i.strip())

    head = kwargs.get("head_node", DEFAULT_HEAD_NODE).split('.')[0]
    if kwargs.get("exitcode", None) is not None:
        from win32com.client import Dispatch  # pylint: disable=C0415
        sched = Dispatch("Microsoft.Hpc.Scheduler.Scheduler")
        sched.Connect(head)
    else:
        sched = None

    basefldr = join(HPC_STORAGE_MAP[head][1], "hpc", head)
    margs = {"head_node": head, "use_print": kwargs.get('use_print', False), "purge": True}
    cnt = 0
    for i in [k for k in sorted(listdir(basefldr)) if k.split('_')[0] in jobs]:
        if sched is not None:
            job = sched.OpenJob(int(i.split('_')[0]))
            tasks = job.GetTaskList(None, None, False)
            tasks = {'T%05d' % i: tasks.Item(i).ExitCode for i in range(tasks.Count)}
        for k in [k for k in sorted(listdir(join(basefldr, i, '2_Output'))) if research(r'T\d{5}', k)]:
            if sched is not None and tasks[k] != kwargs.get("exitcode", None):
                continue

            print("--- starting to scan %s..." % join(basefldr, i, '2_Output', k))
            ret = mts_check(folder=join(basefldr, i, "2_Output", k), **margs)
            print("- return code: %d" % ret)
            cnt += 1

    if sched is not None:
        sched.Close()

    print("finally, we scanned %d folder" % cnt)

    return 0


def print_statistic(**kwargs):
    r"""
    open a Connection to the Oracle DB and returns the number of issues
    given by the JobId.

    :keyword \**kwargs:
        * *headnode* (``str``): HPC head node name, default: DEFAULT_HEAD_NODE
        * *jobid* (``int``): id of HPC job
        * *taskid* (``int``): id of task to query, default: None

    :return: error code
    :rtype: int
    """
    head_node = kwargs.get("head_node", DEFAULT_HEAD_NODE)
    if "logger" in kwargs:
        logger = get_logger(LOGGER_NAME, [kwargs["logger"].handlers[-1].stream, True])
    else:
        logger = (DummyLogger(kwargs.get("use_print", False)) if kwargs["use_print"] else get_logger(LOGGER_NAME))
    try:
        with ErrorDB(head_node.split('.')[0].upper(), kwargs["jobid"],
                     db=kwargs.get("db", HPC_STORAGE_MAP[head_node.split('.')[0].upper()][3])) as ora_db:
            taskid = kwargs.get("taskid", None)
            logger.info("")
            logger.info("MTS Error Log Statistic from JobID:{0: >8}".format(kwargs["jobid"]))
            logger.info("============================================")
            logger.info("--------------------------------------------")
            logger.info("Type             All Tasks    Task:{0:>8}".format(taskid))
            logger.info("--------------------------------------------")
            logger.info("Chrashdumps:  {0:>12}     {1:>12}".format(ora_db.get_num_crashes(),
                                                                   ora_db.get_num_crashes(taskid)))
            logger.info("Exceptions:   {0:>12}     {1:>12}".format(ora_db.get_num_exceptions(),
                                                                   ora_db.get_num_exceptions(taskid)))
            logger.info("Errors:       {0:>12}     {1:>12}".format(ora_db.get_num_errors(),
                                                                   ora_db.get_num_errors(taskid)))
            logger.info("Alerts:       {0:>12}     {1:>12}".format(ora_db.get_num_alerts(),
                                                                   ora_db.get_num_alerts(taskid)))
            logger.info("Infos:        {0:>12}     {1:>12}".format(ora_db.get_num_information(),
                                                                   ora_db.get_num_information(taskid)))
            logger.info("Debug:        {0:>12}     {1:>12}".format(ora_db.get_num_debugs(),
                                                                   ora_db.get_num_debugs(taskid)))
            logger.info("")

    except Exception as exc:
        logger.info(exc)
        return error.ERR_HPC_DATABASE

    return error.ERR_OK


def print_logs(**kwargs):
    r"""
    Open a connection to Oracle DB and return details of job / task.

    :keyword \**kwargs:
        * *headnode* (``str``): HPC head node name, default: DEFAULT_HEAD_NODE
        * *jobid* (``int``): id of HPC job

    :return: error code
    :rtype: int
    """
    head_node = kwargs.get("head_node", DEFAULT_HEAD_NODE)
    logger = DummyLogger(True) if kwargs.get("use_print", False) else get_logger('MTSCheck:')
    try:
        with ErrorDB(head_node.split('.')[0].upper(), kwargs["jobid"],
                     db=kwargs.get("db", "HPC"), autocommit=True) as ora_db:
            logger.info("")
            logger.info("Logs")
            logger.info("type / count / code / desc / src / time")
            logger.info("=" * 100)
            frmt = "%s / %5d / %10s / %s / %s / %s"
            loi = ora_db.get_list_of_incidents(kwargs.get("taskid", None))
            for i in loi:
                logger.info(frmt % i[1:])  # pylint: disable=W1201
            if len(loi) == 0:
                logger.info("no logs available!")
            logger.info("")

    except Exception as exc:
        logger.info(exc)
        return error.ERR_HPC_DATABASE

    return error.ERR_OK


def debug_lib_check(folder):  # pylint: disable=R1260
    """
    check a folder for towards a debug compilation

    :param str folder: folder / file to check
    :return: list of libraries being compiled in debug mode
    :rtype: list
    """
    if not PE:  # ignore silently
        return []

    def check_dll(dll):
        """check a dll"""
        try:
            pef = PE(dll, fast_load=True)
            pef.parse_data_directories(directories=[DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT'],
                                                    DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT'],
                                                    DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_BOUND_IMPORT']])
            for entry in getattr(pef, "DIRECTORY_ENTRY_IMPORT", []) + \
                    getattr(pef, "IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT", []):
                # filter for all MSVC libs
                dependency = str(entry.dll).upper()
                if "MSVC" in dependency and dependency[-5:] == "D.DLL":
                    # found a lib witch is compiled in debug mode
                    return True
        except Exception:  # frequently there's an error that not enough storage is available...
            return False

        return False

    dlls = []
    for fldr, _, files in walk(folder):
        for name in files:
            fname = join(fldr, name)
            try:
                if fnmatch(name, "*.dll") and check_dll(fname):
                    dlls.append(fname)
            except MemoryError:
                pass

    return dlls


def check_mts_ini(fname, folder=None, checkonly=False):  # pylint: disable=W0621
    """
    check if the path to the mts_measurement folder is given in the correct
    way (Prepared for HPC). Otherwise, an error is thrown.

    :param str fname: path to mts.ini file
    :param str folder: path to mts.ini
    :param bool checkonly: only check, do not manipulate
    :raises error.HpcError: once file cannot be read
    :rtype: bool
    :return: success state
    """
    cfg = ConfigParser(allow_no_value=None, delimiters=('=',))
    cfg.optionxform = str
    cfg.read(fname, 'utf_8_sig')

    if folder is not None:
        measpath = cfg.get("System", "UserPath")
        if measpath != '"..\\\\{}\\\\"'.format(folder):
            raise error.HpcError('error in mts.ini file.\n'
                                 'UserPath in section [System] must be "..\\{}\\", '
                                 'but is "..\\{}\\"'.format(folder, measpath))

    checks = (("System", "AllowMultipleInstances", "1",), ("System", "DoNotAskForConfirmation", "1",),)
    changes = False
    for chap, key, val in checks:
        if not cfg.has_option(chap, key) or cfg.get(chap, key) != val:
            cfg.set(chap, key, val)
            changes = True
    if changes and not checkonly:
        chmod(fname, S_IWRITE)
        with open(fname, "w") as cfp:
            cfg.write(cfp, False)

    return changes
