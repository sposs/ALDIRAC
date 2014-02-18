'''
Created on Feb 6, 2014

@author: stephanep
'''
from ALDIRAC.Workflow.Modules.ModuleBase import ModuleBase
from DIRAC import S_OK, S_ERROR, gLogger
from DIRAC.Core.Utilities.Subprocess                      import shellCall
from ALDIRAC.Core.Utilities.SewlabparamsParser import sewlab_xml_parser
import os
import shutil


class SewLab(ModuleBase):
    def __init__(self):
        super(SewLab, self).__init__()
        ModuleBase.__init__(self)
        self.efield = 0.0
        self.options = ""
        self.scriptfile = ""
        self.samplefile = ""
        self.log = gLogger.getSubLogger("SewLab")
        self.InputFile = []
        self.SteeringFile = ''
        self.sequence = ""
        self.sequencetype = ""
        self.parameterchanges = {}
        self.alteredparams = ""
        self.xray = 1.0
        self.parametricvar = ""
        self.varyefield = False
        
    def applicationSpecificInputs(self):
        """ Resolve the application specific inputs
        """
        if not self.OutputFile:
            self.OutputFile = "solution_%s.slo" % self.jobID
        if not self.Efield and not self.varyefield:
            return S_ERROR("Missing E field")
        if self.varyefield:
            self.Efield = self.parametricParameters
        if self.options:
            self.options = self.options.replace(";", " ")
        if self.sequence:
            if self.sequence.count(";"):
                self.sequence = self.sequence.split(";")
                self.sequencetype = "list"
            else:
                self.sequence = os.path.basename(self.sequence)
                self.sequencetype = "file"
                
        if self.alteredparams:
            params = self.alteredparams.rstrip(";").split(";")
            for param in params:
                key, value  = param.split("=")
                self.parameterchanges[key.strip()] = value.strip()
        if self.parametricvar:
            self.parameterchanges[self.parametricvar] = self.parametricParameters
            
        if self.samplefile:
            self.samplefile = os.path.basename(self.samplefile)

        return S_OK()
    
    def applicationSpecificMoveBefore(self):
        """ Copy the sample file
        """
        if not self.samplefile:
            return S_OK()
        
        if self.samplefile:
            if os.path.join(self.basedirectory, self.samplefile):
                try:
                    shutil.copy(os.path.join(self.basedirectory, self.samplefile), 
                                os.path.join (".", self.samplefile))
                except OSError:
                    return S_ERROR("Couldn't copy the sample file %s" % self.samplefile)
        else:
            return S_ERROR("Missing sample file")
        
        if self.sequencetype == "file":
            if os.path.exists(os.path.join(self.basedirectory, self.sequence)):
                try:
                    shutil.copy(os.path.join(self.basedirectory, self.sequence), 
                                os.path.join(".", self.sequence))
                except OSError:
                    return S_ERROR("Failed copying the sequence file")
            else:
                return S_ERROR("Couldn't find the sequence file %s" % self.sequence)
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

        self.log.info("The Sewlab parameter is %s" % self.parameter)
        

        res = self._makeSample()
        if not res['OK']:
            self.log.error("Failed to create the sample file")
            self.setApplicationStatus("Failed to create the sample file", True)
            return res
        res = self._makeScript()
        if not res["OK"]:
            self.log.error("Failed to create the script")
            self.setApplicationStatus("Failed creating the script", True)
            return res
        
        res = self._path()
        if not res["OK"]:
            self.log.error("Failed to locate the sewlab executable")
            self.setApplicationStatus("Failed finding sewlab", True)
            return res 
        sewlab_path = res['Value']
        
        scriptName = '%s_%s_Run_%s.sh' % (self.applicationName, self.applicationVersion, self.STEP_NUMBER)
        with open(scriptName, "w") as script:
            script.write("#!/bin/bash\n")
            script.write("%s exec.script\n" % sewlab_path)
            script.write("exit $?\n")
        os.chmod(scriptName, 0755)
        
        comm = 'sh -c "./%s"' % (scriptName)
        self.setApplicationStatus('%s %s step %s' % (self.applicationName, self.applicationVersion, self.STEP_NUMBER))
        self.stdError = ''
        result = shellCall(0, comm, callbackFunction = self.redirectLogOutput, bufferLimit = 20971520)
        if not result['OK']:
            self.log.error("Application failed :", result["Message"])
            return S_ERROR('Problem Executing Application')

        resultTuple = result['Value']
        
        status = resultTuple[0]
        # stdOutput = resultTuple[1]
        # stdError = resultTuple[2]
        self.log.info( "Status after %s execution is %s" %(os.path.basename(scriptName), str(status)) )
        failed = False
        if status != 0:
            self.log.info( "%s execution completed with non-zero status:" % os.path.basename(scriptName) )
            failed = True
        elif len(self.stdError) > 0:
            self.log.info( "%s execution completed with application warning:" % os.path.basename(scriptName) )
            self.log.info(self.stdError)
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

    
    def _makeSample(self):
        """ Create the Sample file
        """
        if self.SteeringFile:
            if not os.path.exists(self.SteeringFile):
                self.log.error("Missing sample file")
            try:
                pp = sewlab_xml_parser(self.SteeringFile)
                if self.parameterchanges:
                    for param, value in self.parameterchanges:
                        pp.set_param(param, value)
                pp.render_cfg("local.sample")
            except:
                self.log.error("Failed to parse the XML sample file")
                return S_ERROR("Failed to parse the XML file")
        else:
            with open("local.sample", 'w') as sample:
                sample.write("")
        if self.sequencetype == "list":
            with open("local.sample", "a") as seq:
                seq.write("sequence {\n")
                seq.write('  label = "diracsequence";\n')
                seq.write("  xray = %s;\n" % self.xray)
                for item in self.sequence:
                    seq.write("  layer { %s }\n" % item)
                    seq.write("}\n")
        
        return S_OK()
    
    def _makeScript(self):
        """ Make the execution script
        """
        with open("exec.script", "w") as script:
            script.write("""mqw = (Load Sequence From "local.sample" At "diracsequence");
params = (Load Tree From "local.sample");

// Variables
efield = %(efield);

// Potential And Self Basis
pot = (Buildpot mqw Using params);
bpot = (Bias pot To efield);

sol = (Selftransport bpot Using params %(options));

Save sol "%(outputfile)s" 
""" % {"efield": self.efield, "options": self.options, "outputfile": self.OutputFile})
        return S_OK()
    
    def _path(self):
        """ Try to locate sewlab_mono
        """
        bin_name = self.ops.getValue("SewLab/BinName", "sewlab_mono")
        path = self.ops.getValue("SewLab/EC2Path", "/home/ec2-user/")
        f_path = os.path.join(path,bin_name)
        if os.path.exists(f_path):
            return S_OK(f_path)
        shared_area = self.ops.getValue("SharedArea", "/common/exe")
        f_path = os.path.join(shared_area, bin_name)
        if os.path.exists(f_path):
            return S_OK(f_path)
        
        return S_ERROR("Failed to find sewlab binary")
    