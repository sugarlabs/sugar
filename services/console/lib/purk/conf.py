import os
urkpath = os.path.dirname(__file__)

def path(filename=""):
    if filename:
        return os.path.join(urkpath, filename)
    else:
        return urkpath

if os.access(path('profile'),os.F_OK) or os.path.expanduser("~") == "~":
    userpath = path('profile')
    if not os.access(userpath,os.F_OK):
        os.mkdir(userpath)
    if not os.access(os.path.join(userpath,'scripts'),os.F_OK):
        os.mkdir(os.path.join(userpath,'scripts'))
else:
    userpath = os.path.join(os.path.expanduser("~"), ".urk")
    if not os.access(userpath,os.F_OK):
        os.mkdir(userpath, 0700)
    if not os.access(os.path.join(userpath,'scripts'),os.F_OK):
        os.mkdir(os.path.join(userpath,'scripts'), 0700)

CONF_FILE = os.path.join(userpath,'urk.conf')


def pprint(obj, depth=-2):
    depth += 2
    
    string = []

    if isinstance(obj, dict):
        if obj:
            string.append('{\n')
        
            for key in obj:
                string.append('%s%s%s' % (' '*depth, repr(key), ': '))
                string += pprint(obj[key], depth)
                
            string.append('%s%s' % (' '*depth, '},\n'))
            
        else:
            string.append('{},\n')
        
    elif isinstance(obj, list):
        if obj:
            string.append('[\n')
        
            for item in obj:
                string.append('%s' % (' '*depth))
                string += pprint(item, depth)
                
            string.append('%s%s' % (' '*depth, '],\n'))
            
        else:
            string.append('[],\n')
        
    else:
        string.append('%s,\n' % (repr(obj),))
        
    if depth:
        return string
    else:
        return ''.join(string)[:-2]

def save(*args):
    new_file = not os.access(CONF_FILE,os.F_OK)
    fd = file(CONF_FILE, "wb")
    try:
        if new_file:
            os.chmod(CONF_FILE,0600)
        fd.write(pprint(conf))
    finally:
        fd.close()

#events.register('Exit', 'post', save)

try:
    conf = eval(file(CONF_FILE, "U").read().strip())
except IOError, e:
    if e.args[0] == 2:
        conf = {}
    else:
        raise
    
if __name__ == '__main__':
    print pprint(conf)
