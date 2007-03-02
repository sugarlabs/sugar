import time
import os

def insert_demo_data(data_store):
    home_dir = os.path.expanduser('~')
    journal_dir = os.path.join(home_dir, "Journal")
    if not os.path.exists(journal_dir):
        os.makedirs(journal_dir, 0755)

    data = [
        {   'file-path' : os.path.join(journal_dir, 'fishes_in_the_sea.rtf'),
            'object-type' : 'text',
            'date'    : str(time.time() - 100000),
            'title'   : 'Fishes in the Sea',
            'preview' : 'There are many fishes in the sea, and not only...',
            'icon'    : 'theme:object-text',
            'icon-color' : '#C2B00C,#785C78',
            'keep'    : '0',
            'buddies' : str([ { 'name'  : 'Marco',
                                'color' : '#C2B00C,#785C78' },
                              { 'name'  : 'Dan', 
                                'color' : '#75C228,#3A6E3A' } ])
        },
        {   'file-path' : os.path.join(journal_dir, 'my_cat_and_my_fishes.rtf'),
            'object-type' : 'text',
            'date'    : str(time.time() - 200000),
            'title'   : 'My cat and my fishes',
            'preview' : "Don't know why, but my cat looks to like my fishe...",
            'icon'    : 'theme:object-text',
            'icon-color' : '#C2B00C,#785C78',
            'keep'    : '1',
            'buddies' : str([ { 'name'  : 'Eben',
                                'color' : '#C2B00C,#785C78' },
                              { 'name'  : 'Dan', 
                                'color' : '#75C228,#3A6E3A' } ])
        },
        {   'file-path' : os.path.join(journal_dir, 'cat_browsing.hist'),
            'object-type' : 'link',
            'date'    : str(time.time() - 300000),
            'title'   : 'About cats',
            'preview' : "http://en.wikipedia.org/wiki/Cat",
            'icon'    : 'theme:object-link',
            'icon-color' : '#C2B00C,#785C78',
            'keep'    : '0',
            'buddies' : str([ { 'name'  : 'Dan',
                                'color' : '#C2B00C,#785C78' },
                              { 'name'  : 'Tomeu', 
                                'color' : '#75C228,#3A6E3A' } ])
        },
        {   'file-path' : os.path.join(journal_dir, 'our_school.jpeg'),
            'object-type' : 'picture',
            'date'    : str(time.time() - 400000),
            'title'   : 'Our school',
            'preview' : "Our school",
            'icon'    : 'theme:object-image',
            'icon-color' : '#C2B00C,#785C78',
            'keep'    : '0',
            'buddies' : str([ { 'name'  : 'Marco',
                                'color' : '#C2B00C,#785C78' },
                              { 'name'  : 'Eben', 
                                'color' : '#75C228,#3A6E3A' } ])
        },
        {   'file-path' : os.path.join(journal_dir, 'thai_story.abw'),
            'object-type' : 'text',
            'date'    : str(time.time() - 450000),
            'title'   : 'Thai history',
            'preview' : "The history of Thailand begins with the migration of the Thais from their ancestoral home in southern China into mainland southeast asia around the 10th century AD.",
            'icon'    : 'theme:object-text',
            'icon-color' : '#C2B00C,#785C78',
            'keep'    : '1',
            'buddies' : str([ { 'name'  : 'Marco',
                                'color' : '#C2B00C,#785C78' } ])
        },
        {   'file-path' : os.path.join(journal_dir, 'thai_prince.abw'),
            'object-type' : 'text',
            'date'    : str(time.time() - 450000),
            'title'   : 'The Thai Prince',
            'preview' : "Prince Dipangkara Rasmijoti of Thailand, (born 29 April 2005), is a member of the Thailand Royal Family, a grandson of King Bhumibol Adulyadej (Rama IX) of Thailand is the fifth son of Maha Vajiralongkorn, Crown Prince of Thailand.",
            'icon'    : 'theme:object-text',
            'icon-color' : '#C2B00C,#785C78',
            'keep'    : '0',
            'buddies' : str([ { 'name'  : 'Eben', 
                                'color' : '#75C228,#3A6E3A' } ])
        }
    ]
    for obj in data:
        data_store.create(obj)
