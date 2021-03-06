# #######################################################################
# $HeadURL:  $
########################################################################
'''
Base application class. All applications inherit this class.

@author: Stephane Poss

'''
from DIRAC.Core.Workflow.Module import ModuleDefinition
from DIRAC.Core.Workflow.Parameter import Parameter

from DIRAC import S_OK, S_ERROR, gLogger
import inspect, sys, types, os, urllib


__RCSID__ = "$Id: $"


class Application(object):
    """ General application definition. Any new application should inherit from this class.
    """
    #need to define slots
    ## __slots__ = []
    def __init__(self, paramdict=None):
        """ Can define the full application by passing a dictionary in the constructor.
        
        >>> app = Application({"Name":"marlin","Version":"v0111Prod",
        ...                    "SteeringFile":"My_file.xml","NbEvts":1000})
        
        @param paramdict: Dictionary of parameters that can be set. Will throw an exception if one of them does not exist.
        @type paramdict: dict
        
        """
        super(Application, self).__init__()
        #application nane (executable)
        self.appname = ""
        #application version
        self.Version = ""
        #Steering file (duh!)
        self.SteeringFile = ""
        #Input sandbox: steering file automatically added to SB
        self.inputSB = []
        #Input file
        self.InputFile = ""
        #Output file
        self.OutputFile = ""
        self.OutputPath = ""
        self.OutputSE = ''
        self._listofoutput = []
        #Log file
        self.LogFile = ""

        #Detector type (ILD or SID)
        self.detectortype = ""
        #Data type : gen, SIM, REC, DST
        self.datatype = ""

        #Extra command line arguments
        self.ExtraCLIArguments = ""

        ##Needed for Generation+Stdhepcut
        self.willBeCut = False

        ##Debug mode
        self.Debug = False

        #Prod Parameters: things that appear on the prod details
        self.prodparameters = {}
        self.accountInProduction = True
        #Module name and description: Not to be set by the users, internal call only, used to get the Module objects
        self._modulename = ''
        self._moduledescription = ''
        self._importLocation = "ALDIRAC.Workflow.Modules"

        #System Configuration: comes from Job definition
        self._systemconfig = ''

        #Internal member: hold the list of the job's application set before self: used when using getInputFromApp
        self._job = None
        self._jobapps = []
        self._jobsteps = []
        self._jobtype = ''
        #input application: will link the OutputFile of the guys in there with the InputFile of the self 
        self._inputapp = []
        self._linkedidx = None
        #Needed to link the parameters.
        self._inputappstep = None

        #flag set to true in Job.append
        self.addedtojob = False
        ####Following are needed for error report
        self._log = gLogger.getSubLogger(self.__class__.__name__)
        self._errorDict = {}

        #This is used to filter out the members that should not be set when using a dict as input
        self._paramsToExclude = ['_paramsToExclude', "_log", "_errorDict", "addedtojob",
                                 "_inputappstep", "_linkedidx", "_inputapp", "_jobtype",
                                 "_jobsteps", "_jobapps", "_job", "_systemconfig", "_importLocation",
                                 "_moduledescription", "_modulename", "prodparameters",
                                 "datatype", "detectortype", "_listofoutput", "inputSB",
                                 "appname", 'accountInProduction', 'OutputPath']

        ### Next is to use the setattr method.
        self._setparams(paramdict)

    def __repr__(self):
        classstr = "%s" % self.appname
        if self.Version:
            classstr += " %s" % self.Version
        return classstr

    def _setparams(self, params):
        """ Call the setter that was passed in the input dictionary. NASTY!!
        """
        if not params:
            return S_OK()
        for param, value in params.items():
            if type(value) in types.StringTypes:
                value = "'%s'" % value
            try:
                exec "self.set%s(%s)" % (param, str(value))
            except:
                self._log.error("The %s class does not have a set%s method." % (self.__class__.__name__, param))
        return S_OK()

    def _getParamsDict(self):
        """ Return dictionary that can be used to build a new application based on the current
        """
        curdict = self.__dict__
        pdict = {}
        for key, val in curdict.items():
            if not key in self._paramsToExclude:
                if val:
                    pdict[key] = val
        return S_OK(pdict)

    def setName(self, name):
        """ Define name of application
        
        @param name: Name of the application. Normally, every application defines its own, so no need to call that one
        @type name: string 
        """
        self._checkArgs({'name': types.StringTypes})
        self.appname = name
        return S_OK()

    def setVersion(self, version):
        """ Define version to use
        
        @param version: Version of the application to use
        @type version: string
        """
        self._checkArgs({'version': types.StringTypes})
        self.Version = version
        return S_OK()

    def setSteeringFile(self, steeringfile):
        """ Set the steering file, and add it to sandbox
        
        @param steeringfile: Steering file to use. 
        @type steeringfile: string
        """
        self._checkArgs({'steeringfile': types.StringTypes})
        self.SteeringFile = steeringfile
        if os.path.exists(steeringfile) or steeringfile.lower().count("lfn:"):
            self.inputSB.append(steeringfile)
        else:
            self._log.error("Cannot find the steering file neither locally nor as a LFN.")
        return S_OK()

    def setLogFile(self, logfile):
        """ Define application log file
        
        @param logfile: Log file to use. Set by default if not set.
        @type logfile: string
        """
        self._checkArgs({'logfile': types.StringTypes})
        self.LogFile = logfile
        return S_OK()

    def setOutputFile(self, ofile, path=None):
        """ Set the output file
        
        @param ofile: Output file name. Will overwrite the default. This is necessary when linking applications (when using L{getInputFromApp})
        @type ofile: string
        @param path: Set the output path for the output file to go. Will not do anything in a UserJob. Use setOutputData of the job for that functionality.
        @type path: string
        """
        self._checkArgs({'ofile': types.StringTypes})

        self.OutputFile = ofile
        self.prodparameters[ofile] = {}
        if self.detectortype:
            self.prodparameters[ofile]['detectortype'] = self.detectortype
        if self.datatype:
            self.prodparameters[ofile]['datatype'] = self.datatype

        if path:
            self._checkArgs({'path': types.StringTypes})
            self.OutputPath = path

        return S_OK()

    def setOutputSE(self, se):
        """ Set the output storage element for all files produced by this application.
        
        @param se: Storage element name. Example CERN-SRM, IN2P3-SRM, RAL-SRM, IMPERIAL-SRM
        @type se: string
        
        """
        self._checkArgs({'se': types.StringTypes})
        self.OutputSE = se
        return S_OK()

    def setInputFile(self, inputfile):
        """ Set the input file to use
        
        @param inputfile: Input file (data, not steering) to pass to the application. Can be local file of LFN:
        @type inputfile: string or list
        """
        kwargs = {"inputfile": inputfile}
        if not type(inputfile) in types.StringTypes and not type(inputfile) == type([]):
            return self._reportError("InputFile must be string or list of strings", __name__, **kwargs)
        if not type(inputfile) == type([]):
            inputfile = [inputfile]
        for inf in inputfile:
            if os.path.exists(inf) or inf.lower().count("lfn:"):
                self.inputSB.append(inf)

        self.InputFile = ";".join(inputfile)

        return S_OK()

    def getInputFromApp(self, application):
        """ Called to link applications
        
        >>> first_app = MyApp()
        >>> second_app = MyOtherApp()
        >>> second_app.getInputFromApp(first_app)
        
        @param application: Application to link against.
        @type application: application
        """
        self._inputapp.append(application)
        return S_OK()

    def setDebug(self, debug=True):
        """ Set the application to debug mode
        
        >>> app = Application()
        >>> app.setDebug()
        
        @param debug: Set the application to debug mode. Default is True when called. If not, then it's false.
        @type debug: bool
        """
        self._checkArgs({"debug": types.BooleanType})
        self.Debug = debug
        return S_OK()

    def setExtraCLIArguments(self, arguments):
        """ Pass any CLI argument as a string to the application
        """
        self._checkArgs({"arguments": types.StringTypes})
        self.ExtraCLIArguments = arguments
        return S_OK()

    def listAttributes(self):
        """ Method to list attributes for users. Doesn't list any private or semi-private attributes
        """
        self._log.notice('Attribute list :')
        for key, val in self.__dict__.items():
            if key not in self._paramsToExclude:
                if not val:
                    val = "Not defined"
                self._log.notice("  %s: %s" % ( key, val))


    ########################################################################################
    #    More private methods: called by the applications of the jobs, but not by the users
    #    Please, do not touch when you don't know what you are doing.
    #                           / \  //\
    #            |\___/|      /   \//  \\
    #            /0  0  \__  /    //  | \ \    
    #           /     /  \/_/    //   |  \  \  
    #           @_^_@'/   \/_   //    |   \   \ 
    #           //_^_/     \/_ //     |    \    \
    #        ( //) |        \///      |     \     \
    #      ( / /) _|_ /   )  //       |      \     _\
    #    ( // /) '/,_ _ _/  ( ; -.    |    _ _\.-~        .-~~~^-.
    #  (( / / )) ,-{        _      `-.|.-~-.           .~         `.
    # (( // / ))  '/\      /                 ~-. _ .-~      .-~^-.  \
    # (( /// ))      `.   {            }                   /      \  \
    #  (( / ))     .----~-.\        \-'                 .~         \  `. \^-.
    #             ///.----..>        \             _ -~             `.  ^-`  ^-_
    #               ///-._ _ _ _ _ _ _}^ - - - - ~                     ~-- ,.-~
    #                                                                  /.-~
    ########################################################################################

    def _setApplicationModuleAndParameters(self, stepdefinition):
        """Create Application Module, add it to a Step and set values to Module. Called in every applications 
        """
        m1 = self._applicationModule()
        stepdefinition.addModule(m1)
        m1i = stepdefinition.createModuleInstance(m1.getType(), stepdefinition.getType())
        self._applicationModuleValues(m1i)
        return S_OK()

    def _setUserJobFinalization(self, stepdefinition):
        """ Create UserOutputDataModule and add it to Step. 
        Called after the private method setApplicationModuleAndParameters in some user job applications
        """
        m2 = self._getUserOutputDataModule()
        stepdefinition.addModule(m2)
        stepdefinition.createModuleInstance(m2.getType(), stepdefinition.getType())
        return S_OK()

    def _setOutputComputeDataList(self, stepdefinition):
        """ Create ComputeOutputDataListModule and add it to Step. 
        Called after the private method setApplicationModuleAndParameters in some production job applications
        """
        m2 = self._getComputeOutputDataListModule()
        stepdefinition.addModule(m2)
        stepdefinition.createModuleInstance(m2.getType(), stepdefinition.getType())
        return S_OK()

    def _createModuleDefinition(self):
        """ Create Module definition. As it's generic code, all apps will use this.
        """
        moduledefinition = ModuleDefinition(self._modulename)
        moduledefinition.setDescription(self._moduledescription)
        body = 'from %s.%s import %s\n' % (self._importLocation, self._modulename, self._modulename)
        moduledefinition.setBody(body)
        return moduledefinition

    def _getUserOutputDataModule(self):
        """ This is separated as not all applications require user specific output data (i.e. GetSRMFile and Overlay). 
        Only used in UserJobs.
        
        The UserJobFinalization only runs last. It's called every step, but is running only if last.
        """
        moduledefinition = ModuleDefinition('UserJobFinalization')
        moduledefinition.setDescription('Uploads user output data files with specific policies.')
        body = 'from %s.%s import %s\n' % (self._importLocation, 'UserJobFinalization', 'UserJobFinalization')
        moduledefinition.setBody(body)
        return moduledefinition

    def _getComputeOutputDataListModule(self):
        """ This is separated from the applications as this is used in production jobs only.
        """
        moduledefinition = ModuleDefinition("ComputeOutputDataList")
        moduledefinition.setDescription("Compute the output data list to be treated by the last finalization")
        body = 'from %s.%s import %s\n' % (self._importLocation, "ComputeOutputDataList", "ComputeOutputDataList" )
        moduledefinition.setBody(body)
        return moduledefinition

    def _applicationModule(self):
        """ Create the module for the application, and add the parameters to it. Overloaded by every application class.
        """
        return None

    def _applicationModuleValues(self, moduleinstance):
        """ Set the values for the modules parameters. Needs to be overloaded for each application.
        """
        pass

    def _userjobmodules(self, stepdefinition):
        """ Method used to return the needed module for UserJobs. It's different from the ProductionJobs 
        (userJobFinalization for instance)
        """
        self._log.error("This application does not implement the modules, you get an empty list")
        return S_ERROR('Not implemented')

    def _prodjobmodules(self, stepdefinition):
        """ Same as above, but the other way around.
        """
        self._log.error("This application does not implement the modules, you get an empty list")
        return S_ERROR('Not implemented')

    def _checkConsistency(self):
        """ Called from Job Class, overloaded by every class. Used to check that everything is fine, in particular 
        that all required parameters are defined.
        """
        return S_OK()

    def _checkFinalConsistency(self):
        """ Called from Job Class, overloaded by every class. Used to check that everything is fine, in particular that 
        all required parameters are defined.
        Some info are passed from the job to the applications: this is then used to check that it makes the app valid 
        """
        return S_OK()

    def _checkWorkflowConsistency(self):
        """ Called from Job Class, overloaded by every class. Used to check the workflow consistency: linking between 
        applications
        Should also call L{_checkRequiredApp} when needed.
        """
        return S_OK()

    def _checkRequiredApp(self):
        """ Called by L{_checkWorkflowConsistency} when relevant
        """
        if self._inputapp:
            for app in self._inputapp:
                if not app in self._jobapps:
                    return S_ERROR("job order not correct: If this app uses some input coming from an other app, the app in \
                    question must be passed to job.append() before.")
                else:
                    self._linkedidx = self._jobapps.index(app)

        return S_OK()

    def _addBaseParameters(self, stepdefinition):
        """ Add to step the default parameters: appname, version, steeringfile, (nbevts, Energy), LogFile, InputFile, 
        OutputFile, OutputPath
        """
        stepdefinition.addParameter(Parameter("applicationName", "", "string", "", "", False, False,
                                              "Application Name"))
        stepdefinition.addParameter(Parameter("applicationVersion", "", "string", "", "", False, False,
                                              "Application Version"))
        stepdefinition.addParameter(Parameter("SteeringFile", "", "string", "", "", False, False, "Steering File"))
        stepdefinition.addParameter(Parameter("applicationLog", "", "string", "", "", False, False, "Log File"))
        stepdefinition.addParameter(
            Parameter("ExtraCLIArguments", "", "string", "", "", False, False, "Extra CLI arguments"))
        stepdefinition.addParameter(Parameter("InputFile", "", "string", "", "", True, False, "Input File"))

        if len(self.OutputFile):
            stepdefinition.addParameter(Parameter("OutputFile", "", "string", "", "", False, False, "Output File"))

        stepdefinition.addParameter(Parameter("OutputPath", "", "string", "", "", True, False,
                                              "Output File path on the grid"))

        stepdefinition.addParameter(Parameter("OutputSE", "", "string", "", "", True, False,
                                              "Output File storage element"))
        stepdefinition.addParameter(Parameter('listoutput', [], "list", "", "", False, False,
                                              "list of output file name"))
        #Following should be workflow parameters
        #stepdefinition.addParameter(Parameter("NbOfEvents",         0,    "int", "", "", False, False, 
        #                                      "Number of events to process"))
        #stepdefinition.addParameter(Parameter("Energy",             0,    "int", "", "", False, False, "Energy"))

        return self._getSpecificAppParameters(stepdefinition)

    def _getSpecificAppParameters(self, stepdef):
        """ Add specific parameters, should be overloaded
        """
        return S_OK()

    def _setBaseStepParametersValues(self, stepinstance):
        """ Set the values for the basic step parameters
        """

        stepinstance.setValue("applicationName", self.appname)
        stepinstance.setValue("applicationVersion", self.Version)
        stepinstance.setValue("applicationLog", self.LogFile)
        stepinstance.setValue("SteeringFile", self.SteeringFile)
        if not self._inputapp:
            stepinstance.setValue("InputFile", self.InputFile)

        if len(self.OutputFile):
            stepinstance.setValue("OutputFile", self.OutputFile)

        stepinstance.setValue("OutputPath", self.OutputPath)
        stepinstance.setValue("OutputSE", self.OutputSE)
        stepinstance.setValue('listoutput', self._listofoutput)
        stepinstance.setValue('ExtraCLIArguments', urllib.quote(self.ExtraCLIArguments))
        return self._setSpecificAppParameters(stepinstance)

    def _setSpecificAppParameters(self, stepinstance):
        """ Set the value of the parameters. Should be overloaded
        """
        return S_OK()

    def _addParametersToStep(self, stepdefinition):
        """ Method to be overloaded by every application. Add the parameters to the given step. 
        Should call L{_addBaseParameters}.
        Called from Job
        """
        return self._addBaseParameters(stepdefinition)

    def _setStepParametersValues(self, stepinstance):
        """ Method to be overloaded by every application. For all parameters that are not to be linked, 
        set the values in the step instance
        Called from Job
        """
        return self._setBaseStepParametersValues(stepinstance)

    def _resolveLinkedStepParameters(self, stepinstance):
        """ Method to be overloaded by every application that resolve what are the linked parameters (e.g. 
        OuputFile and InputFile). 
        Called from Job.
        """
        return S_OK()

    def _analyseJob(self, job):
        """ Called from Job, only gives the application the knowledge of the Job (application, step, system config)
        """
        self._job = job

        self._systemconfig = job.systemConfig

        self._jobapps = job.applicationlist

        self._jobsteps = job.steps

        self._jobtype = job.type

        return self._doSomethingWithJob()

    def _doSomethingWithJob(self):
        """ As name suggest, if there is something to do with the job, it should be done now
        Example: software to install
        """
        return S_OK()

    def _addedtojob(self):
        """ Called from Job to tell the application that it is added to job and the parameter values are set.
        
        Prevents the user from thinking he can change the values after the app was added to job.
        """
        self.addedtojob = True

    def _checkArgs(self, argNamesAndTypes):
        """ Private method to check the validity of the parameters
        """

        # inspect.stack()[1][0] returns the frame object ([0]) of the caller
        # function (stack()[1]).
        # The frame object is required for getargvalues. Getargvalues returns
        # a tuple with four items. The fourth item ([3]) contains the local
        # variables in a dict.

        args = inspect.getargvalues(inspect.stack()[1][0])[3]

        #

        for argName, argType in argNamesAndTypes.iteritems():

            if not args.has_key(argName):
                self._reportError(
                    'Method does not contain argument \'%s\'' % argName,
                    __name__,
                    **self._getArgsDict(1)
                )

            if not isinstance(args[argName], argType):
                self._reportError(
                    'Argument \'%s\' is not of type %s' % ( argName, argType ),
                    __name__,
                    **self._getArgsDict(1)
                )

    def _getArgsDict(self, level=0):
        """ Private method
        """

        # Add one to stack level such that we take the caller function as the
        # reference point for 'level'

        level += 1

        #

        args = inspect.getargvalues(inspect.stack()[level][0])
        adict = {}

        for arg in args[0]:

            if arg == "self":
                continue

            # args[3] contains the 'local' variables

            adict[arg] = args[3][arg]

        return adict

    #############################################################################
    def _reportError(self, message, name='', **kwargs):
        """Internal Function. Gets caller method name and arguments, formats the 
           information and adds an error to the global error dictionary to be 
           returned to the user. 
           Stolen from DIRAC Job Class
        """
        className = name
        if not name:
            className = __name__
        methodName = sys._getframe(1).f_code.co_name
        arguments = []
        for key in kwargs:
            if kwargs[key]:
                arguments.append('%s = %s ( %s )' % ( key, kwargs[key], type(kwargs[key]) ))
        finalReport = 'Problem with %s.%s() call:\nArguments: %s\nMessage: %s\n' % ( className, methodName,
                                                                                     ', '.join(arguments),
                                                                                     message )
        if self._errorDict.has_key(methodName):
            tmp = self._errorDict[methodName]
            tmp.append(finalReport)
            self._errorDict[methodName] = tmp
        else:
            self._errorDict[methodName] = [finalReport]
        self._log.error(finalReport)
        return S_ERROR(finalReport)
