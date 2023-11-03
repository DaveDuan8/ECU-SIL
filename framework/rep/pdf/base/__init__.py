r"""
framework/rep/pdf/__init__.py
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

  .. code-block:: python

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
:author:        Leidenberger, Ralf

:version:       $Revision: 1.1 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/25 21:28:03CET $
"""
# Import Python Modules -------------------------------------------------------

# Add PyLib Folder to System Paths --------------------------------------------

# Import STK Modules ----------------------------------------------------------

# Import Local Python Modules -------------------------------------------------

"""
CHANGE LOG:
-----------
$Log: __init__.py  $
Revision 1.1 2020/03/25 21:28:03CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/rep/pdf/base/project.pj
"""
