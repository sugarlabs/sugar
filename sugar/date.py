import datetime

class Date(object):
    def __init__(self, timestamp):
        self._timestamp = timestamp

    def __str__(self):
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
