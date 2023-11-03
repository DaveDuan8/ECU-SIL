"""
EBA Common Utils
---------------

Various helper classes and methods which are used in the EBA endurance validation.
"""
import os
import shutil
import xml.dom.minidom
from xml.etree.ElementTree import *
from collections import OrderedDict
from datetime import datetime
import time
import functools
import logging
import logging.config
import inspect
from .logger import LoggerManager
from random import shuffle
import re
from win32com.client import GetObject

__author__ = "Philipp Baust"
__copyright__ = "Copyright 2015, Continental AG"
__version__ = "$Revision: 1.26 $"
__maintainer__ = "$Author: Baust, Philipp (uidg5548) $"
__date__ = "$Date: 2018/10/30 10:36:09CET $"


_log = logging.getLogger(__name__)
_runtime_log = logging.getLogger("RUNTIME")
_deprecation_log = logging.getLogger("DEPRECATION")


#: List of HPC output directories. TODO: Add BLR locations
HPC_ROOT = [r"\\lufs003x.li.de.conti.de\hpc\LU00156VMA",
            r"\\OZFS110.oz.in.conti.de\hpc\OZAS012A",
            r"\\qhsimu.qh.us.conti.de\hpc\QHS6U5CA"]


def runtime_log(f):
    """ Decorator to log function or method execution time.

    :param f: function or method
    :return: wrapped function or method
    """
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if _runtime_log.level != logging.DEBUG:
            # if not configured bypass all the costly computations.
            return f(*args, **kwargs)
        else:
            t0 = time.clock()
            r = f(*args, **kwargs)
            t1 = time.clock()

            # Resolve params to some extend
            params = ""
            if len(args) > 1:
                params += ", ".join([str(a) for a in args[1:]])
            for k, v in kwargs.items():
                if params:
                    params += ", "
                params += "{}={}".format(k, v)

            _runtime_log.debug("{3:10.2f}us: {0:}.{1:}({2:}): "
                               .format(args[0].__class__.__name__, f.__name__, params, (t1 - t0) * 1e6))
            return r
    return wrapped


def deprecated(f):
    """ Decorator for deprecated methods to log the usage of these methods.

    :param function: method
    :return: wrapped method
    """
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if _deprecation_log.level != logging.DEBUG:
            return f(*args, **kwargs)
        else:
            current_frame = inspect.currentframe()
            frames = inspect.getouterframes(current_frame)
            caller = frames[1]
            msg = "Method is deprecated consider refactoring!"
            _deprecation_log.warning("{} ({}, line {}): {}".format(caller[3], caller[1], caller[2], msg))
            return f(*args, **kwargs)
    return wrapper


class BatchPlaylist(object):
    """ Abstraction for a batch playlist. """

    def __init__(self, path=None):
        """ Constructor.

        :param path: Path to the batch playlist
        """
        super(BatchPlaylist, self).__init__()

        # FIXME: Sections are broken

        if path:
            self._path = path
            # self._sections = {}
            self._files = self.parse()
        else:
            self._path = None
            self._files = OrderedDict()
            # self._sections = {}

    @property
    def recordings(self):
        """ Getter for the recordings in the batch playlist
        :return: list of recordings as path
        """
        return self._files.keys()

    def get_sections(self, rec):
        if rec in self._files:
            return self._files[rec]

        return None

    @property
    def path(self):
        """ Getter for the batch playlists path
        :return: full path to the bpl
        """
        return self._path

    def save(self, filename=None, no_sorting=False, randomize=False):
        """ Save th batch playlist

        :param no_sorting:
        :param filename: (Optional) target where to save the batch playlist
        :param randomize: Shuffles the rec file contents
        :return: -
        """
        if filename is not None:
            self._path = filename

        if not self._path:
            raise IOError("Neither path set nor filename given to save batch "
                          "playlist.")

        bpl_root_element = Element("BatchList")

        if no_sorting:
            recs = self._files
        elif randomize:
            r = range(len(self._files))
            shuffle(r)
            recs = []
            items = self._files.keys()
            for k in r:
                recs.append(items[k])
        else:
            recs = sorted(self._files)

        for f_path in recs:
            batch_entry = Element("BatchEntry")
            batch_entry.set("fileName", f_path)

            if any(self._files[f_path]):
                section_list = Element("SectionList")
                batch_entry.append(section_list)

                for (startTime, endTime) in self._files[f_path]:
                    section = Element("Section")
                    section.set("startTime", str(startTime))
                    section.set("endTime", str(endTime))
                    section_list.append(section)

            bpl_root_element.append(batch_entry)

        self._write_bpl(bpl_root_element, self._path)

    @classmethod
    def _write_bpl(cls, root, target):
        """ Pretty print for the XML
        :param root:
        :param target:
        :return:
        """
        ugly_str = tostring(root, encoding="UTF-8", method="xml")

        dom_xml = xml.dom.minidom.parseString(ugly_str)
        pretty_str = dom_xml.toprettyxml()

        with open(target, "w") as fh:
            fh.write(pretty_str)
        fh.close()

    def add_recording(self, recording, sections=None, relative_sections=False):
        """ Adds a recording to the bpl

        :param sections:
        :param recording: path to the recording
        :return: -
        """

        if recording.lower() not in self._files:
            self._files[recording.lower()] = []
        if sections:
            # if relative_sections:
            #     r_sections = []
            #     for (s, e) in sections:
            #         sr = "{}R".format(s)
            #         er = "{}R".format(e)
            #         r_sections.append((sr, er))
            #     self._files[recording.lower()].extend(r_sections)
            # else:

            for st, et in sections:
                self.__add_section(recording.lower(), st, et)

    def __add_section(self, rec, section_st, section_et):
        for k, (start_ts, end_ts) in enumerate(self._files[rec]):
            if start_ts <= section_st <= end_ts and start_ts <= section_et <= end_ts:
                # absorbed do nothing
                _log.debug("New is absorbed")
                return

            if section_st <= start_ts and section_et > end_ts:
                # new section is larger, replace current
                _log.debug("New absorbes current ")
                self._files[rec][k] = (section_st, section_et)
                return

            if start_ts < section_st < end_ts and section_et > end_ts:
                # overlap, new section end is later:
                _log.debug("Extending end")
                self._files[rec][k] = (start_ts, section_et)
                return

            if section_st < start_ts and start_ts < section_et < end_ts:
                # overlap, new section start is earlier:
                _log.debug("Extending start")
                self._files[rec][k] = (section_st, end_ts)
                return

        self._files[rec].append((section_st, section_et))

    def parse(self):
        """ Reads the bpl contents
        :return:
        """
        files = OrderedDict()

        if not os.path.exists(self._path):
            return files

        xml_doc = parse(self._path)
        root = xml_doc.getroot()

        for be in root.iter("BatchEntry"):
            filename = be.attrib["fileName"].lower()
            if filename in files:
                _log.warning("File already parsed '{}'".format(filename))
            else:
                files[filename] = []

            sl = be.find("SectionList")
            if sl is None:
                # no sections....
                continue

            for se in sl.iter("Section"):
                _log.debug("Has Section")

                start_time = se.attrib["startTime"]
                end_time = se.attrib["endTime"]

                # if filename not in self._sections:
                #     self._sections[filename] = []
                files[filename].append((start_time, end_time))

        return files


def normalize_measurement_path(p):
    """ Normalizes the LIFS010 and lUFS003x recording paths to the full name in lower case.
    This gurantees that lifst af recordings can be compared easily.

    :param p: rec file path
    :return: normalized rec file path
    """
    r = p.lower()

    if r.startswith(r"\\lifs010.cw01.contiwan.com"):
        r = os.path.normpath(r)
    elif r.startswith(r"\\lifs010s.cw01.contiwan.com"):
        r = os.path.normpath(r.replace(r"\\lifs010s.cw01.contiwan.com", r"\\lifs010.cw01.contiwan.com"))
    elif r.startswith(r"\\lifs010s"):
        r = os.path.normpath(r.replace(r"\\lifs010s", r"\\lifs010.cw01.contiwan.com"))
    elif r.startswith(r"\\lifs010"):
        r = os.path.normpath(r.replace(r"\\lifs010", r"\\lifs010.cw01.contiwan.com"))

    elif r.startswith(r"\\lufs003x.li.de.conti.de"):
        r = os.path.normpath(r)
    elif r.startswith(r"\\lufs003x"):
        r = os.path.normpath(r.replace(r"\\lufs003x", r"\\lufs003x.li.de.conti.de"))

    return r.lower()  # when not lifs010 recording


def recording_to_bsig_path(recording_full_path, bsig_folder, ext=".bsig", suffix=None):
    """ Computes the BSIG name from (full) recording path and BSIG folder.
    BSIG filename will be computed as <bsig_folder>/<recording_name>[<suffix>]<ext>
    This method will not check for existance.

    :param recording_full_path: Recording full path or recording name
    :param bsig_folder: Folder containing the BSIGs
    :param ext: Optional file extension. Default is '.bsig'
    :param suffix: Optional suffix for bsigname

    :return: absolute path to BSIG
    """
    rec_name = os.path.splitext(os.path.split(recording_full_path)[1])[0]
    if suffix is None:
        return os.path.join(bsig_folder, "{}{}".format(rec_name, ext))
    else:
        return os.path.join(bsig_folder, "{}_{}{}".format(rec_name, suffix, ext))


def backup_file(file_name):
    """ Generic backup of a file

    :param file_name:
    """
    if os.path.exists(file_name):
        _log.info("File '{}' already exists. Creating backup.".format(file_name))
        cur_date = datetime.now()
        name, ext = os.path.splitext(os.path.split(file_name)[1])
        tgt = os.path.join(file_name, "..",
                           "{}_backup_{:%Y%m%d_%H%M%S}.{}".format(name, cur_date, ext))
        shutil.copyfile(file_name, tgt)


class Configuration:
    """ Global singleton (actually a borg) to share global settings.
    Currently this is only used to enable disable debugging and logging globally without the need to
    modify each script.
    """

    __shared_state = None

    def __init__(self):
        """ Constructor. """
        if not Configuration.__shared_state:
            Configuration.__shared_state = self.__dict__
            self.__debug = False
            self.__verbosity_level = 0
            self.__runtime_log = False
            self.__deprecation_log = False
            self._log_configured = False
            self.__logfiles = []
        else:
            self.__dict__ = Configuration.__shared_state

    @property
    def debug(self):
        """ Indicates the script shall run in debug mode.
            Consumers of that flag should make sure to re-throw exceptions in order to get a proper
            stack trace on critical errors.

            .. note:: Current implementation of this flag will also enable runtime logging and deprecation logging
                The log level will also be increased to DEBUG (>3)

        """
        return self.__debug

    @property
    def log_files(self):
        return self.__logfiles

    @debug.setter
    def debug(self, value):
        self.__debug = value
        if value:
            self.deprecation_logging = True
            self.runtime_logging = True
            self.verbosity_level = 3  # INFO

    @property
    def verbosity_level(self):
        return self.__verbosity_level

    @verbosity_level.setter
    def verbosity_level(self, value):
        self.__verbosity_level = value

    @property
    def runtime_logging(self):
        return self.__runtime_log

    @runtime_logging.setter
    def runtime_logging(self, value):
        self.__runtime_log = value

    @property
    def deprecation_logging(self):
        return self.__deprecation_log

    @deprecation_logging.setter
    def deprecation_logging(self, value):
        self.__deprecation_log = value


def sign(v):
    """ Calculates the sign of a number. """
    if v < 0:
        return -1
    else:
        return 1


def configure_logger(filename, working_dir="."):
    """ Configures the loggers.

    :param filename: Name of the log file
    :param working_dir: Path to directory where the log files are written to.
    """
    _cfg = Configuration()

    if _cfg._log_configured:
        _log.debug("Logging already configured. Not reconfiguring..")
        return

    # Hack the log manager always adds a handler with level DEBUG, this is highly undesired.
    # Since we are already setting up a rotating file olog and a stram logger with level INFO or DEBUG depending on
    # the users desired loglevel we will remove  all handlers from the root logger
    _ = LoggerManager()
    for h in logging.root.handlers:
        logging.root.removeHandler(h)

    if not os.path.exists(os.path.abspath(working_dir)):
        os.makedirs(os.path.abspath(working_dir))

    global_config = Configuration()
    if global_config.verbosity_level >= 3:
        level = "DEBUG"
    elif global_config.verbosity_level == 2:
        level = "INFO"
    elif global_config.verbosity_level == 1:
        level = "WARNING"
    else:
        level = "ERROR"

    _cfg.log_files.append(os.path.join(working_dir, filename))
    logging_configuration = {
        "version":                  1,
        "disable_existing_loggers": False,
        "formatters":               {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            },
        },
        "handlers":                 {
            "default":  {
                "level":     level,
                "formatter": "standard",
                "class":     "logging.StreamHandler",
                "stream":    "ext://sys.stdout",
            },
            "file_log": {
                "level":       level,
                "formatter":   "standard",
                "class":       "logging.FileHandler",

                "filename":    os.path.join(working_dir, filename),
                # "maxBytes":    4 * 1024 * 1024,
                # "backupCount": 4,
            },
        },
        "loggers":                  {
            "":        {
                "handlers":  ["default", "file_log"],
                "level":     level,
                "propagate": True
            },
            "PIL.PngImagePlugin": {
                "level":     "CRITICAL",  # effectively disables, this loger talks too much
                "propagate": True
            },
            "fct.eba.common.birdeye": {
                "level":     "ERROR",  # talks too much
                "propagate": True
            },
            "fct.eba.common.bsig": {
                "level":     "CRITICAL",  # talks too much on level < INFO
                "propagate": True
            },
            "PluginFctDB": {
                "level": "ERROR",  # talks too much
                "propagate": True
            }
        }
    }

    if global_config.runtime_logging:
        _cfg.log_files.append(os.path.join(working_dir, "runtime.log"))
        logging_configuration["handlers"]["runtime_log"] = {
            "level": "DEBUG",
            "formatter": "standard",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(working_dir, "runtime.log"),
            "maxBytes": 4 * 1024 * 1024,
            "backupCount": 1,
        }

        logging_configuration["loggers"]["RUNTIME"] = {
            "handlers": ["default", "runtime_log"],
            "level": "DEBUG",
            "propagate": False
        }

    if global_config.deprecation_logging:
        logging_configuration["loggers"]["DEPRECATION"] = {
            "handlers": ["default", "file_log"],
            "level": "DEBUG",
            "propagate": False
        }

    logging.config.dictConfig(logging_configuration)
    _cfg._log_configured = True


def job_folders_by_id(job_ids, sub_directory_path=r"2_Output\_data"):
    """ Job folder discovery by ID
    :param job_ids: HPC job ID or list of ids
    :param sub_directory_path: Optional path to subdir in job folder. Default 2_output\data

    :return: Full path to the HPC share for the given id if given single number
    or list of folders for all given numbers. None in case the jobs could not be found
    """
    #
    # loc_lookup = {"delnd": "LUSS021", "inblr": "OZAS001A", "usabh": "QHS6U4CA"}
    hpc_outfolders = {
        "delnd": r"\\lufs009x.li.de.conti.de\hpc\LU00156VMA",
        "inblr": r"\\OZFS110.oz.in.conti.de\hpc\OZAS012A",
        "usabh": r"\\qhsimu.qh.us.conti.de\hpc\QHS6U5CA",
    }
    try:
        # Accelerate look up by choosing the one at your location instead of polling the world...
        root = GetObject('LDAP://rootDSE')
        srvn = 'LDAP://' + root.Get('dsServiceName')
        ntds = GetObject(srvn)
        site = GetObject(GetObject(GetObject(ntds.Parent).Parent).Parent)
        loc = re.match(r"([a-z]*)\d*", site.Get('cn').lower()).group(1)
        HPC_ROOT = [hpc_outfolders[loc]]
    except Exception as ex:  # lookup error as user is locked out???
        pass


    pat = re.compile("^(\d+)_(.+)$", re.IGNORECASE)
    results = None

    try:
        for root_folder in HPC_ROOT:
            for f in os.listdir(root_folder):
                match = pat.match(f)

                if match:
                    jid = match.group(1)
                    if isinstance(job_ids, (list, tuple)) and jid in job_ids:
                        _log.debug("Found job folder for job id '{}': {}".format(jid, f))
                        if results is None:
                            results = []

                        results.append(os.path.join(root_folder, f, sub_directory_path))
                    elif isinstance(job_ids, (str)) and jid == job_ids:
                        _log.debug("Found job folder for job id '{}': {}".format(job_ids, f))
                        return os.path.join(root_folder, f)
    except Exception as ex:
        _log.debug("Exception while Job lookup. LIFS010 might be down...")
        _log.exception(ex)

    if results is None:
        _log.error("HPC Job does not exist (any longer).")
    return results

"""
..
    LOG:
    $Log: utils.py  $
    Revision 1.26 2018/10/30 10:36:09CET Baust, Philipp (uidg5548) 
    Updates in usecasetooling
    Revision 1.25 2018/09/19 11:57:43CEST Baust, Philipp (uidg5548) 
    Delete logfile on sucessfull execution.
    Revision 1.24 2018/09/10 16:04:12CEST Baust, Philipp (uidg5548) 
    Adjusted loglevel mapping
    Revision 1.23 2018/08/17 10:04:19CEST Olejua Ortiz, Manuel Leonardo (uidv5395) 
    - added ABH server
    Revision 1.22 2018/08/09 08:31:56CEST Olejua Ortiz, Manuel Leonardo (uidv5395) 
    -Added BGL server
    Revision 1.21 2018/07/31 13:19:21CEST Olejua Ortiz, Manuel Leonardo (uidv5395) 
    - \\LIFS010\hpc\luss021 path does not exits any more, causing problem in report generation.
    Revision 1.20 2018/01/10 13:32:13CET Baust, Philipp (uidg5548) 
    + job_folders_by_id
    Revision 1.19 2017/12/13 15:29:30CET Baust, Philipp (uidg5548) 
    Added Shuffle feature
    Revision 1.18 2017/11/04 12:07:27CET Baust, Philipp (uidg5548) 
    Relevant object marking for AWV target objects
    Revision 1.17 2017/10/11 14:15:34CEST Baust, Philipp (uidg5548) 
    Fix: Reporting of property check results.
    Fix: Performance while reading objects
    Revision 1.16 2017/07/31 17:09:25CEST Baust, Philipp (uidg5548) 
    Refactored BSIG reading
    Revision 1.15 2017/07/19 10:04:04CEST Baust, Philipp (uidg5548) 
    FIX: Create working directory for logfile if not existing
    Revision 1.14 2017/07/03 15:43:38CEST Baust, Philipp (uidg5548) 
    Fix: Wrong level for DEBUG
    Revision 1.13 2017/07/03 12:25:37CEST Baust, Philipp (uidg5548) 
    Improved logger configuration
    Revision 1.12 2017/06/28 07:20:51CEST Baust, Philipp (uidg5548) 
    Merged to mainline
    Revision 1.11.1.3 2017/06/28 07:02:45CEST Baust, Philipp (uidg5548) 
    Deprecation logs now the caller of the deprecated function instead of the deprecated function
    Revision 1.11.1.2 2017/06/19 13:29:50CEST Baust, Philipp (uidg5548) 
    Removed handlers for sub loggers to avoid duplicated logging statements
    Revision 1.11.1.1 2017/06/07 13:00:30CEST Baust, Philipp (uidg5548) 
    logging configuration
    Revision 1.11 2017/05/05 13:58:53CEST Baust, Philipp (uidg5548) 
    Switched to python logging
    Revision 1.10 2017/05/04 15:27:11CEST Baust, Philipp (uidg5548) 
    Added runtime logger
    Revision 1.9 2017/03/02 15:02:10CET Baust, Philipp (uidg5548) 
    Moved module from endurance to common
    Moved Config class into module
    Documentation
    Revision 1.8 2016/09/13 17:33:36CEST Baust, Philipp (uidg5548)
    Refactoring of BSIG Copy
    Revision 1.7 2016/09/12 15:18:49CEST Baust, Philipp (uidg5548)
    Bug fix, wrong calling order
    Revision 1.6 2016/08/31 14:31:16CEST Baust, Philipp (uidg5548)
    Refactored image extraction to seperate modules.
    Revision 1.5 2016/08/17 14:56:51CEST Baust, Philipp (uidg5548)
    Added image functions
    Revision 1.4 2016/08/17 12:05:36CEST Baust, Philipp (uidg5548)
    FIX: Extraction of relative samples
    Revision 1.3 2016/08/17 10:43:22CEST Baust, Philipp (uidg5548)
    CSV based labelset extractor
    Revision 1.2 2016/08/09 15:43:20CEST Baust, Philipp (uidg5548)
    Minor fixes
    Some PEP8

"""