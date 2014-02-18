# -*- coding: utf-8 -*-

'''
Created on June 22, 2013

@author: toby
'''
import xml.etree.ElementTree

from ALDIRAC.Core.Utilities.Sewlabparams import SewLabParam, SewLabParams, SewLabParamBlock, SewLabParamTextBlock


def sewlab_xml_parser(xmlinput):
    """Parses xml output of a SewLabParams instance and returns the same object."""
    
    some_file_like = xmlinput

    params = None
    blocks = [None, None, None]
    depth = -1

    for event, element in xml.etree.ElementTree.iterparse(some_file_like, events=('start', 'end')):
        
        if element.tag == 'SewLabParams':
            if event == 'start':
                params = SewLabParams(auto_init=False)
            else: # end
                break

        elif element.tag == 'SewLabParamBlock':
            if event == 'start':
                depth += 1
                blocks[depth] = SewLabParamBlock(element.get('name'), [], indented=depth)
                #print >>sys.stderr, "entering block ({0:d}): {1:s}".format(depth, element.get('name'))
            else: # end
                #print >>sys.stderr, "leaving block ({0:d}): {1:s}".format(depth, element.get('name'))
                if depth == 0:
                    params._add_block(blocks[depth])
                else:
                    blocks[depth-1]._add_param(blocks[depth])
                blocks[depth] = None
                depth -= 1
                

        elif element.tag == 'SewLabParamTextBlock':
            if event == 'start':
                depth += 1
                blocks[depth] = SewLabParamTextBlock(element.get('name'), element.text)
                #print >>sys.stderr, "entering block ({0:d}): {1:s}".format(depth, element.get('name'))
            else: # end
                #print >>sys.stderr, "leaving block ({0:d}): {1:s}".format(depth, element.get('name'))
                params._add_block(blocks[depth])
                blocks[depth] = None
                depth -= 1

        elif element.tag == 'SewLabParam' and event == 'end':
            name = element.get('name')
            if element.get('type') == 'str':
                value = element.get('value')
            else:
                value = eval(element.get('type') + '("' + element.get('value') + '")')
            state = (True if element.get('state').lower() == 'true' else False)
            deprecated = (True if element.get('deprecated').lower() == 'true' else False)
            pdict = dict((('name', name),('value', value),('state', state),('deprecated', deprecated)))
            blocks[depth]._add_param(SewLabParam(pdict))
        
    return params

#if __name__ == '__main__':
#
#    xmlfile = open('./parms.xml', 'r')
#    data = loadxml(xmlfile)
#    xmlfile.close()
#    
#    #print lxml.etree.tostring(data.dumpxml(), pretty_print=True)

# EOF