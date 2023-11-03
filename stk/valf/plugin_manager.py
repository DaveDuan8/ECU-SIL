"""
stk/valf/plugin_manager
-----------------------

Manager for Plugins/Components (looking for PlugIns and using them)

:org:           Continental AG
:author:        Sorin Mogos

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:05:46CEST $
"""
# Import Python Modules -------------------------------------------------------
import os
import sys

# Import STK Modules ----------------------------------------------------------
from stk.util.logger import Logger
from stk.util.tds import UncRepl

# Defines ---------------------------------------------------------------------

# Functions -------------------------------------------------------------------

# Classes ---------------------------------------------------------------------


class PluginManager(object):
    """
    class to search for pluging classes based on 'BaseComponentInterface'
    to be used as observer components

    can check for dublicated class names to throw an error if it finds one
    """
    def __init__(self, folder_path_list, cls):
        """
        initialise a new object, adds existing folders of folder_path_list to sys.path

        :param folder_path_list: list [] of folders to check recursively
        :param cls: base class of which to find subclasses
        """
        self._uncrepl = UncRepl()
        self.__folder_path_list = [self._uncrepl(fpl) for fpl in folder_path_list]
        self.__cls = cls

        self.__logger = Logger(self.__class__.__name__)

        self.__folder_path_list = folder_path_list
        for folder_path in self.__folder_path_list:
            if folder_path not in sys.path:
                sys.path.append(folder_path)

    def __get_plugin_list(self, module_name_list):
        """
        returns list with plugins

        :param module_name_list: list of modules to search in
        :return: list of plugin classes

        """
        plugin_list = []

        for module_name in module_name_list:
            self.__logger.debug("Checking: %s.py..." % module_name)
            try:
                # use relative or absolute (for all stk modules) import method
                if isinstance(module_name, (list, tuple)):
                    module = __import__(module_name[0], globals(), locals(),
                                        module_name[1], 0)
                else:
                    module = __import__(module_name)
            except Exception as msg:
                self.__logger.warning("Couldn't import module '%s' due to '%s'" % (str(module_name), str(msg)))
                continue

            # look through this dictionary for classes
            # that are subclass of PluginInterface but are not PluginInterface itself
            module_candidates = list(module.__dict__.items())

            for class_name, entry in module_candidates:
                if class_name == self.__cls.__name__:
                    continue

                if entry is None:
                    continue

                if str(entry).find("PyQt4") > -1:
                    continue

                try:
                    if issubclass(entry, self.__cls):
                        self.__logger.debug("Found plugin.[Module: '%s', Class: '%s']." % (module_name, class_name))
                        plugin_list.append({"type": entry, "name": class_name})
                except TypeError:
                    # this happens when a non-type is passed in to issubclass. We
                    # don't care as it can't be a subclass of PluginInterface if
                    # it isn't a type
                    continue

        if len(plugin_list) > 0:
            return plugin_list

        return None

    def get_plugin_class_list(self, remove_duplicates=False):
        """searches stk path to find classes

        :param remove_duplicates: wether duplicates should be removed
        :return: list of classes
        """
        module_name_list = []
        for folder_path in self.__folder_path_list:
            try:
                file_list = os.listdir(folder_path)
            except OSError:
                continue

            # For all modules within the stk use absolute module path to
            # avoid problems with dublicate package names
            lst = []
            stk_found = False
            path = folder_path
            module_path = ""
            while stk_found is False:
                head, tail = os.path.split(path)

                if tail == '':
                    if head != '':
                        lst.insert(0, head)
                    break
                else:
                    lst.insert(0, tail)
                    path = head
                    if tail == 'stk':
                        stk_found = True
                        for p_k in lst:
                            module_path += p_k + "."

            for file_name in file_list:
                if file_name.endswith(".py") and not file_name.startswith("__") and not file_name.startswith("stk"):
                    module_name = file_name.rsplit('.', 1)[0]
                    if module_path == "":
                        module_name_list.append(module_name)
                    else:
                        # add stk path to module name
                        module_name_list.append([module_path + module_name, module_name])

        plugin_list = self.__get_plugin_list(module_name_list)
        if len(plugin_list) > 0:
            check_duplicates = self.__check_for_duplicate_classes(plugin_list)
            if check_duplicates == -1 and remove_duplicates is True:
                plugin_list = self.__remove_duplicate_classes(plugin_list)
                return plugin_list
            elif check_duplicates == 0:
                return plugin_list

        return None

    def __check_for_duplicate_classes(self, plugin_list):
        """ Check if there are any duplicates in the class list and throw an error if found.
        @param plugin_list: A list of the plugins found.
        @return: 0 for success and -1 if duplicate is found.
        """
        num_modules = len(plugin_list)
        for idx, module_name in enumerate(plugin_list):
            for i in range(idx + 1, num_modules):
                if module_name["name"] == plugin_list[i]["name"]:
                    self.__logger.error("Duplicate class name found: %s" % (module_name["name"]))
                    return -1
        return 0

    @staticmethod
    def __remove_duplicate_classes(plugin_list):
        """removes duplicate classes form plugin list
        """
        temp_mem = []
        copy_plugin_list = []

        for idx, module_name in enumerate(plugin_list):
            if module_name['name'] not in temp_mem:
                copy_plugin_list.append(plugin_list[idx])
                temp_mem.append(module_name['name'])

        return copy_plugin_list

"""
$Log: plugin_manager.py  $
Revision 1.1 2015/04/23 19:05:46CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/valf/project.pj
Revision 1.13 2015/03/24 11:33:32CET Mertens, Sven (uidv7805) 
importing Logger properly
--- Added comments ---  uidv7805 [Mar 24, 2015 11:33:32 AM CET]
Change Package : 318008:2 http://mks-psad:7002/im/viewissue?selection=318008
Revision 1.12 2015/01/30 10:01:14CET Mertens, Sven (uidv7805)
adding replacer for paths
Revision 1.11 2014/03/26 14:26:10CET Hecker, Robert (heckerr)
Adapted code to python 3.
--- Added comments ---  heckerr [Mar 26, 2014 2:26:10 PM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.10 2013/04/19 12:46:59CEST Hecker, Robert (heckerr)
Revert to old version.
--- Added comments ---  heckerr [Apr 19, 2013 12:47:00 PM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.9 2013/04/12 14:47:14CEST Mertens, Sven (uidv7805)
enabling the use of a connection string on observer level.
Each of them is allowed to have an additional InputData in config,
e.g. ("connectionString", "DBQ=racadmpe;Uid=DEV_MFC31X_ADMIN;Pwd=MFC31X_ADMIN"),
("dbPrefix", "DEV_MFC31X_ADMIN.").
--- Added comments ---  uidv7805 [Apr 12, 2013 2:47:15 PM CEST]
Change Package : 179495:1 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.8 2013/04/05 11:17:43CEST Hospes, Gerd-Joachim (uidv8815)
fix documentation
--- Added comments ---  uidv8815 [Apr 5, 2013 11:17:43 AM CEST]
Change Package : 169590:2 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.7 2013/03/01 10:23:24CET Hecker, Robert (heckerr)
Updates regarding Pep8 Styleguides.
--- Added comments ---  heckerr [Mar 1, 2013 10:23:24 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.6 2013/02/27 16:19:56CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 27, 2013 4:19:57 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.5 2013/02/26 20:18:06CET Raedler, Guenther (uidt9430)
- Updates after Pep8 Styleguides
--- Added comments ---  uidt9430 [Feb 26, 2013 8:18:06 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.4 2013/02/26 16:46:00CET Raedler, Guenther (uidt9430)
- fixed mis up of tabs and spaces (don't edit in beyond compare)
--- Added comments ---  uidt9430 [Feb 26, 2013 4:46:01 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.3 2013/02/26 16:34:35CET Raedler, Guenther (uidt9430)
- add modules in STK with the absolute import method.
Avoid conflicts if packages have the same name
--- Added comments ---  uidt9430 [Feb 26, 2013 4:34:35 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.2 2013/02/19 21:25:38CET Hecker, Robert (heckerr)
Updates according Pep8 Styleguides.
--- Added comments ---  heckerr [Feb 19, 2013 9:25:38 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.1 2013/02/11 11:06:08CET Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/valf/project.pj
------------------------------------------------------------------------------
-- From etk/valf Archive
------------------------------------------------------------------------------
Revision 1.8 2012/07/18 09:06:19CEST Hammernik-EXT, Dmitri (uidu5219)
- added functionality to remove duplicates
--- Added comments ---  uidu5219 [Jul 18, 2012 9:06:20 AM CEST]
Change Package : 100180:1 http://mks-psad:7002/im/viewissue?selection=100180
Revision 1.7 2011/07/21 16:06:10CEST Castell, Christoph (uidt6394)
Added check for duplicate classes.
--- Added comments ---  uidt6394 [Jul 21, 2011 4:06:12 PM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.6 2010/11/24 10:15:21CET Sorin Mogos (mogoss)
* improved error handling
--- Added comments ---  mogoss [Nov 24, 2010 10:15:22 AM CET]
Change Package : 51595:1 http://mks-psad:7002/im/viewissue?selection=51595
Revision 1.5 2010/07/28 11:28:53CEST Sorin Mogos (mogoss)
* code customisation
--- Added comments ---  mogoss [Jul 28, 2010 11:28:53 AM CEST]
Change Package : 47041:2 http://mks-psad:7002/im/viewissue?selection=47041
Revision 1.4 2010/06/28 14:46:10EEST Sorin Mogos (smogos)
* added configuration manager
--- Added comments ---  smogos [2010/06/28 11:46:10Z]
Change Package : 37850:1 http://LISS014:6001/im/viewissue?selection=37850
Revision 1.3 2010/03/19 10:37:39EET Sorin Mogos (smogos)
* code customisation and bug-fixes
--- Added comments ---  smogos [2010/03/19 08:37:39Z]
Change Package : 37850:1 http://LISS014:6001/im/viewissue?selection=37850
Revision 1.2 2010/02/18 15:29:28EET Sorin Mogos (smogos)
* code optimisation and bug-fixes
--- Added comments ---  smogos [2010/02/18 13:29:29Z]
Change Package : 37850:1 http://LISS014:6001/im/viewissue?selection=37850
Revision 1.1 2009/10/30 14:18:42EET dkubera
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/ETK_EngineeringToolKit/04_Engineering/VALF_ValidationFrame/
04_Engineering/31_PyLib/project.pj
"""
