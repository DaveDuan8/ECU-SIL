"""
stk/mts/bpl
-----------

Classes for BPL (BatchPlayList) Handling

**main class**

`Bpl`    container for `BplList`, provide read() and write() methods

**sub classes**

`BplList`       list of `BplListEntry` elements
`BplListEntry`  providing filepath or rec file and list of `Section` elements
`Section`       start and end time stamp, relative or absolute flag

(see structure in `Bpl` class docu)

Bpl file operations (for \*.bpl files) like merge or diff are also provided in `stk.cmd.bpl_operator`.

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.2 $
:contact:       $Author: Mertens, Sven (uidv7805) $ (last change)
:date:          $Date: 2016/07/26 16:14:49CEST $
"""
# - import Python modules ---------------------------------------------------------------------------------------------
from os import path as opath

# - import STK modules ------------------------------------------------------------------------------------------------
from stk.mts.bpl.bpl_xml import BPLXml
from stk.mts.bpl.bpl_ini import BPLIni
from stk.mts.bpl.bpl_txt import BPLTxt
from stk.mts.bpl.bpl_base import BplListEntry, BplException
from stk.util.helper import deprecated
from stk.util.url import remove_fqn

# - defines -----------------------------------------------------------------------------------------------------------
BPL_SUPPORTS = {"bpl": BPLXml, "ini": BPLIni, "txt": BPLTxt}

# - functions ---------------------------------------------------------------------------------------------------------


def lifs010s_to_lifs010(in_path):
    """
    checks a given input path for 'lifs010s' inside the path, replace it
    with 'lifs010' and return the corrected path.

    :param in_path: path to the recording
    :type  in_path: string
    """

    path = in_path.lower()

    if "lifs010s" in path:
        path = path.replace("lifs010s", "lifs010")

    return path


@deprecated('stk.util.tds.replace_lifs')
def lifs010_to_lifs010s(in_path):
    """
    checks a given input path for 'lifs010' inside the path, replace it
    with 'lifs010s' and return the corrected path.

    :deprecated: please use stk.util.tds.replace_lifs() instead

    :param in_path: path to the recording
    :type  in_path: string
    """
    path = in_path.lower()

    if "lifs010." in path:
        path = path.replace("lifs010.", "lifs010s.")

    if "lifs010\\" in path:
        path = path.replace("lifs010\\", "lifs010s\\")

    return path


def diff(set_a, set_b, diff_bpl):
    """
    create a \*.bpl of all entries, which are inside the set_a and not in set_b.

    Support of xml style bpls, ini style bpl, and txt file bpls.

    Compare is not case sensitive.
    Compare is independent from FQN usage.

    :param set_a:         Paths to the reference \*.bpl
    :type set_a:          list[string]
    :param set_b:         Paths to the part bpl's
    :type set_b:          list[string]
    :param diff_bpl:      path to the resulting bpl
    :type diff_bpl:       string
    :return:              None
    """
    # Read the reference List
    reference_txt = []
    for ref_bpl in set_a:
        reference = Bpl(ref_bpl)
        reference_list = reference.read()
        for item in reference_list:
            reference_txt.append(remove_fqn(str(item)))

    part_txt = []
    # Read the Sub List(s)
    for part_bpl in set_b:
        part = Bpl(part_bpl)
        part_list = part.read()
        for item in part_list:
            part_txt.append(remove_fqn(str(item)).lower())

    # Do the Diff
    # Go through the whole reference and check for duplicates in sub
    # if no Duplicate found write it to output.
    diff_txt = []

    for item in reference_txt:
        if item.lower() not in part_txt:
            diff_txt.append(item)

    result = Bpl(diff_bpl)

    for item in diff_txt:
        result.append(BplListEntry(item))

    result.write()

    return None


def sym_diff(set_a, set_b, diff_bpl):
    """
    Create a diff_bpl with all files inside that are a member of exactly one of set_a and set_b.

    Support of xml style bpls, ini style bpl, and txt file bpls.
    Compare is not case sensitive.
    Compare is independent from FQN usage.

    :param set_a:    Paths to bpl files
    :type set_a:     list[string]
    :param set_b:    Path to bpl files
    :type set_b:     list[string]
    :param diff_bpl: path to the resulting bpl file
    :type diff_bpl:  string
    :return:         None
    """

    ref_txt = []
    for ref_bpl in set_a:
        ref = Bpl(ref_bpl)
        ref_list = ref.read()
        for item in ref_list:
            ref_txt.append(remove_fqn(str(item)).lower())

    part_txt = []
    for part_bpl in set_b:
        part = Bpl(part_bpl)
        part_list = part.read()
        for item in part_list:
            part_txt.append(remove_fqn(str(item)).lower())

    diff_list = set(ref_txt).symmetric_difference(set(part_txt))

    diff_bpl = Bpl(diff_bpl)

    for item in diff_list:
        diff_bpl.append(BplListEntry(item))

    diff_bpl.write()

    return None


def merge(in_bpls, out_bpl):
    """
    merge all given input bpls to a single output bpl without any duplicates.
    duplicates will be removed.

    :note: Sections entries will be deleted and not used inside the
           output files.

    :param in_bpls: File names of the input batchplaylists.
    :type in_bpls:  list[string]
    :param out_bpl: Output Filename of the bpl which must be created.
    :type out_bpl:  string
    """

    out = Bpl(out_bpl)

    outlist = []

    for filename in in_bpls:
        # Remove all Sections
        for i in Bpl(filename).read():
            if i not in outlist:
                outlist.append(i)

    for i in outlist:
        out.append(i)

    out.write()


def __get_file_size_mb(filepath):
    """
    Returns the File Size of a File in Megabytes (MB)
    """
    if opath.isfile(filepath):
        file_size = opath.getsize(filepath)
        file_size /= 1024  # B  -> KB
        file_size /= 1024  # KB -> MB
    else:
        file_size = 1.0

    return file_size


def single_split(bplfilepath, outfolder):
    """
    Split a bpl-file into singel bpl's which
    contians the original section information.

    :param bplfilepath: Filepath(url) to the bpl file..
    :type bplfilepath:  string
    :param outfolder:   Folder to store the generated bpl files.
    :type outfolder:    string
    :return:            Array of created bpl files.
    :rtype:             list of bpl paths.
    :author:            Robert Hecker
    :date:              06.08.2013
    """
    bpllist = []

    # Open the *.bpl file
    bpl = Bpl(bplfilepath)
    # Read the whole list
    inputlist = bpl.read()

    counter = 1

    for item in inputlist:
        # Create a new BPL File in TaskName style
        file_name = "Rec%05d.bpl" % counter
        counter += 1
        out_bpl = Bpl(opath.join(outfolder, file_name))
        out_bpl.append(item)
        out_bpl.write()
        bpllist.append(opath.join(outfolder, file_name))

    return bpllist


def create(entries, path):
    """
    Creates a single bpl-file out of some given bpllistentries.

    :param entries: list of BplListEntries
    :type entries:  list[`BplListEntry`]
    :param path:    path to the file to be created.
    :type path:     string
    """
    out_bpl = Bpl(path)

    for entry in entries:
        out_bpl.append(entry)

    out_bpl.write()


def split(bplfilepath, task_size, outfolder=None):
    """
    Split a bpl-file into bpl's with the given task_size which
    contians the original section information.

    :param bplfilepath: Filepath(url) to the bpl file..
    :type bplfilepath:  string
    :param task_size:   Number of recordings per file.
    :type task_size:    int
    :param outfolder:   Folder to store the generated bpl files.
    :type outfolder:    string
    :return:            Array of created bpl files.
    :rtype:             list of bpl paths.
    :author:            Guenther Raedler
    :date:              16.09.2013
    """
    bpllist = []

    # Open the *.bpl file
    bpl = Bpl(bplfilepath)
    # Read the whole list
    inputlist = bpl.read()

    task_cnt = 0
    counter = 0
    while counter < len(inputlist):
        # Create a new BPL File in TaskName style
        file_name = "T%05d.bpl" % (task_cnt + 1)
        out_bpl = Bpl(opath.join(outfolder, file_name))
        file_cnt = 0
        while file_cnt < task_size and counter < len(inputlist):
            item = inputlist[counter]
            out_bpl.append(item)
            file_cnt += 1
            counter += 1

        task_cnt += 1
        out_bpl.write()
        bpllist.append(opath.join(outfolder, file_name))

    return bpllist


def split_parts(bplfilepath, parts, outfolder=None):
    """
    Split a Bpl BatchList into n parts.
    The splitting algorithm tries to split all files regarding the filesize
    of the recording. So one split.bpl file could contain less files,
    if the files have a bigger filesize.
    The pbl Files which are splitted, will be saved in the same folder like
    the original bplfile was found.

    :param bplfilepath: Filepath(url) to the bpl or ini file.
    :type bplfilepath:  string
    :param parts:        Number of wanted splits.
    :type parts:         integer
    :return:            nothing
    :rtype:             None
    :author:            Robert Hecker
    :date:              12.02.2013
    """

    if outfolder is None:
        outfolder = opath.split(bplfilepath)[0]

    # Open the existing bplfilelist and get all members
    bpl = Bpl(bplfilepath)
    rec_list = bpl.read()

    # Get for every File the Filesize
    file_size_list = [__get_file_size_mb(str(item)) for item in rec_list]

    # Calculate the Total Size
    total_size = sum(file_size_list)

    file_part_size = total_size / parts

    file_part = 0
    idx = 0
    file_part_list = []
    # Create all Filepart lists
    while idx < len(file_size_list):

        # Create One Bpl-Content
        bpl_size = 0
        bpl_list = []
        while bpl_size < file_part_size or (file_part + 1) == parts:
            # Append New Element to Current BPL List
            bpl_list.append(rec_list[idx])
            # Increase BplSize
            bpl_size += file_size_list[idx]
            idx += 1
            if idx >= len(file_size_list):
                break
        # Increase FilePart Index
        file_part += 1
        # Add BplList to final List
        file_part_list.append(bpl_list)

    # Writes the BPL File Parts into new BPL Files
    head, ext = opath.splitext(bplfilepath)

    for idx in range(0, len(file_part_list)):
        file_part = file_part_list[idx]
        tmp = "_part_%02d_of_%02d%s" % (idx + 1, parts, ext)
        file_part_pathname = opath.join(outfolder, head + tmp)
        writer = Bpl(file_part_pathname)
        for file_part_member in file_part:
            writer.append(file_part_member)
        writer.write()


# - classes ------------------------------------------------------------------------------------------------------------
class Bpl(object):
    """
    Possibility to read and write Batch Play Lists supported by mts.

    Currently \*.ini, \*.txt and \*.bpl based BatchPlayLists are supported.
    The file structure is automatically selected by the ending.

    - \*.bpl files based on xml and support section definitions for the rec files
    - \*ini, \*.txt files simply list the complete path and file name

    structure:
    ----------

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

    usage (example)
    ---------------
    .. python::

        # Create an instance of your BPL-Reader
        bpl = stk.mts.Bpl(r"D:\testdir\MyBatchPlayList.bpl")

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

     .. python::

        list_dict = bpllist.bpl2dict()
        secttupel = bpllist[0].sectionlist[0].sect2list()  # tuple(<start_ts>, <end_ts>, <rel>)

    Functions to create a BPL files for different usecases are available in module `bpl` .


    :author:        Robert Hecker
    :date:          12.02.2013

    """
    def __new__(cls, filepath):
        try:
            return BPL_SUPPORTS[filepath[-3:].lower()](filepath)
        except KeyError:
            raise BplException("Unsupported file format: '%s'." % filepath[-3:], 1)
        except:
            raise BplException("Unable to open file '%s'." % filepath, 2)

    def read(self):
        """read file"""
        pass

    def write(self):
        """write file"""
        pass

    def append(self, _):
        """append item"""
        pass


def bpl_file_support(filepath):
    """:return: True if filepath is supported by BPL class
    """
    return filepath[-3:].lower() in BPL_SUPPORTS.keys()


@deprecated('__get_file_size_mb')
def __getFileSizeMB(filepath):  # pylint: disable=C0103
    """:deprecated: please use __get_file_size_mb()instead
    """
    return __get_file_size_mb(filepath)


@deprecated('single_split')
def singleSplit(bplfilepath, outfolder):  # pylint: disable=C0103
    """:deprecated: please use single_split()instead
    """
    return single_split(bplfilepath, outfolder)


"""
CHANGE LOG:
-----------
$Log: bpl.py  $
Revision 1.2 2016/07/26 16:14:49CEST Mertens, Sven (uidv7805) 
a bit of simplification
Revision 1.1 2015/04/23 19:04:43CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/mts/bpl/project.pj
Revision 1.39 2015/04/23 15:19:10CEST Hospes, Gerd-Joachim (uidv8815) 
enhance docu
--- Added comments ---  uidv8815 [Apr 23, 2015 3:19:11 PM CEST]
Change Package : 328888:1 http://mks-psad:7002/im/viewissue?selection=328888
Revision 1.38 2015/02/09 18:26:58CET Ellero, Stefano (uidw8660) 
Removed all mts based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Feb 9, 2015 6:26:58 PM CET]
Change Package : 301800:1 http://mks-psad:7002/im/viewissue?selection=301800
Revision 1.37 2015/02/06 08:10:16CET Mertens, Sven (uidv7805) 
using absolute imports
--- Added comments ---  uidv7805 [Feb 6, 2015 8:10:16 AM CET]
Change Package : 303748:1 http://mks-psad:7002/im/viewissue?selection=303748
Revision 1.36 2014/12/09 12:38:14CET Mertens, Sven (uidv7805)
adding dummy members
--- Added comments ---  uidv7805 [Dec 9, 2014 12:38:15 PM CET]
Change Package : 281276:1 http://mks-psad:7002/im/viewissue?selection=281276
Revision 1.35 2014/12/08 13:08:13CET Mertens, Sven (uidv7805)
update according related CR
--- Added comments ---  uidv7805 [Dec 8, 2014 1:08:13 PM CET]
Change Package : 288767:1 http://mks-psad:7002/im/viewissue?selection=288767
Revision 1.34 2014/11/11 19:53:09CET Hecker, Robert (heckerr)
Added new diff function.
--- Added comments ---  heckerr [Nov 11, 2014 7:53:10 PM CET]
Change Package : 280240:1 http://mks-psad:7002/im/viewissue?selection=280240
Revision 1.33 2014/11/11 11:08:55CET Hecker, Robert (heckerr)
removed one function to helper package.
--- Added comments ---  heckerr [Nov 11, 2014 11:08:56 AM CET]
Change Package : 279920:1 http://mks-psad:7002/im/viewissue?selection=279920
Revision 1.32 2014/11/11 10:56:18CET Hecker, Robert (heckerr)
Added asymetric diff.
--- Added comments ---  heckerr [Nov 11, 2014 10:56:19 AM CET]
Change Package : 279920:1 http://mks-psad:7002/im/viewissue?selection=279920
Revision 1.31 2014/11/05 15:30:37CET Ahmed, Zaheer (uidu7634)
defined get_bpl_list_entries in abstract class
--- Added comments ---  uidu7634 [Nov 5, 2014 3:30:37 PM CET]
Change Package : 274722:1 http://mks-psad:7002/im/viewissue?selection=274722
Revision 1.30 2014/10/13 13:17:45CEST Mertens, Sven (uidv7805)
removing some pylints
--- Added comments ---  uidv7805 [Oct 13, 2014 1:17:46 PM CEST]
Change Package : 271081:1 http://mks-psad:7002/im/viewissue?selection=271081
Revision 1.29 2014/10/13 11:14:07CEST Mertens, Sven (uidv7805)
moving BplList, PplListEntry and Section class to base as being recursively imported
--- Added comments ---  uidv7805 [Oct 13, 2014 11:14:08 AM CEST]
Change Package : 271081:1 http://mks-psad:7002/im/viewissue?selection=271081
Revision 1.28 2014/09/19 13:37:54CEST Hospes, Gerd-Joachim (uidv8815)
add __str__ and sect2list for easy Section usage
--- Added comments ---  uidv8815 [Sep 19, 2014 1:37:55 PM CEST]
Change Package : 264210:1 http://mks-psad:7002/im/viewissue?selection=264210
Revision 1.27 2014/08/29 13:49:23CEST Hospes, Gerd-Joachim (uidv8815)
using new module stk.util.tds and its functions to change LIFS010 to fast server
--- Added comments ---  uidv8815 [Aug 29, 2014 1:49:24 PM CEST]
Change Package : 259660:1 http://mks-psad:7002/im/viewissue?selection=259660
Revision 1.26 2014/07/17 15:06:14CEST Hospes, Gerd-Joachim (uidv8815)
get merge_recfile_sections again, add bpl2dict in bpl, add / update tests
--- Added comments ---  uidv8815 [Jul 17, 2014 3:06:15 PM CEST]
Change Package : 245477:1 http://mks-psad:7002/im/viewissue?selection=245477
Revision 1.25 2014/07/15 09:37:49CEST Hecker, Robert (heckerr)
Added Functions to move from lifs010s to lifs010 path and vice versa.
--- Added comments ---  heckerr [Jul 15, 2014 9:37:49 AM CEST]
Change Package : 248675:1 http://mks-psad:7002/im/viewissue?selection=248675
Revision 1.24 2014/07/14 14:37:49CEST Hecker, Robert (heckerr)
Removed all associated Sections from the recs inside mts.bpl.merge.
--- Added comments ---  heckerr [Jul 14, 2014 2:37:49 PM CEST]
Change Package : 248434:1 http://mks-psad:7002/im/viewissue?selection=248434
Revision 1.23 2014/07/11 16:54:40CEST Hecker, Robert (heckerr)
Added Suport for plain txt files with recs in lines.
--- Added comments ---  heckerr [Jul 11, 2014 4:54:41 PM CEST]
Change Package : 248151:1 http://mks-psad:7002/im/viewissue?selection=248151
Revision 1.22 2014/06/24 14:58:59CEST Hecker, Robert (heckerr)
Implemented Functionality.
--- Added comments ---  heckerr [Jun 24, 2014 2:58:59 PM CEST]
Change Package : 244086:1 http://mks-psad:7002/im/viewissue?selection=244086
Revision 1.21 2014/04/02 13:26:17CEST Hecker, Robert (heckerr)
Added check for LIFS010S usage.
Added possibility to use a new method called create_tasks(bplfile)
--- Added comments ---  heckerr [Apr 2, 2014 1:26:17 PM CEST]
Change Package : 227500:1 http://mks-psad:7002/im/viewissue?selection=227500
Revision 1.20 2014/03/24 21:08:10CET Hecker, Robert (heckerr)
Adapted code to python 3.
--- Added comments ---  heckerr [Mar 24, 2014 9:08:10 PM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.19 2014/03/16 21:55:47CET Hecker, Robert (heckerr)
added pylintrc.
--- Added comments ---  heckerr [Mar 16, 2014 9:55:47 PM CET]
Change Package : 225494:1 http://mks-psad:7002/im/viewissue?selection=225494
Revision 1.18 2013/09/24 15:50:07CEST Raedler, Guenther (uidt9430)
- enable original split function and renamed it
--- Added comments ---  uidt9430 [Sep 24, 2013 3:50:07 PM CEST]
Change Package : 198327:1 http://mks-psad:7002/im/viewissue?selection=198327
Revision 1.17 2013/09/24 15:47:07CEST Raedler, Guenther (uidt9430)
- Add new splitting function to support BLF section simulations (ARS353, ARs4xx)
--- Added comments ---  uidt9430 [Sep 24, 2013 3:47:08 PM CEST]
Change Package : 198327:1 http://mks-psad:7002/im/viewissue?selection=198327
Revision 1.16 2013/08/08 08:37:11CEST Hospes, Gerd-Joachim (uidv8815)
fix pylint and pep8 problems
--- Added comments ---  uidv8815 [Aug 8, 2013 8:37:11 AM CEST]
Change Package : 169590:1 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.15 2013/08/07 18:13:43CEST Hospes, Gerd-Joachim (uidv8815)
fix class BplList to support extend, append and other list methods
--- Added comments ---  uidv8815 [Aug 7, 2013 6:13:44 PM CEST]
Change Package : 169590:1 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.14 2013/08/06 15:48:00CEST Hecker, Robert (heckerr)
Added new singleSplit Funtion to bpl module.
--- Added comments ---  heckerr [Aug 6, 2013 3:48:01 PM CEST]
Change Package : 192878:1 http://mks-psad:7002/im/viewissue?selection=192878
Revision 1.13 2013/07/04 17:45:35CEST Hecker, Robert (heckerr)
Removed pep8 violations.
--- Added comments ---  heckerr [Jul 4, 2013 5:45:36 PM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.12 2013/07/01 08:55:18CEST Hecker, Robert (heckerr)
Some Renamings from Rec... to Bpl...
Revision 1.11 2013/06/26 17:19:02CEST Hecker, Robert (heckerr)
Some finetuning in docstrings and importing.
Revision 1.10 2013/06/26 16:02:40CEST Hecker, Robert (heckerr)
Reworked bpl sub-package.
Revision 1.9 2013/06/26 10:51:40CEST Hecker, Robert (heckerr)
Reduced pylint errors.
--- Added comments ---  heckerr [Jun 26, 2013 10:51:40 AM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.8 2013/06/26 10:23:24CEST Hecker, Robert (heckerr)
Increased ModuleTest Coverage for Bpl() Class.
- Get split method working and created Module Tests.
- Get write Method working and created Module Tests.
Revision 1.7 2013/03/28 11:10:55CET Mertens, Sven (uidv7805)
pylint: last unused import removed
--- Added comments ---  uidv7805 [Mar 28, 2013 11:10:55 AM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.6 2013/03/01 09:47:22CET Hecker, Robert (heckerr)
Updates Regarding Pep8.
--- Added comments ---  heckerr [Mar 1, 2013 9:47:22 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.5 2013/02/13 09:39:38CET Hecker, Robert (heckerr)
Improved usability of BPL io.
--- Added comments ---  heckerr [Feb 13, 2013 9:39:38 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.4 2012/12/14 16:22:48CET Hecker, Robert (heckerr)
Removed stk Prefixes in Classes, Member Variables,....
--- Added comments ---  heckerr [Dec 14, 2012 4:22:48 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.3 2012/12/05 13:49:48CET Hecker, Robert (heckerr)
Updated code to pep8 guidelines.
--- Added comments ---  heckerr [Dec 5, 2012 1:49:48 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.2 2012/12/05 09:59:25CET Hecker, Robert (heckerr)
Updated Code partly regarding pep8
--- Added comments ---  heckerr [Dec 5, 2012 9:59:25 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.1 2012/12/04 17:56:53CET Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
    05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/mts/project.pj
"""
