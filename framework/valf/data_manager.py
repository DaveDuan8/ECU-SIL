"""
framework/valf/data_manager.py
------------------------

Implements the data communication mechanism between the validation components
and also generic data storage.

**user interface**

    class `DataManager` with methods to set or get data ports

**basic information**

see framework training slides at Function Test sharepoint:

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
:author:        Leidenberger, Ralf

:version:       $Revision: 1.2 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/31 10:14:10CEST $
"""
# - import framework modules ------------------------------------------------------------------------------------------------
from framework.util.logger import Logger
# from framework.util.helper import deprecated


# - classes -----------------------------------------------------------------------------------------------------------
class DictWatch(dict):
    """dictionary including read/write access counter
    This class is used by Datamanager for each port.
    """
    def __init__(self, *args, **kwargs):
        # noinspection PyTypeChecker
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
        dict.clear(self)
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

    # # @deprecated('set_data_port')
    # def RegisterDataPort(self, port_name, port_value, bus_name="Global"):  # pylint: disable=C0103
    #     """deprecated"""
    #     self.set_data_port(port_name, port_value, bus_name)
    #
    # # @deprecated('set_data_port')
    # def SetDataPort(self, port_name, port_value, bus_name="Global"):  # pylint: disable=C0103
    #     """deprecated"""
    #     self.set_data_port(port_name, port_value, bus_name)
    #
    # # @deprecated('get_data_port')
    # def GetDataPort(self, port_name, bus_name="Global"):  # pylint: disable=C0103
    #     """deprecated"""
    #     return self.get_data_port(port_name, bus_name)
    #
    # # @deprecated('exists_data_port')
    # def ExistsDataPort(self, port_name, bus_name="BUS_BASE"):  # pylint: disable=C0103
    #     """deprecated"""
    #     return self.exists_data_port(port_name, bus_name)
    #
    # # @deprecated('clear_data_port')
    # def ClearDataPorts(self, port_name_list, apl_name="Global", bus_name="BUS_BASE"):  # pylint: disable=C0103
    #     """deprecated"""
    #     return self.clear_data_ports(port_name_list, bus_name)
    #
    # # @deprecated()
    # def GetDataPortPool(self):  # pylint: disable=C0103
    #     """deprecated
    #     """
    #     return self


"""
CHANGE LOG:
-----------
$Log: data_manager.py  $
Revision 1.2 2020/03/31 10:14:10CEST Leidenberger, Ralf (uidq7596) 
initial update
Revision 1.1 2020/03/25 21:38:07CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/valf/project.pj
"""
