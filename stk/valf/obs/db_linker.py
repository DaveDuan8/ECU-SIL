"""
db_linker.py
------------

Observer to setup link to Databases

providing a simple successor to DBConnector observer

Only technology ('ARS4xx', 'MFC4xx', ...) and needed tables ('cat', 'val', 'gbl', ...) needed for initialization.
It's optimized to only setup one db connection for all tables (DBconnector used one for each table),
so it helps to reduce the number of open connections which is limited!

Observer should run as one of the firsts so following can use the connections at an early state.

used states:

    1) `Initialize`:

        setup DB instance based on values stored on DataBus

**User-API Interfaces**

    - `stk.valf` (complete package)
    - `DbLinker` (this module)


:org:           Continental AG
:author:        Sven Mertens

:version:       $Revision: 1.9 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/08/16 16:01:34CEST $
"""
# - Python imports ----------------------------------------------------------------------------------------------------
from collections import defaultdict

# - STK imports -------------------------------------------------------------------------------------------------------
from stk.db import cat, cl, fct, gbl, lbl, obj, par, sim, val
from stk.db.db_common import BaseDB
from stk.valf import BaseComponentInterface as bci
from stk.valf.signal_defs import DBCONNECTION_PORT_NAME, DATABASE_OBJECTS_PORT_NAME


# - classes -----------------------------------------------------------------------------------------------------------
class DbLinker(bci):
    """
    Observer class to establish a db connection and conectors for the different sub-schemes / tables

    expected ports on local bus:

        - ``DbConnection``, bus:
                Database named by technology or sqlite file path like path/to/sqlite/file,
                supported databases: ``ARS4XX, MFC4XX, VGA, algo``
        - ``DataBaseObjects``, bus:
                list connection objects for databases or ``['all']`` for backward compatibility,
                available conections:  ``cat, cl, fct, gbl, lbl, gen, obj, par, sim, val``
                (instances of classes `BaseRecCatalogDB`, `BaseGblDB`, `BaseValResDB`, ...)

    updating port on local bus:

        - ``DataBaseObjects``, bus:
                dict with connection names giving DB connection instances
                ``{'cat': <stk.db.cat.cat.BaseRecCatalogDB at 0x682d350>,``
                ``'foo': None,``
                ``'gbl': <stk.db.gbl.gbl.BaseGblDB at 0x67feff0>}``

    **sample config**

    .. python::

        [DB-Linker]
        ClassName="DbLinker"
        # PortOut=["DataBaseObjects"]
        InputData=[('DbConnection', 'MFC4XX'),
                   ('DataBaseObjects', ['cat', 'gbl', 'foo'])
                   ]
        ConnectBus=["DBBus#1"]
        Active=True
        Order=0

    **remark**

    Input and output of wanted connections are done via **DatabaseObjects** port.

    In case a connection isn't known, None is returned.

    To be a bit backward compatible, you can set ``('DataBaseObject', 'all')`` then ``cat, cl, gbl, gen, obj, par, val``
    are taken into use.

    Connected objects are placed into same port as dictionary, so with config listed above:

    - ``get_data_port(DATABASE_OBJECTS_PORT_NAME, 'my_db_bus')['cat']``
        will return object of RecCatBaseDB
    - ``get_data_port(DATABASE_OBJECTS_PORT_NAME, 'my_db_bus')['foo']``
        will return None (unknown db schema)

    Example usage:

    .. python::

        cat = data_mgr.get_data_port('DataBaseObject', 'DBBus#1')['cat']

        all_coll = cat.get_all_collection_names()

    Using several connections directly from dictionary:

    .. python::

        db = data_mgr.get_data_port('DataBaseObject', 'DBBus#1')

        # db : {'cat': <stk.db.cat.cat.BaseRecCatalogDB at 0x682d350>,
        #       'foo': None,
        #       'gbl': <stk.db.gbl.gbl.BaseGblDB at 0x67feff0>}

        all_coll = db['cat'].get_all_collection_names()
        unit_dist = db['gbl'].get_unit('meter')

    """
    def __init__(self, data_manager, component_name, bus_name="DBBus#1", **kwargs):
        """setup default values

        :param data_manager: data manager to pass through
        :param component_name: name of component to pass through (see config)
        :param bus_name: name of bus to use
        :param kwargs: additional argument, just taking version, if not inside keyword
        """
        kwargs["version"] = "$Revision: 1.9 $"
        bci.__init__(self, data_manager, component_name, bus_name, **kwargs)

        self._dbconn = None

        self._logger.debug()

    def Initialize(self):
        """ called once by Process_Manager,

        reads list of DB connections to create object / connection from
        and thereafter stores all back to same position on port as dictionary.

        for not-found connections None will be returned

        database connections are disconnected at shutdown of valf automagically
        """
        self._logger.debug()

        self._dbconn = BaseDB(self._get_data(DBCONNECTION_PORT_NAME, self._bus_name))
        mods = defaultdict(lambda: lambda _: None,
                           {'cat': cat.BaseRecCatalogDB, 'cl': cl.BaseCLDB, 'fct': fct.BaseFctDB,
                            'gbl': gbl.BaseGblDB, 'lbl': lbl.BaseCameraLabelDB, 'gen': lbl.BaseGenLabelDB,
                            'obj': obj.BaseObjDataDB, 'par': par.BaseParDB, 'sim': sim.BaseSimulationDB,
                            'val': val.BaseValResDB})

        dbmods = self._get_data(DATABASE_OBJECTS_PORT_NAME, self._bus_name)
        if dbmods == 'all':
            dbmods = ['cat', 'cl', 'gbl', 'gen', 'obj', 'par', 'val']

        conns = {mod.lower(): mods[mod.lower()](self._dbconn.db_connection) for mod in dbmods}

        self._set_data(DATABASE_OBJECTS_PORT_NAME, conns, self._bus_name)

        return bci.RET_VAL_OK


"""
CHANGE LOG:
-----------
$Log: db_linker.py  $
Revision 1.9 2016/08/16 16:01:34CEST Hospes, Gerd-Joachim (uidv8815) 
fix epydoc errors
Revision 1.8 2016/08/12 17:34:20CEST Hospes, Gerd-Joachim (uidv8815)
extended docu
Revision 1.7 2016/07/06 15:37:27CEST Mertens, Sven (uidv7805)
use shared db connection
Revision 1.6 2016/04/12 15:04:59CEST Hospes, Gerd-Joachim (uidv8815)
fix docu during result saver implementation
Revision 1.5 2015/06/02 09:51:53CEST Mertens, Sven (uidv7805)
docu update
- Added comments -  uidv7805 [Jun 2, 2015 9:51:54 AM CEST]
Change Package : 338364:1 http://mks-psad:7002/im/viewissue?selection=338364
Revision 1.4 2015/05/19 18:03:19CEST Hospes, Gerd-Joachim (uidv8815)
extend docu
--- Added comments ---  uidv8815 [May 19, 2015 6:03:20 PM CEST]
Change Package : 336934:1 http://mks-psad:7002/im/viewissue?selection=336934
Revision 1.3 2015/05/12 15:41:39CEST Mertens, Sven (uidv7805)
adding possibility to use 'all' connections as previously done
--- Added comments ---  uidv7805 [May 12, 2015 3:41:40 PM CEST]
Change Package : 336932:1 http://mks-psad:7002/im/viewissue?selection=336932
Revision 1.2 2015/05/12 14:12:20CEST Mertens, Sven (uidv7805)
docu update
--- Added comments ---  uidv7805 [May 12, 2015 2:12:20 PM CEST]
Change Package : 336932:1 http://mks-psad:7002/im/viewissue?selection=336932
Revision 1.1 2015/05/12 13:53:39CEST Mertens, Sven (uidv7805)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/valf/obs/project.pj
"""
