#!/usr/bin/env python
##Copyright (c) 2002, Fedor Baart & Hans de Wit (Stichting Farmaceutische Kengetallen)
##All rights reserved.
##
##Redistribution and use in source and binary forms, with or without modification,
##are permitted provided that the following conditions are met:
##
##Redistributions of source code must retain the above copyright notice, this
##list of conditions and the following disclaimer.
##
##Redistributions in binary form must reproduce the above copyright notice,
##this list of conditions and the following disclaimer in the documentation and/or
##other materials provided with the distribution.
##
##Neither the name of the Stichting Farmaceutische Kengetallen nor the names of
##its contributors may be used to endorse or promote products derived from this
##software without specific prior written permission.
##
##THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
##AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
##IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
##DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE
##FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
##DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
##SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
##CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
##OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
##OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

##Thanks to Gerald Rosennfellner for his help and useful comments.

__doc__="""Use SVGdraw to generate your SVGdrawings.

SVGdraw uses an object model drawing and a method toXML to create SVG graphics
by using easy to use classes and methods usualy you start by creating a drawing eg

    d=drawing()
    #then you create a SVG root element
    s=svg()
    #then you add some elements eg a circle and add it to the svg root element
    c=circle()
    #you can supply attributes by using named arguments.
    c=circle(fill='red',stroke='blue')
    #or by updating the attributes attribute:
    c.attributes['stroke-width']=1
    s.addElement(c)
    #then you add the svg root element to the drawing
    d.setSVG(s)
    #and finaly you xmlify the drawing
    d.toXml()
    

this results in the svg source of the drawing, which consists of a circle
on a white background. Its as easy as that;)
This module was created using the SVG specification of www.w3c.org and the
O'Reilly (www.oreilly.com) python books as information sources. A svg viewer
is available from www.adobe.com"""

__version__="1.0"

# there are two possibilities to generate svg:
# via a dom implementation and directly using <element>text</element> strings
# the latter is way faster (and shorter in coding)
# the former is only used in debugging svg programs
# maybe it will be removed alltogether after a while
# with the following variable you indicate whether to use the dom implementation
# Note that PyXML is required for using the dom implementation.
# It is also possible to use the standard minidom. But I didn't try that one.
# Anyway the text based approach is about 60 times faster than using the full dom implementation.
use_dom_implementation=0

from xml.parsers import expat

import exceptions
if use_dom_implementation<>0:
    try:
        from xml.dom import implementation
        from xml.dom.ext import PrettyPrint
    except:
        raise exceptions.ImportError, "PyXML is required for using the dom implementation"
#The implementation is used for the creating the XML document.
#The prettyprint module is used for converting the xml document object to a xml file

import sys
assert sys.version_info[0]>=2
if sys.version_info[1]<2:
    True=1
    False=0
    file=open
    
sys.setrecursionlimit=50
#The recursion limit is set conservative so mistakes like s=svg() s.addElement(s)
#won't eat up too much processor time.

xlinkNSRef = "http://www.w3.org/1999/xlink"

#the following code is pasted form xml.sax.saxutils
#it makes it possible to run the code without the xml sax package installed
#To make it possible to have <rubbish> in your text elements, it is necessary to escape the texts
def _escape(data, entities={}):
    """Escape &, <, and > in a string of data.

    You can escape other strings of data by passing a dictionary as
    the optional entities parameter.  The keys and values must all be
    strings; each key will be replaced with its corresponding value.
    """
    data = data.replace("&", "&amp;")
    data = data.replace("<", "&lt;")
    data = data.replace(">", "&gt;")
    for chars, entity in entities.items():
        data = data.replace(chars, entity)
    return data

def _quoteattr(data, entities={}):
    """Escape and quote an attribute value.

    Escape &, <, and > in a string of data, then quote it for use as
    an attribute value.  The \" character will be escaped as well, if
    necessary.

    You can escape other strings of data by passing a dictionary as
    the optional entities parameter.  The keys and values must all be
    strings; each key will be replaced with its corresponding value.
    """
    data = _escape(data, entities)
    if '"' in data:
        if "'" in data:
            data = '"%s"' % data.replace('"', "&quot;")
        else:
            data = "'%s'" % data
    else:
        data = '"%s"' % data
    return data



def _xypointlist(a):
    """formats a list of xy pairs"""
    s=''
    for e in a: #this could be done more elegant
        s+=str(e)[1:-1] +'  '
    return s

def _viewboxlist(a):
    """formats a tuple"""
    s=''
    for e in a: 
        s+=str(e)+' '
    return s

def _pointlist(a):
    """formats a list of numbers"""
    return str(a)[1:-1]

class pathdata:
    """class used to create a pathdata object which can be used for a path.
    although most methods are pretty straightforward it might be useful to look at the SVG specification."""
    #I didn't test the methods below. 
    def __init__(self,x=None,y=None):
        self.path=[]
        if x is not None and y is not None:
            self.path.append('M '+str(x)+' '+str(y))
    def closepath(self):
        """ends the path"""
        self.path.append('z')
    def move(self,x,y):
        """move to absolute"""
        self.path.append('M '+str(x)+' '+str(y))
    def relmove(self,x,y):
        """move to relative"""
        self.path.append('m '+str(x)+' '+str(y))
    def line(self,x,y):
        """line to absolute"""
        self.path.append('L '+str(x)+' '+str(y))
    def relline(self,x,y):
        """line to relative"""
        self.path.append('l '+str(x)+' '+str(y))
    def hline(self,x):
        """horizontal line to absolute"""
        self.path.append('H'+str(x))
    def relhline(self,x):
        """horizontal line to relative"""
        self.path.append('h'+str(x))
    def vline(self,y):
        """verical line to absolute"""
        self.path.append('V'+str(y))
    def relvline(self,y):
        """vertical line to relative"""
        self.path.append('v'+str(y))
    def bezier(self,x1,y1,x2,y2,x,y):
        """bezier with xy1 and xy2 to xy absolut"""
        self.path.append('C'+str(x1)+','+str(y1)+' '+str(x2)+','+str(y2)+' '+str(x)+','+str(y))
    def relbezier(self,x1,y1,x2,y2,x,y):
        """bezier with xy1 and xy2 to xy relative"""
        self.path.append('c'+str(x1)+','+str(y1)+' '+str(x2)+','+str(y2)+' '+str(x)+','+str(y))
    def smbezier(self,x2,y2,x,y):
        """smooth bezier with xy2 to xy absolut"""
        self.path.append('S'+str(x2)+','+str(y2)+' '+str(x)+','+str(y))
    def relsmbezier(self,x2,y2,x,y):
        """smooth bezier with xy2 to xy relative"""
        self.path.append('s'+str(x2)+','+str(y2)+' '+str(x)+','+str(y))
    def qbezier(self,x1,y1,x,y):
        """quadratic bezier with xy1 to xy absolut"""
        self.path.append('Q'+str(x1)+','+str(y1)+' '+str(x)+','+str(y))
    def relqbezier(self,x1,y1,x,y):
        """quadratic bezier with xy1 to xy relative"""
        self.path.append('q'+str(x1)+','+str(y1)+' '+str(x)+','+str(y))
    def smqbezier(self,x,y):
        """smooth quadratic bezier to xy absolut"""
        self.path.append('T'+str(x)+','+str(y))
    def relsmqbezier(self,x,y):
        """smooth quadratic bezier to xy relative"""
        self.path.append('t'+str(x)+','+str(y))
    def ellarc(self,rx,ry,xrot,laf,sf,x,y):
        """elliptival arc with rx and ry rotating with xrot using large-arc-flag and sweep-flag  to xy absolut"""
        self.path.append('A'+str(rx)+','+str(ry)+' '+str(xrot)+' '+str(laf)+' '+str(sf)+' '+str(x)+' '+str(y))
    def relellarc(self,rx,ry,xrot,laf,sf,x,y):
        """elliptival arc with rx and ry rotating with xrot using large-arc-flag and sweep-flag  to xy relative"""
        self.path.append('a'+str(rx)+','+str(ry)+' '+str(xrot)+' '+str(laf)+' '+str(sf)+' '+str(x)+' '+str(y))
    def __repr__(self):
        return ' '.join(self.path)
    

class Attribute:
    def __init__(self, name, value, nsname=None, nsref=None):
        self.name = name
        self.value = value
        self.nsname = nsname
        self.nsref = nsref
    def __repr__(self):
        return "(%s=%s, ns: %s=%s)" % (self.name, self.value, self.nsname, self.nsref)

def get_attr_value(attrs, name):
    return attrs[name]


class SVGelement:
    """SVGelement(type,attributes,elements,text,namespace,**args)
    Creates a arbitrary svg element and is intended to be subclassed not used on its own.
    This element is the base of every svg element it defines a class which resembles
    a xml-element. The main advantage of this kind of implementation is that you don't
    have to create a toXML method for every different graph object. Every element
    consists of a type, attribute, optional subelements, optional text and an optional
    namespace. Note the elements==None, if elements = None:self.elements=[] construction.
    This is done because if you default to elements=[] every object has a reference
    to the same empty list."""
    def __init__(self,type='',attributes=None,elements=None,text='',namespace='',cdata=None,**args):
        self.type=type
        self._attributes={}
        if attributes:
            for key, value in attributes.items():
                attr = Attribute(key, value)
                self._attributes[key] = attr
        self.elements=[]
        if elements:
            self.elements=elements
        self.text=text
        self.namespace=namespace
        self.cdata=cdata
        for key, value in args.items():
            attr = Attribute(key, value)
            self._attributes[key] = attr
        self._parent = None

    def addElement(self,SVGelement):
        """adds an element to a SVGelement

        SVGelement.addElement(SVGelement)
        """
        self.elements.append(SVGelement)
        SVGelement.setParent(self)

    def setParent(self, parent):
        self._parent = parent

    def setAttribute(self, attribute, replace=True):
        if not replace and self.hasAttribute(attribute.name):
            return
        self._attributes[attribute.name] = attribute

    def delAttribute(self, name):
        if name in self._attributes.keys():
            del self._attributes[name]

    def hasAttribute(self, name):
        if name in self._attributes.keys():
            return True
        return False

    def _construct(attributes):
        raise Exception("Can't construct a default object.")
    _construct = staticmethod(_construct)

    def _get_namespace(attrname, nslist):
        colon_idx = attrname.find(':')
        if colon_idx <= 0:
            return (attrname, None, None)
        nsname = attrname[:colon_idx]
        nsref = None
        attrname = attrname[colon_idx+1:]
        for (ns, val) in nslist:
            if ns == nsname:
                nsref = val
                break
        if not nsref:
            nsname = None
        return (attrname, nsname, nsref)
    _get_namespace = staticmethod(_get_namespace)

    _XMLNS_TAG = "xmlns:"
    def construct(name, attributes, text=None, cdata=None):
        try:
            eltClass = elementTable[name]
        except KeyError, e:
            print "Unknown SVG element %s." % e
            return None
        # Coalesce namespaces into the attributes themselves
        attr_dict = {}
        elt_namespace = None
        namespaces = []
        tmp_attrs = []
        # Separate namespaces from actual attributes
        for attrname, attrvalue in attributes.items():
            if attrname.startswith(SVGelement._XMLNS_TAG):
                namespaces.append((attrname[len(SVGelement._XMLNS_TAG):], attrvalue))
            elif attrname.startswith("xmlns"):
                # Element-wide attribute
                elt_namespace = attrvalue
            else:
                tmp_attrs.append((attrname, attrvalue))

        # Create attributes and assign namespaces to them
        for (attrname, attrvalue) in tmp_attrs:
            nsname = nsref = None
            attr = None
            # search for its namespace, if any
            (attrname, nsname, nsref) = SVGelement._get_namespace(attrname, namespaces)
            attr = Attribute(attrname, attrvalue, nsname, nsref)
            attr_dict[attrname] = attr

        element = eltClass._construct(attr_dict)
        if element:
            for attr in attr_dict.values():
                element.setAttribute(attr, replace=False)
            if text:
                element.text = text
            if cdata:
                element.cdata = cdata
            if not element.namespace and elt_namespace:
                element.namespace = elt_namespace
        return element
    construct = staticmethod(construct)

    def toXml(self,level,f):
        f.write('\t'*level)
        f.write('<'+self.type)
        if self.namespace:
            f.write(' xmlns="'+ _escape(str(self.namespace))+'" ')
        for attkey, attr in self._attributes.items():
            if attr.nsname:
                f.write(' xmlns:'+_escape(str(attr.nsname))+'="'+_escape(str(attr.nsref))+'" ')
                f.write(' '+_escape(str(attr.nsname))+':'+_escape(str(attkey))+'='+_quoteattr(str(attr.value)))
            else:
                f.write(' '+_escape(str(attkey))+'='+_quoteattr(str(attr.value)))
        if self.elements or self.text or self.cdata:
            f.write('>')
        if self.elements:
            f.write('\n')
        for element in self.elements:
            element.toXml(level+1,f)
        if self.cdata:
            f.write('\n'+'\t'*(level+1)+'<![CDATA[')
            for line in self.cdata.splitlines():
               f.write('\n'+'\t'*(level+2)+line)
            f.write('\n'+'\t'*(level+1)+']]>\n')
        if self.text:
            if isinstance(self.text, str): #If the text is only text
                f.write(_escape(str(self.text)))
            else:                         #If the text is a spannedtext class
                f.write(str(self.text))
        if self.elements:
            f.write('\t'*level+'</'+self.type+'>\n')
        elif self.text: 
            f.write('</'+self.type+'>\n')
        elif self.cdata:
            f.write('\t'*level+'</'+self.type+'>\n')
        else:
            f.write('/>\n')
            
class tspan(SVGelement):
    """ts=tspan(text='',**args)

    a tspan element can be used for applying formatting to a textsection
    usage:
    ts=tspan('this text is bold')
    ts.attributes['font-weight']='bold'
    st=spannedtext()
    st.addtspan(ts)
    t=text(3,5,st)
    """
    def __init__(self,text=None,**args):
        SVGelement.__init__(self,'tspan',**args)
        if self.text<>None:
            self.text=text
    def __repr__(self):
        s="<tspan"
        for key, attr in self._attributes.items():
            s+= ' %s="%s"' % (key,attr.value)
        s+='>'
        s+=self.text
        s+='</tspan>'
        return s

    def _construct(attributes):
        return tspan()
    _construct = staticmethod(_construct)

    
class tref(SVGelement):
    """tr=tref(link='',**args)

    a tref element can be used for referencing text by a link to its id.
    usage:
    tr=tref('#linktotext')
    st=spannedtext()
    st.addtref(tr)
    t=text(3,5,st)
    """
    def __init__(self,link,**args):
        SVGelement.__init__(self,'tref',**args)
        self.setAttribute(Attribute('href', link, 'xlink', xlinkNSRef))
    def __repr__(self):
        s="<tref"
        for key, attr in self._attributes.items():
            s+= ' %s="%s"' % (key,attr.value)
        s+='/>'
        return s

    def _construct(attributes):
        href = get_attr_value(attributes, 'href')
        if href and href.nsname == 'xlink':
            return tref(href.value)
        return None
    _construct = staticmethod(_construct)
    
class spannedtext:
    """st=spannedtext(textlist=[])

    a spannedtext can be used for text which consists of text, tspan's and tref's
    You can use it to add to a text element or path element. Don't add it directly
    to a svg or a group element.
    usage:
    
    ts=tspan('this text is bold')
    ts.attributes['font-weight']='bold'
    tr=tref('#linktotext')
    tr.attributes['fill']='red'
    st=spannedtext()
    st.addtspan(ts)
    st.addtref(tr)
    st.addtext('This text is not bold')
    t=text(3,5,st)
    """
    def __init__(self,textlist=None):
        if textlist==None:
            self.textlist=[]
        else:
            self.textlist=textlist
    def addtext(self,text=''):
        self.textlist.append(text)
    def addtspan(self,tspan):
        self.textlist.append(tspan)
    def addtref(self,tref):
        self.textlist.append(tref)
    def __repr__(self):
        s=""
        for element in self.textlist:
            s+=str(element)
        return s
    
class rect(SVGelement):
    """r=rect(width,height,x,y,fill,stroke,stroke_width,**args)
    
    a rectangle is defined by a width and height and a xy pair 
    """
    def __init__(self,x=None,y=None,width=None,height=None,fill=None,stroke=None,stroke_width=None,**args):
        if width==None or height==None:
            if width<>None:
                raise ValueError, 'height is required'
            if height<>None:
                raise ValueError, 'width is required'
            else:
                raise ValueError, 'both height and width are required'
        SVGelement.__init__(self,'rect',{'width':width,'height':height},**args)
        if x<>None:
            self.setAttribute(Attribute('x', x))
        if y<>None:
            self.setAttribute(Attribute('y', y))
        if fill<>None:
            self.setAttribute(Attribute('fill', fill))
        if stroke<>None:
            self.setAttribute(Attribute('stroke', stroke))
        if stroke_width<>None:
            self.setAttribute(Attribute('stroke-width', stroke_width))

    def _construct(attributes):
        width = get_attr_value(attributes, 'width')
        height = get_attr_value(attributes, 'height')
        return rect(width=width.value, height=height.value)
    _construct = staticmethod(_construct)


class ellipse(SVGelement):
    """e=ellipse(rx,ry,x,y,fill,stroke,stroke_width,**args)

    an ellipse is defined as a center and a x and y radius.
    """
    def __init__(self,cx=None,cy=None,rx=None,ry=None,fill=None,stroke=None,stroke_width=None,**args):
        if rx==None or ry== None:
            if rx<>None:
                raise ValueError, 'rx is required'
            if ry<>None:
                raise ValueError, 'ry is required'
            else:
                raise ValueError, 'both rx and ry are required'
        SVGelement.__init__(self,'ellipse',{'rx':rx,'ry':ry},**args)
        if cx<>None:
            self.setAttribute(Attribute('cx', cx))
        if cy<>None:
            self.setAttribute(Attribute('cy', cy))
        if fill<>None:
            self.setAttribute(Attribute('fill', fill))
        if stroke<>None:
            self.setAttribute(Attribute('stroke', stroke))
        if stroke_width<>None:
            self.setAttribute(Attribute('stroke-width', stroke_width))
        
    def _construct(attributes):
        rx = get_attr_value(attributes, 'rx')
        ry = get_attr_value(attributes, 'ry')
        return ellipse(rx=rx.value, ry=ry.value)
    _construct = staticmethod(_construct)


class circle(SVGelement):
    """c=circle(x,y,radius,fill,stroke,stroke_width,**args)

    The circle creates an element using a x, y and radius values eg
    """
    def __init__(self,cx=None,cy=None,r=None,fill=None,stroke=None,stroke_width=None,**args):
        if r==None:
            raise ValueError, 'r is required'
        SVGelement.__init__(self,'circle',{'r':r},**args)
        if cx<>None:
            self.setAttribute(Attribute('cx', cx))
        if cy<>None:
            self.setAttribute(Attribute('cy', cy))
        if fill<>None:
            self.setAttribute(Attribute('fill', fill))
        if stroke<>None:
            self.setAttribute(Attribute('stroke', stroke))
        if stroke_width<>None:
            self.setAttribute(Attribute('stroke-width', stroke_width))

    def _construct(attributes):
        r = get_attr_value(attributes, 'r')
        if int(r.value) == 1:
            return point()
        else:
            return circle(r=r.value)
    _construct = staticmethod(_construct)


class point(circle):
    """p=point(x,y,color)
    
    A point is defined as a circle with a size 1 radius. It may be more efficient to use a
    very small rectangle if you use many points because a circle is difficult to render.
    """
    def __init__(self,x=None,y=None,fill=None,**args):
        circle.__init__(self,x,y,1,fill,**args)

class line(SVGelement):
    """l=line(x1,y1,x2,y2,stroke,stroke_width,**args)
    
    A line is defined by a begin x,y pair and an end x,y pair
    """
    def __init__(self,x1=None,y1=None,x2=None,y2=None,stroke=None,stroke_width=None,**args):
        SVGelement.__init__(self,'line',**args)
        if x1<>None:
            self.setAttribute(Attribute('x1', x1))
        if y1<>None:
            self.setAttribute(Attribute('y1', y1))
        if x2<>None:
            self.setAttribute(Attribute('x2', x2))
        if y2<>None:
            self.setAttribute(Attribute('y2', y2))
        if stroke_width<>None:
            self.setAttribute(Attribute('stroke-width', stroke_width))
        if stroke<>None:
            self.setAttribute(Attribute('stroke', stroke))

    def _construct(attributes):
        return line()
    _construct = staticmethod(_construct)

            
class polyline(SVGelement):
    """pl=polyline([[x1,y1],[x2,y2],...],fill,stroke,stroke_width,**args)
    
    a polyline is defined by a list of xy pairs
    """
    def __init__(self,points,fill=None,stroke=None,stroke_width=None,**args):
        SVGelement.__init__(self,'polyline',{'points':_xypointlist(points)},**args)
        if fill<>None:
            self.setAttribute(Attribute('fill', fill))
        if stroke_width<>None:
            self.setAttribute(Attribute('stroke-width', stroke_width))
        if stroke<>None:
            self.setAttribute(Attribute('stroke', stroke))

    def _construct(attributes):
        points = get_attr_value(attributes, 'points')
        return polyline(points.value)
    _construct = staticmethod(_construct)


class polygon(SVGelement):
    """pl=polyline([[x1,y1],[x2,y2],...],fill,stroke,stroke_width,**args)
    
    a polygon is defined by a list of xy pairs
    """
    def __init__(self,points,fill=None,stroke=None,stroke_width=None,**args):
        SVGelement.__init__(self,'polygon',{'points':_xypointlist(points)},**args)
        if fill<>None:
            self.setAttribute(Attribute('fill', fill))
        if stroke_width<>None:
            self.setAttribute(Attribute('stroke-width', stroke_width))
        if stroke<>None:
            self.setAttribute(Attribute('stroke', stroke))

    def _construct(attributes):
        points = get_attr_value(attributes, 'points')
        return polygon(points.value)
    _construct = staticmethod(_construct)


class path(SVGelement):
    """p=path(path,fill,stroke,stroke_width,**args)

    a path is defined by a path object and optional width, stroke and fillcolor
    """
    def __init__(self,pathdata,fill=None,stroke=None,stroke_width=None,id=None,**args):
        SVGelement.__init__(self,'path',{'d':str(pathdata)},**args)
        if stroke<>None:
            self.setAttribute(Attribute('stroke', stroke))
        if fill<>None:
            self.setAttribute(Attribute('fill', fill))
        if stroke_width<>None:
            self.setAttribute(Attribute('stroke-width', stroke_width))
        if id<>None:
            self.setAttribute(Attribute('id', id))
        
    def _construct(attributes):
        pathdata = get_attr_value(attributes, 'd')
        return path(pathdata.value)
    _construct = staticmethod(_construct)

        
class text(SVGelement):
    """t=text(x,y,text,font_size,font_family,**args)
    
    a text element can bge used for displaying text on the screen
    """
    def __init__(self,x=None,y=None,text=None,font_size=None,font_family=None,text_anchor=None,**args):
        SVGelement.__init__(self,'text',**args)
        if x<>None:
            self.setAttribute(Attribute('x', x))
        if y<>None:
            self.setAttribute(Attribute('y', y))
        if font_size<>None:
            self.setAttribute(Attribute('font-size', font_size))
        if font_family<>None:
            self.setAttribute(Attribute('font-family', font_family))
        if text<>None:
            self.text=text
        if text_anchor<>None:
            self.setAttribute(Attribute('text-anchor', text_anchor))

    def _construct(attributes):
        return text()
    _construct = staticmethod(_construct)


class textpath(SVGelement):
    """tp=textpath(text,link,**args)

    a textpath places a text on a path which is referenced by a link.   
    """
    def __init__(self,link,text=None,**args):
        SVGelement.__init__(self,'textPath',**args)
        self.setAttribute(Attribute('href', link, 'xlink', xlinkNSRef))
        if text<>None:
            self.text=text

    def _construct(attributes):
        href = get_attr_value(attributes, 'href')
        if href and href.nsname == 'xlink':
            return textpath(href.value)
        return None
    _construct = staticmethod(_construct)


class pattern(SVGelement):
    """p=pattern(x,y,width,height,patternUnits,**args)

    A pattern is used to fill or stroke an object using a pre-defined
    graphic object which can be replicated ("tiled") at fixed intervals
    in x and y to cover the areas to be painted.
    """
    def __init__(self,x=None,y=None,width=None,height=None,patternUnits=None,**args):
        SVGelement.__init__(self,'pattern',**args)
        if x<>None:
            self.setAttribute(Attribute('x', x))
        if y<>None:
            self.setAttribute(Attribute('y', y))
        if width<>None:
            self.setAttribute(Attribute('width', width))
        if height<>None:
            self.setAttribute(Attribute('height', height))
        if patternUnits<>None:
            self.setAttribute(Attribute('patternUnits', patternUnits))

    def _construct(attributes):
        return pattern()
    _construct = staticmethod(_construct)


class title(SVGelement):
    """t=title(text,**args)
    
    a title is a text element. The text is displayed in the title bar
    add at least one to the root svg element
    """
    def __init__(self,text=None,**args):
        SVGelement.__init__(self,'title',**args)
        if text<>None:
            self.text=text

    def _construct(attributes):
        return title()
    _construct = staticmethod(_construct)


class description(SVGelement):
    """d=description(text,**args)
    
    a description can be added to any element and is used for a tooltip
    Add this element before adding other elements.
    """
    def __init__(self,text=None,**args):
        SVGelement.__init__(self,'desc',**args)
        if text<>None:
            self.text=text

    def _construct(attributes):
        return description()
    _construct = staticmethod(_construct)


class lineargradient(SVGelement):
    """lg=lineargradient(x1,y1,x2,y2,id,**args)

    defines a lineargradient using two xy pairs.
    stop elements van be added to define the gradient colors.
    """
    def __init__(self,x1=None,y1=None,x2=None,y2=None,id=None,**args):
        SVGelement.__init__(self,'linearGradient',**args)
        if x1<>None:
            self.setAttribute(Attribute('x1', x1))
        if y1<>None:
            self.setAttribute(Attribute('y1', y1))
        if x2<>None:
            self.setAttribute(Attribute('x2', x2))
        if y2<>None:
            self.setAttribute(Attribute('y2', y2))
        if id<>None:
            self.setAttribute(Attribute('id', id))

    def _construct(attributes):
        return lineargradient()
    _construct = staticmethod(_construct)


class radialgradient(SVGelement):
    """rg=radialgradient(cx,cy,r,fx,fy,id,**args)

    defines a radial gradient using a outer circle which are defined by a cx,cy and r and by using a focalpoint.
    stop elements van be added to define the gradient colors.
    """
    def __init__(self,cx=None,cy=None,r=None,fx=None,fy=None,id=None,**args):
        SVGelement.__init__(self,'radialGradient',**args)
        if cx<>None:
            self.setAttribute(Attribute('cx', cx))
        if cy<>None:
            self.setAttribute(Attribute('cy', cy))
        if r<>None:
            self.setAttribute(Attribute('r', r))
        if fx<>None:
            self.setAttribute(Attribute('fx', fx))
        if fy<>None:
            self.setAttribute(Attribute('fy', fy))
        if id<>None:
            self.setAttribute(Attribute('id', id))

    def _construct(attributes):
        return radialgradient()
    _construct = staticmethod(_construct)

            
class stop(SVGelement):
    """st=stop(offset,stop_color,**args)

    Puts a stop color at the specified radius
    """
    def __init__(self,offset,stop_color=None,**args):
        SVGelement.__init__(self,'stop',{'offset':offset},**args)
        if stop_color<>None:
            self.setAttribute(Attribute('stop-color', stop_color))

    def _construct(attributes):
        offset = get_attr_value(attributes, 'offset')
        return stop(offset.value)
    _construct = staticmethod(_construct)
            
class style(SVGelement):
    """st=style(type,cdata=None,**args)

    Add a CDATA element to this element for defing in line stylesheets etc..
    """
    def __init__(self,type,cdata=None,**args):
        SVGelement.__init__(self,'style',{'type':type},cdata=cdata, **args)

    def _construct(attributes):
        type = get_attr_value(attributes, 'type')
        return style(type.value)
    _construct = staticmethod(_construct)
        
            
class image(SVGelement):
    """im=image(url,width,height,x,y,**args)

    adds an image to the drawing. Supported formats are .png, .jpg and .svg.
    """
    def __init__(self,url,x=None,y=None,width=None,height=None,**args):
        if width==None or height==None:
            if width<>None:
                raise ValueError, 'height is required'
            if height<>None:
                raise ValueError, 'width is required'
            else:
                raise ValueError, 'both height and width are required'
        SVGelement.__init__(self,'image',{'width':width,'height':height},**args)
        self.setAttribute(Attribute('href', url, 'xlink', xlinkNSRef))
        if x<>None:
            self.setAttribute(Attribute('x', x))
        if y<>None:
            self.setAttribute(Attribute('y', y))
 
    def _construct(attributes):
        href = get_attr_value(attributes, 'href')
        width = get_attr_value(attributes, 'width')
        height = get_attr_value(attributes, 'height')
        if href and href.nsname == 'xlink':
            return image(href.value, width=width.value, height=height.value)
        return None
    _construct = staticmethod(_construct)


class cursor(SVGelement):
    """c=cursor(url,**args)

    defines a custom cursor for a element or a drawing
    """
    def __init__(self,url,**args):
        SVGelement.__init__(self,'cursor',**args)
        self.setAttribute(Attribute('href', url, 'xlink', xlinkNSRef))

    def _construct(attributes):
        href = get_attr_value(attributes, 'href')
        if href and href.nsname == 'xlink':
            return cursor(href.value)
        return None
    _construct = staticmethod(_construct)

    
class marker(SVGelement):
    """m=marker(id,viewbox,refX,refY,markerWidth,markerHeight,**args)
    
    defines a marker which can be used as an endpoint for a line or other pathtypes
    add an element to it which should be used as a marker.
    """
    def __init__(self,id=None,viewBox=None,refx=None,refy=None,markerWidth=None,markerHeight=None,**args):
        SVGelement.__init__(self,'marker',**args)
        if id<>None:
            self.setAttribute(Attribute('id', id))
        if viewBox<>None:
            self.setAttribute(Attribute('viewBox', _viewboxlist(viewBox)))
        if refx<>None:
            self.setAttribute(Attribute('refX', refx))
        if refy<>None:
            self.setAttribute(Attribute('refY', refy))
        if markerWidth<>None:
            self.setAttribute(Attribute('markerWidth', markerWidth))
        if markerHeight<>None:
            self.setAttribute(Attribute('markerHeight', markerHeight))

    def _construct(attributes):
        return marker()
    _construct = staticmethod(_construct)

        
class group(SVGelement):
    """g=group(id,**args)
    
    a group is defined by an id and is used to contain elements
    g.addElement(SVGelement)
    """
    def __init__(self,id=None,**args):
        SVGelement.__init__(self,'g',**args)
        if id<>None:
            self.setAttribute(Attribute('id', id))

    def _construct(attributes):
        return group()
    _construct = staticmethod(_construct)

class symbol(SVGelement):
    """sy=symbol(id,viewbox,**args)

    defines a symbol which can be used on different places in your graph using
    the use element. A symbol is not rendered but you can use 'use' elements to
    display it by referencing its id.
    sy.addElement(SVGelement)
    """
    
    def __init__(self,id=None,viewBox=None,**args):
        SVGelement.__init__(self,'symbol',**args)
        if id<>None:
            self.setAttribute(Attribute('id', id))
        if viewBox<>None:
            self.setAttribute(Attribute('viewBox', _viewboxlist(viewBox)))

    def _construct(attributes):
        return symbol()
    _construct = staticmethod(_construct)

            
class defs(SVGelement):
    """d=defs(**args)

    container for defining elements
    """
    def __init__(self,**args):
        SVGelement.__init__(self,'defs',**args)

    def _construct(attributes):
        return defs()
    _construct = staticmethod(_construct)


class switch(SVGelement):
    """sw=switch(**args)

    Elements added to a switch element which are "switched" by the attributes
    requiredFeatures, requiredExtensions and systemLanguage.
    Refer to the SVG specification for details.
    """
    def __init__(self,**args):
        SVGelement.__init__(self,'switch',**args)

    def _construct(attributes):
        return switch()
    _construct = staticmethod(_construct)


class use(SVGelement):
    """u=use(link,x,y,width,height,**args)
    
    references a symbol by linking to its id and its position, height and width
    """
    def __init__(self,link,x=None,y=None,width=None,height=None,**args):
        SVGelement.__init__(self,'use',**args)
        self.setAttribute(Attribute('href', link, 'xlink', xlinkNSRef))
        if x<>None:
            self.setAttribute(Attribute('x', x))
        if y<>None:
            self.setAttribute(Attribute('y', y))

        if width<>None:
            self.setAttribute(Attribute('width', width))
        if height<>None:
            self.setAttribute(Attribute('height', height))

    def _construct(attributes):
        href = get_attr_value(attributes, 'href')
        if href and href.nsname == 'xlink':
            return use(href.value)
        return None
    _construct = staticmethod(_construct)


class link(SVGelement):
    """a=link(url,**args)

    a link  is defined by a hyperlink. add elements which have to be linked
    a.addElement(SVGelement)
    """
    def __init__(self,link='',**args):
        SVGelement.__init__(self,'a',**args)
        self.setAttribute(Attribute('href', link, 'xlink', xlinkNSRef))

    def _construct(attributes):
        href = get_attr_value(attributes, 'href')
        if href and href.nsname == 'xlink':
            return link(href.value)
        return None
    _construct = staticmethod(_construct)

        
class view(SVGelement):
    """v=view(id,**args)

    a view can be used to create a view with different attributes"""
    def __init__(self,id=None,**args):
        SVGelement.__init__(self,'view',**args)
        if id<>None:
            self.setAttribute(Attribute('id', id))

    def _construct(attributes):
        return view()
    _construct = staticmethod(_construct)


class script(SVGelement):
    """sc=script(type,type,cdata,**args)

    adds a script element which contains CDATA to the SVG drawing

    """
    def __init__(self,type,cdata=None,**args):
        SVGelement.__init__(self,'script',{'type':type},cdata=cdata,**args)

    def _construct(attributes):
        type = get_attr_value(attributes, 'type')
        return script(type.value, cdata=cdata.value)
    _construct = staticmethod(_construct)

        
class animate(SVGelement):
    """an=animate(attribute,from,to,during,**args)

    animates an attribute.    
    """
    def __init__(self,attribute,fr=None,to=None,dur=None,**args):
        SVGelement.__init__(self,'animate',{'attributeName':attribute},**args)
        if fr<>None:
            self.setAttribute(Attribute('from', fr))
        if to<>None:
            self.setAttribute(Attribute('to', to))
        if dur<>None:
            self.setAttribute(Attribute('dur', dur))

    def _construct(attributes):
        attribute = get_attr_value(attributes, 'attributeName')
        return animate(attribute.value)
    _construct = staticmethod(_construct)

        
class animateMotion(SVGelement):
    """an=animateMotion(pathdata,dur,**args)

    animates a SVGelement over the given path in dur seconds
    """
    def __init__(self,pathdata=None,dur=None,**args):
        SVGelement.__init__(self,'animateMotion',**args)
        if pathdata<>None:
            self.setAttribute(Attribute('path', str(pathdata)))
        if dur<>None:
            self.setAttribute(Attribute('dur', dur))

    def _construct(attributes):
        return animateMotion()
    _construct = staticmethod(_construct)


class animateTransform(SVGelement):
    """antr=animateTransform(type,from,to,dur,**args)
    
    transform an element from and to a value.
    """
    def __init__(self,type=None,fr=None,to=None,dur=None,**args):
        SVGelement.__init__(self,'animateTransform',{'attributeName':'transform'},**args)
        #As far as I know the attributeName is always transform
        if type<>None:
            self.setAttribute(Attribute('type', type))
        if fr<>None:
            self.setAttribute(Attribute('from', fr))
        if to<>None:
            self.setAttribute(Attribute('to', to))
        if dur<>None:
            self.setAttribute(Attribute('dur', dur))

    def _construct(attributes):
        return animateTransform()
    _construct = staticmethod(_construct)


class animateColor(SVGelement):
    """ac=animateColor(attribute,type,from,to,dur,**args)

    Animates the color of a element
    """
    def __init__(self,attribute,type=None,fr=None,to=None,dur=None,**args):
        SVGelement.__init__(self,'animateColor',{'attributeName':attribute},**args)
        if type<>None:
            self.setAttribute(Attribute('type', type))
        if fr<>None:
            self.setAttribute(Attribute('from', fr))
        if to<>None:
            self.setAttribute(Attribute('to', to))
        if dur<>None:
            self.setAttribute(Attribute('dur', dur))        

    def _construct(attributes):
        attribute = get_attr_value(attributes, 'attributeName')
        return animateColor(attribute.value)
    _construct = staticmethod(_construct)


class set(SVGelement):
    """st=set(attribute,to,during,**args)
    
    sets an attribute to a value for a
    """
    def __init__(self,attribute,to=None,dur=None,**args):
        SVGelement.__init__(self,'set',{'attributeName':attribute},**args)
        if to<>None:
            self.setAttribute(Attribute('to', to))
        if dur<>None:
            self.setAttribute(Attribute('dur', dur))

    def _construct(attributes):
        attribute = get_attr_value(attributes, 'attributeName')
        return set(attribute.value)
    _construct = staticmethod(_construct)


class svg(SVGelement):
    """s=svg(viewbox,width,height,**args)
    
    a svg or element is the root of a drawing add all elements to a svg element.
    You can have different svg elements in one svg file
    s.addElement(SVGelement)

    eg
    d=drawing()
    s=svg((0,0,100,100),'100%','100%')
    c=circle(50,50,20)
    s.addElement(c)
    d.setSVG(s)
    d.toXml()
    """
    def __init__(self,viewBox=None, width=None, height=None,**args):
        SVGelement.__init__(self,'svg',**args)
        if viewBox<>None:
            self.setAttribute(Attribute('viewBox', _viewboxlist(viewBox)))
        if width<>None:
            self.setAttribute(Attribute('width', width))
        if height<>None:
            self.setAttribute(Attribute('height', height_))
        self.namespace="http://www.w3.org/2000/svg"

    def _construct(attributes):
        return svg()
    _construct = staticmethod(_construct)


class ElementHelper(object):
    def __init__(self, name, attrs):
        self.name = name
        self.attrs = attrs
        self.cdata = None
        self.text = None

class Stack(object):
    def __init__(self):
        self._stack = []

    def push(self, obj):
        self._stack.append(obj)

    def pop(self):
        if len(self._stack) == 0:
            return None
        obj = self._stack[-1]
        del self._stack[-1]
        return obj

    def peek(self):
        if len(self._stack) == 0:
            return None
        return self._stack[-1]

    def is_empty(self):
        if len(self._stack) == 0:
            return True
        return False

    def size(self):
        return len(self._stack)

class SVGImportParser(object):
    def __init__(self):
        self._indent = 0
        self._cdata = 0
        self._stack = Stack()
        self._base = None
        self._debug = False

    def getBaseElement(self):
        return self._base

    def log(self, msg):
        if self._debug:
            print "    " * self._indent + msg

    def StartElementHandler(self, name, attrs):
        self.log("<%s>" % name)
        self._indent = self._indent + 1
        import copy
        attrs = copy.deepcopy(attrs)
        for attrname, attrvalue in attrs.items():
            self.log("%s = %s" % (attrname, attrvalue))
        parent = self._stack.peek()
        elt = SVGelement.construct(name, attrs)
        if not self._base:
            self._base = elt
        if parent and elt:
            parent.addElement(elt)
        self._stack.push(elt)

    def StartCdataSectionHandler(self):
        self._cdata = 1

    def CharacterDataHandler(self, content):
        if self._cdata:
            self.log("CDATA = '%s'" % content)
            elt = self._stack.peek()
            if elt:
                elt.cdata = elt.cdata + content
        else:
            if len(content) and not content.isspace():
                self.log("Text = '%s'" % content.strip())
                elt = self._stack.peek()
                if elt:
                    if not elt.text:
                        elt.text = ""
                    elt.text = elt.text + content.strip()

    def EndCdataSectionHandler(self):
        self._cdata = 0

    def EndElementHandler(self, name):
        self._indent = self._indent - 1
        self.log("</%s>" % name)
        self._stack.pop()

    def CommentHandler(self, comment):
        self.log("Comment = '%s'" % comment)

    def StartNamespaceDeclHandler(self, prefix, uri):
        self.log("Namespace = '%s' -> '%s'" % (prefix, uri))

    def EndNamespaceDeclHandler(self, prefix):
        self.log("Namespace = '%s'" % prefix)

        
class drawing:
    """d=drawing()

    this is the actual SVG document. It needs a svg element as a root.
    Use the addSVG method to set the svg to the root. Use the toXml method to write the SVG
    source to the screen or to a file
    d=drawing()
    d.addSVG(svg)
    d.toXml(optionalfilename)
    """

    def __init__(self):
        self.svg=None

    def setSVG(self,svg):
        self.svg=svg
        #Voeg een element toe aan de grafiek toe.

    def fromXml(self, xml):
        HANDLER_NAMES = [
            'StartElementHandler', 'EndElementHandler',
            'CharacterDataHandler',
            'StartNamespaceDeclHandler', 'EndNamespaceDeclHandler',
            'CommentHandler',
            'StartCdataSectionHandler', 'EndCdataSectionHandler',
            ]

        # Create a parser
        parser = expat.ParserCreate()

        handler = SVGImportParser()
        for name in HANDLER_NAMES:
            setattr(parser, name, getattr(handler, name))
        parser.returns_unicode = 0

        # Parse the XML
        parser.Parse(xml)
        base_element = handler.getBaseElement()
        if not base_element or not isinstance(base_element, svg):
            raise Exception("Base element was not SVG.")
        self.setSVG(base_element)

    if use_dom_implementation==0:      
        def toXml(self, filename='',compress=False):
            import cStringIO
            xml=cStringIO.StringIO()
            xml.write("<?xml version='1.0' encoding='UTF-8'?>\n")
            xml.write("<!DOCTYPE svg PUBLIC \"-//W3C//DTD SVG 1.0//EN\" \"http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd \">\n")      
            self.svg.toXml(0,xml)
            if not filename:
                if compress:
                    import gzip
                    f=cStringIO.StringIO()
                    zf=gzip.GzipFile(fileobj=f,mode='wb')
                    zf.write(xml.getvalue())
                    zf.close()
                    f.seek(0)
                    return f.read()
                else:
                    return xml.getvalue()
            else:
                if filename[-4:]=='svgz':
                    import gzip
                    f=gzip.GzipFile(filename=filename,mode="wb", compresslevel=9)
                    f.write(xml.getvalue())
                    f.close()
                else:
                    f=file(filename,'w')
                    f.write(xml.getvalue())
                    f.close()

    else:
        def toXml(self,filename='',compress=False):
            """drawing.toXml()        ---->to the screen
            drawing.toXml(filename)---->to the file
            writes a svg drawing to the screen or to a file
            compresses if filename ends with svgz or if compress is true
            """
            doctype = implementation.createDocumentType('svg',"-//W3C//DTD SVG 1.0//EN""",'http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd ')
        
            global root
            #root is defined global so it can be used by the appender. Its also possible to use it as an arugument but
            #that is a bit messy.
            root=implementation.createDocument(None,None,doctype)
            #Create the xml document.
            global appender
            def appender(element,elementroot):
                """This recursive function appends elements to an element and sets the attributes
                and type. It stops when alle elements have been appended"""
                if element.namespace:
                    e=root.createElementNS(element.namespace,element.type)
                else:
                    e=root.createElement(element.type)
                if element.text:
                    textnode=root.createTextNode(element.text)
                    e.appendChild(textnode)
                for attr in element.attributes.values():   #in element.attributes is supported from python 2.2
                    if attr.nsname and attr.nsref:
                        e.setAttributeNS(attr.nsref, attr.nsname+":"+attr.name, str(attr.value))
                    else:
                        e.setAttribute(attr.name,str(attr.value))
                if element.elements:
                    for el in element.elements:
                        e=appender(el,e)
                elementroot.appendChild(e)
                return elementroot
            root=appender(self.svg,root)
            if not filename:
                import cStringIO
                xml=cStringIO.StringIO()
                PrettyPrint(root,xml)
                if compress:
                    import gzip
                    f=cStringIO.StringIO()
                    zf=gzip.GzipFile(fileobj=f,mode='wb')
                    zf.write(xml.getvalue())
                    zf.close()
                    f.seek(0)
                    return f.read()
                else:
                    return xml.getvalue()
            else:
                try:
                    if filename[-4:]=='svgz':
                        import gzip
                        import cStringIO
                        xml=cStringIO.StringIO()
                        PrettyPrint(root,xml)
                        f=gzip.GzipFile(filename=filename,mode='wb',compresslevel=9)
                        f.write(xml.getvalue())
                        f.close()
                    else:
                        f=open(filename,'w')
                        PrettyPrint(root,f)
                        f.close()
                except:
                    print "Cannot write SVG file: " + filename

    def validate(self):
        try:
            import xml.parsers.xmlproc.xmlval
        except:
            raise exceptions.ImportError,'PyXml is required for validating SVG'
        svg=self.toXml()
        xv=xml.parsers.xmlproc.xmlval.XMLValidator()
        try:
            xv.feed(svg)
        except:
            raise "SVG is not well formed, see messages above"
        else:
            print "SVG well formed"


elementTable = {
    'tspan': tspan,
    'tref': tref,
    'rect': rect,
    'ellipse': ellipse,
    'circle': circle,
    'line': line,
    'polyline': polyline,
    'polygon': polygon,
    'path': path,
    'text': text,
    'textPath': textpath,
    'pattern': pattern,
    'title': title,
    'desc': description,
    'linearGradient': lineargradient,
    'radialGradient': radialgradient,
    'stop': stop,
    'style': style,
    'image': image,
    'cursor': cursor,
    'marker': marker,
    'g': group,
    'symbol': symbol,
    'defs': defs,
    'switch': switch,
    'use': use,
    'a': link,
    'view': view,
    'script': script,
    'animate': animate,
    'animateMotion': animateMotion,
    'animateTransform': animateTransform,
    'animateColor': animateColor,
    'set': set,
    'svg': svg
}    

def from_file(document):
    import sys
    f = open(sys.argv[1], "r")
    fc = f.read()
    document.fromXml(fc)
    print document.toXml()

def to_file(document):
    s=svg((0,0,100,100))
    r=rect(-100,-100,300,300,'cyan')
    s.addElement(r)

    text = tspan("Foobar")
    s.addElement(text)
    
    t=title('SVGdraw Demo')
    s.addElement(t)
    g=group('animations')
    e=ellipse(0,0,5,2)
    g.addElement(e)
    c=circle(0,0,1,'red')
    g.addElement(c)
    pd=pathdata(0,-10)
    for i in range(6):
        pd.relsmbezier(10,5,0,10)
        pd.relsmbezier(-10,5,0,10)
    an=animateMotion(pd,10)
    an.setAttribute(Attribute('rotate', 'auto-reverse'))
    an.setAttribute(Attribute('repeatCount', "indefinite"))
    g.addElement(an)
    s.addElement(g)
    for i in range(20,120,20):
        u=use('#animations',i,0)
        s.addElement(u)
    for i in range(0,120,20):
        for j in range(5,105,10):
            c=circle(i,j,1,'red','black',.5)
            s.addElement(c)
    document.setSVG(s)
     
    print document.toXml()

def main():
    d=drawing()
    from_file(d)
#    to_file(d)

if __name__=='__main__':
    main()
