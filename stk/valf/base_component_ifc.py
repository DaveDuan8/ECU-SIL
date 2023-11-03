"""
stk.valf.base_component_ifc.py
------------------------------

Main interface for all Framework and Validation Observers

In your observer sould derive from and call `BaseComponentInterface.__init__` to get the general things done,
e.g. the logger, data manager, bus name:

.. python::

    class MyObserver(BaseComponentInterface):

        def __init__(self, data_manager, component_name, bus_name="BUS_BASE"):
            \"\"\"setup default values
            \"\"\"
            BaseComponentInterface.__init__(self, data_manager, component_name, bus_name, "$Revision: 1.1 $")

            self._logger.debug()  # log execution of this method as DEBUG line

            self._my_var = self._data_manager.get_data_port('my_setting', self._bus_name)

            print('my observer version: %s' % self._version)
            print('my component: %s' % self._component_name)

..

The base class also provides methods to set and read ports on the data busses. These are more flexible,
e.g _get_data() will search data on a local (passed) directory, the given bus or the global bus.
Only if in all these storage parts the given port name is not found a default value will be returned:

- `_set_data` (port_name, port_value, bus_name=None)::

    sets the given port with value on given bus,
    if bus_name is None, using own bus

    **attention**: the default behaviour for the bus name differs from `DataManager.set_data`:
    there the bus 'global' is used as default if no bus is specified

    Parameters:

        port_name(str): The name of the port
        port_value(object): The value of the port
        bus_name(str): opt. bus name, default: local


- `_get_data` (port_name, bus_name=None, local={}, default=None)::

    used to grab settings
    1. from localDict, if no localDict available or found there
    2. from port at busName
    3. from port at 'global' bus

    **attention**:
    if the data should be read only from the specified bus `DataManager.get_data_port()` must be used:

      # read only from 'MyBus' and return error if not set:
      val = self._data_manager.get_data_port('MyPort', 'MyBus')

    Parameters:

        port_name(str): name of port to grab value from
        bus_name(str): name of bus to use (second)
        local(dict): dict to grab value from (first)
        default(object): value to use when no value found
        return(object): value / default


:org:           Continental AG
:author:        Gicu Benchea

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:05:43CEST $
"""
__all__ = ['BaseComponentInterface', 'ValidationException']

# - import STK modules ------------------------------------------------------------------------------------------------
from stk.util import Logger
from stk.error import StkError
from stk.util.helper import deprecation
from stk.util.tds import UncRepl


# - classes -----------------------------------------------------------------------------------------------------------
class ValidationException(StkError):
    """Base of all validation errors"""

    def __init__(self, description):
        """pass description to parent
        """
        StkError.__init__(self, str(description))


class GetPortError(ValidationException):
    """deprecated"""
    def __init__(self, description):
        """deprecated"""
        deprecation("Class '%s' is deprecated, avoid it's usage!" % self.__class__.__name__)
        ValidationException.__init__(self, str(description), True)

    def __str__(self):
        eqq = "=" * 53 + "\n"
        return str("%sERROR: %s\n%s" % (eqq, self.description, eqq))


class BaseComponentInterface(object):
    """**base class for observers**

    call the init of this base class to get the general things done, e.g. the logger:

    ..python::

        class MyObserver:

            def __init__(self, data_manager, component_name, bus_name="BUS_BASE"):
                '''setup default values
                '''
                BaseComponentInterface.__init__(self, data_manager, component_name, bus_name, "$Revision: 1.1 $")

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
        :type  data_manager: object
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
        self._logger.info('init observer %s of %s' % (self._version, str(type(self))))
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

    def Initialize(self):  # pylint: disable=C0103
        """ This function is called only once after the startup. """
        return BaseComponentInterface.RET_VAL_OK

    def PostInitialize(self):  # pylint: disable=C0103
        """Is called after all the component have been initialized. """
        return BaseComponentInterface.RET_VAL_OK

    def LoadData(self):  # pylint: disable=C0103
        """ Prepare the input data for processing (ex: read the date from a file). """
        return BaseComponentInterface.RET_VAL_OK

    def ProcessData(self):  # pylint: disable=C0103
        """ Process the input data. """
        return BaseComponentInterface.RET_VAL_OK

    def PostProcessData(self):  # pylint: disable=C0103
        """ All the components has terminated the process data and execute post process. """
        return BaseComponentInterface.RET_VAL_OK

    def PreTerminate(self):  # pylint: disable=C0103
        """ Collect results and generate the final report if necessary. """
        return BaseComponentInterface.RET_VAL_OK

    def Terminate(self):  # pylint: disable=C0103
        """ The validation session is ended. Release resouces and database connection if necessary. """
        return BaseComponentInterface.RET_VAL_OK

    def GetComponentInterfaceVersion(self):  # pylint: disable=C0103
        """ Return the version of the  component interface"""
        return "$Revision: 1.1 $".partition(':')[2].strip('$ ')

    def GetComponentVersion(self):  # pylint: disable=C0103
        """ Return the version of component """
        return self._version.partition(':')[2].strip('$ ') if hasattr(self, '_version') else '0.0'

    def GetComponentName(self):  # pylint: disable=C0103
        """ Return the name of component """
        return self._component_name if hasattr(self, '_component_name') else self.__class__.__name__


"""
$Log: base_component_ifc.py  $
Revision 1.1 2015/04/23 19:05:43CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/valf/project.pj
Revision 1.20 2015/04/02 17:27:41CEST Hospes, Gerd-Joachim (uidv8815) 
new logging of used version
--- Added comments ---  uidv8815 [Apr 2, 2015 5:27:42 PM CEST]
Change Package : 324999:1 http://mks-psad:7002/im/viewissue?selection=324999
Revision 1.19 2015/03/10 13:19:22CET Mertens, Sven (uidv7805) 
docu update: bci should be derived from
--- Added comments ---  uidv7805 [Mar 10, 2015 1:19:22 PM CET]
Change Package : 314142:2 http://mks-psad:7002/im/viewissue?selection=314142
Revision 1.18 2015/02/10 19:40:05CET Hospes, Gerd-Joachim (uidv8815)
update docu, fix epydoc errors
--- Added comments ---  uidv8815 [Feb 10, 2015 7:40:07 PM CET]
Change Package : 302321:1 http://mks-psad:7002/im/viewissue?selection=302321
Revision 1.16 2015/02/03 20:47:47CET Mertens, Sven (uidv7805)
adding UncRepl.acer for inherited components to be usefull
--- Added comments ---  uidv7805 [Feb 3, 2015 8:47:47 PM CET]
Change Package : 301804:1 http://mks-psad:7002/im/viewissue?selection=301804
Revision 1.15 2015/01/30 09:18:24CET Mertens, Sven (uidv7805)
pool alignment
Revision 1.14 2014/12/08 14:19:59CET Mertens, Sven (uidv7805)
update coll_reader according UncReplacer
Revision 1.13 2014/11/21 13:34:47CET Hospes, Gerd-Joachim (uidv8815)
update class docu: using local bus as default
--- Added comments ---  uidv8815 [Nov 21, 2014 1:34:48 PM CET]
Change Package : 279149:1 http://mks-psad:7002/im/viewissue?selection=279149
Revision 1.12 2014/11/20 19:08:19CET Hospes, Gerd-Joachim (uidv8815)
ping removed, speed up of bsig file search
Revision 1.11 2014/11/11 14:29:02CET Mertens, Sven (uidv7805)
adding support for a more easy get and set data (port) functionality
--- Added comments ---  uidv7805 [Nov 11, 2014 2:29:02 PM CET]
Change Package : 279543:1 http://mks-psad:7002/im/viewissue?selection=279543
Revision 1.10 2014/02/19 16:21:30CET Mertens, Sven (uidv7805)
- using class' name instead of noname,
- inserting back ValidationException
--- Added comments ---  uidv7805 [Feb 19, 2014 4:21:31 PM CET]
Change Package : 219802:1 http://mks-psad:7002/im/viewissue?selection=219802
Revision 1.9 2014/02/19 15:48:13CET Mertens, Sven (uidv7805)
component name is not used on some unittests, so using fallback "noname"
--- Added comments ---  uidv7805 [Feb 19, 2014 3:48:13 PM CET]
Change Package : 219802:1 http://mks-psad:7002/im/viewissue?selection=219802
Revision 1.8 2013/10/01 13:43:52CEST Mertens, Sven (uidv7805)
adding version to init method as globally repeated in every observer
--- Added comments ---  uidv7805 [Oct 1, 2013 1:43:52 PM CEST]
Change Package : 185933:7 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.7 2013/07/04 14:34:43CEST Mertens, Sven (uidv7805)
providing a step ahead for oberservers being able to reduce some more code...
--- Added comments ---  uidv7805 [Jul 4, 2013 2:34:44 PM CEST]
Change Package : 185933:3 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.6 2013/04/23 14:05:19CEST Raedler, Guenther (uidt9430)
added common return values for all VALF Plugins
--- Added comments ---  uidt9430 [Apr 23, 2013 2:05:20 PM CEST]
Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.5 2013/03/28 14:20:09CET Mertens, Sven (uidv7805)
pylint: solving some W0201 (Attribute %r defined outside __init__) errors
--- Added comments ---  uidv7805 [Mar 28, 2013 2:20:09 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.4 2013/03/28 09:33:22CET Mertens, Sven (uidv7805)
pylint: removing unused imports
--- Added comments ---  uidv7805 [Mar 28, 2013 9:33:23 AM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.3 2013/03/01 10:23:19CET Hecker, Robert (heckerr)
Updates regarding Pep8 Styleguides.
--- Added comments ---  heckerr [Mar 1, 2013 10:23:20 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.2 2013/02/19 20:59:01CET Hecker, Robert (heckerr)
Improved Coding style.
--- Added comments ---  heckerr [Feb 19, 2013 8:59:01 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.1 2013/02/11 11:06:04CET Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/valf/project.pj
------------------------------------------------------------------------------
-- From etk/valf Archive
------------------------------------------------------------------------------
Revision 1.6 2011/07/27 10:37:38CEST Sorin Mogos (mogoss)
* update: added return value 0 for all methods
--- Added comments ---  mogoss [Jul 27, 2011 10:37:38 AM CEST]
Change Package : 72325:1 http://mks-psad:7002/im/viewissue?selection=72325
Revision 1.5 2011/07/18 10:25:06CEST Sorin Mogos (mogoss)
* update: renamed "GenerateReport" method as "PreTerminate"
Revision 1.4 2011/07/13 12:26:32CEST Sorin Mogos (mogoss)
* update: added "GenerateReport" method to collect results and generate validation report
--- Added comments ---  mogoss [Jul 13, 2011 12:26:32 PM CEST]
Change Package : 72325:1 http://mks-psad:7002/im/viewissue?selection=72325
Revision 1.3 2010/06/28 13:46:23CEST smogos
* added configuration manager
--- Added comments ---  smogos [2010/06/28 11:46:23Z]
Change Package : 37850:1 http://LISS014:6001/im/viewissue?selection=37850
Revision 1.2 2009/11/18 13:09:34EET Sorin Mogos (smogos)
* some bug-fixes
--- Added comments ---  smogos [2009/11/18 11:09:34Z]
Change Package : 33973:1 http://LISS014:6001/im/viewissue?selection=33973
Revision 1.1 2009/10/30 14:17:10EET dkubera
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/ETK_EngineeringToolKit/04_Engineering/VALF_ValidationFrame/
    04_Engineering/31_PyLib/project.pj
"""
