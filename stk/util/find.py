"""
stk/util/find.py
----------------

Stand alone utility functions for class searches based on subclassing.


:org:           Continental AG
:author:        Sven Mertens

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:05:30CEST $
"""

# - import Python modules ---------------------------------------------------------------------------------------------
from os import path as opath, listdir
from sys import path as spath
from inspect import ismodule
import traceback

# - import STK modules ------------------------------------------------------------------------------------------------
from stk.util.helper import deprecated


# - functions ---------------------------------------------------------------------------------------------------------
def instantiate_class(base_class, search, *args, **kwargs):
    """Uses find_class to search first for relevant classes, next to it uses
    first found and instantiates it and if available calling Initialize method.
    This is good to search for BaseDB related DB classes based upon SQLite
    or Oracle based. for a short test see the unit test under
    test_util/test_find.py.

    Additional parameters (args, kwargs) will be pushed through to class
    which will be instantiated and returned.

    :param base_class: find the class based on, e.g. stk.db.cl.SQLite3BaseDB
    :param search: could be path e.g. "stk\\db\\cl" or module, e.g. stk.db.cl
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

    # return already imported module (module != file), mainly used in stk.db
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

    # For all modules within the stk use absolute module path to
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
            if tail == 'stk':
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
                # add stk path to module name
                mod_list.append([mod_path + mod_name, mod_name])

    # try to import and check internals
    plug_list = []
    for mod_name in mod_list:
        try:
            # use relative or absolute (for all stk modules) import method
            if isinstance(mod_name, (list, tuple)):
                module = __import__(mod_name[0], globals(), locals(), mod_name[1], 0)
            else:
                module = __import__(mod_name)
        except Exception:
            err_list.append((mod_name, traceback.format_exc()))
            continue

        plug_list.extend(find_entry(base_class, module))
        try:
            del module
        except:
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


@deprecated('instantiate_class')
def instantiateClass(base_class, search, *args, **kwargs):  # pylint: disable=C0103
    """deprecated"""
    return instantiate_class(base_class, search, *args, **kwargs)


@deprecated('find_class')
def findClass(base_class, search, remove_duplicates=True, with_error_list=False):  # pylint: disable=C0103
    """deprecated"""
    return find_class(base_class, search, remove_duplicates, with_error_list)


@deprecated('find_entry')
def findEntry(base_class, module):  # pylint: disable=C0103
    """deprecated"""
    return find_entry(base_class, module)


"""
CHANGE LOG:
-----------
$Log: find.py  $
Revision 1.1 2015/04/23 19:05:30CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/util/project.pj
Revision 1.12 2015/03/09 09:36:58CET Mertens, Sven (uidv7805) 
docu update
--- Added comments ---  uidv7805 [Mar 9, 2015 9:36:59 AM CET]
Change Package : 314290:1 http://mks-psad:7002/im/viewissue?selection=314290
Revision 1.11 2015/01/23 21:44:22CET Ellero, Stefano (uidw8660)
Removed all util based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Jan 23, 2015 9:44:23 PM CET]
Change Package : 296837:1 http://mks-psad:7002/im/viewissue?selection=296837
Revision 1.10 2014/12/16 19:23:06CET Ellero, Stefano (uidw8660)
Remove all db.obj based deprecated function usage inside STK and module tests.
Revision 1.9 2014/03/24 21:56:55CET Hecker, Robert (heckerr)
Adapted to python 3.
--- Added comments ---  heckerr [Mar 24, 2014 9:56:55 PM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.8 2014/03/20 22:50:10CET Hecker, Robert (heckerr)
One more BugFix to get UnitTest working.
--- Added comments ---  heckerr [Mar 20, 2014 10:50:10 PM CET]
Change Package : 224339:1 http://mks-psad:7002/im/viewissue?selection=224339
Revision 1.6 2013/11/22 15:45:56CET Hospes, Gerd-Joachim (uidv8815)
fixed list of paths/files, logging error for unreadable entries, expand test suite to check lists
--- Added comments ---  uidv8815 [Nov 22, 2013 3:45:56 PM CET]
Change Package : 207698:1 http://mks-psad:7002/im/viewissue?selection=207698
Revision 1.5 2013/10/01 15:05:22CEST Hospes, Gerd-Joachim (uidv8815)
internal list adaption to simple format, '-->' added during output
--- Added comments ---  uidv8815 [Oct 1, 2013 3:05:23 PM CEST]
Change Package : 196951:1 http://mks-psad:7002/im/viewissue?selection=196951
Revision 1.4 2013/10/01 14:21:16CEST Hospes, Gerd-Joachim (uidv8815)
FR199155: fix error msg for observer load problems
--- Added comments ---  uidv8815 [Oct 1, 2013 2:21:16 PM CEST]
Change Package : 196951:1 http://mks-psad:7002/im/viewissue?selection=196951
Revision 1.3 2013/06/21 14:24:53CEST Mertens, Sven (uidv7805)
find_class returns instance when searching for module instead of list of dict.
adding new function to search and doing the instance actually.
--- Added comments ---  uidv7805 [Jun 21, 2013 2:24:53 PM CEST]
Change Package : 185933:1 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.2 2013/06/13 15:26:01CEST Mertens, Sven (uidv7805)
fix: adaptation for single file as search argument
--- Added comments ---  uidv7805 [Jun 13, 2013 3:26:01 PM CEST]
Change Package : 185933:3 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.1 2013/05/23 06:28:03CEST Mertens, Sven (uidv7805)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/04_Engineering/
    stk/util/project.pj
"""
