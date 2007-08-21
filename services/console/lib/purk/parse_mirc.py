try:
    from conf import conf
except ImportError:
    conf = {}

BOLD = '\x02'
UNDERLINE = '\x1F'
MIRC_COLOR = '\x03'
MIRC_COLOR_BG = MIRC_COLOR, MIRC_COLOR
BERS_COLOR = '\x04'
RESET = '\x0F'

colors = (
  '#FFFFFF', '#000000', '#00007F', '#009300', 
  '#FF0000', '#7F0000', '#9C009C', '#FF7F00',
  '#FFFF00', '#00FF00', '#009393', '#00FFFF',
  '#0000FF', '#FF00FF', '#7F7F7F', '#D2D2D2'
  )

def get_mirc_color(number):
    if number == '99':
        return None

    number = int(number) & 15
    
    confcolors = conf.get('colors', colors)
    try:
        return confcolors[number]
    except:
        # someone edited their colors wrongly
        return colors[number]
    
DEC_DIGITS, HEX_DIGITS = set('0123456789'), set('0123456789abcdefABCDEF')

def parse_mirc_color(string, pos, open_tags, tags):
    color_chars = 1

    if MIRC_COLOR in open_tags:
        fgtag = open_tags.pop(MIRC_COLOR)
        fgtag['to'] = pos
        tags.append(fgtag)
    
    if MIRC_COLOR_BG in open_tags:
        bgtag = open_tags.pop(MIRC_COLOR_BG)
        bgtag['to'] = pos
        tags.append(bgtag)

        bg = bgtag['data'][1]
    else:
        bg = None

    if string[0] in DEC_DIGITS:   
        if string[1] in DEC_DIGITS:
            fg = get_mirc_color(string[:2])
            string = string[1:]
            color_chars += 2

        else:
            fg = get_mirc_color(string[0])
            color_chars += 1
        
        if string[1] == "," and string[2] in DEC_DIGITS:
            if string[3] in DEC_DIGITS:
                bg = get_mirc_color(string[2:4])
                color_chars += 3

            else:
                bg = get_mirc_color(string[2])
                color_chars += 2
    
    else:
        fg = bg = None
    
    if fg:
        open_tags[MIRC_COLOR] = {'data': ("foreground",fg), 'from': pos}
    else:
        open_tags.pop(MIRC_COLOR,None)
    
    if bg:
        open_tags[MIRC_COLOR_BG] = {'data': ("background",bg), 'from': pos}
    else:
        open_tags.pop(MIRC_COLOR_BG,None)
              
    return color_chars

def parse_bersirc_color(string, pos, open_tags, tags):
    bg = None
    if MIRC_COLOR in open_tags:
        tag = open_tags.pop(MIRC_COLOR)
        tag['to'] = pos
        tags.append(tag)
        
    if MIRC_COLOR_BG in open_tags:
        bgtag = open_tags.pop(MIRC_COLOR_BG)
        bgtag['to'] = pos
        tags.append(bgtag)

        bg = bgtag['data'][1]
    
    for c in (0, 1, 2, 3, 4, 5):
        if string[c] not in HEX_DIGITS:
            return 1
    fg = '#' + string[:6].upper()

    color_chars = 7
    for c in (7, 8, 9, 10, 11, 12):
        if string[c] not in HEX_DIGITS:
            break
    else:
        if string[6] == ",":
            bg = '#' + string[7:13].upper()
            color_chars = 14
        
    if fg:
        open_tags[MIRC_COLOR] = {'data': ("foreground",fg), 'from': pos}
    else:
        open_tags.pop(MIRC_COLOR,None)
    
    if bg:
        open_tags[MIRC_COLOR_BG] = {'data': ("background",bg), 'from': pos}
    else:
        open_tags.pop(MIRC_COLOR_BG,None)
    
    return color_chars
  
def parse_bold(string, pos, open_tags, tags):
    if BOLD in open_tags:
        tag = open_tags.pop(BOLD)
        tag['to'] = pos
        tags.append(tag)
        
    else:
        open_tags[BOLD] = {'data': ('weight', BOLD), 'from': pos}

    return 1

def parse_underline(string, pos, open_tags, tags):
    if UNDERLINE in open_tags:
        tag = open_tags.pop(UNDERLINE)
        tag['to'] = pos
        tags.append(tag)
        
    else:
        open_tags[UNDERLINE] = {'data': ('underline', UNDERLINE), 'from': pos}
        
    return 1

def parse_reset(string, pos, open_tags, tags):
    for t in open_tags:
        tag = open_tags[t]
        tag['to'] = pos
        tags.append(tag)

    open_tags.clear()
    
    return 1

tag_parser = {
    MIRC_COLOR: parse_mirc_color,
    BERS_COLOR: parse_bersirc_color,
    BOLD: parse_bold,
    UNDERLINE: parse_underline,
    RESET: parse_reset
    }

def parse_mirc(string):
    string += RESET

    out = ''
    open_tags = {}
    tags = []
    text_i = outtext_i = 0

    for tag_i, char in enumerate(string):
        if char in tag_parser:
            out += string[text_i:tag_i]

            outtext_i += tag_i - text_i

            text_i = tag_i + tag_parser[char](
                                string[tag_i+1:], 
                                outtext_i, 
                                open_tags,
                                tags
                                )

    return tags, out

#transforms for unparse_mirc

#^O
def transform_reset(start, end):
    return RESET, '', {}

#^K
def transform_color_reset(start, end):
    if ('foreground' in start and 'foreground' not in end) or \
          ('background' in start and 'background' not in end):
        result = start.copy()
        result.pop("foreground",None)
        result.pop("background",None)
        return MIRC_COLOR, DEC_DIGITS, result
    else:
        return '','',start

#^KXX
def transform_color(start, end):
    if (start.get('foreground',99) != end.get('foreground',99)):
        confcolors = conf.get('colors', colors)
        result = start.copy()
        if 'foreground' in end:
            try:
                index = list(confcolors).index(end['foreground'].upper())
            except ValueError:
                return '','',start
            result['foreground'] = end['foreground']
        else:
            index = 99
            del result['foreground']
        return '\x03%02i' % index, ',', result
    else:
        return '','',start

#^KXX,YY
def transform_bcolor(start, end):
    if (start.get('background',99) != end.get('background',99)):
        confcolors = conf.get('colors', colors)
        result = start.copy()
        if 'foreground' in end:
            try:
                fg_index = list(confcolors).index(end['foreground'].upper())
            except ValueError:
                return '','',start
            result['foreground'] = end['foreground']
        else:
            fg_index = 99
            result.pop('foreground',None)
        if 'background' in end:
            try:
                bg_index = list(confcolors).index(end['background'].upper())
            except ValueError:
                return '','',start
            result['background'] = end['background']
        else:
            bg_index = 99
            del result['background']
        return '\x03%02i,%02i' % (fg_index, bg_index), ',', result
    else:
        return '','',start

#^LXXXXXX
def transform_bersirc(start, end):
    if 'foreground' in end and end['foreground'] != start.get('foreground'):
        result = start.copy()
        result['foreground'] = end['foreground']
        return "\x04%s" % end['foreground'][1:], ',', result
    else:
        return '','',start

#^LXXXXXX,YYYYYY
def transform_bbersirc(start, end):
    if 'foreground' in end and 'background' in end and (
          end['foreground'] != start.get('foreground') or 
          end['background'] != start.get('background')):
        result = start.copy()
        result['foreground'] = end['foreground']
        result['background'] = end['background']
        return "\x04%s,%s" % (end['foreground'][1:], end['background'][1:]), ',', result
    else:
        return '','',start


#^B
def transform_underline(start, end):
    if ('underline' in start) != ('underline' in end):
        result = start.copy()
        if 'underline' in start:
            del result['underline']
        else:
            result['underline'] = UNDERLINE
        return UNDERLINE, '', result
    else:
        return '','',start

#^U
def transform_bold(start, end):
    if ('weight' in start) != ('weight' in end):
        result = start.copy()
        if 'weight' in start:
            del result['weight']
        else:
            result['weight'] = BOLD
        return BOLD, '', result
    else:
        return '','',start

#^B^B
#In some rare circumstances, we HAVE to do this to generate a working string
def transform_dbold(start, end):
    return BOLD*2, '', start

#return the formatting needed to transform one set of format tags to another
def transform(start, end, nextchar=" "):
    transform_functions = (
        transform_reset, transform_color_reset, transform_color, transform_bcolor,
        transform_bersirc, transform_bbersirc, transform_underline, 
        transform_bold, transform_dbold,
        )
    
    candidates = [('','',start)]
    result = None
    
    for f in transform_functions:
        for string, badchars, s in candidates[:]:
            newstring, badchars, s = f(s, end)
            string += newstring
            if newstring and (result == None or len(string) < len(result)):
                if nextchar not in badchars and s == end:
                    result = string
                else:
                    candidates.append((string, badchars, s))
    return result

def unparse_mirc(tagsandtext):
    lasttags, lastchar = {}, ''
    
    string = []
    for tags, char in tagsandtext:
        if tags != lasttags:
            string.append(transform(lasttags, tags, char[0]))
        string.append(char)
        lasttags, lastchar = tags, char
    return ''.join(string)

if __name__ == "__main__":
    tests = [
        'not\x02bold\x02not',
        'not\x1Funderline\x1Fnot',
        
        "\x02\x1FHi\x0F",
        
        'not\x030,17white-on-black\x0304red-on-black\x03nothing',
        
        "\x040000CC<\x04nick\x040000CC>\x04 text",
        
        '\x04770077,FFFFFFbersirc color with background! \x04000077setting foreground! \x04reset!',
        
        '\x047700,FFFFbersirc',
        
        "\x03123Hello",
        
        "\x0312,Hello",
        
        "\x034Hello",
        
        "Bo\x02ld",
        
        "\x034,5Hello\x036Goodbye",
        
        "\x04ff0000,00ff00Hello\x040000ffGoodbye",
        
        "\x04777777(\x0400CCCCstuff\x04777777)\x04",
        
        '\x0307orange\x04CCCCCCgrey\x0307orange',
        
        '\x04CCCCCC,444444sdf\x0304jkl',
        
        '\x0403\x02\x02,trixy',
        
        '\x04FFFFFF\x02\x02,000000trixy for bersirc',
        ]
        
    results = [
        ([{'from': 3, 'data': ('weight', '\x02'), 'to': 7}], 'notboldnot'),

        ([{'from': 3, 'data': ('underline', '\x1f'), 'to': 12}], 'notunderlinenot'),

        ([{'from': 0, 'data': ('weight', '\x02'), 'to': 2}, {'from': 0, 'data': ('underline', '\x1f'), 'to': 2}], 'Hi'),

        ([{'from': 3, 'data': ('foreground', '#FFFFFF'), 'to': 17}, {'from': 3, 'data': ('background', '#000000'), 'to': 17}, {'from': 17, 'data': ('foreground', '#FF0000'), 'to': 29}, {'from': 17, 'data': ('background', '#000000'), 'to': 29}], 'notwhite-on-blackred-on-blacknothing'),

        ([{'from': 0, 'data': ('foreground', '#0000CC'), 'to': 1}, {'from': 5, 'data': ('foreground', '#0000CC'), 'to': 6}], '<nick> text'),

        ([{'from': 0, 'data': ('foreground', '#770077'), 'to': 31}, {'from': 0, 'data': ('background', '#FFFFFF'), 'to': 31}, {'from': 31, 'data': ('foreground', '#000077'), 'to': 51}, {'from': 31, 'data': ('background', '#FFFFFF'), 'to': 51}], 'bersirc color with background! setting foreground! reset!'),

        ([], '7700,FFFFbersirc'),
        
        ([{'from': 0, 'data': ('foreground', '#0000FF'), 'to': 6}], '3Hello'),

        ([{'from': 0, 'data': ('foreground', '#0000FF'), 'to': 6}], ',Hello'),

        ([{'from': 0, 'data': ('foreground', '#FF0000'), 'to': 5}], 'Hello'),

        ([{'from': 2, 'data': ('weight', '\x02'), 'to': 4}], 'Bold'),

        ([{'from': 0, 'data': ('foreground', '#FF0000'), 'to': 5}, {'from': 0, 'data': ('background', '#7F0000'), 'to': 5}, {'from': 5, 'data': ('foreground', '#9C009C'), 'to': 12}, {'from': 5, 'data': ('background', '#7F0000'), 'to': 12}], 'HelloGoodbye'),

        ([{'from': 0, 'data': ('foreground', '#FF0000'), 'to': 5}, {'from': 0, 'data': ('background', '#00FF00'), 'to': 5}, {'from': 5, 'data': ('foreground', '#0000FF'), 'to': 12}, {'from': 5, 'data': ('background', '#00FF00'), 'to': 12}], 'HelloGoodbye'),

        ([{'from': 0, 'data': ('foreground', '#777777'), 'to': 1}, {'from': 1, 'data': ('foreground', '#00CCCC'), 'to': 6}, {'from': 6, 'data': ('foreground', '#777777'), 'to': 7}], '(stuff)'),
        
        ([{'from': 0, 'data': ('foreground', '#FF7F00'), 'to': 6}, {'from': 6, 'data': ('foreground', '#CCCCCC'), 'to': 10}, {'from': 10, 'data': ('foreground', '#FF7F00'), 'to': 16}], 'orangegreyorange'),
        
        ([{'from': 0, 'data': ('foreground', '#CCCCCC'), 'to': 3}, {'from': 0, 'data': ('background', '#444444'), 'to': 3}, {'from': 3, 'data': ('foreground', '#FF0000'), 'to': 6}, {'from': 3, 'data': ('background', '#444444'), 'to': 6}], 'sdfjkl'),
        
        ([{'from': 2, 'data': ('weight', '\x02'), 'to': 2}], '03,trixy'),
        
        ([{'from': 0, 'data': ('weight', '\x02'), 'to': 0}, {'from': 0, 'data': ('foreground', '#FFFFFF'), 'to': 24}], ',000000trixy for bersirc'),
        ]
    
    #"""

    #r = range(20000)    
    #for i in r:
    #    for test in tests:
    #        parse_mirc(test)
            
    """
    
    lines = [eval(line.strip()) for line in file("parse_mirc_torture_test.txt")]
    
    for r in range(100):
        for line in lines:
            parse_mirc(line)
            
    #""" 
    
    def setify_tags(tags):
        return set(frozenset(tag.iteritems()) for tag in tags if tag['from'] != tag['to'])
    
    def parsed_eq((tags1, text1), (tags2, text2)):
        return setify_tags(tags1) == setify_tags(tags2) and text1 == text2
    
    def parsed_to_unparsed((tags, text)):
        result = []
        for i, char in enumerate(text):
            result.append((
                dict(tag['data'] for tag in tags if tag['from'] <= i < tag['to']),
                char))
        return result
    
    for i, (test, result) in enumerate(zip(tests, results)):
        if not parsed_eq(parse_mirc(test), result):
            print "parse_mirc failed test %s:" % i
            print repr(test)
            print parse_mirc(test)
            print result
            print
        
        elif not parsed_eq(parse_mirc(unparse_mirc(parsed_to_unparsed(result))), result):
            print "unparse_mirc failed test %s:" % i
            print repr(test)
            print unparse_mirc(test)
            print

#import dis
#dis.dis(parse_mirc)
