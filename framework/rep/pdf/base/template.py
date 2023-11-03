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
:author:        Leidenberger, Ralf

:version:       $Revision: 1.1 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/25 21:28:04CET $
"""
# Import Python Modules --------------------------------------------------------
import reportlab.platypus.doctemplate as dtp
from reportlab.lib.styles import getSampleStyleSheet
# import warnings

# Import STK Modules -----------------------------------------------------------

# Defines ----------------------------------------------------------------------
PAGE_TEMPLATE_PORTRAIT = 'portrait'
PAGE_TEMPLATE_LANDSCAPE = 'landscape'

# Functions --------------------------------------------------------------------

# Classes ----------------------------------------------------------------------


class Style(object):
    def __init__(self):
        self._styles = getSampleStyleSheet()
        # noinspection PyPep8Naming
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
        # noinspection PyCallByClass,PyTypeChecker
        dtp.PageTemplate.__init__(self, self.ID, self.frames, onPage=self.on_page,
                                  pagesize=doctemplate.pagesize)

    # noinspection PyMethodMayBeStatic
    def on_page(self, canv, doc):
        """
        Callback Method, which will be called during the rendering process,
        to draw on every page identical items, like header of footers.
        """
        pass


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
        # noinspection PyCallByClass,PyTypeChecker
        dtp.PageTemplate.__init__(self, self.ID, self.frames, onPage=self.on_page,
                                  pagesize=(doctemplate.pagesize[1], doctemplate.pagesize[0]))

    # noinspection PyMethodMayBeStatic
    def on_page(self, canv, doc):
        """
        Callback Method, which will be called during the rendering process, to draw on every page
        identical items, like header of footers.
        """
        pass


class PdfDocTemplate(dtp.BaseDocTemplate):  # pylint: disable=R0904
    """
    **Document Template for basic pdf document.**

    :author:        Robert Hecker
    :date:          22.09.2013
    """
    def __init__(self, style, filepath):
        dtp.BaseDocTemplate.__init__(dtp.BaseDocTemplate(self), filepath)
        self._style = style

        # noinspection PyTypeChecker
        self.addPageTemplates([PortraitPageTemplate(self), LandscapePageTemplate(self)])


"""
CHANGE LOG:
-----------
$Log: template.py  $
Revision 1.1 2020/03/25 21:28:04CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/rep/pdf/base/project.pj
"""
