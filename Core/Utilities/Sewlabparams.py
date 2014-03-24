# -*- coding: utf-8 -*-

'''
Created on June 17, 2013

Contains old material written by Tobias Gresch at ETHZ.
Revised configuration parameters on June 14, 2013.

A (patched-up) trial to wrap the sewlab configuration file into
python classes. Allows to modify the simulation parameters directly,
e.g. p.transport.taup_sorting = 0.1, and to dump everything to xml and
re-parse the xml to a same object.

@author: toby
'''

import sys
import xml.etree.ElementTree


from xml.etree.ElementTree import Element, SubElement


#
#
# dummy-materials
#
# This function returns a string containing the standard material block.
# This material block is still used to calculate the lattice-constant (linearly
# interpolated) and the refractive index and therefore always the same block data
# can be used.
#
#

dummy_material_params = """materials {
    bulk {
        alias            = InAs;
        mass            = 0.027;
        epsilon-inf        = 12.25;    // not used
        epsilon-zero    = 15.15;
        hLO                = 12.0;        // not used
        hTO                = 12.0;        // not used
        direct-gap        = 0.356;        // obsolete
        lattice-const    = 6.0583;
    }
    bulk {
        alias            = GaAs;
        mass            = 0.067;
        epsilon-inf     = 10.92;    // not used
        epsilon-zero    = 12.68;
        hLO                = 0.0361;    // not used
        hTO                = 0.0335;    // not used
        direct-gap        = 1.16053;    // not used
        lattice-const    = 5.65;
    }
    bulk {
        alias            = AlAs;
        mass            = 0.15;
        epsilon-inf     = 8.16;        // not used
        epsilon-zero    = 10.14;
        hLO                = 0.0496;    // not used
        hTO                = 0.0445;    // not used
        direct-gap        = 2.5982;    // not used
        lattice-const    = 5.66;
    }
    alloy {
        alias = GaInAs;
        zero-fraction = InAs;
        full-fraction = GaAs;
    }
    alloy {
        alias = AlInAs;
        zero-fraction = InAs;
        full-fraction = AlAs;
    }
    interface {
        left-material = GaAs;
        right-material = AlAs;
        discontinuity = 0.9;
    }
    interface {
        left-material = InAs;
        right-material = AlAs;
        discontinuity = 1.4;
    }
    interface {
        left-material = InAs;
        right-material = GaAs;
        discontinuity = 0.6;
    }
}
"""

#
#
# parameter definitions
#
#

buildpot_params = {
    'name':'buildpot-params',
    'params':[
        {'name':'bulk-step', 'value':1, 'state':True},
        {'name':'interface-step', 'value':0.01, 'state':True},
        {'name':'interface-diffusion', 'value':0.0, 'state':True},
        {'name':'mesh-style', 'value':'fixed-step', 'state':True},
        {'name':'phony-left-barrier', 'value':'NO', 'state':True, 'subparams':{ \
            'left-barrier':[
                {'name':'thickness', 'value':350.0, 'state':True},
                {'name':'material', 'value':'AlInAs', 'state':True},
                {'name':'label', 'value':'"left phony"', 'state':True},
                {'name':'x', 'value':0.48, 'state':False},
                {'name':'mass', 'value':0.076, 'state':False},
                {'name':'gap', 'value':1.41, 'state':False},
                {'name':'discont', 'value':0.52, 'state':False},
            ]},
        },
        {'name':'phony-right-barrier', 'value':'AUTO', 'state':True, 'subparams':{ \
            'right-barrier':[
                {'name':'thickness', 'value':350, 'state':True},
                {'name':'material', 'value':'AlInAs', 'state':True},
                {'name':'label', 'value':'"right phony"', 'state':True},
                {'name':'x', 'value':0.48, 'state':False},
                {'name':'mass', 'value':0.076, 'state':False},
                {'name':'gap', 'value':1.41, 'state':False},
                {'name':'discont', 'value':0.52, 'state':False},
            ]},
        },
        {'name':'has-box-wall', 'value':True, 'state':True},
        {'name':'auto-box-wall', 'value':True, 'state':True, 'subparams':{ \
            'box-wall-layer':[
                {'name':'thickness', 'value':2.0, 'state':True},
                {'name':'material', 'value':'AlInAs', 'state':True},
                {'name':'label', 'value':'"box layer"', 'state':True},
                {'name':'x', 'value':0.48, 'state':False},
                {'name':'mass', 'value':0.076, 'state':False},
                {'name':'gap', 'value':10.0, 'state':False},
                {'name':'discont', 'value':0.52, 'state':False},
            ]},
        },
        
    ]
} # buildpot-params

transport_params = {
    'name':'transport',
    'params':[
        {'name':'taup-sorting ', 'value': 0.08, 'state':False, 'deprecated':True},
        {'name':'tunneltime-max', 'value':100, 'state':False, 'deprecated':True},
        {'name':'tunneltime-maxstates', 'value':10, 'state':False, 'deprecated':True},
        {'name':'initial-temperature', 'value':1200.0, 'state':True},
        {'name':'electron-T-maxiter', 'value':500, 'state':True},
        {'name':'electron-T-tolerance', 'value':0.5, 'state':True},
        {'name':'k-space-sampling', 'value':256, 'state':True},
        {'name':'number-of-kT-before-cut-off', 'value':7,'state':True},
        {'name':'hlo-energy', 'value':0.034, 'state':True},
        {'name':'hlo-temperature', 'value':303.0, 'state':True},
        {'name':'hlo-qscreen', 'value':0.0, 'state':True},
        {'name':'ifr-inplane-corr', 'value':90, 'state':True},
        {'name':'ifr-vertical-corr', 'value':15.0, 'state':True},
        {'name':'ifr-height', 'value':1.2, 'state':True},
        {'name':'use-uniform-taup', 'value':False, 'state':True, 'deprecated':True},
        {'name':'uniform-taup', 'value':0.04, 'state':True, 'deprecated':True},
        {'name':'pop-tolerance', 'value':1e-3, 'state':True},
        {'name':'pop-max-iterations', 'value':500, 'state':True},
        {'name':'pop-stab-damping', 'value':1e-3, 'state':True},
        {'name':'solution-maxiter', 'value':500, 'state':True},
        {'name':'current-uniformity-limit', 'value':1e-6, 'state':True, 'deprecated':True},
        {'name':'solution-uniformity-limit', 'value':1e-2, 'state':True, 'deprecated':True},
        {'name':'imaginary-part-limit', 'value':1e-10, 'state':True, 'deprecated':True},
        {'name':'light-fixed-laser-energy', 'value':False, 'state':True},
        {'name':'light-use-bloch-gain', 'value':False, 'state':True},
        {'name':'light-laser-energy', 'value':0.160,'state':True},
        {'name':'light-gain-window-min-energy', 'value':0.140,'state':True},
        {'name':'light-gain-window-max-energy', 'value':0.180,'state':True},
        {'name':'light-gain-window-sampling', 'value':128,'state':True},
        {'name':'light-losses', 'value':5.5, 'state':True},
        {'name':'light-initial-photonflux', 'value':2e22, 'state':True},
        {'name':'light-bracketing-maxiter', 'value':128, 'state':True},
        {'name':'light-convergence-maxiter', 'value':5000, 'state':True},
        {'name':'light-convergence-tolerance', 'value':0.1, 'state':True},
        {'name':'light-damping-factor', 'value':0.3, 'state':True},
        {'name':'light-photonflux-precision', 'value':0.05, 'state':True},
    ],
} # transport

solver_params = {
    'name':'solver',
    'params':[
        {'name':'emin', 'value':0.001, 'state':True},
        {'name':'emax', 'value':1.5, 'state':True},
        {'name':'up-to-bound-state', 'value':30, 'state':True},
        {'name':'continuum-emin', 'value':0.001, 'state':True},
        {'name':'continuum-emax', 'value':1.5, 'state':True},
        {'name':'initial-samples', 'value':1200, 'state':True},
        {'name':'np', 'value':True, 'state':True},
        {'name':'energy-precision', 'value':1e-12, 'state':True},
        {'name':'max-divergence', 'value':1e-4, 'state':True},
        {'name':'letal-divergence', 'value':True, 'state':False},
        {'name':'max-iterations', 'value':1000, 'state':True},
        {'name':'boundify', 'value':True, 'state':True},
        {'name':'adjust-box-wall', 'value':True, 'state':True},
        {'name':'wf-resampling', 'value':True, 'state':True},
        {'name':'wf-step', 'value':1.0, 'state':True},
        {'name':'up-to-continuum-state', 'value':200, 'state':True},    
    ],
} # solver_params

selfsolver_params = {
    'name':'selfsolver',
    'params':[
        {'name':'max-iterations', 'value':500, 'state':True},
        {'name':'damping-factor', 'value':1e-3, 'state':True},
        {'name':'energy-precision', 'value':1.5e-4, 'state':True},
        {'name':'period-wraping', 'value':2, 'state':True},
        {'name':'output-history-file', 'value':False, 'state':True},
        {'name':'convergence-crop', 'value':10, 'state':True},
        {'name':'converge_on_selfpot', 'value':True, 'state':True},
    ],
} # selfsolver

thermal_params = {
    'name':'thermal-model',
    'params':[
        {'name':'initial-fermi-min', 'value':-1e-3, 'state':True},
        {'name':'initial-fermi-max', 'value':1e-3, 'state':True},
        {'name':'fermi-bracketing-max-iterations', 'value':100, 'state':True},
        {'name':'fermi-brent-max-iterations', 'value':100, 'state':True},
        {'name':'fermi-tolerance', 'value':1e-8, 'state':True},
    ],
} # thermal-model

absorption_params = {
    'name':'absorption',
    'params':[
        {'name':'min-photon-energy', 'value':1e-5, 'state':True}, # eV
        {'name':'max-photon-energy', 'value':0.5, 'state':True}, # eV
        {'name':'spectrum-sampling', 'value':512, 'state':True},
        {'name':'k-space-sampling', 'value':64, 'state':True},
        {'name':'number-of-kT-before-cut-off', 'value':7, 'state':True},
        {'name':'use-non-parabolicity', 'value':True, 'state':True},
        {'name':'default-subband-broadening', 'value':4e-3, 'state':True},
        {'name':'modal-index', 'value':3.3, 'state':True},
        {'name':'modal-overlap', 'value':1.0, 'state':True},
    ],
} # absorption-params

impurity_params = {
    'name':'impurities',
    'params':[
        {'name':'angular-sampling', 'value':32, 'state':True},
        {'name':'formfactor-lod', 'value':8, 'state':True},
        {'name':'exp-cutoff', 'value':1e-06, 'state':True},
        {'name':'crop-profile', 'value':True, 'state':True},
        {'name':'zero-trigger', 'value':0.0, 'state':True},
        {'name':'wf-step', 'value':3.0, 'state':True},
    ],
} # impurities

ifr_params = {
    'name':'ifr',
    'params':[
        {'name':'angular-sampling','value':32, 'state':True},
    ],
} # ifr-params

hlo_params = {
    'name':'hlo',
    'params':[
        {'name':'level-of-details', 'value':8, 'state':True},
        {'name':'angular-sampling', 'value':32, 'state':True},
        {'name':'kp0', 'value':71.3,'state':True},
        {'name':'exp-cutoff', 'value':1e-6,'state':True},
    ],
} # hlo-params

alloyd_params = {
    'name':'alloy-disorder',
    'params':[
        {'name':'angular-sampling', 'value':32, 'state':True},
    ],
} # alloy-disorder

show_params = {
    'name':'show-options',
    'params':[
        {'name':'underline-eigenstates', 'value':True, 'state':True},
    ],
} # show-options

# a list of all the parameters
SEWLAB_PARAMS = [
    dummy_material_params,
    buildpot_params,
    solver_params,
    absorption_params,
    ifr_params,
    hlo_params,
    alloyd_params,
    impurity_params,
    transport_params,
    selfsolver_params,
    thermal_params,
    show_params
]






















class SewSpecialNames ():
    """A class providing methods for sewlab configuration paramter names
    
    Parameter names for sewlab are sparated by dashes ('-') which is an operator
    under python. Therefore, we replace systematically all the dashes in the
    parameter names by underscores ('_'). However, some configuration parameter
    names do not use dashes but underscores, which need not to be treated at all.
    """

    __INVARIANT__ = ['converge_on_selfpot']

    def _enc_name(self, name):
        """A method used to encode the specified name for internal use."""
        if name in self.__INVARIANT__:
            return name
        return name.replace('-', '_')
    
    def _dec_name(self, name):
        """A method used to decode the specified name for external use."""
        if name in self.__INVARIANT__:
            return name
        return name.replace('_', '-')




class SewLabParams (object, SewSpecialNames):
    """Class grouping together all the sewlab parameter sections."""

    def __init__(self, auto_init=True):
        if auto_init:
            # initialize the instance with the old parameters
            self.__attrs__ = ['materials']
            self.__setattr__('materials', SewLabParamTextBlock('materials', dummy_material_params))
            for block in SEWLAB_PARAMS[1:]:
                self._add_block(SewLabParamBlock(self._enc_name(block['name']), block['params']))
                #self.__attrs__.append(self._enc_name(block['name']))
                #self.__setattr__(self._enc_name(block['name']), )
        else:
            self.__attrs__ = []
        return

    def _add_block(self, block):
        if isinstance(block, SewLabParamBlock):
            if block.name not in self.__attrs__:
                self.__attrs__.append(block.name)
            self.__setattr__(block.name, block)
        return

    def ajust(self, design):
        """This function reads some values from a design and adapts the
        configuration parameters accordingly.
        """
        
        pass

    def _ajdust_light_window(self, center, wing=50.0):
        pass
    
    def _ajust_boxwall(self, material):
        pass

    def _adjust_phony(self, material, which='both'):
        pass

    def _render_cfg(self):
        """Internal configuration rendering routine.
        Returns a string with the configuration data.
        """
        s = ''
        for a in self.__attrs__:
            s += self.__getattribute__(a).render_cfg()
        return(s)

    def render_cfg(self, filename=None):
        """Configuration rendering routine.
        Takes a filename as argument and writes the configuration data into
        the file.
        """
        if filename is not None:
            f = file(filename, 'w')
            f.write(self._render_cfg())
            f.close()
            return
        return self._render_cfg()

    def set_param(self, name, value):
        """Set parameter with name to value
        
        Returns True if parameter was found and value was set.
        """
        param = self._find_param(name)
        if param is not None:
            try:
                param.value = value
            except:
                pass
            else:
                return True
        return False

    def get_param(self, name):
        """Returns the value of parameter with name"""
        return(self._find_param(name).value)

    def _find_param(self, name):
        """Returns parameter with name
        
        Name can be a simple parameter name which then will return the first
        parameter whose name matches. It can also be a path and a parameter name,
        separated by a dot, e.g. buildpot-params.right-barrier.material in which
        case the first parameter will be returned where also the path elements
        match.
        """
        elems = map(self._enc_name, name.split('.'))
        name_ = elems[-1]
        #print >>sys.stderr, "*** name: ", elems[-1], " encoded: ", name_, " attributes: ", str(self.__attrs__)
        callers = []
        for attr in self.__attrs__:
            param_ = self.__dict__[attr]
            if attr == name_: # in the actual code this will never happen as __attrs__ only contains blocks...
                if isinstance(param_, SewLabParam):
                    return param_
            elif isinstance(param_, SewLabParamBlock) and not isinstance(param_, SewLabParamTextBlock):
                param = param_._find_param(name_, callers=callers, path=elems[:-1])
                if param is not None:
                    return param
        return

    def dumpxml(self, parent=None):
        if parent is None:
            parent = Element(type(self).__name__)
        for a in self.__attrs__:
            self.__getattribute__(a).dumpxml(parent)
        return parent

    def apply_xml_diff(self, xmlinput):
        """Overwrites parameters passed as xml string."""

        some_file_like = xmlinput

        blocknames = [None, None, None]
        depth = -1
        
        for event, element in xml.etree.ElementTree.iterparse(some_file_like, events=('start', 'end')):
            
            if element.tag == 'SewLabParamsDiff':
                if event == 'start':
                    continue
                else: # end
                    break
        
            elif element.tag == 'SewLabParamBlock':
                if event == 'start':
                    depth += 1
                    blocknames[depth] = self._enc_name(element.get('name'))
                    print >>sys.stderr, "entering block ({0:d}): {1:s}".format(depth, element.get('name'))
                else: # end
                    print >>sys.stderr, "leaving block ({0:d}): {1:s}".format(depth, element.get('name'))
                    blocknames[depth] = None
                    depth -= 1
                    
        
            elif element.tag == 'SewLabParamTextBlock':
                if event == 'start':
                    depth += 1
                    blocknames[depth] = self._enc_name(element.get('name'))
                    print >>sys.stderr, "entering block ({0:d}): {1:s}".format(depth, element.get('name'))
                else: # end
                    print >>sys.stderr, "leaving block ({0:d}): {1:s}".format(depth, element.get('name'))
                    blocknames[depth] = None
                    depth -= 1
        
            elif element.tag == 'SewLabParam' and event == 'end':
                name = self._enc_name(element.get('name'))
                if element.get('type') == 'str':
                    value = element.get('value')
                else:
                    value = eval(element.get('type') + '("' + element.get('value') + '")')
                state = (True if element.get('state').lower() == 'true' else False)
                deprecated = (True if element.get('deprecated').lower() == 'true' else False)
                param = SewLabParam(dict((('name', name),('value', value),('state', state),('deprecated', deprecated))))
                
                # update the parameter
                if depth == 1:
                    self.__getattribute__(blocknames[0]).__getattribute__(blocknames[1])._add_param(param)
                elif depth == 0:
                    self.__getattribute__(blocknames[0])._add_param(param)
            
        return



class SewLabParam (object, SewSpecialNames):
    """Class representing a single sewlab configuration parameter."""

    def __init__(self, pdict):
        self.name = self._enc_name(pdict['name'])
        self.value = pdict['value']
        self.type = type(self.value)
        self.active = (True if (pdict.has_key('state') and pdict['state'] is True) else False)
        self.deprecated = (True if (pdict.has_key('deprecated') and pdict['deprecated'] is True) else False)

    def __str__(self):
        return (self._dec_name(self.name) + ' = ' + self._dec_value(self.value) + ';')
    
    def __repr__(self):
        return(self.__str__())
    
    def render_cfg(self):
        return(self.__str__())
    
    def dumpxml(self, parent):
        p = SubElement(parent, type(self).__name__)
        p.set('name', self.name)
        p.set('value', str(self.value))
        p.set('type', self.type.__name__)
        p.set('state', ('True' if self.active else 'False'))
        p.set('deprecated', ('True' if self.deprecated else 'False'))
    
    def _dec_value(self, value):
        """Method to decode parameter types internally where cast to string does not do the job."""
        if self.type.__name__ == 'bool':
            return ('TRUE' if self.value is True else 'FALSE')
        return(str(value))


class SewLabParamBlock (object, SewSpecialNames):
    """Class representing a block of sewlab configuration parameters."""

    __SPACES_PER_INDENT__ = 4

    def __init__(self, name, parry, indented=0):
        self.name = self._enc_name(name)
        self.indented = indented
        self.__attrs__ = []
        for p in parry:
            self._add_param(SewLabParam(p))
            #self.__attrs__.append(self._enc_name(p['name']))
            #self.__setattr__(self._enc_name(p['name']), SewLabParam(p))
            if p.has_key('subparams'):
                for key in p['subparams']:
                    self._add_param(SewLabParamBlock(key, p['subparams'][key], indented=indented+1))
                    #self.__attrs__.append(self._enc_name(key))
                    #self.__setattr__(self._enc_name(key), SewLabParamBlock(self._enc_name(key), p['subparams'][key], indented=indented+1))
        return

    def _add_param(self, param):
        if param.name not in self.__attrs__:
            self.__attrs__.append(param.name)
        self.__setattr__(param.name, param)

    def render_cfg(self):
        s = (' ' * self.indented * self.__SPACES_PER_INDENT__) + self._dec_name(self.name)+ '\n'
        s += (' ' * self.indented * self.__SPACES_PER_INDENT__) + '{\n'
        for a in self.__attrs__:
            if isinstance(self.__getattribute__(a), SewLabParamBlock):
                s += ' ' * self.indented * self.__SPACES_PER_INDENT__
            else:
                s += ' ' * (self.indented + 1) * self.__SPACES_PER_INDENT__
            s += self.__getattribute__(a).render_cfg() + '\n'
        s += (' ' * self.indented * self.__SPACES_PER_INDENT__) + '}\n'
        return(s)

    def dumpxml(self, parent):
        block = SubElement(parent, type(self).__name__)
        block.set('name', self._dec_name(self.name))
        for a in self.__attrs__:
            self.__getattribute__(a).dumpxml(block)

    def _find_param(self, name, callers=[], path=[]):
        """Recursive function that returns the parameter with name or None"""
        name_ = self._enc_name(name)
        callers.append(self.name)
        #print >>sys.stderr, "name: ", name, " encoded: ", name_, " callers: ", str(callers)
        for attr in self.__attrs__:
            param_ = self.__dict__[attr]
            if attr == name_:
                if isinstance(param_, SewLabParam):
                    if  (len(path)) == 0 or (callers[-len(path):] == path): 
                        return param_
            elif isinstance(param_, SewLabParamBlock) and not isinstance(param_, SewLabParamTextBlock):
                param = param_._find_param(name, callers=callers, path=path)
                if param is not None:
                    return param
        callers.pop(-1) # we didn't find anything in this branch... popping path of current element
        return        

    def __setattr__(self, name, value):
        # we need to overwrite the __setattr__ method in order to treat configuration parameters specially
        try:
            if name in self.__attrs__:
                if isinstance(self.__getattribute__(name), (SewLabParam, SewLabParamBlock)):
                    self.__getattribute__(name).__setattr__('value', value)
        except:
            object.__setattr__(self, name, value)


class SewLabParamTextBlock (SewLabParamBlock):
    """Class representing a text block for configuration parameters."""

    def __init__(self, name, text):
        self.name = self._enc_name(name)
        self._text = text

    def __str__(self):
        return(self._text)

    def render_cfg(self):
        return(self._text)

    def dumpxml(self, parent):
        p = SubElement(parent, type(self).__name__)
        p.set('name', self._dec_name(self.name))
        p.text = self._text
        return


#if __name__ == '__main__':
#    
#    from sewlabparams_parser import loadxml
#    
#    # initialize param instance from zero
#    p = SewLabParams()
#    
#    # open xmlfile, dump the param block to xml
#    f = open('./params.xml', 'w')
#    f.writelines(lxml.etree.tostringlist(p.dumpxml(), pretty_print=True, xml_declaration=True, encoding='utf-8'))
#    f.close()
#
#    # change a parameter...
#    p.selfsolver.energy_precision = 0.00015;
#
#    # open the xml file and parse the data
#    xf = open('./params.xml', 'r')
#    pp = loadxml(xf)
#    xf.close()
#
#    # open xml diff and apply
#    xmldiff = '''<?xml version='1.0' encoding='utf-8'?>
#<SewLabParamsDiff>
#  <SewLabParamBlock name="show-options">
#    <SewLabParam name="underline_eigenstates" value="False" type="bool" state="True" deprecated="False"/>
#  </SewLabParamBlock>
#</SewLabParamsDiff>
#'''
#    pp.apply_xml_diff(xmldiff)
#
#    pp.render_cfg()

# EOF