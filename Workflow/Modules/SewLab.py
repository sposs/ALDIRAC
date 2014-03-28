'''
Created on Feb 6, 2014

@author: stephanep
'''
from ALDIRAC.Workflow.Modules.ModuleBase import ModuleBase
from DIRAC import S_OK, S_ERROR, gLogger
from DIRAC.Core.Utilities.Subprocess                      import shellCall
import os

from xml.etree import ElementTree
from xml.etree.ElementTree import SubElement
from ALDIRAC.SimuDBSystem.Client.SimuDBClient import SimuDBClient
from sewlabwrapper.utils.sewlabparams_parser import sewlab_xml_parser

class SewLab(ModuleBase):
    def __init__(self):
        super(SewLab, self).__init__()
        self.scriptfile = ""
        self.samplefile = ""
        self.log = gLogger.getSubLogger("SewLab")
        self.InputFile = []
        self.SteeringFile = ''
        self.sequence = ""
        self.sequencetype = ""
        self.parameterchanges = {}
        self.alteredparams = ""
        self.parametricvar = ""
        self.simudb = SimuDBClient()
        
    def applicationSpecificInputs(self):
        """ Resolve the application specific inputs
        """
        if not self.OutputFile:
            self.OutputFile = "solution_%s.dat" % self.jobID
        self.parameterchanges["outputfile"] = self.OutputFile
        if self.alteredparams:
            params = self.alteredparams.rstrip(";").split(";")
            for param in params:
                key, value  = param.split("=")
                self.parameterchanges[key.strip()] = value.strip()
        if self.parametricvar:
            self.parameterchanges[self.parametricvar] = self.parametricParameters


        if not self.SteeringFile:
            if self.InputFile:
                self.SteeringFile  = os.path.basename(self.InputFile[0])
        return S_OK()
    
    def runIt(self):
        """ Now do something
        """

        self.result = S_OK()
        if not self.applicationLog:
            self.result = S_ERROR( 'No Log file provided' )
        if not self.result['OK']:
            self.log.error("Failed to resolve input parameters:", self.result["Message"])
            return self.result

        if not self.workflowStatus['OK'] or not self.stepStatus['OK']:
            self.log.verbose('Workflow status = %s, step status = %s' % (self.workflowStatus['OK'], self.stepStatus['OK']))
            return S_OK('%s should not proceed as previous step did not end properly' % self.applicationName)        

        self.SteeringFile = os.path.basename(self.SteeringFile)

        res = self._altersample()
        if not res['OK']:
            self.log.error("Failed to change the file")
            self.setApplicationStatus("Failed to change the file", True)
            return res
        
        res = self._path()
        if not res["OK"]:
            self.log.error("Failed to locate the sewlab executable")
            self.setApplicationStatus("Failed finding sewlab", True)
            return res 
        sewlab_path, fin_path = res['Value']
       
        extra_opts = "-o /Setup=Prod -o /Prod/SewlabPath=%s" % fin_path
        scriptName = '%s_%s_Run_%s.sh' % (self.applicationName, self.applicationVersion, self.STEP_NUMBER)
        with open(scriptName, "w") as script:
            script.write("#!/bin/bash\n")
            script.write("declare -x LD_LIBRARY_PATH=/lib/x86_64-linux-gnu/:$LD_LIBRARY_PATH\n")
            script.write("%s -i %s %s\n" % (sewlab_path, self.SteeringFile, extra_opts))
            script.write("exit $?\n")
        os.chmod(scriptName, 0755)
        
        comm = 'sh -c "./%s"' % (scriptName)
        self.setApplicationStatus('%s %s step %s' % (self.applicationName, self.applicationVersion, self.STEP_NUMBER))
        res = self.simudb.set_status(self.jobName, "running")
        if not res['OK']:
            self.log.error("Failed to set status to running:", res["Message"])
            res = self.simudb.set_status(self.jobName, "running")
            if not res['OK']:
                self.log.error("Failed again to set status to running:", res["Message"])
                self.log.error("Will fail the task")
                return S_ERROR("Issues with task state machine")
        self.stdError = ''
        result = shellCall(0, comm, callbackFunction = self.redirectLogOutput, bufferLimit = 20971520)
        if not result['OK']:
            self.log.error("Application failed :", result["Message"])
            res = self.simudb.set_status(self.jobName, "failed", "Error while executing sewlab")
            if not res["OK"]:
                self.log.error("Failed to set task to failed:", res["Message"])
            return S_ERROR('Problem Executing Application')

        resultTuple = result['Value']
        
        status = resultTuple[0]
        # stdOutput = resultTuple[1]
        # stdError = resultTuple[2]
        self.log.info( "Status after %s execution is %s" %(os.path.basename(scriptName), str(status)) )
        failed = False
        if status != 0:
            self.log.info( "%s execution completed with non-zero status:" % os.path.basename(scriptName) )
            res = self.simudb.set_status(self.jobName, "failed", "Sewlab exited with status %s" % status)
            if not res["OK"]:
                self.log.error("Failed to set task to failed:", res["Message"])
            failed = True
        elif len(self.stdError) > 0:
            self.log.info( "%s execution completed with application warning:" % os.path.basename(scriptName) )
            self.log.info(self.stdError)
        elif not os.path.exists(self.OutputFile):
            self.log.error("Missing output file")
            res = self.simudb.set_status(self.jobName, "failed", "Missing output after sewlab execution")
            if not res["OK"]:
                self.log.error("Failed to set task to failed:", res["Message"])
            status = 2
            failed = True
        else:
            self.log.info( "%s execution completed successfully:" % os.path.basename(scriptName) )
        
        if failed == True:
            self.log.error( "==================================\n StdError:\n" )
            self.log.error( self.stdError )
            return S_ERROR('%s Exited With Status %s' % (os.path.basename(scriptName), status))
        
        #Above can't be removed as it is the last notification for user jobs
        self.setApplicationStatus('%s (%s %s) Successful' %(os.path.basename(scriptName), 
                                                            self.applicationName, self.applicationVersion))
        return S_OK('%s (%s %s) Successful' % (os.path.basename(scriptName), 
                                               self.applicationName, self.applicationVersion))

    
    def _altersample(self):
        """ Create the Sample file
        """
        if self.SteeringFile:
            if not os.path.exists(self.SteeringFile):
                self.log.error("Missing input file")
                return S_ERROR("Missing input file")
            try:
                pp = sewlab_xml_parser(self.SteeringFile)
                xml_repr = pp.dumpxml()
                if self.parameterchanges:
                    for param, value in self.parameterchanges.items():
                        if pp.set_param(param, value):
                            del self.parameterchanges[param]
                    xml_repr = pp.dumpxml()
                tree = ElementTree.parse(self.SteeringFile)
                seq = tree.getroot().find("SewLabSequence")
                seq = self.alter_xml(seq, self.parameterchanges)
                xml_repr.append(seq)
                script = SubElement(xml_repr, "SewLabScript")
                script_elems = tree.getroot().findall("SewLabScript/SewLabScriptParam")
                for elem in script_elems:
                    altered_elem = self.alter_xml(elem, self.parameterchanges)
                    script.append(altered_elem)
                for param, value in self.parameterchanges.items(): #all remaining elements are added as script parameters
                    SubElement(script, "SewLabScriptParam", {"name": param, "value": value, 
                                                             "type": type(value).__name__})
                final_tree = ElementTree.ElementTree(xml_repr)
                final_tree.write(self.SteeringFile)
            except Exception as error:
                self.log.error("Failed to parse the XML file:", str(error))
                return S_ERROR("Failed to parse the XML file")
        
        return S_OK()
    
    def _path(self):
        """ Try to locate sewlab_mono
        """
        bin_name = self.ops.getValue("SewLab/ALBinName", "al_sewlabwrapper")
        path = self.ops.getValue("SewLab/EC2realPath", "/home/ec2-user/")
        real_bin_name = self.ops.getValue("SewLab/BinName", "sewlab_mono")
        real_bin_path = self.ops.getValue("SewLab/EC2Path", "/home/ec2-user/")
        real_path = os.path.join(real_bin_path, real_bin_name)
        if not os.path.exists(real_path):
            self.log.error("Couldn't find the sewlab binary:", real_path)
            return S_ERROR("Missing sewlab binary")
        
        f_path = os.path.join(path,bin_name)
        if os.path.exists(f_path) and os.path.exists(real_path):
            return S_OK((f_path, real_path))
        
        shared_area = self.ops.getValue("SharedArea", "/common/exe")
        f_path = os.path.join(shared_area, bin_name)
        if os.path.exists(f_path) and os.path.exists(real_path):
            return S_OK((f_path, real_path))
        
        return S_ERROR("Failed to find sewlab binary")
    
    def alter_xml(self, input_element, params_dict):
        """ Change values
        """
        for param, value in params_dict.items():
            if input_element.get("name", None) == param:
                ptype = input_element.get("type", None)
                if ptype:
                    value = eval("%s(%s)" % (ptype, value))
                input_element.attrib["value"] = value
                del params_dict[param]
        return input_element

    