r"""
stk/rep/pdf/__init__.py
-----------------------

Subpackage for writing basic pdf documents.


**Following Classes are available for the User-API:**

  - `Pdf` class for base pdf report methods
  - `Story` wrapper class providing methods to set up the report like add_heading() or add_paragraph().

Templates and flowables classes are under constant development and therefore internal API,
backward compatibility regarding methods and file locations can not be guaranteed with all the needed changes.

**example pdf**

There are examples created by our module test at:

 - blank report only using page sizes at basic.pdf_

 - blank report using base templates with page header and footer at basic_with_template.pdf_
 - both created by `STK\\05_Testing\\05_Test_Environment\\moduletest\\test_rep\\test_pdf\\test_base\\test_pdf.py`,
   please check the test for further code examples


**To use the hpc package from your code do following:**

  .. python::

    import stk.rep.pdf as pdf

    # Create a instance of the Pdf class.
    doc = pdf.Pdf()

    # Write Something into the pdf
    doc.add_paragraph("Hello World")

    # Render pdf story to file
    doc.build('out.pdf')

.. _basic.pdf: http://uud296ag:8080/job/STK_NightlyBuild/lastSuccessfulBuild/artifact/
               05_Testing/04_Test_Data/02_Output/rep/basic.pdf
.. _basic_with_template.pdf: http://uud296ag:8080/job/STK_NightlyBuild/lastSuccessfulBuild/artifact/
                             05_Testing/04_Test_Data/02_Output/rep/basic_with_template.pdf

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:05:13CEST $
"""
# Import Python Modules -------------------------------------------------------

# Add PyLib Folder to System Paths --------------------------------------------

# Import STK Modules ----------------------------------------------------------

# Import Local Python Modules -------------------------------------------------

"""
CHANGE LOG:
-----------
$Log: __init__.py  $
Revision 1.1 2015/04/23 19:05:13CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/rep/pdf/base/project.pj
Revision 1.6 2015/02/19 11:47:09CET Mertens, Sven (uidv7805) 
line to short fix
--- Added comments ---  uidv7805 [Feb 19, 2015 11:47:10 AM CET]
Change Package : 308634:1 http://mks-psad:7002/im/viewissue?selection=308634
Revision 1.5 2014/07/29 12:37:12CEST Hospes, Gerd-Joachim (uidv8815)
pep8 fixes of too long lines for http links, epydoc and pylint adjustments
--- Added comments ---  uidv8815 [Jul 29, 2014 12:37:12 PM CEST]
Change Package : 246030:1 http://mks-psad:7002/im/viewissue?selection=246030
Revision 1.4 2014/07/28 19:16:25CEST Hospes, Gerd-Joachim (uidv8815)
extend epydoc
--- Added comments ---  uidv8815 [Jul 28, 2014 7:16:26 PM CEST]
Change Package : 246030:1 http://mks-psad:7002/im/viewissue?selection=246030
Revision 1.3 2014/06/16 14:57:54CEST Hospes, Gerd-Joachim (uidv8815)
add table_of_* to base report
--- Added comments ---  uidv8815 [Jun 16, 2014 2:57:55 PM CEST]
Change Package : 241724:1 http://mks-psad:7002/im/viewissue?selection=241724
Revision 1.2 2013/10/25 09:02:30CEST Hecker, Robert (heckerr)
Removed Pep8 Issues.
--- Added comments ---  heckerr [Oct 25, 2013 9:02:30 AM CEST]
Change Package : 202843:1 http://mks-psad:7002/im/viewissue?selection=202843
Revision 1.1 2013/10/18 09:22:12CEST Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
STK_ScriptingToolKit/04_Engineering/stk/rep/pdf/base/project.pj
"""
