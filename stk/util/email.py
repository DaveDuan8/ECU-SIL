"""
stk/util/email
--------------

Module for sending e-mails

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:05:29CEST $
"""
# Import Python Modules -------------------------------------------------------
from __future__ import absolute_import
import os
import smtplib
from email.mime.text import MIMEText
import win32com.client

# Add PyLib Folder to System Paths --------------------------------------------

# Import STK Modules ----------------------------------------------------------

# Import Local Python Modules -------------------------------------------------

# Defines ---------------------------------------------------------------------

# Classes ---------------------------------------------------------------------


class Smtp(object):
    """
    Smtp class is a simple class for writing e-mails with an available Smtp Server.

    :author:        Robert Hecker
    :date:          06.05.2013
    """

    def __init__(self, server="smtphub07.conti.de"):
        """
        Initialize all member variables.

        :param server: SMTPServer to use
        :type  server: string

        :author:        Robert Hecker
        :date:          06.05.2013
        """

        self._server = server

    def sendmail(self, send_from, send_to, subject, body):
        """
        Deprecated version of mail sending. Please use send_message function in the future.

        :param send_from: sender address
        :type  send_from: string
        :param send_to: single receiver address or list of addresses
        :type  send_to: string or list of strings
        :param subject: Subject of E-Mail
        :type  subject: string
        :param body: Message of E-Mail
        :type  body: string

        :author:        Robert Hecker
        :date:          06.05.2013
        """
        if subject is not None:
            body = 'Subject: %s\n\n%s' % (subject, body)

        # Append Footnote to the Body, to see, which User send the mail.
        body += "\n"
        body += "\n"
        temp = "email send via stk.util.email.Smtp from the UserID: %s" % (os.environ["username"])
        body += "-" * len(temp) + "\n"
        body += temp

        if type(send_to) is str:
            send_to = [send_to]

        self.send_message(send_from=send_from,
                          to_recipients=send_to,
                          subject=subject,
                          body=body)

    def send_message(self, send_from, to_recipients, subject, body,
                     footer_message=None, reply_to=None, cc_recipients=None, bcc_recipients=None):
        """
        Send a email with subject and message to a single receiver or a
        list of receivers.

        :param send_from: mail_from
        :type  send_from: string
        :param to_recipients: single receiver address or list of addresses
        :type  to_recipients: list[string]
        :param cc_recipients: single cc-receiver address or list of addresses
        :type  cc_recipients: list[string]
        :param bcc_recipients: single bcc-receiver address or list of addresses
        :type  bcc_recipients: list[string]
        :param subject: Subject of E-Mail
        :type  subject: string
        :param body: Message of E-Mail
        :type  body: string
        :param reply_to: single mail address of the reply-to recipient
        :type  reply_to: string

        :original author:        Thomas Bass
        :date:                   07.10.2014
        """
        COMMASPACE = ', '

        if footer_message:
            body += footer_message

        msg = MIMEText(body)
        if subject:
            msg['Subject'] = subject
        msg['From'] = send_from
        msg['To'] = COMMASPACE.join(to_recipients)
        if cc_recipients:
            msg['CC'] = COMMASPACE.join(cc_recipients)
        if bcc_recipients:
            msg['BCC'] = COMMASPACE.join(bcc_recipients)
        if reply_to:
            msg['Reply-To'] = reply_to

        server = smtplib.SMTP(self._server)
        server.sendmail(send_from, to_recipients, msg.as_string())
        server.quit()


class NotesMail(object):
    """
    NotesMail uses an existing Notes Session to write a e-mail.

    :author:        Robert Hecker
    :date:          06.05.2013
    """
    def __init__(self):
        pass

    @staticmethod
    def sendmail(send_to, subject, body, attachments=None):
        """
        Use Notes to send an email from the current user

        :param send_to: a list of email addresses to send to
                        (or full names from the notes address book)
        :type  send_to: list of string
        :param subject: subject of the email
        :type  subject: string
        :param body: Message of E-Mail
        :type  body: string
        :param attachments: list of full path and file names to attach to the email
        :type  attachments: list of strings (paths)

        :notes: body: empty lines didn't seem to come through properly for me, I had to
                include at least a space on each line to keep them from disappearing.
                This will send email from the currently active Notes account, and ask you for a
                password if you're not logged in - so, it would probably need some kind of
                modification to be used unattended on a server somewhere...
                If you want to extend this, you can find more documentation on the Notes COM API
                at http://www.lotus.com/developers/devbase.nsf/homedata/homecom
                a windows help version can be had by following the "Download Now" link on that
                page and scrolling to the bottom of the page.
                (There may be better stuff out there, this is just the first thing I found. ;)

        :author:        Robert Hecker
        :date:          06.05.2013
        """

        sess = win32com.client.Dispatch("Notes.NotesSession")
        database = sess.getdatabase('', '')
        database.openmail
        doc = database.createdocument

        # Set the recipient to the current user as a default
        if not send_to:
            send_to = sess.UserName

        doc.SendTo = send_to
        doc.Subject = subject

        rti = doc.createrichtextitem('Body')
        rti.AppendText(body)

        # Notes attachments get made in RichText items...
        if attachments:
            richtext = doc.createrichtextitem('Attachment')
            for path in attachments:
                richtext.embedobject(1454, '', path)

        doc.Send(0)

"""
$Log: email.py  $
Revision 1.1 2015/04/23 19:05:29CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/util/project.pj
Revision 1.6 2014/10/23 13:41:04CEST Hecker, Robert (heckerr) 
updated for correct response feature.
--- Added comments ---  heckerr [Oct 23, 2014 1:41:04 PM CEST]
Change Package : 270790:1 http://mks-psad:7002/im/viewissue?selection=270790
Revision 1.5 2014/07/29 18:25:35CEST Hospes, Gerd-Joachim (uidv8815)
fix pylint error W0102 and some others
--- Added comments ---  uidv8815 [Jul 29, 2014 6:25:36 PM CEST]
Change Package : 250927:1 http://mks-psad:7002/im/viewissue?selection=250927
Revision 1.4 2014/03/16 21:55:45CET Hecker, Robert (heckerr)
added pylintrc.
--- Added comments ---  heckerr [Mar 16, 2014 9:55:46 PM CET]
Change Package : 225494:1 http://mks-psad:7002/im/viewissue?selection=225494
Revision 1.3 2013/09/09 11:41:39CEST Hecker, Robert (heckerr)
Added UserID into footer of the email-body.
--- Added comments ---  heckerr [Sep 9, 2013 11:41:40 AM CEST]
Change Package : 196670:1 http://mks-psad:7002/im/viewissue?selection=196670
Revision 1.2 2013/08/27 08:34:39CEST Hecker, Robert (heckerr)
Corrected parameter documentation.
--- Added comments ---  heckerr [Aug 27, 2013 8:34:39 AM CEST]
Change Package : 195099:1 http://mks-psad:7002/im/viewissue?selection=195099
Revision 1.1 2013/05/07 08:52:02CEST Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
STK_ScriptingToolKit/04_Engineering/stk/util/project.pj
"""
