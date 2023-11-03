"""
framework.valf.base_component_ifc.py
------------------------------
:org:           Continental AG
:author:        Leidenberger, Ralf

:version:       $Revision: 1.2 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/31 10:14:09CEST $
"""

# - import framework modules ------------------------------------------------------------------------------------------------
from framework.util import Logger
from framework.util.error import StkError
from framework.util.tds import UncRepl

__all__ = ['BaseComponentInterface', 'ValidationException']
# - classes -----------------------------------------------------------------------------------------------------------


class ValidationException(StkError):
    """Base of all validation errors"""

    def __init__(self, description):
        """pass description to parent
        """
        StkError.__init__(self, str(description))


class BaseComponentInterface(object):
    """**base class for observers**

    call the init of this base class to get the general things done, e.g. the logger:

    .. code-block:: python

        class MyObserver:

            def __init__(self, data_manager, component_name, bus_name="BUS_BASE"):
                '''setup default values
                '''
                BaseComponentInterface.__init__(self, data_manager, component_name, bus_name, "$Revision: 1.2 $")

                self._logger.debug()  # log execution of this method as DEBUG line
                self._my_var = None

    """
    # Error codes.
    RET_VAL_OK = 0
    RET_VAL_ERROR = -1

    def __init__(self, data_manager, component_name, bus_name, version="$Revsion: 0.0 $"):  # intentionally wrong
        """all the std things are going here, helping to reduce common code

        inherited observers can use this without the need for creating dummy methods

        :param data_manager: instance of class ``DataManager`` of the validation suite
        # :type  data_manager: object
        :param component_name: name of this observer instance as defined in config with ``[observer_name]``
        :type  component_name: str
        :param bus_name:  name of data manager port where this observer instance expects and writes data
                          as defined in config with ``ConnectBus=["my_bus"]``
        :type  bus_name:  str
        :param version:   version of this source, normally mks member revision
        :type  version:   str
        """
        self._data_manager = data_manager
        self._component_name = component_name
        self._bus_name = bus_name[0] if type(bus_name) in (tuple, list) else bus_name
        self._version = version

        self._logger = Logger(component_name)
        self._uncrepl = UncRepl()

    def _get_data(self, port_name, bus_name=None, local=None, default=None):
        """
        used to grab settings
        1. from localDict, if no localDict available or found there
        2. from port at busName
        3. from port at 'global' bus

        **attention**: if the data should be read only from the specified bus `DataManager.get_data_port()`
        must be used::

          val = self._data_manager.get_data_port('MyPort', 'MyBus')

        :param port_name: name of port to grab value from
        :type port_name: str
        :param bus_name: name of bus to use (second)
        :type bus_name: str
        :param local: dict to grab value from (first)
        :type local: dict
        :param default: value to use when no value found
        :type default: object
        :return: value / default
        :rtype: object
        """
        val = local.get(port_name, default) if type(local) == dict else default
        if val is default:
            bus_name = self._bus_name if bus_name is None else bus_name

            if bus_name in self._data_manager and port_name in self._data_manager[bus_name]:
                val = self._data_manager[bus_name][port_name]
            elif 'global' in self._data_manager:
                val = self._data_manager["global"].get(port_name, default)
        return val

    def _set_data(self, port_name, port_value, bus_name=None):
        """sets the given port with value on given bus
        if bus_name is None, using own bus

        :param port_name: The name of the port
        :type port_name: str
        :param port_value: The value of the port
        :type port_value: object
        :param bus_name: opt. bus name, default: local
        :type bus_name: str
        """
        self._data_manager.set_data_port(port_name, port_value, self._bus_name if bus_name is None else bus_name)

    def initialize(self):  # pylint: disable=C0103
        """ This function is called only once after the startup. """
        return BaseComponentInterface.RET_VAL_OK

    def post_initialize(self):  # pylint: disable=C0103
        """Is called after all the component have been initialized. """
        return BaseComponentInterface.RET_VAL_OK

    def load_data(self):  # pylint: disable=C0103
        """ Prepare the input data for processing (ex: read the date from a file). """
        return BaseComponentInterface.RET_VAL_OK

    def process_data(self):  # pylint: disable=C0103
        """ Process the input data. """
        return BaseComponentInterface.RET_VAL_OK

    def post_process_data(self):  # pylint: disable=C0103
        """ All the components has terminated the process data and execute post process. """
        return BaseComponentInterface.RET_VAL_OK

    def pre_terminate(self, _processed_files="-", _processed_time="-"):  # pylint: disable=C0103
        """ Collect results and generate the final report if necessary. """
        return BaseComponentInterface.RET_VAL_OK

    def terminate(self):  # pylint: disable=C0103
        """ The validation session is ended. Release resouces and database connection if necessary. """
        return BaseComponentInterface.RET_VAL_OK

    # def GetComponentInterfaceVersion(self):  # pylint: disable=C0103
    #     """ Return the version of the  component interface"""
    #     return "$Revision: 1.2 $".partition(':')[2].strip('$ ')

    # def GetComponentVersion(self):  # pylint: disable=C0103
    #     """ Return the version of component """
    #     return self._version.partition(':')[2].strip('$ ') if hasattr(self, '_version') else '0.0'

    def get_component_name(self):  # pylint: disable=C0103
        """ Return the name of component """
        return self._component_name if hasattr(self, '_component_name') else self.__class__.__name__


"""
$Log: base_component_ifc.py  $
Revision 1.2 2020/03/31 10:14:09CEST Leidenberger, Ralf (uidq7596) 
initial update
Revision 1.1 2020/03/25 21:38:06CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/valf/project.pj
"""
