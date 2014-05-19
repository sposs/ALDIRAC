#!/usr/bin/env python
import sys
import os
from xml.etree.ElementTree import ElementTree
import tempfile
from ALDIRAC.Interfaces.API.Applications import SewlabPostProcess

try:
    import simudb
except ImportError:
    print 'Missing simudb, try installing with pip install'
    sys.exit(1)
try:
    import sewlabwrapper
except ImportError:
    print "Missing sewlabwrapper, try installing with pip install"
    sys.exit(1)
    
from DIRAC.Core.Base import Script
from DIRAC import S_OK
class CLIParams(object):
    def __init__(self):
        self.designid = 0
        self._input = ""
        self._sampling = 5

    def setDesignID(self, opt):
        self.designid = int(opt)
        return S_OK()

    def setInput(self, opt):
        self._input = opt
        return S_OK()
    
    def setSampling(self, opt):
        self._sampling = int(opt)
        return S_OK()
    
    def registerSwitches(self):
        Script.registerSwitch("", "design=", "The designID", self.setDesignID)
        Script.registerSwitch("s:", "sampling=", "Number of samples", self.setSampling)
        Script.registerSwitch("i:", "input=", "Input XML", self.setInput)
        Script.setUsageMessage("%s --design=120 -i file.xml -s 5" % Script.scriptName)
        
        
def autoalign():
    return 45

if __name__  == "__main__":
    clip = CLIParams()
    clip.registerSwitches()
    
    Script.parseCommandLine()
    
    
    from simudb.main.main import Design
    from sewlabwrapper.sewlab.main import Sewlab as Sewlab_run
    from DIRAC import gLogger, exit as dexit
    from ALDIRAC.Core.Utilities.SewlabUtils import IVLorentianMesh

    if not clip.designid:
        gLogger.error("Missing design ID")
        dexit(1)
    if not clip._input:
        gLogger.error("Missing input file")
        dexit(1)
    
    input_file = clip._input
    if not os.path.exists(input_file):
        gLogger.error("Cannot find input file", input_file)
        dexit(1)
    
    
    #get the sequence
    design = Design()
    design.set_design(clip.designid)
    design_xml = design.get_design_xml()
    seq = design_xml.find("SewlabSequence")
    
    #Add the sequence to the input file
    t = ElementTree()
    t.parse(input_file)
    root = t.getroot()
    root.append(seq)
    
    #write new input file
    tmpdir = tempfile.mkdtemp()
    tmpfile = os.path.join(tmpdir, "localinputxml.xml")
    t.write(tmpfile)
    
    #Get the alignment field
    sewlab_r = Sewlab_run(tmpfile)
    sewlab_r.run_alignement_field()
    returned_status = sewlab_r.run()
    if returned_status:
        gLogger.error("Sewlab alignment failed:", returned_status)
        dexit(1)
    alignment_dict = sewlab_r.get_alignement_info()
    if not alignment_dict:
        gLogger.error("Alignment dict is empty, cannot proceed:", str(alignment_dict))
        dexit(1)

    #Get the mesh
    mesh = IVLorentianMesh(alignment_dict["electricField"], clip._sampling).electricFields
    mesh = [-x for x in mesh]#because the result of mesh is a list of positive numbers
    
    from ALDIRAC.Interfaces.API.Applications import Sewlab
    from ALDIRAC.Interfaces.API.Dirac import Dirac
    from ALDIRAC.Interfaces.API.UserJob import UserJob

    d = Dirac(True, "repo_design_%s.rep" % clip.designid)
    j = UserJob()
    j.setName("Test")
    j.setJobGroup("test")
    j.setCPUTime(1000)
    j.setOutputSandbox(["*.log", "*.pkl"])
    j.setGenericParametricInput(mesh)
    s = Sewlab()
    s.setSteeringFile(tmpfile)
    s.setParametricVariationOn("efield")
    s.setOutputFile("temp.dat")
    #s.setAlteredParameters("efield = -50")

    res = j.append(s)
    if not res["OK"]:
        gLogger.error(res["Message"])
        dexit(1)
    
    sewlab_post = SewlabPostProcess()
    sewlab_post.getInputFromApp(s)
    sewlab_post.setOutputFile("design_%s.pkl" % (clip.designid))
    res = j.append(sewlab_post)
    if not res["OK"]:
        gLogger.error(res["Message"])
        dexit(1)
    j.setLogLevel("VERBOSE")
    res = j.submit(d)
    
    if not res['OK']:
        gLogger.error(res["Message"])
        dexit(1)
    else:
        gLogger.notice("JobIDs:", res['Value'])
        dexit()
