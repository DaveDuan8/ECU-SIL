"""
stk/valf/data_manager.py
------------------------

Implements the data communication mechanism between the validation components
and also generic data storage.

**user interface**

    class `DataManager` with methods to set or get data ports

**basic information**

see STK training slides at Function Test sharepoint:

https://cws1.conti.de/content/00012124/Team%20Documents/Trainings/VALF_ValidationFramework/Algo_Validation_Training.pptx

**additional information**

data manager is using a class derived from ``dict`` internally. So there are several ways to access the data:

    equal ways to extract data:

    - ``self._data_manager.get_data_port('bus', 'port')``
    - ``self._data_manager['bus']['port']``

    *but* if element not available you'll get

    - ``None`` from ``get_data_port()``, no error in log file!
    - ``KeyError`` exception for the second line

**attention: all bus and port keys are stored lower case!**

providing also method ``get()`` with definable default return value:

    use return values if bus/port not available:

    - ``self._data_manager.get_data_port('bus', 'res_list')``:
        returns None if port or bus not set
    - ``self._data_manager['bus'].get('res_list', [0, 0])``:
        returns [0, 0] if port not set, None if bus not defined

    default return for not existing bus or port: None

all other general ``dict`` methods available:

    - check if data bus with name k is defined:
      ``if k in self._data_manager``:
    - list of all ports on 'bus#1':
      ``self._data_manager['bus#1'].keys()``

:org:           Continental AG
:author:        Gicu Benchea

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:05:45CEST $
"""
# - import STK modules ------------------------------------------------------------------------------------------------
from stk.util.logger import Logger
# from stk.util.helper import deprecated


# - classes -----------------------------------------------------------------------------------------------------------
class DictWatch(dict):
    """dictionary including read/write access counter
    This class is used by Datamanager for each port.
    """
    def __init__(self, *args, **kwargs):
        dict.__init__(self)
        self.stats = {}
        self.update(*args, **kwargs)

    def get(self, key, default=None):
        """retrieves value for given key, if key isn't inside, returns default

        :param key: key to be used
        :param default: default to be returned, if key not in dict
        :return: value for key
        """
        key = key.lower()
        return self[key] if key in self else default

    def __getitem__(self, key):
        key = key.lower()
        val = dict.__getitem__(self, key)

        self.stats[key][0] += 1
        return val

    def __setitem__(self, key, val):
        key = key.lower()
        dict.__setitem__(self, key, val)

        if key not in self.stats:
            self.stats[key] = [0, 1]
        else:
            self.stats[key][1] += 1

    def __delitem__(self, key):
        key = key.lower()
        if dict.pop(self, key, None):
            self.stats.__delitem__(key)

    def __contains__(self, item):
        return dict.__contains__(self, item.lower())

    def update(self, *args, **kwargs):
        """updates self dictionary

        :param args: another dict
        :param kwargs: another dict
        """
        for k, v in dict(*args, **kwargs).iteritems():
            self[k] = v

    def clear(self):
        """clears self entries
        """
        dict.clear()
        self.stats.clear()


class DataManager(DictWatch):
    """handling ports to exchange data between components
    """
    def __init__(self, default=None):
        """datamanager

        :param default: value to return when bus / port doesn't exist (via get_data_port)
        """
        self._logger = Logger(self.__class__.__name__)
        DictWatch.__init__(self)
        self._default = default

    def __str__(self):
        """returns the name
        """
        return self.__class__.__name__

    def __del__(self):
        """mgr is being remove from mem, valf has finished, I guess
        """
        print ("DataManager '%s' exited" % self.__class__.__name__)

    def set_data_port(self, port, value, bus='global'):
        """Registers port data with given name, value and bus

        If a bus or port is not already declared it will be defined.

        :param port: name of port
        :type port: str
        :param value: value to set port to
        :type value: object
        :param bus: opt. name of bus to use, default "global"
        :type bus: str
        """
        if bus in self:
            self[bus][port] = value
        else:
            self[bus] = DictWatch({port: value})

    def get_data_port(self, port, bus="global"):
        """
        returns value of the named data port / bus from data manger

        If the port or bus is not defined the data manager default (see `__init__`) will be returned.
        There is no exception raised and no error in the log file.

        :param port: name of value to be returned
        :type  port: str
        :param bus: opt. name of the bus providing the port, default "global"
        :type  bus: str
        :return: object
        """
        if self.exists_data_port(port, bus):
            return self[bus][port]

        return self._default

    def exists_data_port(self, port_name, bus_name="global"):
        """checks weather port at bus exits or not

        :param port_name: port name to check
        :type  port_name: str
        :param bus_name: bus name to check
        :return: wether data port is registred
        :type  bus_name: str
        :rtype: bool
        """
        return bus_name in self and port_name in self[bus_name]

    def clear_data_ports(self, port_list, bus="global"):
        """
        deletes all ports in given list

        :param port_list: list [] of ports
        :type port_list: list
        :param bus: opt. bus name, default "BUS_BASE"
        :type bus: str
        :return: success status
        :rtyp: bool
        """
        if bus not in self:
            return False

        if type(port_list) == str:
            port_list = [port_list]

        for port in port_list:
            del self[bus][port]
        return True

    def get_registered_bus_list(self):
        """
        provides list of all registerd busses

        :return: bus list or None
        """
        return self.keys()

    def get_registered_ports(self, bus='global'):
        """
        returns registered ports for specified bus

        :param bus: name of bus to get ports from
        :type  bus: str
        :return: list of port names
        :rtype:  list(str)
        """
        if bus in self:
            return self[bus].keys()

        return []

    def port_access_stat(self):
        """
        writes statistic in logger of all unused ports (only read, only written)
        """
        for bus, ports in self.items():
            self._logger.error("Status of: '%s'..." % str(bus))
            for port in ports:
                if ports.stats[port][0] == 0:
                    self._logger.error("...Port '%s' was never read from." % str(port))
                if ports.stats[port][1] == 1:
                    self._logger.error("...Port '%s' was only set once." % str(port))
        self._logger.error("End of port status.")

    # @deprecated('set_data_port')
    def RegisterDataPort(self, port_name, port_value, bus_name="Global"):  # pylint: disable=C0103
        """deprecated"""
        self.set_data_port(port_name, port_value, bus_name)

    # @deprecated('set_data_port')
    def SetDataPort(self, port_name, port_value, bus_name="Global"):  # pylint: disable=C0103
        """deprecated"""
        self.set_data_port(port_name, port_value, bus_name)

    # @deprecated('get_data_port')
    def GetDataPort(self, port_name, bus_name="Global"):  # pylint: disable=C0103
        """deprecated"""
        return self.get_data_port(port_name, bus_name)

    # @deprecated('exists_data_port')
    def ExistsDataPort(self, port_name, bus_name="BUS_BASE"):  # pylint: disable=C0103
        """deprecated"""
        return self.exists_data_port(port_name, bus_name)

    # @deprecated('clear_data_port')
    def ClearDataPorts(self, port_name_list, apl_name="Global", bus_name="BUS_BASE"):  # pylint: disable=C0103
        """deprecated"""
        return self.clear_data_ports(port_name_list, bus_name)

    # @deprecated()
    def GetDataPortPool(self):  # pylint: disable=C0103
        """deprecated
        """
        return self


"""
CHANGE LOG:
-----------
$Log: data_manager.py  $
Revision 1.1 2015/04/23 19:05:45CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/valf/project.pj
Revision 1.23 2015/04/02 15:13:12CEST Hospes, Gerd-Joachim (uidv8815) 
docu update, add using DataManager as dict
--- Added comments ---  uidv8815 [Apr 2, 2015 3:13:13 PM CEST]
Change Package : 324228:1 http://mks-psad:7002/im/viewissue?selection=324228
Revision 1.22 2015/03/27 09:56:34CET Mertens, Sven (uidv7805) 
removing warning logs
--- Added comments ---  uidv7805 [Mar 27, 2015 9:56:35 AM CET]
Change Package : 317742:2 http://mks-psad:7002/im/viewissue?selection=317742
Revision 1.21 2015/03/19 09:45:22CET Mertens, Sven (uidv7805)
add missing docstring
--- Added comments ---  uidv7805 [Mar 19, 2015 9:45:23 AM CET]
Change Package : 317742:1 http://mks-psad:7002/im/viewissue?selection=317742
Revision 1.20 2015/03/18 11:41:14CET Mertens, Sven (uidv7805)
being able to switch off all warnings when accessing missing port / bus
--- Added comments ---  uidv7805 [Mar 18, 2015 11:41:15 AM CET]
Change Package : 317742:1 http://mks-psad:7002/im/viewissue?selection=317742
Revision 1.19 2015/03/18 10:11:31CET Mertens, Sven (uidv7805)
- adding default default parameter,
- removing additional log output,
- chaning error to warning as defaults returned
--- Added comments ---  uidv7805 [Mar 18, 2015 10:11:31 AM CET]
Change Package : 317742:1 http://mks-psad:7002/im/viewissue?selection=317742
Revision 1.18 2015/02/10 17:51:24CET Hospes, Gerd-Joachim (uidv8815)
add missing methods to get new data manager running
--- Added comments ---  uidv8815 [Feb 10, 2015 5:51:26 PM CET]
Change Package : 271291:4 http://mks-psad:7002/im/viewissue?selection=271291
Revision 1.17 2015/02/09 09:34:02CET Mertens, Sven (uidv7805)
fix for port_access_stat
--- Added comments ---  uidv7805 [Feb 9, 2015 9:34:02 AM CET]
Change Package : 303748:1 http://mks-psad:7002/im/viewissue?selection=303748
Revision 1.16 2015/02/06 10:10:44CET Hospes, Gerd-Joachim (uidv8815)
add errors for wrong port/bus name
--- Added comments ---  uidv8815 [Feb 6, 2015 10:10:45 AM CET]
Change Package : 303227:1 http://mks-psad:7002/im/viewissue?selection=303227
Revision 1.15 2015/02/05 10:28:43CET Mertens, Sven (uidv7805)
- removing deprecation warning from RegisterDataPort,
- adding replacement for ExistsDataPort (also without warning)
--- Added comments ---  uidv7805 [Feb 5, 2015 10:28:44 AM CET]
Change Package : 303510:1 http://mks-psad:7002/im/viewissue?selection=303510
Revision 1.14 2015/02/03 20:54:54CET Mertens, Sven (uidv7805)
using absolute paths instead of relative
--- Added comments ---  uidv7805 [Feb 3, 2015 8:54:54 PM CET]
Change Package : 301804:1 http://mks-psad:7002/im/viewissue?selection=301804
Revision 1.13 2015/01/30 11:59:13CET Mertens, Sven (uidv7805)
fix for wrong dict usage
Revision 1.12 2015/01/30 10:26:05CET Mertens, Sven (uidv7805)
disabling deprecation
Revision 1.11 2015/01/30 09:15:58CET Mertens, Sven (uidv7805)
check for lifs and naming convention alignment
--- Added comments ---  uidv7805 [Jan 30, 2015 9:15:59 AM CET]
Change Package : 288765:1 http://mks-psad:7002/im/viewissue?selection=288765
Revision 1.10 2014/11/06 15:07:17CET Mertens, Sven (uidv7805)
object changes
Revision 1.9 2014/03/26 14:26:11CET Hecker, Robert (heckerr)
Adapted code to python 3.
--- Added comments ---  heckerr [Mar 26, 2014 2:26:11 PM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.8 2013/07/04 14:24:14CEST Mertens, Sven (uidv7805)
exiting is more friendly than dying: could be misunderstood with a crash
--- Added comments ---  uidv7805 [Jul 4, 2013 2:24:15 PM CEST]
Change Package : 185933:1 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.7 2013/05/29 08:38:56CEST Mertens, Sven (uidv7805)
adding local pylint ignore and str representation as intended
--- Added comments ---  uidv7805 [May 29, 2013 8:38:56 AM CEST]
Change Package : 179495:7 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.6 2013/04/03 15:57:44CEST Hospes, Gerd-Joachim (uidv8815)
style fix
--- Added comments ---  uidv8815 [Apr 3, 2013 3:57:44 PM CEST]
Change Package : 169590:2 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.5 2013/04/03 15:28:47CEST Hospes, Gerd-Joachim (uidv8815)
fixed dublicate code in SetDataPort and RegisterDataPort, added epydoc content
--- Added comments ---  uidv8815 [Apr 3, 2013 3:28:48 PM CEST]
Change Package : 169590:2 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.4 2013/03/28 09:33:18CET Mertens, Sven (uidv7805)
pylint: removing unused imports
--- Added comments ---  uidv7805 [Mar 28, 2013 9:33:18 AM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.3 2013/03/01 10:23:23CET Hecker, Robert (heckerr)
Updates regarding Pep8 Styleguides.
--- Added comments ---  heckerr [Mar 1, 2013 10:23:23 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.2 2013/02/20 08:21:26CET Hecker, Robert (heckerr)
Adapted to Pep8 Coding Style.
--- Added comments ---  heckerr [Feb 20, 2013 8:21:27 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.1 2013/02/11 11:06:07CET Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm
/STK_ScriptingToolKit/04_Engineering/stk/valf/project.pj
------------------------------------------------------------------------------
-- From etk/valf Archive
------------------------------------------------------------------------------
Revision 1.8 2012/04/30 10:16:38CEST Mogos, Sorin (mogoss)
* change: if at least one file was processed correctely then
__process_data returns 0 (RET_VAL_OK)
--- Added comments ---  mogoss [Apr 30, 2012 10:16:39 AM CEST]
Change Package : 104217:1 http://mks-psad:7002/im/viewissue?selection=104217
Revision 1.7 2011/07/19 12:57:46CEST Sorin Mogos (mogoss)
* update: added 'bus_name' parameter to 'get_registered_ports' method
* fix: some minor bug-fixes
--- Added comments ---  mogoss [Jul 19, 2011 12:57:48 PM CEST]
Change Package : 72325:1 http://mks-psad:7002/im/viewissue?selection=72325
Revision 1.6 2010/10/01 13:31:25CEST Sorin Mogos (mogoss)
* removed component_name dependencies
Revision 1.5 2010/06/28 13:46:21CEST smogos
* added configuration manager
--- Added comments ---  smogos [2010/06/28 11:46:21Z]
Change Package : 37850:1 http://LISS014:6001/im/viewissue?selection=37850
Revision 1.4 2010/03/19 10:35:11EET Sorin Mogos (smogos)
* code customisation and bug-fixes
--- Added comments ---  smogos [2010/03/19 08:35:11Z]
Change Package : 37850:1 http://LISS014:6001/im/viewissue?selection=37850
Revision 1.3 2010/03/04 09:16:27EET Gicu Benchea (gbenchea)
Add the bus constructor parameter
--- Added comments ---  gbenchea [2010/03/04 07:16:27Z]
Change Package : 31947:1 http://LISS014:6001/im/viewissue?selection=31947
Revision 1.2 2010/02/18 15:29:21EET Sorin Mogos (smogos)
* code optimisation and bug-fixes
--- Added comments ---  smogos [2010/02/18 13:29:21Z]
Change Package : 37850:1 http://LISS014:6001/im/viewissue?selection=37850
Revision 1.1 2009/10/30 14:18:41EET dkubera
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/ETK_EngineeringToolKit/04_Engineering/VALF_ValidationFrame/
    04_Engineering/31_PyLib/project.pj
"""
