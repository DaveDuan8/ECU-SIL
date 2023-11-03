"""
trie
-------------

documentation of trie
docu docu

:org:           Continental AG
:author:        Sven Mertens

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:05:33CEST $
"""

# Import Python Modules ------------------------------------------------------

# - import STK modules -------------------------------------------------------
from stk.util.helper import deprecated

# TODO: implementation of a save and a load method (json?)
# next question: what to support: txt / xml / etc ?


class CTrie(object):
    """Tree implementation initiated by use case validation sets
    """
    def __init__(self, ident, parent, value):
        """
        constraint trie implementation
        :param ident: constraint (/ set) ID
        :param parent: parent id
        :param value: initial value
        """
        self.kids = []
        self.parent = parent
        self.ident = ident
        self.value = list(value) if isinstance(value, tuple) else value
        # TODO: appendValue only works for lists or dicts
        # self.value = list(value) if isinstance(value, tuple) else [value]
        self.result = None

    def add_kid(self, kid_id, parent, value):
        """
        adds a kid underneath parent with value
        :param kid_id: new ID of kid
        :param parent: parent ID
        :param value: kid value
        :return: True / False
        """
        if parent == self.ident:
            self.kids.append(CTrie(kid_id, parent, value))
            return True

        for k in self.kids:
            if k.add_kid(kid_id, parent, value):
                return True
        return False

    def append_value(self, kid_id, value):
        """
        appends value to a kid by ID
        :param kid_id: kid ID
        :param value: value to add to existing
        :return: True / False
        """
        if self.ident == kid_id:
            if isinstance(self.value, list):
                self.value.append(value)
            elif isinstance(self.value, dict):
                self.value.update(value)
            return True

        for k in self.kids:
            if k.append_value(kid_id, value):
                return True
        return False

    def kid_value(self, kid_id):
        """
        :param kid_id: kid ID to search for
        :return: value of kid
        """
        if len(self.kids) == 0 and self.ident == kid_id:
            return self.value

        for k in self.kids:
            value = k.kid_value(kid_id)
            if value is not None:
                return value
        return None

    def kid_result(self, kid_id):
        """
        :param kid_id: kid ID to search for
        :return: result of kid
        """
        # if len(self.kids) == 0 and self.ident == kidID:
        if self.ident == kid_id:
            return self.result

        for k in self.kids:
            value = k.kid_result(kid_id)
            if value is not None:
                return value
        return None

    def eval_kids(self, func):
        """evaluate the value by using func.
        Result(s) saved to local variable result.
        :param func: evaluation function
        """
        # how to prevent endless loop?
        # if len(self.kids) == 0:
        # self.result = func(self.value)
        # else:
        for k in self.kids:
            k.eval_kids(func)

        # put it to end, so first eval kids
        self.result = func(self)

    def eval_results(self, func):
        """evaluate the results by using func.
        :param func: evaluation function
        :return: func result
        """
        # TODO: evalResults not needed any more?
        res = []
        res.append(self.result)
        for k in self.kids:
            res.append(k.eval_results(func))

        return func[self.value](res)

    @property
    def all_kid_ids(self):
        """
        :return: ID's of only kids
        """
        ids = []
        for k in self.kids:
            ids.append(k.ident)
            ids.extend(k.all_kid_ids)
        return ids

    @property
    def all_ids(self):
        """
        :return: all sub ID's
        """
        ids = [self.ident]
        for k in self.kids:
            ids.extend(k.all_ids)
        return ids

    @property
    def values(self):
        """
        :return: list of [set_id, value] (list of lists)
        """
        vals = []

        vals.append([self.ident, self.value])

        for k in self.kids:
            vals.extend(k.values)

        return vals

    @deprecated('add_kid')
    def addKid(self, kid_id, parent, value):  # pylint: disable=C0103
        """deprecated"""
        return self.add_kid(kid_id, parent, value)

    @deprecated('append_value')
    def appendValue(self, kid_id, value):  # pylint: disable=C0103
        """deprecated"""
        return self.append_value(kid_id, value)

    @deprecated('kid_value')
    def kidValue(self, kid_id):  # pylint: disable=C0103
        """deprecated"""
        return self.kid_value(kid_id)

    @deprecated('kid_result')
    def kidResult(self, kid_id):  # pylint: disable=C0103
        """deprecated"""
        return self.kid_result(kid_id)

    @deprecated('eval_kids')
    def evalKids(self, func):  # pylint: disable=C0103
        """deprecated"""
        return self.eval_kids(func)

    @deprecated('eval_results')
    def evalResults(self, func):  # pylint: disable=C0103
        """deprecated"""
        return self.eval_results(func)

    @property
    @deprecated('all_kid_ids')
    def allKidIDs(self):  # pylint: disable=C0103
        """deprecated"""
        return self.all_kid_ids

    @property
    @deprecated('all_ids')
    def allIDs(self):  # pylint: disable=C0103
        """deprecated"""
        return self.all_ids

"""
CHANGE LOG:
-----------
$Log: trie.py  $
Revision 1.1 2015/04/23 19:05:33CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/util/project.pj
Revision 1.14 2015/01/23 21:44:18CET Ellero, Stefano (uidw8660) 
Removed all util based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Jan 23, 2015 9:44:19 PM CET]
Change Package : 296837:1 http://mks-psad:7002/im/viewissue?selection=296837
Revision 1.13 2014/03/16 21:55:48CET Hecker, Robert (heckerr) 
added pylintrc.
--- Added comments ---  heckerr [Mar 16, 2014 9:55:48 PM CET]
Change Package : 225494:1 http://mks-psad:7002/im/viewissue?selection=225494
Revision 1.12 2014/02/19 17:55:45CET Skerl, Anne (uid19464)
*enable appendValue() to use dict
--- Added comments ---  uid19464 [Feb 19, 2014 5:55:46 PM CET]
Change Package : 220258:1 http://mks-psad:7002/im/viewissue?selection=220258
Revision 1.11 2013/12/18 16:49:11CET Skerl, Anne (uid19464)
pylint
--- Added comments ---  uid19464 [Dec 18, 2013 4:49:11 PM CET]
Change Package : 198254:10 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.10 2013/12/18 13:44:06CET Skerl, Anne (uid19464)
*remove old comments
--- Added comments ---  uid19464 [Dec 18, 2013 1:44:07 PM CET]
Change Package : 198254:8 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.9 2013/11/29 16:41:02CET Skerl, Anne (uid19464)
*pep8
--- Added comments ---  uid19464 [Nov 29, 2013 4:41:03 PM CET]
Change Package : 198254:3 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.8 2013/11/29 15:12:05CET Skerl, Anne (uid19464)
*changes for module test: add methode kidResult(), bugfixes values(), evalResults()
--- Added comments ---  uid19464 [Nov 29, 2013 3:12:06 PM CET]
Change Package : 198254:3 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.7 2013/11/26 19:11:22CET Skerl, Anne (uid19464)
*change: appendValue, evalKids, evalResults, allKidIDs
--- Added comments ---  uid19464 [Nov 26, 2013 7:11:22 PM CET]
Change Package : 198254:2 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.6 2013/04/03 08:02:15CEST Mertens, Sven (uidv7805)
pylint: minor error, warnings fix
--- Added comments ---  uidv7805 [Apr 3, 2013 8:02:16 AM CEST]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.5 2013/03/22 08:24:25CET Mertens, Sven (uidv7805)
aligning bulk of files again for peping 8
Revision 1.4 2013/03/06 10:21:23CET Mertens, Sven (uidv7805)
done, pep8 styling
--- Added comments ---  uidv7805 [Mar 6, 2013 10:21:24 AM CET]
Change Package : 176171:7 http://mks-psad:7002/im/viewissue?selection=176171
Revision 1.3 2013/03/01 10:29:41CET Mertens, Sven (uidv7805)
bugfixing STK imports
--- Added comments ---  uidv7805 [Mar 1, 2013 10:29:42 AM CET]
Change Package : 176171:2 http://mks-psad:7002/im/viewissue?selection=176171
Revision 1.2 2013/02/28 17:09:53CET Mertens, Sven (uidv7805)
initial version of constraint related classes
--- Added comments ---  uidv7805 [Feb 28, 2013 5:09:54 PM CET]
Change Package : 176171:1 http://mks-psad:7002/im/viewissue?selection=176171
Revision 1.1 2013/02/21 12:42:48CET Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
STK_ScriptingToolKit/04_Engineering/
    stk/util/project.pj
"""
