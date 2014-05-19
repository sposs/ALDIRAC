'''
Created on Feb 6, 2014

@author: stephanep
'''
from ALDIRAC.Interfaces.API.Application import Application
from DIRAC.Core.Workflow.Parameter                    import Parameter
from DIRAC.ConfigurationSystem.Client.Helpers.Operations import Operations
from DIRAC import S_OK, S_ERROR
import types
import os

class GenericApplication(Application):
    """ Run a script (python or shell) in an application environment.

    Example:

    >>> ga = GenericApplication()
    >>> ga.setScript("myscript.py")
    >>> ga.setArguments("some command line arguments")
    >>> ga.setDependency({"root":"5.26"})

    In case you also use the setExtraCLIArguments method, whatever you put
    in there will be added at the end of the CLI, i.e. after the Arguments
    """
    def __init__(self, paramdict=None):
        self.Script = None
        self.Arguments = ''
        self.dependencies = {}
        ### The Application init has to come last as if not the passed
        ### parameters are overwritten by the defaults.
        super(GenericApplication, self).__init__(paramdict)
        #Those have to come last as the defaults from Application are not right
        self._modulename = "ApplicationScript"
        self.appname = self._modulename
        self._moduledescription = 'An Application script module that can \
execute any provided script in the given project name and version environment'

    def setScript(self, script):
        """ Define script to use

        @param script: Script to run on. Can be shell or python.
        Can be local file or LFN.
        @type script: string
        """
        self._checkArgs({
            'script': types.StringTypes
          })
        if os.path.exists(script) or script.lower().count("lfn:"):
            self.inputSB.append(script)
        self.Script = script
        return S_OK()

    def setArguments(self, args):
        """ Optional: Define the arguments of the script

        @param args: Arguments to pass to the command line call
        @type args: string

        """
        self._checkArgs({
            'args': types.StringTypes
          })
        self.Arguments = args
        return S_OK()

    def setDependency(self, appdict):
        """ Define list of application you need

        >>> app.setDependency({"mokka":"v0706P08","marlin":"v0111Prod"})

        @param appdict: Dictionary of application to use: {"App":"version"}
        @type appdict: dict

        """
        #check that dict has proper structure
        self._checkArgs({
            'appdict': types.DictType
          })

        self.dependencies.update(appdict)
        return S_OK()

    def _applicationModule(self):
        m1 = self._createModuleDefinition()
        m1.addParameter(Parameter("script",      "", "string", "", "", False,
                                  False, "Script to execute"))
        m1.addParameter(Parameter("arguments",   "", "string", "", "", False,
                                  False, "Arguments to pass to the script"))
        m1.addParameter(Parameter("debug",    False,   "bool", "", "", False,
                                  False, "debug mode"))
        return m1

    def _applicationModuleValues(self, moduleinstance):
        moduleinstance.setValue("script",    self.Script)
        moduleinstance.setValue('arguments', self.Arguments)
        moduleinstance.setValue('debug',     self.Debug)

    def _userjobmodules(self, stepdefinition):
        res1 = self._setApplicationModuleAndParameters(stepdefinition)
        res2 = self._setUserJobFinalization(stepdefinition)
        if not res1["OK"] or not res2["OK"]:
            return S_ERROR('userjobmodules failed')
        return S_OK()

    def _prodjobmodules(self, stepdefinition):
        res1 = self._setApplicationModuleAndParameters(stepdefinition)
        res2 = self._setOutputComputeDataList(stepdefinition)
        if not res1["OK"] or not res2["OK"]:
            return S_ERROR('prodjobmodules failed')
        return S_OK()

    def _addParametersToStep(self, stepdefinition):
        res = self._addBaseParameters(stepdefinition)
        if not res["OK"]:
            return S_ERROR("Failed to set base parameters")
        return S_OK()

    def _setStepParametersValues(self, instance):
        self._setBaseStepParametersValues(instance)
        for depn, depv in self.dependencies.items():
            self._job._addSoftware(depn, depv)
        return S_OK()

    def _checkConsistency(self):
        """ Checks that script and dependencies are set.
        """
        if not self.Script:
            return S_ERROR("Script not defined")
        elif not self.Script.lower().count("lfn:") and \
        not os.path.exists(self.Script):
            return S_ERROR("Specified script is not an LFN and was not found \
on disk")

        #if not len(self.dependencies):
        #  return S_ERROR("Dependencies not set: No application to install. \
#If correct you should use job.setExecutable")
        return S_OK()

#######################################################################
### Below is the really relevant stuff
######################################
class Sewlab(Application):
    '''
    classdocs
    '''
    def __init__(self, params=None):
        '''
        Constructor
        '''
        self.AlteredParameters = ""
        self.ParametricVariationOn = ""
        super(Sewlab, self).__init__(params)
        self._modulename = "SewLab"
        self.appname = "sewlab"
        self._moduledescription = 'The sewlab wrapper'
        self.ops = Operations()

    def setAlteredParameters(self, params):
        """ Alter some simulation parameters
        
        >>> sewlab.setAlteredParameter(["transport.hlo-temperature = 300.0", \
            "transport.number-of-kT-before-cut-off=7"])
            
        """
        if not type(params) == types.ListType:
            params  = [params]
        self.AlteredParameters = ";".join(params)

    def setParametricVariationOn(self, param):
        """ Say on what parameter the parametric job applies
        
        Example:
        
        >>> job.setGenericParametricInput([250, 260, 270, 280, 290, 300])
        >>> sewlab.setParametricVariationOn("transport.hlo-temperature")
        
        will create 6 jobs, where the parameter transport.hlo-temperature will be varied
        """
        self._checkArgs({'param': types.StringType})
        self.ParametricVariationOn = param
        
        
    def _applicationModule(self):
        m1 = self._createModuleDefinition()
        m1.addParameter(Parameter("alteredparams", "", "string", "", "", False,
                                  False, "sequence"))
        m1.addParameter(Parameter("parametricvar", "", "string", "", "", False,
                                  False, "Parameter concerned by the parametric job"))
        
        return m1

    def _applicationModuleValues(self, moduleinstance):
        moduleinstance.setValue("alteredparams", self.AlteredParameters)
        moduleinstance.setValue("parametricvar", self.ParametricVariationOn)

    def _userjobmodules(self, stepdefinition):
        res1 = self._setApplicationModuleAndParameters(stepdefinition)
        res2 = self._setUserJobFinalization(stepdefinition)
        if not res1["OK"] or not res2["OK"]:
            return S_ERROR('userjobmodules failed')
        return S_OK()

    def _addParametersToStep(self, stepdefinition):
        res = self._addBaseParameters(stepdefinition)
        if not res["OK"]:
            return S_ERROR("Failed to set base parameters")
        return S_OK()

    def _setStepParametersValues(self, instance):
        """ Nothing to do here
        """
        self._setBaseStepParametersValues(instance)
        #for depn, depv in self.dependencies.items():
        #    self._job._addSoftware(depn, depv)
        return S_OK()

    def _checkConsistency(self):
        """ Checks that script and dependencies are set.
        """
        if not self.SteeringFile:
            return S_ERROR("Missing what Sewlab should do")
        
        if not self.Version:
            vers = self.ops.getValue("SewLab/Version", "")
            self.Version = vers
        return S_OK()


######################################################
class SewlabPostProcess(Application):
    """ Post process the sewlab results
    """
    def __init__(self, params=None):
        
        super(SewlabPostProcess, self).__init__(params)
        self._modulename = "SewlabPostProcess"
        self.appname = "SewlabPostProcess"
        self._moduledescription = 'The sewlab post processor'
        
    def _userjobmodules(self, stepdefinition):
        res1 = self._setApplicationModuleAndParameters(stepdefinition)
        res2 = self._setUserJobFinalization(stepdefinition)
        if not res1["OK"] or not res2["OK"]:
            return S_ERROR('userjobmodules failed')
        return S_OK()

    def _applicationModule(self):
        m1 = self._createModuleDefinition()
        return m1
    
    def _addParametersToStep(self, stepdefinition):
        res = self._addBaseParameters(stepdefinition)
        if not res["OK"]:
            return S_ERROR("Failed to set base parameters")
        return S_OK()

    def _setStepParametersValues(self, instance):
        """ Nothing to do here
        """
        self._setBaseStepParametersValues(instance)
        return S_OK()

    def _checkConsistency(self):
        """ Checks
        """
        return S_OK()
    
    def _checkWorkflowConsistency(self):
        return self._checkRequiredApp()

    def _resolveLinkedStepParameters(self, stepinstance):
        if type(self._linkedidx) == types.IntType:
            self._inputappstep = self._jobsteps[self._linkedidx]
        if self._inputappstep:
            stepinstance.setLink("InputFile", self._inputappstep.getType(), "OutputFile")
        return S_OK() 

class RegisterOutput(Application):
    """ Take the input file, and send it straight to the SimuDB
    """
    def __init__(self, params=None):
        super(RegisterOutput, self).__init__(params)
        self._modulename = "RegisterOutput"
        self.appname = self._modulename
        self._moduledescription = 'Register the output into the SimuDB'
        
    def _userjobmodules(self, stepdefinition):
        res1 = self._setApplicationModuleAndParameters(stepdefinition)
        res2 = self._setUserJobFinalization(stepdefinition)
        if not res1["OK"] or not res2["OK"]:
            return S_ERROR('userjobmodules failed')
        return S_OK()

    def _applicationModule(self):
        m1 = self._createModuleDefinition()
        return m1
    
    def _addParametersToStep(self, stepdefinition):
        res = self._addBaseParameters(stepdefinition)
        if not res["OK"]:
            return S_ERROR("Failed to set base parameters")
        return S_OK()

    def _setStepParametersValues(self, instance):
        """ Nothing to do here
        """
        self._setBaseStepParametersValues(instance)
        return S_OK()
        
    def _checkWorkflowConsistency(self):
        return self._checkRequiredApp()

    def _resolveLinkedStepParameters(self, stepinstance):
        if type(self._linkedidx) == types.IntType:
            self._inputappstep = self._jobsteps[self._linkedidx]
        if self._inputappstep:
            stepinstance.setLink("InputFile", self._inputappstep.getType(), "OutputFile")
        return S_OK() 

class AnalyseRun(Application):
    """ Analysis class, used to store relevant parameters (for qcl_datamining for example)
    """
    def __init__(self, params=None):
        self.Store = False
        super(AnalyseRun, self).__init__(params)
        self._modulename = "Analysis"
        self.appname = self._modulename
        self._moduledescription = 'Run some analysis on the output file'
        
    def setStore(self, Store=True):
        """ Send those results to the DB directly
        """
        self.Store = Store

    def _userjobmodules(self, stepdefinition):
        res1 = self._setApplicationModuleAndParameters(stepdefinition)
        res2 = self._setUserJobFinalization(stepdefinition)
        if not res1["OK"] or not res2["OK"]:
            return S_ERROR('userjobmodules failed')
        return S_OK()

    def _applicationModule(self):
        m1 = self._createModuleDefinition()
        m1.addParameter(Parameter("store_output", "", "string", "", "", False,
                                  False, "Store the output to the DB"))
        return m1

    def _applicationModuleValues(self, moduleinstance):
        moduleinstance.setValue("store_output", self.Store)
    
    def _addParametersToStep(self, stepdefinition):
        res = self._addBaseParameters(stepdefinition)
        if not res["OK"]:
            return S_ERROR("Failed to set base parameters")
        return S_OK()

    def _setStepParametersValues(self, instance):
        """ Nothing to do here
        """
        self._setBaseStepParametersValues(instance)
        return S_OK()

    def _checkConsistency(self):
        """ Checks
        """
        return S_OK()
    
    def _checkWorkflowConsistency(self):
        return self._checkRequiredApp()

    def _resolveLinkedStepParameters(self, stepinstance):
        if type(self._linkedidx) == types.IntType:
            self._inputappstep = self._jobsteps[self._linkedidx]
        if self._inputappstep:
            stepinstance.setLink("InputFile", self._inputappstep.getType(), "OutputFile")
        return S_OK() 

    

######################################################################################################
from DIRAC import gLogger
def get_app_list(app_dict):
    """ Given a generic application name, return a list of applications to be added
    Format is app['name'] = version
    """
    app_list = []
    for name, version in app_dict.items():
        if name.lower() == "sewlab":
            app1 = Sewlab()
            app1.setVersion(version)
            app1.setOutputFile("default.slo")
            app_list.append(app1)
            app2 = SewlabPostProcess()
            app2.getInputFromApp(app1)
            app2.setOutputFile("data.pkl")
            app_list.append(app2)
            appAna = AnalyseRun()
            appAna.getInputFromApp(app2)
            app3 = RegisterOutput()
            app3.getInputFromApp(app2)
            app_list.append(app3)
        else:
            gLogger.error("Invalid application name")
            return S_ERROR("Bad application name")

    return S_OK(app_list)

