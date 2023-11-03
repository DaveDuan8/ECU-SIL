# -*- coding:utf-8 -*-
"""
framework/valf/process_manager
------------------------

The internal core manager for Validation Framework used by Valf class.

**User-API Interfaces**

    - `framework.valf` (complete package)
    - `Valf`     (where this internal manager is used)


:org:           Continental AG
:author:        Leidenberger, Ralf

:version:       $Revision: 1.2 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/31 10:14:11CEST $
"""

# disable W0703: general exceptions needed to continue processing in any case on hpc
# pylint: disable=R0902,R0912,R0914,R0915,W0702,C0103,W0703

# - import Python modules ---------------------------------------------------------------------------------------------
from os import path as opath

# noinspection PyProtectedMember
from sys import path as spath, _getframe, exit as sexit
from inspect import currentframe
from configparser import RawConfigParser, NoOptionError
from collections import OrderedDict
from traceback import format_exc
from re import search
from framework.io.signalreader import SignalReader
from framework.util.defines import *
# - import framework modules ------------------------------------------------------------------------------------------------

from framework.util.logger import Logger
from framework.util.tds import UncRepl
from framework.util.error import ValfError
from framework.util.find import find_class
from framework.valf.base_component_ifc import BaseComponentInterface as bci
from framework.valf.data_manager import DataManager
from framework.valf.progressbar import ProgressBar
from framework.util.defines import CFG_FILE_VERSION_PORT_NAME

# - defines -----------------------------------------------------------------------------------------------------------
VALF_DIR = opath.dirname(opath.abspath(currentframe().f_code.co_filename))
if VALF_DIR not in spath:
    spath.append(VALF_DIR)

STKDIR = opath.abspath(opath.join(VALF_DIR, "..", "framework"))
if STKDIR not in spath:
    spath.append(STKDIR)

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
        # self._logger.debug()

        self._component_list = []

        self._version = "$Revision: 1.2 $"

        self._progressbar = None
        self._file_count = 0
        self._object_map_list = []
        self._config_file_loaded = False
        self._fail_on_error = fail_on_error
        self._configfiles = []  # used as stack to load configs recursively
        self._config_file_versions = {}

        self._uncrepl = UncRepl()

        plugin_dir.extend([self._uncrepl(dir_) for dir_ in OBS_DIRS if dir_ not in plugin_dir])

        self._logger.info("Searching for plug-ins. Please wait...")
        class_map_list, self._plugin_error_list = find_class(bci, plugin_dir, with_error_list=True)
        if class_map_list is None:
            self._logger.error("No plug-ins found.")
            return

        self._logger.info("%d plug-ins found: %s." % (len(class_map_list), ", ".join([i['name']
                                                                                     for i in class_map_list])))
        self._plugin_map = {plugin['name']: plugin["type"] for plugin in class_map_list}

        # Create data manager object
        # noinspection PyBroadException
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
        # self._logger.debug()

        # Calls Initialize for each component in the list
        for component in self._component_list:
            # noinspection PyBroadException
            try:
                if component.initialize() != bci.RET_VAL_OK:
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
            # noinspection PyBroadException
            try:
                if component.post_initialize() != bci.RET_VAL_OK:
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
        # self._logger.mem_usage()
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
        self._processed_files = 0
        self._processed_time = 0
        while not self.get_data_port("IsFinished"):
            # update progressbar position
            self._progressbar(counter)

            counter += 1

            # Calls LoadData for each component in the list
            for component in self._component_list:
                # noinspection PyBroadException
                try:
                    ret = component.load_data()
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
                # noinspection PyBroadException
                try:
                    ret = component.process_data()
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
            component = None
            # Calls PostProcessData for each component in the list
            for component in self._component_list:
                # noinspection PyBroadException
                try:
                    ret = component.post_process_data()
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

            # self._logger.mem_usage()
            ret = bci.RET_VAL_OK
            if component is not None:
                # noinspection PyProtectedMember
                sil60_reader = SignalReader(component._data_manager.get_data_port("CurrentSimFile", BUS_SIL_208),delim=',')
                ts_tmp = sil60_reader["MTS.Package.TimeStamp"]
                self._processed_time += ts_tmp[-1] - ts_tmp[0]
            else:
                self._processed_time += 0
            self._processed_files += 1
        if counter > 0:
            self._progressbar(counter)

        return ret

    def _terminate(self):
        """calls pre_terminate and terminate of ordered observers
        """
        self._logger.debug()

        # Calls PreTerminate for each component in the list
        for component in self._component_list:
            # noinspection PyBroadException
            try:
                component._processed_files = self._processed_files
                component._processed_time = self._processed_time

                if component.pre_terminate(_processed_files=self._processed_files,
                                           _processed_time=self._processed_time) != bci.RET_VAL_OK:
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
            # noinspection PyBroadException
            try:
                if component.terminate() != bci.RET_VAL_OK:
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
                arguments = eval(component_map[componentname].get("Arguments", "[]"))
                key_words = eval(component_map[componentname].get("KeyWords", "{}"))
                order = component_map[componentname].get("Order", max(autoorder) + 1)
                if order in autoorder:
                    self._logger.info("order %d for component %s already in use!" % (order, componentname))
                autoorder.append(order)
                # check them, they should be there all!
                if (componentname != "Global" and
                        (class_name is None or port_out_list is None or
                         input_data_list is None or connect_bus_list is None)):
                    msg = "Invalid port value or syntax wrong on component: '%s' with parsed settings\n" \
                          "ClassName: %s, PortOut: %s,\n" \
                          "InputData: %s, \n" \
                          "ConnectBus: %s\n"\
                          "  only ClassName for 'Global' can be None, compare parsed settings with defines in config." \
                          % (componentname, class_name, port_out_list, input_data_list, connect_bus_list)
                    raise ValueError(msg)
            except Exception as err:
                self._logger.error(err)
                if self._fail_on_error:
                    raise
                continue

            if type(connect_bus_list) not in (list, tuple):
                connect_bus_list = [connect_bus_list]

            if class_name in self._plugin_map:
                # Observer can be loaded -> Everything fine.
                # self._logger.debug("Loading plug-in: '%s'." % componentname)
                if len(arguments) > 0 and len(key_words) > 0:
                    cls_obj = self._plugin_map[class_name](self._data_manager, componentname, connect_bus_list,
                                                           *arguments, **key_words)
                elif len(key_words) > 0:
                    cls_obj = self._plugin_map[class_name](self._data_manager, componentname, connect_bus_list,
                                                           **key_words)
                elif len(arguments) > 0:
                    cls_obj = self._plugin_map[class_name](self._data_manager, componentname, connect_bus_list,
                                                           *arguments)
                else:
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
                # raise ValfError(msg, ValfError.ERR_OBSERVER_CLASS_NOT_FOUND)

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

        called recursively for included config files

        :param configfile: path/to/config.file
        :return: component map
        """
        self._configfiles.append(self._uncrepl(opath.abspath(configfile)))
        config = RawConfigParser()
        try:
            config.read(self._configfiles[-1])
        except Exception as err:
            self._logger.exception("Couldn't read config file '%s', exception:\n%s" % (self._configfiles[-1], err))
            if self._fail_on_error:
                raise
            return {}

        component_name_list = config.sections()
        if not len(component_name_list):
            self._logger.error("Invalid configuration file: '%s'" % self._configfiles[-1])
            return {}

        includecomp = component_name_list if inccomp is None else [inccomp]

        includeconfig = []
        componentmap = OrderedDict()
        try:
            for componentname in component_name_list:
                if componentname == "Global":
                    # noinspection PyBroadException
                    try:  # try to retrieve the version anyway from global, even when being in in include list
                        revsn = "Revision"  # MKS workaround as it's replacing...
                        mtc = search(r"(\$%s:\s[\d\.]+\s\$)" % revsn, config.get(componentname, "Version", fallback=''))
                        self.get_data_port(CFG_FILE_VERSION_PORT_NAME)[self._configfiles[-1]] = \
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
                except NoOptionError:
                    pass

                componentmap[componentname] = {}
                try:
                    include = config.get(componentname, "Include").strip('"\' ')
                    if len(include):
                        includeconfig.append([include, None if componentname == "Global" else componentname])
                except NoOptionError:
                    pass

                try:
                    componentmap[componentname]["ClassName"] = config.get(componentname, "ClassName")
                except NoOptionError:
                    pass
                try:
                    componentmap[componentname]["PortOut"] = config.get(componentname, "PortOut")
                except NoOptionError:
                    pass
                try:
                    componentmap[componentname]["InputData"] = config.get(componentname, "InputData")
                except NoOptionError:
                    pass
                try:
                    componentmap[componentname]["Order"] = int(config.get(componentname, "Order"))
                except NoOptionError:
                    pass
                try:
                    componentmap[componentname]["ConnectBus"] = config.get(componentname, "ConnectBus")
                except NoOptionError:
                    pass
                try:
                    componentmap[componentname]["Arguments"] = config.get(componentname, "Arguments")
                except NoOptionError:
                    pass
                try:
                    componentmap[componentname]["KeyWords"] = config.get(componentname, "KeyWords")
                except NoOptionError:
                    pass

            # iterate through additional configs now
            for inc in includeconfig:
                if not opath.isabs(inc[0]):
                    inc[0] = opath.join(opath.dirname(self._configfiles[-1]), inc[0])
                inccomps = self._read_config(inc[0], inc[1])
                for ncomp in inccomps:
                    if ncomp not in componentmap:
                        componentmap[ncomp] = inccomps[ncomp]
                    else:
                        componentmap[ncomp].update(inccomps[ncomp])

        except Exception as err:
            self._logger.exception('EXCEPTION stopped config read:')
            if self._fail_on_error:
                raise err

        self._configfiles.pop()

        return componentmap

    @property
    def last_config(self):
        """:return: last config file used
        """
        return self._configfiles[-1] if self._configfiles else None

    def run(self):
        """called by Valf to start state machine
        """
        if not self._config_file_loaded:
            self._logger.error("Configuration file was not loaded. Please call 'load_configuration' method.")
            return bci.RET_VAL_ERROR

        comps = [c.get_component_name() for c in self._component_list]
        self._logger.info("components configured: %s" % ", ".join(comps))

        # noinspection PyBroadException
        try:
            if self._initialize() is bci.RET_VAL_ERROR:
                return bci.RET_VAL_ERROR
        except Exception as _:
            self._logger.exception('EXCEPTION during initialization of observers:')
            if self._fail_on_error:
                raise
            return bci.RET_VAL_ERROR

        # noinspection PyBroadException
        try:
            if self._process_data() is bci.RET_VAL_ERROR:
                return bci.RET_VAL_ERROR
        except Exception as _:
            self._logger.exception('EXCEPTION during data processing of observers:')
            if self._fail_on_error:
                raise
            return bci.RET_VAL_ERROR

        # noinspection PyBroadException
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
Revision 1.2 2020/03/31 10:14:11CEST Leidenberger, Ralf (uidq7596) 
initial update
Revision 1.1 2020/03/25 21:38:08CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/valf/project.pj
"""
