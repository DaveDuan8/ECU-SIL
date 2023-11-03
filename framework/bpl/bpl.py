"""
framework/mts/bpl
-----------

Classes for BPL (BatchPlayList) Handling

**main class**

`Bpl`    container for :py:class:`BplList`, provide read() and write() methods

**sub classes**

`BplList`       list of `BplListEntry` elements
`BplListEntry`  providing filepath or rec file and list of `Section` elements
`Section`       start and end time stamp, relative or absolute flag

(see structure in `Bpl` class docu)

Bpl file operations (for \*.bpl files) like merge or diff are also provided in `framework.cmd.bpl_operator`.

:org:           Continental AG
:author:        Leidenberger, Ralf

:version:       $Revision: 1.2 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/31 09:00:47CEST $
"""
# - import Python modules ---------------------------------------------------------------------------------------------
from os.path import isfile, getsize

# - import framework modules ------------------------------------------------------------------------------------------------
from framework.bpl.bpl_xml import BPLXml
from framework.bpl.bpl_base import BplListEntry, BplException
from framework.util.helper import DefDict

# - defines ------------------------------------------------------------------------------------------------------------
BPL_SUPPORTS = DefDict(default=BPLXml, **{".bpl": BPLXml})


# - functions ---------------------------------------------------------------------------------------------------------


def __get_file_size_mb(filepath):
    """
    Returns the File Size of a File in Megabytes (MB)
    """
    if isfile(filepath):
        file_size = getsize(filepath)
        file_size /= 1000  # B  -> KB
        file_size /= 1000  # KB -> MB
    else:
        file_size = 1.0

    return file_size


def create(entries, path):
    """
    Creates a single bpl-file out of some given bpllistentries.

    :param entries: list of BplListEntries
    :type entries:  list[`BplListEntry`]
    :param path:    path to the file to be created.
    :type path:     string
    """
    with Bpl(path, "w") as out_bpl:
        for entry in entries:
            out_bpl.append(entry)


# - classes ------------------------------------------------------------------------------------------------------------
class Bpl(object):
    r"""
    Possibility to read and write Batch Play Lists supported by mts.

    Currently \*.ini, \*.txt and \*.bpl based BatchPlayLists are supported.
    The file structure is automatically selected by the ending.

    - \*.bpl files based on xml and support section definitions for the rec files
    - \*ini, \*.txt files simply list the complete path and file name

    **structure:**

    ::

        `BplList`  -  list (`BplListEntry`)
                              |
                              +- filename (str)
                              |
                              -- sectionlist (list(`Section`))
                                                   |
                                                   +- start_ts (long)
                                                   +- end_ts (long)
                                                   +- rel (bool)

    In case of BplList read from \*.ini or \*.txt file the sectionlist is empty.

    **usage (example)**

    .. code-block:: python

        # Create an instance of your BPL-Reader
        bpl = framework.mts.Bpl(r"D:\testdir\MyBatchPlayList.bpl")

        # Get whole RecFile List out from bpl file
        bpllist = bpl.read()                        # type: BplList

        # Iterate over whole list in a for loop
        for bplentry in bpllist:                    # type: BplListEntry
            recfilename = str(recfile) # Convertion to string is mandatory !!!.
            for section in recfile.sectionlist:     # type: Section
                start = section.start_ts
                end = section.end_ts
                is_relative_timestamp = section.rel

    The internal Bpl structure is ported from mts, but you can convert it to a dict if needed.
    Similar there is a method to convert the Section to a list:

     .. code-block:: python

        list_dict = bpllist.bpl2dict()
        secttupel = bpllist[0].sectionlist[0].sect2list()  # tuple(<start_ts>, <end_ts>, <rel>)

    Functions to create a BPL files for different usecases are available in module `bpl` .


    :author:        Robert Hecker
    :date:          12.02.2013

    """
    def __new__(cls, filepath, *args, **kwargs):
        try:
            if hasattr(filepath, "read"):
                fname = filepath.name
            else:
                fname = filepath
            return BPL_SUPPORTS[fname[-4:].lower()](filepath, *args, **kwargs)
        except KeyError:
            raise BplException("Unsupported file format: '%s'." % filepath[-3:], KeyError)
        except Exception as _:
            raise BplException("Unable to open file '%s'." % filepath, _)

    def read(self):
        """read in"""
        print("empty implementation in the super class" + self.fname)
        pass

    def write(self):
        """write out"""
        print("empty implementation in the super class" + self.fname)
        pass


"""
CHANGE LOG:
-----------
$Log: bpl.py  $
Revision 1.2 2020/03/31 09:00:47CEST Leidenberger, Ralf (uidq7596) 
initial update
Revision 1.1 2020/03/25 20:58:03CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/bpl/project.pj
"""
