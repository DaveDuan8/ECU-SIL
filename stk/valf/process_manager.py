# -*- coding:utf-8 -*-
"""
stk/valf/process_manager
------------------------

The internal core manager for Validation Framework used by Valf class.

**User-API Interfaces**

    - `stk.valf` (complete package)
    - `Valf`     (where this internal manager is used)


:org:           Continental AG
:author:        Sorin Mogos

:version:       $Revision: 1.10 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2017/07/11 09:28:31CEST $
"""

# disable W0703: general exceptions needed to continue processing in any case on hpc
# pylint: disable=R0902,R0912,R0914,R0915,W0702,C0103,W0703

# - import Python modules ---------------------------------------------------------------------------------------------
from os import path as opath
from sys import path as spath, _getframe, exit as sexit
from inspect import currentframe
from configparser import RawConfigParser
from collections import OrderedDict
from traceback import format_exc
from re import search

# - import STK modules ------------------------------------------------------------------------------------------------
VALF_DIR = opath.dirname(opath.abspath(currentframe().f_code.co_filename))
if VALF_DIR not in spath:
    spath.append(VALF_DIR)

STKDIR = opath.abspath(opath.join(VALF_DIR, "..", "stk"))
if STKDIR not in spath:
    spath.append(STKDIR)

from stk.util.logger import Logger
from stk.util.tds import UncRepl
from stk.valf.error import ValfError
from stk.util.find import find_class
from stk.valf.base_component_ifc import BaseComponentInterface as bci
from stk.valf.data_manager import DataManager
from stk.valf.progressbar import ProgressBar
from stk.valf.signal_defs import CFG_FILE_VERSION_PORT_NAME

# - defines -----------------------------------------------------------------------------------------------------------
# default observer directories:
OBS_DIRS = [VALF_DIR, opath.join(VALF_DIR, 'obs')]

PORT_NAME_INDEX = 0
PORT_CLASS_INSTANCE_INDEX = 1
PORT_VALUE_INDEX = 2
# should be removed, but some modules use these definitions:
RET_VAL_OK = bci.RET_VAL_OK
RET_VAL_ERROR = bci.RET_VAL_ERROR


# - classes -----------------------------------------------------------------------------------------------------------
class ProcessManager(object):
    r"""
    valf internal class to provide essential processing for observers

    - initialize

        - start logger
        - initialize data_manager
        - search classes based on class BaseComponentInterface

    - load configuration

        - import declared observer modules
        - set data ports

    - run validation

        - call all methods of all observers sequentially
        - use bpl_reader or similar to run through all recordings

    This class also is responsible to read out configuration and interpretation from config file.

    general used ports on bus ``Global``:

        - set "ConfigFileVersions"
            dict with file name as key and version as value for each loaded config file
        - read "FileCount"
            to show progress bar
        - read "IsFinished"
            to continue with next state when all sections of a recording are validated (set by `SignalExtractor`)

    Also setting ports as defined in ``InputData``  for the named bus.

    """
    def __init__(self, plugin_dir, fail_on_error=False):
        """init essencials

        :param plugin_dir: path or list of paths where to start search for observers
        :type plugin_dir:  string or list of strings

        :param fail_on_error: flag to break immediately if an exception is found
        :type fail_on_error:  boolean
        """
        self._logger = Logger(self.__class__.__name__)
        self._logger.debug()

        self._component_list = []

        self._version = "$Revision: 1.10 $"

        self._progressbar = None
        self._file_count = 0
        self._object_map_list = []
        self._config_file_loaded = False
        self._fail_on_error = fail_on_error
        self._configfile = None
        self._config_file_versions = {}

        self._uncrepl = UncRepl()

        plugin_dir.extend([self._uncrepl(dir_) for dir_ in OBS_DIRS if dir_ not in plugin_dir])

        self._logger.info("Searching for plug-ins. Please wait...")
        class_map_list, self._plugin_error_list = find_class(bci, plugin_dir, with_error_list=True)
        if class_map_list is None:
            self._logger.error("No plug-ins found.")
            return

        self._logger.debug("%d plug-ins found: %s." % (len(class_map_list), ", ".join([i['name']
                                                                                       for i in class_map_list])))
        self._plugin_map = {plugin['name']: plugin["type"] for plugin in class_map_list}

        # Create data manager object
        try:
            self._data_manager = DataManager()
        except:
            self._logger.exception("Couldn't instantiate 'DataManager' class.")
            if self._fail_on_error:
                raise
            sexit(bci.RET_VAL_ERROR)

    def _initialize(self):
        """calls initialize and post_initialize of ordered observers
        """
        self._logger.debug()

        # Calls Initialize for each component in the list
        for component in self._component_list:
            try:
                if component.Initialize() != bci.RET_VAL_OK:
                    self._logger.error("Class '%s' returned with error from Initialize() method." %
                                       component.__class__.__name__)
                    return bci.RET_VAL_ERROR
            except:
                self._logger.exception('EXCEPTION during Initialize of %s:\n%s' %
                                       (component.__class__.__name__, format_exc()))
                if self._fail_on_error:
                    raise
                return bci.RET_VAL_ERROR

        # Calls PostInitialize for each component in the list
        for component in self._component_list:
            try:
                if component.PostInitialize() != bci.RET_VAL_OK:
                    self._logger.error("Class '%s' returned with error from PostInitialize() method."
                                       % component.__class__.__name__)
                    return bci.RET_VAL_ERROR
            except:
                self._logger.exception('EXCEPTION during PostInitialize of %s:\n%s' %
                                       (component.__class__.__name__, format_exc()))
                if self._fail_on_error:
                    raise
                return bci.RET_VAL_ERROR

        self._file_count = self.get_data_port("FileCount")
        if self._file_count > 0:
            self._progressbar = ProgressBar(0, self._file_count, multiline=True)
        else:
            self._file_count = 0

        self._logger.debug("all components ready to run!")
        self._logger.mem_usage()
        return bci.RET_VAL_OK

    def _process_data(self):
        """calls load_data, process_data as well as post_process_data of ordered observers
        """
        self._logger.debug()

        if self._file_count == 0:
            self._logger.debug(str(_getframe().f_code.co_name) + "No files to process.")
            return RET_VAL_OK

        ret = bci.RET_VAL_ERROR
        counter = 0

        while not self.get_data_port("IsFinished"):
            # update progressbar position
            self._progressbar(counter)

            counter += 1

            # Calls LoadData for each component in the list
            for component in self._component_list:
                try:
                    ret = component.LoadData()
                    if ret is bci.RET_VAL_ERROR:
                        self._logger.error("Class '%s' returned with error from LoadData() method, "
                                           "continue with next sim file." % component.__class__.__name__)
                        break
                except:
                    self._logger.exception('exception raised during LoadData of %s:\n%s, '
                                           'continue with next sim file.'
                                           % (component.__class__.__name__, format_exc()))
                    ret = bci.RET_VAL_ERROR
                    if self._fail_on_error:
                        raise
                    break

            if ret is bci.RET_VAL_ERROR:
                continue

            # Calls ProcessData for each component in the list
            for component in self._component_list:
                try:
                    ret = component.ProcessData()
                    if ret is bci.RET_VAL_ERROR:
                        self._logger.error("Class '%s' returned with error from ProcessData() method, "
                                           "continue with next sim file." % component.__class__.__name__)
                        break
                except:
                    self._logger.exception('EXCEPTION during ProcessData of %s:\n%s, '
                                           'continue with next sim file.'
                                           % (component.__class__.__name__, format_exc()))
                    ret = bci.RET_VAL_ERROR
                    if self._fail_on_error:
                        raise
                    break

            if ret is bci.RET_VAL_ERROR:
                continue

            # Calls PostProcessData for each component in the list
            for component in self._component_list:
                try:
                    ret = component.PostProcessData()
                    if ret is bci.RET_VAL_ERROR:
                        self._logger.error("Class '%s' returned with error from PostProcessData() method, "
                                           "continue with next sim file." % component.__class__.__name__)
                        break
                except:
                    self._logger.exception('EXCEPTION during PostProcessData of %s:\n%s, '
                                           'continue with next sim file.'
                                           % (component.__class__.__name__, format_exc()))
                    ret = bci.RET_VAL_ERROR
                    if self._fail_on_error:
                        raise
                    break

            if ret is bci.RET_VAL_ERROR:
                continue

            # we have processed correctly at least a file,
            # set _process_data return value to OK in order to finish it's process

            self._logger.mem_usage()
            ret = bci.RET_VAL_OK

        if counter > 0:
            self._progressbar(counter)

        return ret

    def _terminate(self):
        """calls pre_terminate and terminate of ordered observers
        """
        self._logger.debug()

        # Calls PreTerminate for each component in the list
        for component in self._component_list:
            try:
                if component.PreTerminate() != bci.RET_VAL_OK:
                    self._logger.error("Class '%s' returned with error from PreTerminate() method."
                                       % component.__class__.__name__)
                    return bci.RET_VAL_ERROR
            except Exception:
                self._logger.exception('EXCEPTION during PreTerminate of observer %s:\n%s'
                                       % (component.__class__.__name__, format_exc()))
                if self._fail_on_error:
                    raise
                return bci.RET_VAL_ERROR

        # Calls Terminate for each component in the list
        for component in self._component_list:
            try:
                if component.Terminate() != bci.RET_VAL_OK:
                    self._logger.exception("Class '%s' returned with error from Terminate() method."
                                           % component.__class__.__name__)
                    return bci.RET_VAL_ERROR
            except:
                self._logger.exception('EXCEPTION during Terminate of observer %s:\n%s'
                                       % (component.__class__.__name__, format_exc()))
                if self._fail_on_error:
                    raise
                return bci.RET_VAL_ERROR

        return bci.RET_VAL_OK

    def get_data_port(self, port_name, bus_name="Global"):
        """gets data from a bus/port

        :param port_name: port name to use
        :param bus_name: bus name to use
        :return: data from bus/port
        """
        return self._data_manager.get_data_port(port_name, bus_name)

    def set_data_port(self, port_name, port_value, bus_name="Global"):
        """sets data to a bus/port

        :param port_name: port name to use
        :param port_value: data value to be set
        :param bus_name: bus name to use
        :return: data from bus/port
        """
        self._data_manager.set_data_port(port_name, port_value, bus_name)

    def _get_err_trace(self):
        """returns error trace from error list
        """
        if self._plugin_error_list:
            err_trace = '\n'.join('++ file: {0}.py -- {1}\n'.format(e[0], e[1].replace('\n', '\n--> '))
                                  for e in self._plugin_error_list)
        else:
            err_trace = 'no detailed info about failure'

        return err_trace

    def load_configuration(self, configfile):
        """loads configuration from cfg-file

        see more details in `Valf.LoadConfig`

        :param configfile: path/to/file.cfg
        :return: success (bool)
        """
        configfile = self._uncrepl(configfile)
        cls_obj = None

        if not opath.exists(configfile):
            raise ValfError("Configuration file '%s' doesn't exist or is invalid." % configfile)
            # self._logger.error("Configuration file '%s' doesn't exist or is invalid." % configfile)
            # return False

        self.set_data_port(CFG_FILE_VERSION_PORT_NAME, self._config_file_versions)
        autoorder = [-1]
        component_map = self._read_config(configfile)
        self._logger.info("loading version: '%s' of config file '%s'" %
                          (self._config_file_versions.get(configfile, ""), configfile))
        for componentname in component_map:
            try:  # retrieve details
                class_name = eval(component_map[componentname].get("ClassName", "None"))
                # port_in_list = component_map[componentname].get("PortIn")
                port_out_list = eval(component_map[componentname].get("PortOut", "[]"))
                input_data_list = eval(component_map[componentname].get("InputData", "[]"))
                connect_bus_list = eval(component_map[componentname].get("ConnectBus", "Bus#1"))
                order = component_map[componentname].get("Order", max(autoorder) + 1)
                if order in autoorder:
                    self._logger.info("order %d for component %s already in use!" % (order, componentname))
                autoorder.append(order)
                # check them, they should be there all!
                if (componentname != "Global" and
                        (class_name is None or port_out_list is None or
                         input_data_list is None or connect_bus_list is None)):
                    raise
            except:
                self._logger.error("Invalid port value or syntax wrong on component: '%s'" % componentname)
                if self._fail_on_error:
                    raise
                continue

            if type(connect_bus_list) not in (list, tuple):
                connect_bus_list = [connect_bus_list]

            if class_name in self._plugin_map:
                # Observer can be loaded -> Everything fine.
                # self._logger.debug("Loading plug-in: '%s'." % componentname)
                cls_obj = self._plugin_map[class_name](self._data_manager, componentname, connect_bus_list)
            elif componentname != "Global":
                # Observer can NOT be loaded -> Create Log Entry and raise Exception !
                err_trace = self._get_err_trace()

                # Create Log Entry
                self._logger.error('some python modules have coding errors')
                self._logger.error('Please check following list for more details:')
                self._logger.error(err_trace)

                msg = "Observer with ClassName %s not found, please check log for more info!" % class_name
                self._logger.error(msg)
                self._logger.error("File: \"valf.log\"")
                raise ValfError(msg, ValfError.ERR_OBSERVER_CLASS_NOT_FOUND)

            for port_out in port_out_list:
                for bus_name in connect_bus_list:
                    tmp = "Register port: Provider="
                    tmp += "'%s', PortName='%s', Bus='%s'." % (componentname, port_out, bus_name)
                    self._logger.debug(tmp)
                    self.set_data_port(port_out, None, bus_name)

            if type(input_data_list) == list:  # do it the usual way
                for input_data in input_data_list:
                    param_name = input_data[0]
                    param_value = input_data[1]
                    for bus_name in connect_bus_list:
                        tmp = "Setting input data.[Component='%s', " % componentname
                        tmp += "Bus='%s', PortName='%s', " % (bus_name, param_name)
                        tmp += "PortValue=%s]" % str(param_value)
                        self._logger.debug(tmp)
                        self.set_data_port(param_name, param_value, bus_name)
            elif type(input_data_list) == dict:  # we've got key value pairs already
                for param_name, param_value in input_data_list.iteritems():
                    for bus_name in connect_bus_list:
                        tmp = "Setting input data.[Component='%s', " % componentname
                        tmp += "Bus='%s', PortName='%s', " % (bus_name, param_name)
                        tmp += "PortValue=%s]" % str(param_value)
                        self._logger.debug(tmp)
                        self.set_data_port(param_name, param_value, bus_name)

            if componentname != "Global":
                self._object_map_list.append({"Order": order, "ComponentName": componentname, "ClsObj": cls_obj})

        # If whole Observer loading is done successfully,
        # we write anyway all found coding errors into the Log File as warnings
        if self._plugin_error_list:
            err_trace = self._get_err_trace()
            self._logger.warning('some python modules have coding errors')
            self._logger.warning('Please check following list for more details:')
            self._logger.warning(err_trace)

        self._component_list = []
        if len(self._object_map_list):
            self._object_map_list.sort(key=lambda x: x["Order"])

            for object_map in self._object_map_list:
                self._component_list.append(object_map["ClsObj"])

        if not self._component_list:
            self._logger.error("No component loaded. Please check config file '%s'." % str(configfile))
            return False

        self._config_file_loaded = True

        return True

    def _read_config(self, configfile, inccomp=None):
        """ read in the configuration file

        :param configfile: path/to/config.file
        :return: component map
        """
        self._configfile = self._uncrepl(opath.abspath(configfile))
        config = RawConfigParser()
        try:
            config.read(self._configfile)
        except Exception as err:
            self._logger.exception("Couldn't read config file '%s', exception:\n%s" % (self._configfile, err))
            if self._fail_on_error:
                raise
            return {}

        component_name_list = config.sections()
        if not len(component_name_list):
            self._logger.error("Invalid configuration file: '%s'" % self._configfile)
            return {}

        includecomp = component_name_list if inccomp is None else [inccomp]

        includeconfig = []
        componentmap = OrderedDict()
        try:
            for componentname in component_name_list:
                if componentname == "Global":
                    try:  # try to retrieve the version anyway from global, even when being in in include list
                        revsn = "Revision"  # MKS workaround as it's replacing...
                        mtc = search(r"(\$%s:\s[\d\.]+\s\$)" % revsn, config.get(componentname, "Version", fallback=''))
                        self.get_data_port(CFG_FILE_VERSION_PORT_NAME)[self._configfile] = \
                            '' if mtc is None else mtc.group(1)
                    except:
                        pass

                # don't import if not inside specific chapter
                if componentname not in includecomp:
                    continue
                # when active is False the component will not be loaded
                try:
                    if str(config.get(componentname, "Active")).lower() == "false":
                        continue
                except:
                    pass

                componentmap[componentname] = {}
                try:
                    include = config.get(componentname, "Include").strip('"\' ')
                    if len(include):
                        includeconfig.append([include, None if componentname == "Global" else componentname])
                except:
                    pass

                # key_name_list = config.options(componentname)
                try:
                    componentmap[componentname]["ClassName"] = config.get(componentname, "ClassName")
                except:
                    pass
                try:
                    componentmap[componentname]["PortOut"] = config.get(componentname, "PortOut")
                except:
                    pass
                try:
                    componentmap[componentname]["InputData"] = config.get(componentname, "InputData")
                except:
                    pass
                try:
                    componentmap[componentname]["Order"] = int(config.get(componentname, "Order"))
                except:
                    pass
                try:
                    componentmap[componentname]["ConnectBus"] = config.get(componentname, "ConnectBus")
                except:
                    pass

            # iterate through additional configs now
            for inc in includeconfig:
                if not opath.isabs(inc[0]):
                    inc[0] = opath.join(opath.dirname(self._configfile), inc[0])
                inccomps = self._read_config(inc[0], inc[1])
                for ncomp in inccomps:
                    if ncomp not in componentmap:
                        componentmap[ncomp] = inccomps[ncomp]
                    else:
                        componentmap[ncomp].update(inccomps[ncomp])

        except Exception:
            self._logger.exception('EXCEPTION stopped config read:')
            if self._fail_on_error:
                raise

        self._configfile = None

        return componentmap

    @property
    def last_config(self):
        """:return: last config file used
        """
        return self._configfile

    def run(self):
        """called by Valf to start state machine
        """
        if not self._config_file_loaded:
            self._logger.error("Configuration file was not loaded. Please call 'load_configuration' method.")
            return bci.RET_VAL_ERROR

        comps = [c.GetComponentName() for c in self._component_list]
        self._logger.info("components configured: %s" % ", ".join(comps))

        try:
            if self._initialize() is bci.RET_VAL_ERROR:
                return bci.RET_VAL_ERROR
        except Exception as _:
            self._logger.exception('EXCEPTION during initialization of observers:')
            if self._fail_on_error:
                raise
            return bci.RET_VAL_ERROR

        try:
            if self._process_data() is bci.RET_VAL_ERROR:
                return bci.RET_VAL_ERROR
        except Exception as _:
            self._logger.exception('EXCEPTION during data processing of observers:')
            if self._fail_on_error:
                raise
            return bci.RET_VAL_ERROR

        try:
            if self._terminate() is bci.RET_VAL_ERROR:
                return bci.RET_VAL_ERROR
        except Exception as _:
            self._logger.exception('EXCEPTION while terminating observers')
            if self._fail_on_error:
                raise
            return bci.RET_VAL_ERROR

        return bci.RET_VAL_OK


"""
$Log: process_manager.py  $
Revision 1.10 2017/07/11 09:28:31CEST Hospes, Gerd-Joachim (uidv8815) 
add RET_VAL_ERROR and _OK again as used by other modules and perhaps users tests
Revision 1.9 2017/07/10 18:06:45CEST Hospes, Gerd-Joachim (uidv8815)
final fix in ProcessManager and module test test_valf updated
Revision 1.8 2016/06/23 18:34:30CEST Hospes, Gerd-Joachim (uidv8815)
update docu, use full #Revision: 1.2 # string for version
Revision 1.7 2016/06/23 16:13:23CEST Mertens, Sven (uidv7805)
read out properly
Revision 1.6 2016/06/23 15:09:51CEST Mertens, Sven (uidv7805)
pylint fix
Revision 1.5 2016/06/23 14:56:30CEST Mertens, Sven (uidv7805)
config read update
Revision 1.4 2016/06/21 16:48:58CEST Hospes, Gerd-Joachim (uidv8815)
finalize docu for config
Revision 1.3 2016/06/21 13:53:56CEST Hospes, Gerd-Joachim (uidv8815)
add config file versions and tests for it
Revision 1.2 2015/10/22 11:20:23CEST Hospes, Gerd-Joachim (uidv8815)
log details about error while parsing cfg
- Added comments -  uidv8815 [Oct 22, 2015 11:20:24 AM CEST]
Change Package : 389212:1 http://mks-psad:7002/im/viewissue?selection=389212
Revision 1.1 2015/04/23 19:05:47CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/valf/project.pj
Revision 1.31 2015/04/09 16:31:09CEST Hospes, Gerd-Joachim (uidv8815)
add traceback to log for exceptions
--- Added comments ---  uidv8815 [Apr 9, 2015 4:31:09 PM CEST]
Change Package : 326836:1 http://mks-psad:7002/im/viewissue?selection=326836
Revision 1.30 2015/03/27 09:55:01CET Mertens, Sven (uidv7805)
removing warning argument
--- Added comments ---  uidv7805 [Mar 27, 2015 9:55:01 AM CET]
Change Package : 317742:2 http://mks-psad:7002/im/viewissue?selection=317742
Revision 1.29 2015/03/18 13:25:44CET Mertens, Sven (uidv7805)
through valf, data manager's warnings can be switched off
--- Added comments ---  uidv7805 [Mar 18, 2015 1:25:45 PM CET]
Change Package : 317742:1 http://mks-psad:7002/im/viewissue?selection=317742
Revision 1.28 2015/02/10 19:40:02CET Hospes, Gerd-Joachim (uidv8815)
update docu, fix epydoc errors
--- Added comments ---  uidv8815 [Feb 10, 2015 7:40:04 PM CET]
Change Package : 302321:1 http://mks-psad:7002/im/viewissue?selection=302321
Revision 1.27 2015/02/03 20:59:10CET Mertens, Sven (uidv7805)
using absolute paths
--- Added comments ---  uidv7805 [Feb 3, 2015 8:59:10 PM CET]
Change Package : 301804:1 http://mks-psad:7002/im/viewissue?selection=301804
Revision 1.26 2015/01/30 14:45:18CET Mertens, Sven (uidv7805)
fix for duplicate dir entries
Revision 1.25 2015/01/30 09:17:10CET Mertens, Sven (uidv7805)
lifs replacement
Revision 1.24 2014/11/20 19:37:29CET Hospes, Gerd-Joachim (uidv8815)
add valf/obs to plugin path
--- Added comments ---  uidv8815 [Nov 20, 2014 7:37:29 PM CET]
Change Package : 282158:1 http://mks-psad:7002/im/viewissue?selection=282158
Revision 1.23 2014/07/18 12:00:23CEST Hospes, Gerd-Joachim (uidv8815)
fix pylint issues
--- Added comments ---  uidv8815 [Jul 18, 2014 12:00:23 PM CEST]
Change Package : 244453:1 http://mks-psad:7002/im/viewissue?selection=244453
Revision 1.22 2014/07/18 10:03:51CEST Hospes, Gerd-Joachim (uidv8815)
print mem info after each run
--- Added comments ---  uidv8815 [Jul 18, 2014 10:03:52 AM CEST]
Change Package : 244453:1 http://mks-psad:7002/im/viewissue?selection=244453
Revision 1.21 2014/05/09 11:32:12CEST Hospes, Gerd-Joachim (uidv8815)
report prints either detailed overview table or developer details
--- Added comments ---  uidv8815 [May 9, 2014 11:32:12 AM CEST]
Change Package : 233158:1 http://mks-psad:7002/im/viewissue?selection=233158
Revision 1.20 2014/05/09 10:04:38CEST Hospes, Gerd-Joachim (uidv8815)
pylint fixes
--- Added comments ---  uidv8815 [May 9, 2014 10:04:39 AM CEST]
Change Package : 230866:1 http://mks-psad:7002/im/viewissue?selection=230866
Revision 1.19 2014/05/08 20:08:10CEST Hospes, Gerd-Joachim (uidv8815)
added files from P.Baust with additional tests and some minor valf fixes
--- Added comments ---  uidv8815 [May 8, 2014 8:08:10 PM CEST]
Change Package : 230866:1 http://mks-psad:7002/im/viewissue?selection=230866
Revision 1.18 2014/03/26 14:26:12CET Hecker, Robert (heckerr)
Adapted code to python 3.
--- Added comments ---  heckerr [Mar 26, 2014 2:26:13 PM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.17 2014/03/13 17:28:47CET Hospes, Gerd-Joachim (uidv8815)
show/log exceptions with stack trace in valf, add. test_exceptions and
fixes in process_manager
--- Added comments ---  uidv8815 [Mar 13, 2014 5:28:48 PM CET]
Change Package : 221496:1 http://mks-psad:7002/im/viewissue?selection=221496
Revision 1.16 2014/02/19 16:39:54CET Mertens, Sven (uidv7805)
fixing wrong define from ValfError class
--- Added comments ---  uidv7805 [Feb 19, 2014 4:39:55 PM CET]
Change Package : 219802:1 http://mks-psad:7002/im/viewissue?selection=219802
Revision 1.15 2014/02/19 15:17:36CET Mertens, Sven (uidv7805)
readding logger output
--- Added comments ---  uidv7805 [Feb 19, 2014 3:17:37 PM CET]
Change Package : 219802:1 http://mks-psad:7002/im/viewissue?selection=219802
Revision 1.14 2014/02/19 14:16:06CET Mertens, Sven (uidv7805)
new include property for distributed configuration
--- Added comments ---  uidv7805 [Feb 19, 2014 2:16:07 PM CET]
Change Package : 219802:1 http://mks-psad:7002/im/viewissue?selection=219802
Revision 1.13 2013/10/30 10:52:29CET Hecker, Robert (heckerr)
Replaced Exception with more usefull information for the End User,
and put extra information into the log file.
--- Added comments ---  heckerr [Oct 30, 2013 10:52:29 AM CET]
Change Package : 202843:1 http://mks-psad:7002/im/viewissue?selection=202843
Revision 1.12 2013/10/16 14:27:02CEST Hospes, Gerd-Joachim (uidv8815)
add error messages if observer method returns with error
--- Added comments ---  uidv8815 [Oct 16, 2013 2:27:02 PM CEST]
Change Package : 199263:1 http://mks-psad:7002/im/viewissue?selection=199263
Revision 1.11 2013/10/01 13:45:16CEST Hospes, Gerd-Joachim (uidv8815)
new error msg for operator load problems
--- Added comments ---  uidv8815 [Oct 1, 2013 1:45:17 PM CEST]
Change Package : 196951:1 http://mks-psad:7002/im/viewissue?selection=196951
Revision 1.10 2013/07/04 11:17:49CEST Hospes, Gerd-Joachim (uidv8815)
changes for new module valf:
- process_manager initiates data_manager at init instead of load_config
- bpl uses correct module path
- processbar with simple 'include sys' to redirect process bar output
--- Added comments ---  uidv8815 [Jul 4, 2013 11:17:49 AM CEST]
Change Package : 169590:1 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.9 2013/05/29 08:37:44CEST Mertens, Sven (uidv7805)
adaptation for config loading without ConfigManager
--- Added comments ---  uidv7805 [May 29, 2013 8:37:44 AM CEST]
Change Package : 179495:8 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.8 2013/05/23 11:31:42CEST Mertens, Sven (uidv7805)
adding some comments
Revision 1.7 2013/05/23 07:55:12CEST Mertens, Sven (uidv7805)
adding comments and changing to connectionString and findClass
--- Added comments ---  uidv7805 [May 23, 2013 7:55:12 AM CEST]
Change Package : 179495:8 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.6 2013/04/19 12:44:28CEST Hecker, Robert (heckerr)
Revert to working version.
--- Added comments ---  heckerr [Apr 19, 2013 12:44:29 PM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.5 2013/04/12 14:46:52CEST Mertens, Sven (uidv7805)
enabling the use of a connection string on observer level.
Each of them is allowed to have an additional InputData in config,
e.g. ("connectionString", "DBQ=racadmpe;Uid=DEV_MFC31X_ADMIN;Pwd=MFC31X_ADMIN"),
("dbPrefix", "DEV_MFC31X_ADMIN.").
--- Added comments ---  uidv7805 [Apr 12, 2013 2:46:53 PM CEST]
Change Package : 179495:1 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.4 2013/03/21 17:28:00CET Mertens, Sven (uidv7805)
solving minor pylint error issues
Revision 1.3 2013/03/01 10:23:24CET Hecker, Robert (heckerr)
Updates regarding Pep8 Styleguides.
--- Added comments ---  heckerr [Mar 1, 2013 10:23:24 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.2 2013/02/19 21:25:39CET Hecker, Robert (heckerr)
Updates according Pep8 Styleguides.
--- Added comments ---  heckerr [Feb 19, 2013 9:25:39 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.1 2013/02/11 11:06:08CET Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/valf/project.pj
------------------------------------------------------------------------------
-- From etk/valf Archive
------------------------------------------------------------------------------
Revision 1.16 2012/04/30 10:16:49CEST Mogos, Sorin (mogoss)
* change: if at least one file was processed correctely then
__process_data returns 0 (RET_VAL_OK)
--- Added comments ---  mogoss [Apr 30, 2012 10:16:49 AM CEST]
Change Package : 104217:1 http://mks-psad:7002/im/viewissue?selection=104217
Revision 1.15 2011/10/31 11:40:16CET Sorin Mogos (mogoss)
* change: changed stk library path
--- Added comments ---  mogoss [Oct 31, 2011 11:40:16 AM CET]
Change Package : 85403:1 http://mks-psad:7002/im/viewissue?selection=85403
Revision 1.14 2011/08/12 09:21:01CEST Sorin Mogos (mogoss)
* update: improved error handling
--- Added comments ---  mogoss [Aug 12, 2011 9:21:01 AM CEST]
Change Package : 72325:1 http://mks-psad:7002/im/viewissue?selection=72325
Revision 1.13 2011/07/20 18:18:34CEST Castell Christoph (uidt6394) (uidt6394)
Added error handling for the case when one of the framework functions is
missing from a module.
--- Added comments ---  uidt6394 [Jul 20, 2011 6:18:34 PM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.12 2011/07/18 10:25:07CEST Sorin Mogos (mogoss)
* update: renamed "GenerateReport" method as "PreTerminate"
--- Added comments ---  mogoss [Jul 18, 2011 10:25:07 AM CEST]
Change Package : 72325:1 http://mks-psad:7002/im/viewissue?selection=72325
Revision 1.11 2011/07/13 12:26:33CEST Sorin Mogos (mogoss)
* update: added "GenerateReport" method to collect results and
generate validation report
Revision 1.10 2011/05/19 12:04:03CEST Sorin Mogos (mogoss)
* update: added get_data_port method
--- Added comments ---  mogoss [May 19, 2011 12:04:03 PM CEST]
Change Package : 65320:1 http://mks-psad:7002/im/viewissue?selection=65320
Revision 1.9 2010/07/28 11:28:52CEST Sorin Mogos (mogoss)
* code customisation
Revision 1.8 2010/06/28 14:46:26EEST Sorin Mogos (smogos)
* added configuration manager
--- Added comments ---  smogos [2010/06/28 11:46:26Z]
Change Package : 37850:1 http://LISS014:6001/im/viewissue?selection=37850
Revision 1.7 2010/03/19 10:39:10EET Sorin Mogos (smogos)
* code customisation and bug-fixes
--- Added comments ---  smogos [2010/03/19 08:39:11Z]
Change Package : 37850:1 http://LISS014:6001/im/viewissue?selection=37850
Revision 1.6 2010/03/04 09:16:28EET Gicu Benchea (gbenchea)
Add the bus constructor parameter
--- Added comments ---  gbenchea [2010/03/04 07:16:28Z]
Change Package : 31947:1 http://LISS014:6001/im/viewissue?selection=31947
Revision 1.5 2010/02/18 16:19:15EET Sorin Mogos (smogos)
* code optimisation and bug-fixes
--- Added comments ---  smogos [2010/02/18 14:19:16Z]
Change Package : 37850:1 http://LISS014:6001/im/viewissue?selection=37850
Revision 1.3 2009/11/18 13:10:39EET Sorin Mogos (smogos)
* some bug-fixes
--- Added comments ---  smogos [2009/11/18 11:10:39Z]
Change Package : 33973:1 http://LISS014:6001/im/viewissue?selection=33973
Revision 1.2 2009/10/30 18:25:28EET dkubera
make initial call generic : valf_process_manager <config_file>
--- Added comments ---  dkubera [2009/10/30 16:25:29Z]
Change Package : 32862:1 http://LISS014:6001/im/viewissue?selection=32862
Revision 1.1 2009/10/30 13:18:43CET dkubera
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/ETK_EngineeringToolKit/
    04_Engineering/VALF_ValidationFrame/04_Engineering/31_PyLib/project.pj
"""
