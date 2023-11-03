"""
framework/valf/plugin_manager
-----------------------

Manager for Plugins/Components (looking for PlugIns and using them)

:org:           Continental AG
:author:        Leidenberger, Ralf

:version:       $Revision: 1.2 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/31 10:14:11CEST $
"""
# Import Python Modules -------------------------------------------------------
import os
import sys

# Import framework Modules ----------------------------------------------------------
from framework.util.logger import Logger
from framework.util.tds import UncRepl

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
                # use relative or absolute (for all framework modules) import method
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
        """searches framework path to find classes

        :param remove_duplicates: wether duplicates should be removed
        :return: list of classes
        """
        module_name_list = []
        for folder_path in self.__folder_path_list:
            try:
                file_list = os.listdir(folder_path)
            except OSError:
                continue

            # For all modules within the framework use absolute module path to
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
                    if tail == 'framework':
                        stk_found = True
                        for p_k in lst:
                            module_path += p_k + "."

            for file_name in file_list:
                if file_name.endswith(".py") and not file_name.startswith("__") and not file_name.startswith("framework"):
                    module_name = file_name.rsplit('.', 1)[0]
                    if module_path == "":
                        module_name_list.append(module_name)
                    else:
                        # add framework path to module name
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
Revision 1.2 2020/03/31 10:14:11CEST Leidenberger, Ralf (uidq7596) 
initial update
Revision 1.1 2020/03/25 21:38:08CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/valf/project.pj
"""
