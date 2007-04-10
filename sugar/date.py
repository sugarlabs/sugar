"""Simple date-representation model"""
import datetime

class Date(object):
    """Date-object storing a simple time.time() float
    
    XXX not sure about the rationale for this class,
    possibly it makes transfer over dbus easier?
    """
    def __init__(self, timestamp):
        """Initialise via a timestamp (floating point value)"""
        self._timestamp = timestamp

    def __str__(self):
        """Produce a formatted date representation
        
        Eventually this should produce a localised version 
        of the date.  At the moment it always produces English
        dates in long form with Today and Yesterday 
        special-cased and dates from this year not presenting
        the year in the date.
        """
        date = datetime.date.fromtimestamp(self._timestamp)
        today = datetime.date.today()

        # FIXME localization
        if date == today:
            result = 'Today'
        elif date == today - datetime.timedelta(1):
            result = 'Yesterday'
        elif date.year == today.year:
            result = date.strftime('%B %d')
        else:
            result = date.strftime('%B %d, %Y')

        time = datetime.datetime.fromtimestamp(self._timestamp)
        result = result + ', ' + time.strftime('%I:%M %p')

        return result
