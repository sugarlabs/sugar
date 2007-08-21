import purk

class Interface(object):
    def __init__(self):
        client = purk.Client()
        client.show()
        client.join_server('irc.freenode.net')
        self.widget = client.get_widget()


