"""
stk/dmg/lbl
-----------

**Label data management**

Interface for Data Management to the label DB providing special methods to retrieve information

**User-API Interfaces**

  - `merge_bpl_sequences`     retrieve & merge all label sequences stored for a list of recordings
                              (batch play list, bpl)
  - `merge_recfile_sequences` retrieve & merge label sequences for one recording

All other functions and classes of this package are internal interfaces
and might get changed without backward compatibility!


:org:           Continental AG
:author:        Joachim Hospes

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:06:24CEST $
"""
# - import Python modules ---------------------------------------------------------------------------------------------
from os import path as opath
from sys import path as spath


# - import STK modules ------------------------------------------------------------------------------------------------
STKDIR = opath.abspath(r"..\..")
if STKDIR not in spath:
    spath.append(STKDIR)

from stk.db.lbl.camlabel import BaseCameraLabelDB
from stk.mts import BplList, BplListEntry
from stk.util.logger import Logger


# - functions ---------------------------------------------------------------------------------------------------------
def merge_bpl_sequences(bpl_list, project_name=None, function=None, department=None, lbl_db_conn=None):
    """
    **read and merge all label sequences from label Db for all recfiles of a bpl**

    filtered by project, function and department.

    Creates a new BplList instance with labelled sections for all elements of the given bpl list.
    See `merge_recfile_sequences` for more details about merged sections.

    **Attention**: the time stamps in the ordered sections does not have to be a
    valid time stamp of one recording frame, it might be a time value between two adjacent frames!
    *Use the returned values as lower or upper border when filtering recording frames.*

    **Example:**

    get sections for complete bpl using already existing connection to LabelDb:

    .. python::
        # create bpl list directly from file:
        bpl_list = mts.Bpl("bpl_file_name.bpl").read()

        bpl_sects = dmt.lbl.merge_bpl_sequences(bpl_list, "MFC300", "sr", "eva", label_db)


        # get a dict with all sections per recfile {'rec1':[(23, 34), (47, 52)], 'rec2:[(31, 78)], ...}
        bpl_dict = bpl_sects.bpl2dict()

    to get sections for only one recording if no Db connection is available:

    .. python::
        # call for one file name only:
        # create list and append entry for recording
        bpl_list = mts.BplList()
        bpl_list.append(mts.BplListEntry(r'Continuous_2014.04.15_at_08.24.17.rec'))

        bpl_sects = dmt.lbl.merge_bpl_sequences(bpl_list, "MFC300", "sr", "eva")


    :param bpl_list:     instance of BplList object
    :type bpl_list:      `BplList`
    :param project_name: Project name to filter label sequences
    :type project_name:  string
    :param function:     Function name to filter label sequences
    :type function:      string
    :param department:   department name to filter sequences
    :type department:    string, currently used ['dev'|'eva']
    :param lbl_db_conn:  opt. connection to label db, if none is passed own connection will be created
                         setting up a connection will take its time, so if one is available pass it
    :type lbl_db_conn:   instance of `DBConnect`
    :returns:  bpl list with recfile name and list of start and end time of the labelled sections (`BplListEntry`)
    :rtype:    `BplList`

    :author: Joachim Hospes
    :date:   17.07.2014
    """
    # setup own db connection if not given
    the_conn = lbl_db_conn is None
    if the_conn:
        the_conn = BaseCameraLabelDB('algo')

    # BplList to be returned:
    sect_list = BplList()

    for rec in bpl_list:
        # append merged sections of this rec to BplList
        rec_list = merge_recfile_sequences(the_conn if the_conn else lbl_db_conn,
                                           rec.filepath, project_name, function, department)
        sect_list.append(rec_list)

    # if own connection was created terminate it now
    if the_conn:
        the_conn.close()

    return sect_list


def merge_recfile_sequences(lbl_db_conn, recfile_name, project_name=None, function=None, department=None):
    """
    **read and merge all label sequences from label Db for given recfile**

    filtered by project, function and department.

    During labelling process the original label sequences will be completely or partly overwritten
    or extended by additional sections::

        recording:  +------------------------------------------------------+
        1st order:      +--S1-----+       +--------S2-------+  +--S3--+
        revision1:           +-S1.1--+       +--S2.1--+     +--+S3.1
        merged   :      +------------+    +---------------------------+

    This method returns the merged list of all combined sections stored in LabelDb without overlap,
    so the number or returned sections will be smaller than returned by `GetMeasurementSequences`
    directly from LabelDb which provides the unchanged list of sections for a recfile.

    **Attention**: the time stamps in the ordered sections does not have to be a
    valid time stamp of one recording frame, it might be a time value between two adjacent frames!
    *Use the returned values as lower or upper border when filtering recording frames.*

    **Example:**

    .. python::
        recfile_name = 'Continuous_2014.04.15_at_08.24.17.rec'  # or Port "CurrentFile", or ...

        bpl_list_entry = dmt.lbl.merge_recfile_sequences(lbl_db_conn, recfile_name, "MFC300", "sr", "eva")

        # get simple list of start/end tuples:
        sect_list = [(s.start_ts, s.end_ts) for s in bpl_list_entry]

    See `merge_bpl_sections` example how to get sections if no LabelDb connection is available.

    :param lbl_db_conn:  connection to label db
    :type lbl_db_conn:   instance of `DBConnect`
    :param recfile_name: name of recording, leading path will be removed to check Label Db entry
    :type recfile_name:  string
    :param project_name: Project name to filter label sequences
    :type project_name:  string
    :param function:     Function name to filter label sequences
    :type function:      string
    :param department:   department (process) name to filter sequences
    :type department:    string, currently used ['dev'|'eva']

    :returns: bpl list entry with according section list giving start_ts and end_ts of the labelled sections,
              all sections will have absolute time stamps (BplListEntry.rel = False)
    :rtype:  `BplListEntry`

    :author: Joachim Hospes
    :date:   17.07.2014
    """
    logger = Logger(__name__)
    # get labeled sections from db and merge them
    sections, _ = lbl_db_conn.get_measurement_sequences(recfile_name, project_name, function, department)
    if not sections:
        logger.warning('no sections stored in LabelDb for %s filtered by %s, %s and %s' %
                       (recfile_name, project_name, function, department))
    sections.sort()
    logger.debug('LabelDb returned for %s: %s' % (recfile_name, sections))
    i = 0
    while i < len(sections) - 1:
        while i < len(sections) - 1 and sections[i][1] >= sections[i + 1][0]:
            sections[i] = (sections[i][0], max(sections[i][1], sections[i + 1][1]))
            sections.pop(i + 1)
        i += 1

    bpl_list_entry = BplListEntry(recfile_name)
    for sect in sections:
        bpl_list_entry.append(sect[0], sect[1], False)

    return bpl_list_entry


"""
CHANGE LOG:
-----------
$Log: lbl.py  $
Revision 1.1 2015/04/23 19:06:24CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/dmt/project.pj
Revision 1.8 2015/01/20 08:19:56CET Mertens, Sven (uidv7805) 
changing to non-deprecated call
--- Added comments ---  uidv7805 [Jan 20, 2015 8:19:56 AM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.7 2014/11/10 14:55:25CET Mertens, Sven (uidv7805)
fix for wrong termination
--- Added comments ---  uidv7805 [Nov 10, 2014 2:55:25 PM CET]
Change Package : 279419:1 http://mks-psad:7002/im/viewissue?selection=279419
Revision 1.6 2014/11/07 15:40:52CET Hospes, Gerd-Joachim (uidv8815) 
new rec files, update deprecated calls
--- Added comments ---  uidv8815 [Nov 7, 2014 3:40:53 PM CET]
Change Package : 279135:1 http://mks-psad:7002/im/viewissue?selection=279135
Revision 1.5 2014/07/17 18:28:46CEST Hospes, Gerd-Joachim (uidv8815)
finalise epydoc
--- Added comments ---  uidv8815 [Jul 17, 2014 6:28:46 PM CEST]
Change Package : 245477:1 http://mks-psad:7002/im/viewissue?selection=245477
Revision 1.4 2014/07/17 15:06:16CEST Hospes, Gerd-Joachim (uidv8815)
get merge_recfile_sections again, add bpl2dict in bpl, add / update tests
--- Added comments ---  uidv8815 [Jul 17, 2014 3:06:17 PM CEST]
Change Package : 245477:1 http://mks-psad:7002/im/viewissue?selection=245477
Revision 1.3 2014/07/17 10:59:35CEST Hospes, Gerd-Joachim (uidv8815)
add logging output and usage example
--- Added comments ---  uidv8815 [Jul 17, 2014 10:59:36 AM CEST]
Change Package : 245477:1 http://mks-psad:7002/im/viewissue?selection=245477
Revision 1.2 2014/07/16 14:36:35CEST Hospes, Gerd-Joachim (uidv8815)
cleanup camlabel, reduce dmt.lbl to one function, update tests
--- Added comments ---  uidv8815 [Jul 16, 2014 2:36:36 PM CEST]
Change Package : 245477:1 http://mks-psad:7002/im/viewissue?selection=245477
Revision 1.1 2014/07/15 19:32:22CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
    STK_ScriptingToolKit/04_Engineering/stk/dmt/project.pj
"""
