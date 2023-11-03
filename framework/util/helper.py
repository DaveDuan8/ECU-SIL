# """
# framework/util/helper.py
# ------------------
#
# Stand alone utility functions.
#
#
# :org:           Continental AG
# :author:        Leidenberger, Ralf
#
# :version:       $Revision: 1.2 $
# :contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
# :date:          $Date: 2020/03/31 09:22:57CEST $
# """
# # pylint: disable=C0103
#
# - import Python modules ---------------------------------------------------------------------------------------------
from os import path, walk
from collections import OrderedDict


def list_folders(head_dir):
    """ Return list of sub folders

    :param head_dir: start directory to search files within
    :return: generator of path/to/files found
    """
    for root, dirs, _ in walk(head_dir, topdown=True):
        for dir_name in dirs:
            dir_path = path.join(root, dir_name)
            yield dir_path


def singleton(cls):
    """This is a decorator providing a singleton interface.

    for an example, have a look into logger module

    :param cls: class to create singleton interface from
    """
    _instances = {}

    def getinstance(*args, **kwargs):
        """checks and returns the instance of class (already being instantiated)

        :param args: std arguments to pass to __init__
        :param kwargs: xtra args to pass
        """

        # additional functionality to force a new instance,
        # e.g. to test a new Logger with different file
        if "stk_moduletest_purge_instance" in kwargs:
            kwargs.pop("stk_moduletest_purge_instance")
            if cls in _instances:
                _instances.pop(cls)

        if cls not in _instances:
            _instances[cls] = cls(*args, **kwargs)

        # if inits is not None:
        #     _instances[cls].initialize(**inits)

        return _instances[cls]
    return getinstance


class DefDict(OrderedDict):
    """I'm a default dict, but with my own missing method.

    .. code-block:: python

        from framework.util.helper import DefDict

        # set default to -1
        dct = DefDict(-1)
        # create key / value pairs: 'a'=0, 'b'=1, 'c'=-1, 'd'=-1
        dct.update((['a', 0], ['b', 1], 'c', 'd']))
        # prints 1
        print(dct['b'])
        # prints -1 (3rd index)
        print(dct[2])

    :param default: default value for missing key
    :type default: object
    """

    def __init__(self, default=None, **kwargs):
        OrderedDict.__init__(self)
        if len(kwargs) > 0:
            self.update(**kwargs)
        self._def = default

    def __getitem__(self, item):
        return self.values()[item] if type(item) == int else OrderedDict.__getitem__(self, item)

    def __missing__(self, _):
        return self._def


def arg_trans(mapping, *args, **kwargs):
    """argument transformation into dict with defaults

    :param mapping: list of argument names including their defaults
    :type mapping: list
    :param args: argument list
    :type args: list
    :param kwargs: named arguments with defaults
    :type kwargs: dict
    :return: dict with transferred arguments
    :rtype: dict
    """
    dflt = kwargs.pop('default', None)
    newmap = DefDict(dflt)
    k, l = 0, len(args)
    # update from mapping
    for i in mapping:
        key = i[0] if type(i) in (tuple, list) else i
        val = args[k] if l > k else (i[1] if type(i) in (tuple, list) else dflt)
        newmap[key] = val
        k += 1
    # update rest from args
    while k < l:
        newmap["arg%d" % k] = args[k]
        k += 1

    # update left over from kwargs
    newmap.update(kwargs)
    return newmap


def sec_to_hms_string(seconds):
    """ Converts seconds to an HMS string of the format 00:00:00.

    :param seconds: Input seconds.
    :return: HMS string
    """
    if seconds is not None:
        mins, secs = divmod(seconds, 60)
        hours, mins = divmod(mins, 60)
        return "%02d:%02d:%02d" % (hours, mins, secs)
    return ""


"""
CHANGE LOG:
-----------
$Log: helper.py  $
Revision 1.2 2020/03/31 09:22:57CEST Leidenberger, Ralf (uidq7596) 
initial update
Revision 1.1 2020/03/25 21:33:25CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/util/project.pj
"""
