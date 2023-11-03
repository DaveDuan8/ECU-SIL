"""
framework/valf/progressbar
--------------------

text based progressbar

:org:           Continental AG
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
    def __init__(self, min_value=0, max_value=100, total_width=50, multiline=False):
        """init with defaults:

        :param min_value: 0 as a starting point
        :param max_value: we're going to 100 maximum
        :param total_width: how much chars should be printed out by a call
        :param multiline: wether to add a CR at end or not
        """
        self.__progress_bar = "[]"
        self.__min = min_value
        self.__max = max_value
        self.__span = max_value - min_value
        self.__width = total_width
        self.__amount = 0
        self.__update_amount(0)
        self.__old_amount = 0

        self.__multiline = multiline

        self.__old_progBar = "[]"

    def __update_amount(self, new_amount=0):
        """ Update the progress bar with the new amount (with min and max
        values set at initialization; if it is over or under, it takes the
        min or max value as a default.
        """
        self.__amount = min(max(new_amount, self.__min), self.__max)

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

        self.__update_amount(value)

        tmp = None
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
Revision 1.2 2020/03/31 10:14:12CEST Leidenberger, Ralf (uidq7596) 
initial update
Revision 1.1 2020/03/25 21:38:08CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/valf/project.pj
"""
