"""
framework/util/find.py
----------------

Stand alone utility functions for class searches based on subclassing.


:org:           Continental AG
:author:        Leidenberger, Ralf

:version:       $Revision: 1.2 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/31 09:22:56CEST $
"""

# - import Python modules ---------------------------------------------------------------------------------------------
from os import path as opath, listdir
from sys import path as spath
from inspect import ismodule
import traceback


# - functions ---------------------------------------------------------------------------------------------------------
def instantiate_class(base_class, search, *args, **kwargs):
    """Uses find_class to search first for relevant classes, next to it uses
    first found and instantiates it and if available calling Initialize method.
    This is good to search for BaseDB related DB classes based upon SQLite
    or Oracle based. for a short test see the unit test under
    test_util/test_find.py.

    Additional parameters (args, kwargs) will be pushed through to class
    which will be instantiated and returned.

    :param base_class: find the class based on, e.g. framework.db.cl.SQLite3BaseDB
    :param search: could be path e.g. "framework\\db\\cl" or module, e.g. framework.db.cl
    :param args: additional arguments for class instanziation
    :param kwargs: even more arguments
    :return: instance of found class, already initialized
    """
    cls = find_class(base_class, search, kwargs.get('remove_duplicates', True))
    kwargs.pop('remove_duplicates', None)
    mod = cls[0]['type'](*args, **kwargs)
    return mod


def find_class(base_class, search, remove_duplicates=True, with_error_list=False):
    """
    Returns the classes found under search(path(s)) based upon base_class
    as list of dict. Dictionary contains the type and name of the item found.
    remove_duplicates indicates whether to remove found duplicates.
    If wanted it also returns the list of errors raised during the imports of
    the modules

    :param base_class: class name to search for
    :param search: path(s) or file(s) (string or list of strings) or module / object (already imported) list of
                   modules to search inside
    :param remove_duplicates: removes duplicates found, default: True
    :param with_error_list: returns additional list of errors raised during / module import, default: False
    :return: list of dict of candidates found: [{'type': ..., 'name': ...}, ...]
    """
    # recursive call to 'unpack' lists of paths or modules:
    if type(search) == list:
        if with_error_list:
            clist = []
            elist = []
            for i in search:
                ctmp, etmp = find_class(base_class, i, remove_duplicates, True)
                clist.extend(ctmp)
                elist.extend(etmp)
            return clist, elist
        else:
            classlist = []
            for entry in search:
                found = find_class(base_class, entry, remove_duplicates)
                classlist.extend(found)
            return classlist
    # for single path, file or module continue here:

    # return already imported module (module != file), mainly used in framework.db
    if ismodule(search):
        return (find_entry(base_class, search), []) if with_error_list else find_entry(base_class, search)

    mod_list = []
    err_list = []

    folder = search
    try:
        files = listdir(folder)
    except Exception as ex:
        # if listdir was called with file name:
        if opath.exists(search):
            files = [opath.basename(search)]
            folder = opath.dirname(search)
        else:
            # otherwise search was a not readable entry or empty resp. None
            # if needed classes were found in other paths/files then valf can
            # continue, otherwise to let valf on HPC close correctly
            # we return logging that error
            print("ERROR: '%s' (path not existing: %s)" % (str(ex), folder))
            return ([], ["ERROR on %s: '%s'" % (search, str(ex))]) if with_error_list else []

    # For all modules within the framework use absolute module path to
    # avoid problems with duplicate package names
    lst = []
    fpath = folder
    mod_path = ""

    while True:
        head, tail = opath.split(fpath)

        if tail == '':
            if head != '':
                lst.insert(0, head)
            break
        else:
            lst.insert(0, tail)
            if tail == 'framework':
                mod_path += ".".join(lst) + "."
                break
            fpath = head

    # now find the files inside
    for file_name in files:
        if (not file_name.startswith("__")) and file_name.endswith(".py"):
            mod_name = file_name.rsplit('.', 1)[0]
            if mod_path == "":
                if folder not in spath:
                    spath.append(folder)
                mod_list.append(mod_name)
            else:
                # add framework path to module name
                mod_list.append([mod_path + mod_name, mod_name])

    # try to import and check internals
    plug_list = []
    for mod_name in mod_list:
        try:
            # use relative or absolute (for all framework modules) import method
            if isinstance(mod_name, (list, tuple)):
                module = __import__(mod_name[0], globals(), locals(), mod_name[1], 0)
            else:
                module = __import__(mod_name)
        except ImportError:
            err_list.append((mod_name, traceback.format_exc()))
            continue

        plug_list.extend(find_entry(base_class, module))
        try:
            del module
        except ImportError:
            pass

    if remove_duplicates and len(plug_list) > 1:
        dups = []
        for idx0 in range(0, len(plug_list)):
            for idx1 in range(idx0 + 1, len(plug_list)):
                if plug_list[idx0]["name"] == plug_list[idx1]["name"]:
                    dups.append(idx1)

        for idx in sorted(set(dups), reverse=True):
            plug_list.pop(idx)

    return plug_list if not with_error_list else (plug_list, err_list)


def find_entry(base_class, module):
    """iterator through that module to search for base_class,
    used by find_class function

    :param base_class: class name to search for
    :param module: module to search for
    :return: list of pluggable interfaces (classes)
    """
    plugs = []
    for class_name, entry in list(module.__dict__.items()):
        try:
            if entry is None or str(entry).find("PyQt4") >= 0:
                continue

            if issubclass(entry, base_class) and entry != base_class:
                # self.__logger.debug("Found plugin.[Module: '%s', Class: '%s']." % (module_name, class_name))
                plugs.append({"type": entry, "name": class_name})
        except TypeError:
            # this happens when a non-type is passed in to issubclass. We
            # don't care as it can't be a subclass of PluginInterface if
            # it isn't a type
            continue
    return plugs


def find_subclasses(base_class, class_lst=None):
    """return list of own class and all currently known sub classes of the passed class

    param base_class: class to search subclasses
    type  base_class: object
    param class_lst:  used internally, list of classes in recursion
    type  class_lst:  list
    return class_list: list of all sub classes
    """
    if not class_lst:
        class_lst = [base_class]
    for subcl in base_class.__subclasses__():
        find_subclasses(subcl, class_lst)

        class_lst.append(subcl)
    return class_lst


"""
CHANGE LOG:
-----------
$Log: find.py  $
Revision 1.2 2020/03/31 09:22:56CEST Leidenberger, Ralf (uidq7596) 
initial update
Revision 1.1 2020/03/25 21:33:24CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/util/project.pj
"""
