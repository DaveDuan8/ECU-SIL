"""
stk/util/helper.py
------------------

Stand alone utility functions.


:org:           Continental AG
:author:        Christoph Castell

:version:       $Revision: 1.9 $
:contact:       $Author: Mertens, Sven (uidv7805) $ (last change)
:date:          $Date: 2017/07/14 12:01:23CEST $
"""
# pylint: disable=C0103

# - import Python modules ---------------------------------------------------------------------------------------------
from os import path, walk
from sys import version_info
from datetime import datetime
from math import pow as mpow, log
import numpy.core as npc
from warnings import warn
from re import match
from functools import wraps
from collections import OrderedDict

# - defines -----------------------------------------------------------------------------------------------------------
# Vehicle Dynamics Definitions
PORT_VDY_VEHICLE_SPEED = "VehicleSpeed"
PORT_VDY_VEHICLE_ACCEL = "VehicleAccelXObjSync"
PORT_VDY_VEHICLE_CURVE = "VehicleCurveObjSync"
PORT_VDY_VEHICLE_YAWRATE = "VehicleYawRateObjSync"


# - functions ---------------------------------------------------------------------------------------------------------
def list_folders(head_dir):
    """ Return list of sub folders

    :param head_dir: start directory to search files within
    :return: generator of path/to/files found
    """
    for root, dirs, _ in walk(head_dir, topdown=True):
        for dir_name in dirs:
            dir_path = path.join(root, dir_name)
            yield dir_path


def singleton(cls):
    """This is a decorator providing a singleton interface.
    for an example, have a look into logger module

    :param cls: class to create singleton interface from
    """
    _instances = {}

    def getinstance(*args, **kwargs):
        """checks and returns the instance of class (already being instantiated)

        :param args: std arguments to pass to __init__
        :param kwargs: xtra args to pass
        """
        # idea: providing extra inits for a singleton to be able to call a kind of __init__: initialize afterwards
        # inits = getattr(cls, 'extra_inits', None)
        # if inits is not None:
        #     inits = {i: kwargs.pop(i, None) for i in inits}

        # additional functionality to force a new instance,
        # e.g. to test a new Logger with different file
        if "stk_moduletest_purge_instance" in kwargs:
            kwargs.pop("stk_moduletest_purge_instance")
            if cls in _instances:
                _instances.pop(cls)

        if cls not in _instances:
            _instances[cls] = cls(*args, **kwargs)

        # if inits is not None:
        #     _instances[cls].initialize(**inits)

        return _instances[cls]
    return getinstance


@singleton
class DeprecationUsage(object):
    """for internal valf usage only to be able to switch off deprecation warnings (set inside valf)
    """
    def __init__(self):
        self._stat = True

        from stk.util.logger import Logger

        self.log = Logger("deprecation").warning

    @property
    def status(self):
        """:return: status of deprecation usage
        """
        return self._stat

    @status.setter
    def status(self, value):
        """
        :param value: new status
        :type value: bool
        """
        if not isinstance(value, bool):
            raise TypeError
        self._stat = value


def deprecated(replacement=None):
    """
    This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used.

    Attention: the functions are marked as deprecated to get them removed!

    In some rare cases it might be needed to suppress the warnings.
    To disable deprecation warnings set ''DeprecationUsage().status = False''.

    :param replacement: name of function / method / property to replace decorated one

    *usage:*
    @deprecated()
    (if you just want to state that it's deprecated) or
    @deprecated('new_function_name')
    (if you want to tell a replacement)
    """
    def outer(fun):
        """outer call wraps message output

        :param fun: function to call
        """
        msg = "'%s' is deprecated" % (fun.fget.func_name if type(fun) == property else fun.__name__)
        if replacement is not None:
            msg += ", please use '%s' instead" % (replacement if type(replacement) == str else replacement.__name__)
        if fun.__doc__ is None:
            fun.__doc__ = msg

        @wraps(fun)
        def inner(*args, **kwargs):
            """inner call outputs message

            :param args: list of arguments to pass through to fun
            :param kwargs: dict of arguments to pass through as well
            """
            if DeprecationUsage().status:
                DeprecationUsage().log(msg)
            return fun(*args, **kwargs)

        return inner

    return outer


def deprecation(message):
    """deprecated, please use deprecated decorator instead

    :param message: msg to get printed as warning
    """
    if DeprecationUsage().status:
        warn(message, UserWarning if version_info[1] <= 7 else PendingDeprecationWarning, stacklevel=2)


@singleton
class Wmi(object):
    """
    A WMI provider for STK
    """
    def __init__(self):
        try:
            from wmi import WMI
            self._wproc = WMI("localhost", namespace="root\\cimv2")
        except ImportError:
            self._wproc = None

    @property
    def is_available(self):
        """status if WMI is available on your computer (WMI must be installed)

        :return: weather WMI is available
        :rtype: bool
        """
        return self._wproc is not None

    def execute(self, cls, *args, **kwargs):
        """execute a query by WMI and return results,

        please review timgolden.me.uk/python/wmi/cookbook.html for more details!

        :param cls: class to use, e.g. 'Win32_PerfRawData_PerfProc_Process'
        :param args: mostly used for columns, e.g. ["WorkingSet", "WorkingSetPeak"]
        :param kwargs: here you can define a kind of where clause, e.g. IDProcess=self.pid
        :return: result class instance from WMI
        """
        if self._wproc is not None:
            return getattr(self._wproc, cls)(*args, **kwargs)
        return None


class DefDict(OrderedDict):
    """I'm a default dict, but with my own missing method.

    .. python::
        from stk.util.helper import DefDict

        # set default to -1
        dct = DefDict(-1)
        # create key / value pairs: 'a'=0, 'b'=1, 'c'=-1, 'd'=-1
        dct.update((['a', 0], ['b', 1], 'c', 'd']))
        # prints 1
        print(dct['b'])
        # prints -1 (3rd index)
        print(dct[2])

    :param default: default value for missing key
    :type default: object
    """

    def __init__(self, default=None, **kwargs):
        OrderedDict.__init__(self)
        if len(kwargs) > 0:
            self.update(**kwargs)
        self._def = default

    def __getitem__(self, item):
        return self.values()[item] if type(item) == int else OrderedDict.__getitem__(self, item)

    def __missing__(self, _):
        return self._def


class DefSpace(dict):
    """I'm a default space dict, but with my own getattr method.

    :param kwargs: dictionary to initialize with
    """

    def __init__(self, **kwargs):
        dict.__init__(self, **kwargs)

    def __getattr__(self, item):
        if item in self:
            return self[item]
        else:
            raise AttributeError

    def __setattr__(self, key, value):
        self[key] = value

    def update(self, **kwargs):
        self._args.update(kwargs)


def arg_trans(mapping, *args, **kwargs):
    """argument transformation into dict with defaults

    :param mapping: list of argument names including their defaults
    :type mapping: list
    :param args: argument list
    :type args: list
    :param kwargs: named arguments with defaults
    :type kwargs: dict
    :return: dict with transferred arguments
    :rtype: dict
    """
    dflt = kwargs.pop('default', None)
    newmap = DefDict(dflt)
    k, l = 0, len(args)
    # update from mapping
    for i in mapping:
        key = i[0] if type(i) in (tuple, list) else i
        val = args[k] if l > k else (i[1] if type(i) in (tuple, list) else dflt)
        newmap[key] = val
        k += 1
    # update rest from args
    while k < l:
        newmap["arg%d" % k] = args[k]
        k += 1

    # update left over from kwargs
    newmap.update(kwargs)
    return newmap


def sec_to_hms_string(seconds):
    """ Converts seconds to an HMS string of the format 00:00:00.

    :param seconds: Input seconds.
    :return: HMS string
    """
    if seconds is not None:
        mins, secs = divmod(seconds, 60)
        hours, mins = divmod(mins, 60)
        return "%02d:%02d:%02d" % (hours, mins, secs)
    return ""


def get_current_date_string():
    """ Get the current date as a string.

    :return: Date string in format DD.MM.YYYY.
    """
    date_time = datetime.now()
    year = "%04d" % date_time.year
    month = "%02d" % date_time.month
    day = "%02d" % date_time.day
    current_date_str = "%s.%s.%s" % (day, month, year)
    return current_date_str


def get_name_from_path(file_path):
    """ Get a file name from a file path.

    :param file_path: The file path.
    :return: os.path.basename(file_path)
    """
    head_tail = path.split(file_path)
    root_ext = path.splitext(head_tail[1])
    return root_ext[0]


def human_size(num, unit=None):
    """format a size in bytes to human readable format, e.g. bytes, KB, MB, GB, TB, PB, EB, ZB, YB

    Note that bytes/KB will be reported in whole numbers but MB and
    above will have greater precision e.g. 1 byte, 43 bytes, 443 KB, 4.3 MB, 4.43 GB, etc

    :param num: raw size in bytes
    :type num: int
    :param unit: wished unit to get size_bytes converted
    :type unit: str
    """
    # --> http://en.wikipedia.org/wiki/Metric_prefix#List_of_SI_prefixes
    unit_list = [('bytes', 0), ('kB', 0), ('MB', 1), ('GB', 2), ('TB', 2), ('PB', 2), ('EB', 3), ('ZB', 3), ('YB', 3)]

    ret = ""
    if num < 0:
        num *= -1
        ret = "-"
    if num > 1:
        if unit is None:
            exp = min(int(log(num, 1000)), len(unit_list) - 1)
        else:
            exp = next((i for i in xrange(len(unit_list)) if unit_list[i][0].lower() == unit.lower()), 0)
        quot = float(num) / 10 ** (exp * 3)
        unit, num_decimals = unit_list[exp]
        frmt_str = '{:.%sf} {}' % num_decimals
        ret += frmt_str.format(quot, unit)
    elif num == 0:
        ret = '0 bytes'
    elif num == 1:
        ret += '1 byte'

    return ret


def path_ellipsis(filename, maxlength=60):
    """a path ellipsis is the truncation of parts in the the middle of a path
    exceeding a certain amount of characters e.g. C:\\Path_Begins_Here<....>\\ends.here

    :param filename: path/to/file.name to be ellipsed
    :type filename: str
    :param maxlength: max length allowed
    :type maxlength: int
    :return: ellipsed path, returned path exceeds maxlength if file.name exceeds it already
    """
    # split path string into < drive > < directory > < filename >
    if filename is None:
        return ''
    drv = match(r'(\w:\\|\\\\\w*\\\w*\\)', filename)
    pre = drv.group(1) if drv else ''
    mid = path.dirname(filename[len(pre):])
    post = path.basename(filename)

    lng = 0
    seg = len(mid)
    fit = ''

    # find the longest string that fits using bisection method
    while seg > 1:
        seg -= seg / 2

        left = lng + seg
        right = len(mid)

        # restore path with < drive > and < filename >
        tst = path.join(pre, mid[:left] + '...' + mid[right:], post)

        # candidate string fits into control boundaries, try a longer string
        # stop when seg <= 1
        if len(tst) <= maxlength:
            lng += seg
            fit = tst

    if lng == 0:  # string can't fit into control
        # < drive > and < directory > are empty, return < filename >
        if len(pre) == 0 and len(mid) == 0:
            return post

        # measure "C:\...\filename.ext"
        fit = path.join(pre, '...', post)

        # if still not fit then return "...\filename.ext"
        if len(fit) > maxlength:
            fit = path.join('...', post)
    return fit


def get_report_config_from_file(report_module_path):
    """ Extracts the report config data from a file and returns.

    :param report_module_path: The path to the report module.
    :return: Returns the report config xml string.
    """
    config_xml = ""
    config_found_b = False
    rep_file = open(report_module_path, "r").readlines()
    for line in rep_file:
        if line.find("<configuration_options>") == 0:
            config_found_b = True
        if line.find("</configuration_options>") == 0:
            config_xml += line
            config_found_b = False
        if config_found_b:
            config_xml += line
    return config_xml


def get_ego_displ(vdy_data, cycle_time):
    """ Calculate the EGO displacement for each cycle

    :param vdy_data:    Vehicle Dynamic data (dictionary from data_extractor)
    :type  vdy_data:    dict
    :param cycle_time:  Time of each cycle
    :type  cycle_time:  list
    :return: ego displacement vector
    """
    velocity = vdy_data[PORT_VDY_VEHICLE_SPEED]
    accel = vdy_data[PORT_VDY_VEHICLE_ACCEL]

    ego_displ = [0] * len(velocity)

    for cycle_idx in range(0, len(velocity)):
        delta_t = cycle_time[cycle_idx]
        ego_displ[cycle_idx] = (velocity[cycle_idx] * delta_t) + (0.5 * accel[cycle_idx] * mpow(delta_t, 2))

    return ego_displ


def std_dev(data):
    """calculates a standard deviation

    :param data: list of values
    :return: deviation, mean value
    """
    t_sum = 0.0
    length = len(data)
    meanval = npc.mean(data)
    for i in range(length):
        temp = data[i] - meanval
        temp = temp * temp
        t_sum += temp

    if length <= 1:
        dev = npc.sqrt(t_sum / length)
    else:
        dev = npc.sqrt(t_sum / (length - 1))

    return dev, meanval


def get_cycle_time(time_stamps):
    """ Calculate the cycle time according to the time stamps

    :param time_stamps : time stamps of the signal from data_extractor in micro seconds
    :type  time_stamps : list
    :return: Cycle Time Vector in seconds

    todo: check usage of cycle time
    """
    length = len(time_stamps)
    total_cycle = [0] * length
    if length > 0:

        for k in range(1, length - 1):
            total_cycle[k] = float((time_stamps[k] - time_stamps[k - 1])) / 1000000.0

        if length > 1:
            total_cycle[0] = total_cycle[1]
    return total_cycle


def get_driving_distance(ego_displ, start_index, stop_index):
    """ Calculate the Driving Distance

    :param ego_displ: EGO Displacement
    :type  ego_displ: dict
    :param start_index: Start index
    :type  start_index: int
    :param stop_index: Stop index
    :type  stop_index: int
    :return: distance between start and end index driven in meters
    """
    driv_dist = 0
    for idx in range(start_index, stop_index):
        driv_dist += ego_displ[idx]

    return driv_dist


def get_time_vec_in_ms(time_vec_us):
    """ converts a given time vector from Microseconds into milliseconds

    :param time_vec_us: Time vector in micro seconds
    :type  time_vec_us: list
    :return: Time Vector in milliseconds
    """
    time_vec_ms = [ts / 1000.0 for ts in time_vec_us]
    return time_vec_ms


def get_time_vec_in_sec(time_vec_us):
    """ converts a given time vector from Microseconds into seconds

    :param time_vec_us: Time vector in micro seconds
    :type  time_vec_us: list
    :return: Time Vector in seconds
    """
    time_vec_s = [ts / 1000000.0 for ts in time_vec_us]
    return time_vec_s


def get_time_in_sec(time_us):
    """ converts a given time from Microseconds into seconds

    :param time_us: Time in micro seconds
    :type  time_us: int
    :return: Time Vector in seconds
    """
    return time_us / 1000000.0


def get_speed_in_kmph(speed_vec_mps):
    """
    converts a given speed vector from meters per second
    into kilometers per second

    :param speed_vec_mps: Speed vector in meters per second
    :return: Speed Vector in kilometers per second
    """
    speed_vec = [val * 3.600 for val in speed_vec_mps]
    return speed_vec


@deprecated(list_folders)
def ListFolders(head_dir):
    """deprecated"""
    return list_folders(head_dir)


@deprecated(sec_to_hms_string)
def Sec2HmsString(seconds):
    """deprecated"""
    return sec_to_hms_string(seconds)


@deprecated(get_current_date_string)
def GetCurrentDateString():
    """deprecated"""
    return get_current_date_string()


@deprecated(get_name_from_path)
def GetNameFromPath(file_path):
    """deprecated"""
    return get_name_from_path(file_path)


@deprecated(get_report_config_from_file)
def GetReportConfigFromFile(report_module_path):
    """deprecated"""
    return get_report_config_from_file(report_module_path)


@deprecated(get_ego_displ)
def GetEgoDispl(vdy_data, cycle_time):
    """deprecated"""
    return get_ego_displ(vdy_data, cycle_time)


@deprecated(std_dev)
def StdDev(data):
    """deprecated"""
    return std_dev(data)


@deprecated(get_cycle_time)
def GetCycleTime(time_stamps):
    """deprecated"""
    return get_cycle_time(time_stamps)


@deprecated(get_driving_distance)
def GetDrivingDistance(ego_displ, start_index, stop_index):
    """deprecated"""
    return get_driving_distance(ego_displ, start_index, stop_index)


@deprecated(get_time_vec_in_ms)
def GetTimeVecIn_ms(time_vec_us):
    """deprecated"""
    return get_time_vec_in_ms(time_vec_us)


@deprecated(get_time_vec_in_sec)
def GetTimeVecIn_sec(time_vec_us):
    """deprecated"""
    return get_time_vec_in_sec(time_vec_us)


@deprecated(get_time_in_sec)
def GetTimeIn_sec(time_us):
    """deprecated"""
    return get_time_in_sec(time_us)


@deprecated(get_speed_in_kmph)
def GetSpeedIn_kmph(speed_vec_mps):
    """deprecated"""
    return get_speed_in_kmph(speed_vec_mps)

"""
CHANGE LOG:
-----------
$Log: helper.py  $
Revision 1.9 2017/07/14 12:01:23CEST Mertens, Sven (uidv7805) 
check argument before
Revision 1.8 2017/02/13 08:41:39CET Mertens, Sven (uidv7805) 
fix units
Revision 1.7 2017/02/12 13:55:40CET Hospes, Gerd-Joachim (uidv8815)
pep8 fixes
Revision 1.6 2016/12/16 16:39:53CET Hospes, Gerd-Joachim (uidv8815)
allow new singleton purge with first call
Revision 1.5 2016/12/16 10:42:17CET Hospes, Gerd-Joachim (uidv8815)
new parameter in singleton to force a new instance for module tests
Revision 1.4 2016/06/17 12:30:35CEST Mertens, Sven (uidv7805)
doing proper import
Revision 1.3 2016/04/05 15:48:24CEST Mertens, Sven (uidv7805)
little helper class
Revision 1.2 2015/06/19 11:13:08CEST Hospes, Gerd-Joachim (uidv8815)
warning using the Logger, test_helper adapted to check Logger lastmsg
--- Added comments ---  uidv8815 [Jun 19, 2015 11:13:08 AM CEST]
Change Package : 348149:1 http://mks-psad:7002/im/viewissue?selection=348149
Revision 1.1 2015/04/23 19:05:30CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/util/project.pj
Revision 1.25 2015/03/19 11:43:02CET Mertens, Sven (uidv7805)
update for left over arguments being inside dict as well
--- Added comments ---  uidv7805 [Mar 19, 2015 11:43:02 AM CET]
Change Package : 318794:1 http://mks-psad:7002/im/viewissue?selection=318794
Revision 1.24 2015/02/27 15:05:17CET Mertens, Sven (uidv7805)
fix for key / val
Revision 1.23 2015/02/27 14:52:25CET Mertens, Sven (uidv7805)
adding Wmi class as having it's own class would break import with python's wmi class
Revision 1.22 2015/02/19 10:55:21CET Mertens, Sven (uidv7805)
adding deprecation warning helper class to be able to switch on/off those warnings
Revision 1.21 2015/01/22 14:29:22CET Ellero, Stefano (uidw8660)
Removed all util based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Jan 22, 2015 2:29:23 PM CET]
Change Package : 296837:1 http://mks-psad:7002/im/viewissue?selection=296837
Revision 1.20 2015/01/22 10:34:18CET Mertens, Sven (uidv7805)
adding singleton decorator
--- Added comments ---  uidv7805 [Jan 22, 2015 10:34:19 AM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.19 2014/11/12 14:56:57CET Mertens, Sven (uidv7805)
more documentation
--- Added comments ---  uidv7805 [Nov 12, 2014 2:56:58 PM CET]
Change Package : 279543:1 http://mks-psad:7002/im/viewissue?selection=279543
Revision 1.18 2014/11/11 14:23:02CET Mertens, Sven (uidv7805)
deprecated support for properties
Revision 1.17 2014/10/24 08:19:08CEST Mertens, Sven (uidv7805)
adding unc drive support
--- Added comments ---  uidv7805 [Oct 24, 2014 8:19:09 AM CEST]
Change Package : 270789:1 http://mks-psad:7002/im/viewissue?selection=270789
Revision 1.16 2014/10/23 17:10:21CEST Mertens, Sven (uidv7805)
moving zip to list as of Py3 compatibility
--- Added comments ---  uidv7805 [Oct 23, 2014 5:10:21 PM CEST]
Change Package : 270789:1 http://mks-psad:7002/im/viewissue?selection=270789
Revision 1.15 2014/10/23 16:35:55CEST Mertens, Sven (uidv7805)
adding functions for a human readable size conversation and one for a path ellipsis
--- Added comments ---  uidv7805 [Oct 23, 2014 4:35:57 PM CEST]
Change Package : 270789:1 http://mks-psad:7002/im/viewissue?selection=270789
Revision 1.14 2014/10/09 20:44:06CEST Hecker, Robert (heckerr)
Example usage and change for deprecated porperty.
--- Added comments ---  heckerr [Oct 9, 2014 8:44:06 PM CEST]
Change Package : 270819:1 http://mks-psad:7002/im/viewissue?selection=270819
Revision 1.13 2014/03/24 21:56:56CET Hecker, Robert (heckerr)
Adapted to python 3.
--- Added comments ---  heckerr [Mar 24, 2014 9:56:56 PM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.12 2014/03/16 21:55:51CET Hecker, Robert (heckerr)
added pylintrc.
--- Added comments ---  heckerr [Mar 16, 2014 9:55:52 PM CET]
Change Package : 225494:1 http://mks-psad:7002/im/viewissue?selection=225494
Revision 1.11 2013/10/01 16:41:25CEST Mertens, Sven (uidv7805)
last fine adjustment
--- Added comments ---  uidv7805 [Oct 1, 2013 4:41:25 PM CEST]
Change Package : 185933:7 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.10 2013/09/09 12:13:57CEST Raedler, Guenther (uidt9430)
- removed old function already supported by stk.geo
- cleared import which is  not valid in this module
--- Added comments ---  uidt9430 [Sep 9, 2013 12:13:57 PM CEST]
Change Package : 196676:1 http://mks-psad:7002/im/viewissue?selection=196676
Revision 1.9 2013/05/23 06:24:08CEST Mertens, Sven (uidv7805)
removed some pylint errors
--- Added comments ---  uidv7805 [May 23, 2013 6:24:08 AM CEST]
Change Package : 179495:7 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.8 2013/05/14 10:49:43CEST Ibrouchene-EXT, Nassim (uidt5589)
Removed functions that are now in the clothoid package.
--- Added comments ---  uidt5589 [May 14, 2013 10:49:43 AM CEST]
Change Package : 182606:2 http://mks-psad:7002/im/viewissue?selection=182606
Revision 1.7 2013/03/28 09:33:13CET Mertens, Sven (uidv7805)
pylint: removing unused imports
--- Added comments ---  uidv7805 [Mar 28, 2013 9:33:14 AM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.6 2013/03/22 09:20:49CET Mertens, Sven (uidv7805)
last pep8 update on non-trailing white space errors
--- Added comments ---  uidv7805 [Mar 22, 2013 9:20:50 AM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.5 2013/03/01 15:39:18CET Hecker, Robert (heckerr)
Updates regarding Pep8 Styleguides.
--- Added comments ---  heckerr [Mar 1, 2013 3:39:18 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.4 2013/02/28 08:12:21CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 28, 2013 8:12:21 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.3 2013/02/27 16:19:58CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 27, 2013 4:19:58 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.2 2013/02/19 14:40:41CET Raedler, Guenther (uidt9430)
added helper function to list folders
--- Added comments ---  uidt9430 [Feb 19, 2013 2:40:42 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.1 2013/02/11 10:56:34CET Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
STK_ScriptingToolKit/04_Engineering/stk/util/project.pj
------------------------------------------------------------------------------
-- From etk/vpc Archive
------------------------------------------------------------------------------
Revision 1.19 2012/05/08 16:32:57CEST Ibrouchene-EXT, Nassim (uidt5589)
Improved computation time for the road functions.
--- Added comments ---  uidt5589 [May 8, 2012 4:33:00 PM CEST]
Change Package : 94467:3 http://mks-psad:7002/im/viewissue?selection=94467
Revision 1.18 2012/03/27 14:31:41CEST Raedler-EXT, Guenther (uidt9430)
reintegrate changes from branch into common trunk
--- Added comments ---  uidt9430 [Mar 27, 2012 2:31:42 PM CEST]
Change Package : 88554:1 http://mks-psad:7002/im/viewissue?selection=88554
Revision 1.17 2012/02/28 10:13:52CET Ibrouchene-EXT, Nassim (uidt5589)
Added a few functions common to road and trajectory estimation.
--- Added comments ---  uidt5589 [Feb 28, 2012 10:13:52 AM CET]
Change Package : 94467:1 http://mks-psad:7002/im/viewissue?selection=94467
Revision 1.16 2012/02/01 11:47:37CET Raedler-EXT, Guenther (uidt9430)
- added common std and mean calculation
--- Added comments ---  uidt9430 [Feb 1, 2012 11:47:38 AM CET]
Change Package : 88150:1 http://mks-psad:7002/im/viewissue?selection=88150
Revision 1.15 2011/12/15 14:15:57CET Raedler-EXT, Guenther (uidt9430)
- added function GetTimeVecIn_sec and GetTimeIn_sec
- added function GetSpeedInKmph
--- Added comments ---  uidt9430 [Dec 15, 2011 2:15:58 PM CET]
Change Package : 88150:1 http://mks-psad:7002/im/viewissue?selection=88150
Revision 1.14 2011/11/18 13:17:40CET Raedler Guenther (uidt9430) (uidt9430)
- added new function ShiftTimelineOfPointPairList()
- added some documentation
--- Added comments ---  uidt9430 [Nov 18, 2011 1:17:41 PM CET]
Change Package : 67780:7 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.13 2011/11/16 12:57:18CET Castell Christoph (uidt6394) (uidt6394)
Return types not clear from function name and also not commented. Left for author to fix.
Replaced magic number with val_gd.CYCLE_TIME_S (bad programming parctice).
Inconsistent localy defined cycle time in ADMA and some other modules also need to be replaced.
--- Added comments ---  uidt6394 [Nov 16, 2011 12:57:19 PM CET]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.12 2011/11/16 10:35:11CET Raedler Guenther (uidt9430) (uidt9430)
- fixed error due to renamed port name
--- Added comments ---  uidt9430 [Nov 16, 2011 10:35:11 AM CET]
Change Package : 76661:1 http://mks-psad:7002/im/viewissue?selection=76661
Revision 1.11 2011/11/15 10:33:47CET Raedler Guenther (uidt9430) (uidt9430)
- addef function to calculate the corrct cycle time of the measurement
--- Added comments ---  uidt9430 [Nov 15, 2011 10:33:47 AM CET]
Change Package : 76661:1 http://mks-psad:7002/im/viewissue?selection=76661
Revision 1.10 2011/11/11 09:33:31CET Castell Christoph (uidt6394) (uidt6394)
Made VDY port names global.
--- Added comments ---  uidt6394 [Nov 11, 2011 9:33:31 AM CET]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.9 2011/11/07 15:32:37CET Raedler Guenther (uidt9430) (uidt9430)
- added new functions for boxes and polygons
--- Added comments ---  uidt9430 [Nov 7, 2011 3:32:37 PM CET]
Change Package : 67780:7 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.8 2011/10/07 07:45:12CEST Raedler Guenther (uidt9430) (uidt9430)
- extened validation event class
- added new class for stationary obstacles
- added global defines
--- Added comments ---  uidt9430 [Oct 7, 2011 7:45:12 AM CEST]
Change Package : 76661:3 http://mks-psad:7002/im/viewissue?selection=76661
Revision 1.7 2011/09/20 12:30:16CEST Castell Christoph (uidt6394) (uidt6394)
Added GetNameFromPath() function.
--- Added comments ---  uidt6394 [Sep 20, 2011 12:30:16 PM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.6 2011/08/11 10:51:29CEST Raedler Guenther (uidt9430) (uidt9430)
-- checks for None
--- Added comments ---  uidt9430 [Aug 11, 2011 10:51:29 AM CEST]
Change Package : 67780:5 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.5 2011/08/03 13:01:07CEST Castell Christoph (uidt6394) (uidt6394)
Added function to get report config from file.
--- Added comments ---  uidt6394 [Aug 3, 2011 1:01:07 PM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.4 2011/08/02 07:11:32CEST Raedler Guenther (uidt9430) (uidt9430)
- added functions to get and split a pointpair lists
- added function to change a time vector from us to ms
--- Added comments ---  uidt9430 [Aug 2, 2011 7:11:32 AM CEST]
Change Package : 67780:5 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.3 2011/07/29 09:36:39CEST Castell Christoph (uidt6394) (uidt6394)
New GetEgoPath(VDYData) function. Not the ideal location for this function.
May move in future if better location found.
--- Added comments ---  uidt6394 [Jul 29, 2011 9:36:39 AM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.2 2011/07/28 08:29:27CEST Castell Christoph (uidt6394) (uidt6394)
Added Sec2HmsString() and GetCurrentDateString() functions.
--- Added comments ---  uidt6394 [Jul 28, 2011 8:29:28 AM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.1 2011/07/21 15:09:57CEST Castell Christoph (uidt6394) (uidt6394)
Initial revision
Member added to project /nfs/projekte1/PROJECTS/ARS301/06_Algorithm/05_Testing/
    05_Test_Environment/algo/ars301_req_test/valf_tests/vpc/project.pj
"""
