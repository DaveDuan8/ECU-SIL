"""
easter.py
---------

PyHPC's easter egg
"""
# - import Python modules ----------------------------------------------------------------------------------------------
from datetime import datetime
from dateutil.easter import easter

# - features -----------------------------------------------------------------------------------------------------------
# pylint: disable=C0103
this = "is it already easter?"

today = datetime.now().date()
if easter(today.year) > today:
    that = "well, easter is already gone this year!"
elif easter(today.year) == today:
    that = "hey, today is easter! don't you have a day off?"
else:
    that = "hurry up, easter is in {} days!".format((easter(today.year) - today).days)
