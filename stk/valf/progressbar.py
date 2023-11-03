"""
stk/valf/progressbar
--------------------

text based progressbar

:org:           Continental AG
:author:        Sorin Mogos

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:05:47CEST $
"""
# Import Python Modules -------------------------------------------------------
import sys

# Classes ---------------------------------------------------------------------


class ProgressBar(object):
    """ Creates a text-based progress bar. Call the object with the `print`
        command to see the progress bar, which looks something like this:

        ``[##########        22%                ]``

        You may specify the progress bar's width, min and max values on init.
    """
    def __init__(self, minValue=0, maxValue=100, totalWidth=50, multiline=False):
        """init with defaults:

        :param minValue: 0 as a starting point
        :param maxValue: we're going to 100 maximum
        :param totalWidth: how much chars should be printed out by a call
        :param multiline: wether to add a CR at end or not
        """
        self.__progress_bar = "[]"
        self.__min = minValue
        self.__max = maxValue
        self.__span = maxValue - minValue
        self.__width = totalWidth
        self.__amount = 0
        self.__updateAmount(0)
        self.__old_amount = 0

        self.__multiline = multiline

        self.__old_progBar = "[]"

    def __updateAmount(self, newAmount=0):
        """ Update the progress bar with the new amount (with min and max
        values set at initialization; if it is over or under, it takes the
        min or max value as a default.
        """
        self.__amount = min(max(newAmount, self.__min), self.__max)

        # Figure out the new percent done, round to an integer
        min_diff = float(self.__amount - self.__min)
        done = int(round((min_diff / float(self.__span)) * 100.0))

        # Figure out how many hash bars the percentage should be
        all_full = self.__width - 2
        hashes = int(round((done / 100.0) * all_full))

        # Build a progress bar with an arrow of equal signs; special cases for
        # empty and full
        if hashes == 0:
            self.__bar = "[=%s]" % ('=' * (all_full - 1))
        elif hashes == all_full:
            self.__bar = "[%s]" % ('#' * all_full)
        else:
            self.__bar = "[%s%s]" % ('#' * hashes, '=' * (all_full - hashes))

        # figure out where to put the percentage, roughly centered
        place = (len(self.__bar) / 2) - len(str(done))
        perstr = str(done) + "%"

        # slice the percentage into the bar
        self.__bar = ''.join([self.__bar[0:place], perstr, self.__bar[place + len(perstr):]])

    def __str__(self):
        return str("[PROCESS] " + self.__bar)

    def __call__(self, value):
        """ Updates the amount, and writes to stdout. Prints a carriage return
        first, so it will overwrite the current line in stdout."""

        self.__old_progBar = self.__bar

        self.__updateAmount(value)

        if self.__multiline:
            sys.stdout.write('\n')
        else:
            tmp = self.__width + 11
            sys.stdout.write('\r' * tmp)

        sys.stdout.write(str(self))
        sys.stdout.flush()
        if self.__multiline:
            sys.stdout.write('\n\n')
        elif self.__amount >= self.__max:
            sys.stdout.write('\n')
            sys.stdout.write('\r' * tmp)
            sys.stdout.write(' ' * tmp)
            sys.stdout.write('\r' * tmp)
            sys.stdout.write('\nDone...\n\n')

        self.__old_amount = self.__amount


"""
$Log: progressbar.py  $
Revision 1.1 2015/04/23 19:05:47CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/valf/project.pj
Revision 1.12 2015/02/10 19:39:54CET Hospes, Gerd-Joachim (uidv8815) 
update docu, fix epydoc errors
--- Added comments ---  uidv8815 [Feb 10, 2015 7:39:56 PM CET]
Change Package : 302321:1 http://mks-psad:7002/im/viewissue?selection=302321
Revision 1.11 2014/11/07 14:02:05CET Hospes, Gerd-Joachim (uidv8815) 
get test running again, formal fixes
--- Added comments ---  uidv8815 [Nov 7, 2014 2:02:06 PM CET]
Change Package : 275075:1 http://mks-psad:7002/im/viewissue?selection=275075
Revision 1.10 2014/11/06 14:47:43CET Mertens, Sven (uidv7805)
object update
Revision 1.9 2013/07/04 11:17:47CEST Hospes, Gerd-Joachim (uidv8815)
changes for new module valf:
- process_manager initiates data_manager at init instead of load_config
- bpl uses correct module path
- processbar with simple 'include sys' to redirect process bar output
--- Added comments ---  uidv8815 [Jul 4, 2013 11:17:47 AM CEST]
Change Package : 169590:1 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.8 2013/04/03 08:02:15CEST Mertens, Sven (uidv7805)
pylint: minor error, warnings fix
--- Added comments ---  uidv7805 [Apr 3, 2013 8:02:15 AM CEST]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.7 2013/03/01 10:23:25CET Hecker, Robert (heckerr)
Updates regarding Pep8 Styleguides.
--- Added comments ---  heckerr [Mar 1, 2013 10:23:25 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.6 2013/02/28 08:12:17CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 28, 2013 8:12:18 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.5 2013/02/27 17:55:10CET Hecker, Robert (heckerr)
Removed all E000 - E200 Errors regarding Pep8.
--- Added comments ---  heckerr [Feb 27, 2013 5:55:11 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.4 2013/02/27 16:19:54CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 27, 2013 4:19:55 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.3 2013/02/26 20:18:07CET Raedler, Guenther (uidt9430)
- Updates after Pep8 Styleguides
--- Added comments ---  uidt9430 [Feb 26, 2013 8:18:08 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.2 2013/02/19 21:16:25CET Hecker, Robert (heckerr)
Updates after Pep8 Styleguides..
--- Added comments ---  heckerr [Feb 19, 2013 9:16:26 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.1 2013/02/11 11:06:09CET Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/valf/project.pj
------------------------------------------------------------------------------
-- From etk/valf Archive
------------------------------------------------------------------------------
Revision 1.4 2010/06/28 13:46:24CEST smogos
* added configuration manager
--- Added comments ---  smogos [2010/06/28 11:46:25Z]
Change Package : 37850:1 http://LISS014:6001/im/viewissue?selection=37850
Revision 1.3 2010/03/19 10:40:25EET Sorin Mogos (smogos)
* code customisation and bug fixes
--- Added comments ---  smogos [2010/03/19 08:40:26Z]
Change Package : 37850:1 http://LISS014:6001/im/viewissue?selection=37850
Revision 1.2 2010/02/18 15:30:58EET Sorin Mogos (smogos)
* code optimisation and bug-fixes
--- Added comments ---  smogos [2010/02/18 13:30:58Z]
Change Package : 37850:1 http://LISS014:6001/im/viewissue?selection=37850
Revision 1.1 2009/10/30 14:18:45EET dkubera
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/ETK_EngineeringToolKit/04_Engineering/VALF_ValidationFrame/
    04_Engineering/31_PyLib/project.pj
"""
