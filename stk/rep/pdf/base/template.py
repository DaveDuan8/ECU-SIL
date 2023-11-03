"""
stk/rep/pdf/base/template.py
----------------------------

Template Module for pdf Reports

Module which contains the needed interfaces to:

**Internal-API Interfaces**

    - `Style`
    - `PortraitPageTemplate`
    - `LandscapePageTemplate`
    - `PdfDocTemplate`

**User-API Interfaces**

    - `stk.rep` (complete package)

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.2 $
:contact:       $Author: Mertens, Sven (uidv7805) $ (last change)
:date:          $Date: 2017/02/17 10:50:03CET $
"""
# Import Python Modules --------------------------------------------------------
import reportlab.platypus.doctemplate as dtp
from reportlab.lib.styles import getSampleStyleSheet
# import warnings

# Import STK Modules -----------------------------------------------------------
from stk.util.helper import deprecated

# Defines ----------------------------------------------------------------------
PAGE_TEMPLATE_PORTRAIT = 'portrait'
PAGE_TEMPLATE_LANDSCAPE = 'landscape'

# Functions --------------------------------------------------------------------

# Classes ----------------------------------------------------------------------


class Style(object):
    def __init__(self):
        self._styles = getSampleStyleSheet()
        self._styles["Normal"].wordWrap = 'CJK'

        self.header = None

    @property
    def styles(self):
        return self._styles


class PortraitPageTemplate(dtp.PageTemplate):
    """
    **Page Template for basic Pages in portrait orientation.**

    :author:        Robert Hecker
    :date:          22.09.2013
    """
    ID = PAGE_TEMPLATE_PORTRAIT

    def __init__(self, doctemplate):
        self.frames = [dtp.Frame(doctemplate.leftMargin, doctemplate.bottomMargin,  # pylint: disable=E1101
                                 doctemplate.width, doctemplate.height, id='F0')]  # pylint: disable=E1101
        dtp.PageTemplate.__init__(self, self.ID, self.frames, onPage=self.on_page, pagesize=doctemplate.pagesize)

    def on_page(self, canv, doc):
        """
        Callback Method, which will be called during the rendering process,
        to draw on every page identical items, like header of footers.
        """
        pass

    @deprecated('on_page')
    def OnPage(self, canv, doc):
        """
        :deprecated: use `on_page` instead
        """
        # warnings.warn('Method "OnPage" is deprecated use "on_page" instead', stacklevel=2)
        return self.on_page(canv, doc)


class LandscapePageTemplate(dtp.PageTemplate):
    """
    **Page Template for basic Pages in landscape orientation.**

    :author:        Robert Hecker
    :date:          22.09.2013
    """
    ID = PAGE_TEMPLATE_LANDSCAPE

    def __init__(self, doctemplate):
        self.frames = [dtp.Frame(doctemplate.leftMargin, doctemplate.bottomMargin,  # pylint: disable=E1101
                                 doctemplate.width, doctemplate.height, id='F0')]  # pylint: disable=E1101
        dtp.PageTemplate.__init__(self, self.ID, self.frames, onPage=self.on_page,
                                  pagesize=(doctemplate.pagesize[1], doctemplate.pagesize[0]))

    def on_page(self, canv, doc):
        """
        Callback Method, which will be called during the rendering process, to draw on every page
        identical items, like header of footers.
        """
        pass

    @deprecated('on_page')
    def OnPage(self, canv, doc):
        """
        :deprecated: use `on_page` instead
        """
        # warnings.warn('Method "OnPage" is deprecated use "on_page" instead', stacklevel=2)
        return self.on_page(canv, doc)


class PdfDocTemplate(dtp.BaseDocTemplate):  # pylint: disable=R0904
    """
    **Document Template for basic pdf document.**

    :author:        Robert Hecker
    :date:          22.09.2013
    """
    def __init__(self, style, filepath):
        dtp.BaseDocTemplate.__init__(self, filepath)
        self._style = style

        self.addPageTemplates([PortraitPageTemplate(self), LandscapePageTemplate(self)])


"""
CHANGE LOG:
-----------
$Log: template.py  $
Revision 1.2 2017/02/17 10:50:03CET Mertens, Sven (uidv7805) 
adding word wrap
Revision 1.1 2015/04/23 19:05:14CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/rep/pdf/base/project.pj
Revision 1.6 2015/01/27 21:20:07CET Ellero, Stefano (uidw8660)
Removed all rep based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Jan 27, 2015 9:20:08 PM CET]
Change Package : 296836:1 http://mks-psad:7002/im/viewissue?selection=296836
Revision 1.5 2014/07/29 12:41:26CEST Hospes, Gerd-Joachim (uidv8815)
pep8 fixes of too long lines for http links, epydoc and pylint adjustments
--- Added comments ---  uidv8815 [Jul 29, 2014 12:41:27 PM CEST]
Change Package : 246030:1 http://mks-psad:7002/im/viewissue?selection=246030
Revision 1.4 2014/03/28 11:32:45CET Hecker, Robert (heckerr)
commented out warnings.
--- Added comments ---  heckerr [Mar 28, 2014 11:32:46 AM CET]
Change Package : 228098:1 http://mks-psad:7002/im/viewissue?selection=228098
Revision 1.3 2014/03/28 10:25:52CET Hecker, Robert (heckerr)
Adapted to new coding guiedlines incl. backwardcompatibility.
--- Added comments ---  heckerr [Mar 28, 2014 10:25:53 AM CET]
Change Package : 228098:1 http://mks-psad:7002/im/viewissue?selection=228098
Revision 1.2 2013/10/25 09:02:34CEST Hecker, Robert (heckerr)
Removed Pep8 Issues.
--- Added comments ---  heckerr [Oct 25, 2013 9:02:35 AM CEST]
Change Package : 202843:1 http://mks-psad:7002/im/viewissue?selection=202843
Revision 1.1 2013/10/18 09:22:14CEST Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
STK_ScriptingToolKit/04_Engineering/stk/rep/pdf/base/project.pj
"""
