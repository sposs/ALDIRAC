"""
SubmitAgent: find and submit new simulations tasks

Created on Mar 6, 2014

@author: stephanep
"""
from DIRAC                                            import S_OK, S_ERROR
from DIRAC                                            import gMonitor
from DIRAC.Core.Base.AgentModule                      import AgentModule
from DIRAC.Core.Security.ProxyInfo                    import getProxyInfo
from DIRAC.WorkloadManagementSystem.Client.WMSClient  import WMSClient
import subprocess
from ALDIRAC.Interfaces.API.UserJob                   import UserJob
from ALDIRAC.Interfaces.API.Applications              import get_app_list
from DIRAC.DataManagementSystem.Client.DataManager    import DataManager
from DIRAC.Core.Utilities.List                        import breakListIntoChunks
import os
from simudb.db.simu_interface import SimuInterface
from simudb.db.combined import CombinedInterface
from simudb.helpers.script_base import create_connection
from xml.etree.ElementTree import tostring
from DIRAC.ConfigurationSystem.Client.Helpers.Operations import Operations
from DIRAC.Resources.Catalog.FileCatalogClient import FileCatalogClient
#import time


__RCSID__ = '$Id: $'
AGENT_NAME = 'SimuDBSystem/SubmitAgent'


class SubmitAgent(AgentModule):
    
    def __init__(self, *args, **kwargs):

        AgentModule.__init__(self, *args, **kwargs)
        self.simudb = None
        self.shifterProxy = "ProductionManager"
        self.submissionClient = WMSClient()
        self.fc = FileCatalogClient()
        
    def initialize(self):
        self.am_setOption('shifterProxy', self.shifterProxy)
        gMonitor.registerActivity("SubmittedTasks",
                                  "Automatically submitted tasks",
                                  "SimuDB Monitoring", "Tasks",
                                  gMonitor.OP_ACUM)

        return S_OK()
    
    def execute(self):
        """ Prepare the execution
        """
        testmode = self.am_getOption("TestMode", False)
        self.log.info("Testmode is ", testmode)
        self.store_output = self.am_getOption("StoreOutput", True)
        self.log.info("Storing the output always:", self.store_output)
        connection = create_connection(testmode=testmode)
        self.simudb = SimuInterface(connection)
        self.combined = CombinedInterface(connection)
        self.destination_sites = {}
        self.destination_sites["sewlab"] = Operations().getValue("SewLab/DestinationSite", ["AL.farm.ch"])
        self.destination_sites["simulase"] = Operations().getValue("Simulase/DestinationSite", ["AL.farm.ch"])
        self.destination_sites["lastip"] = Operations().getValue("Lastip/DestinationSite", ["AL.farm.ch"])
        self.destination_sites["algorunner"] = Operations().getValue("AlgoRunner/DestinationSite", ["AL.farm.ch"])
        self.destination_sites["generic"] = Operations().getValue("Generic/DestinationSite", ["AL.farm.ch"])
        self.log.info("Destination sites:", str(self.destination_sites))
        self.submit_pools = {}
        self.submit_pools["sewlab"] = Operations().getValue("SewLab/SubmitPools", "")
        self.submit_pools["simulase"] = Operations().getValue("Simulase/SubmitPools", "")
        self.submit_pools["lastip"] = Operations().getValue("Lastip/SubmitPools", "")
        self.submit_pools["algorunner"] = Operations().getValue("AlgoRunner/SubmitPools", "")
        self.submit_pools["generic"] = Operations().getValue("Generic/SubmitPools", "")
        self.log.info("SubmitPools", str(self.submit_pools))
        self.cpu_times = {}
        self.cpu_times["sewlab"] = Operations().getValue("SewLab/MaxCPUTime")
        self.cpu_times["simulase"] = Operations().getValue("Simulase/MaxCPUTime")
        self.cpu_times["lastip"] = Operations().getValue("Lastip/MaxCPUTime")
        self.cpu_times["algorunner"] = Operations().getValue("AlgoRunner/MaxCPUTime")
        self.cpu_times["generic"] = Operations().getValue("Generic/MaxCPUTime")
        self.log.info("MaxCPUTimes: ", str(self.cpu_times))
        self.verbosity = Operations().getValue("JobVerbosity", "INFO")
        self.storageElement = Operations().getValue("StorageElement", "AL-DIP")
        self.group_size = Operations().getValue("SewLab/GroupSize", 10)
        res = self._get_new_tasks()
        if not res["OK"]:
            self.log.error("Failed getting the simulations to submit")
            self.simudb.close_session()
            return res
        res = self._submit(res['Value'])
        if not res["OK"]:
            self.log.error("Submission of simulations failed")
            self.simudb.close_session()
            return res
        self.simudb.close_session()
        connection.close()
        return S_OK()
    
    def _get_new_tasks(self):
        """ Get the simu groups that are new/submitting
        In them, get the tasks that are new
        Mark the simugroup as submitted if not task are found
        
        """
        try:
            # TODO: make sure the simu groups that have no simulations are still returned so
            # TODO: that they get their final status
            simusdict = self.simudb.get_runs_with_status_in_group_with_status(status=["new"], gstat=["new",
                                                                                                     "submitting"])
            ## session is opened
        except:
            return S_ERROR("Couldn't get the simu dict")
        simus_ids = {}
        total_tasks = 0 
        for simugroupid in simusdict.keys():
            if simugroupid not in simus_ids:
                simus_ids[simugroupid] = []
            if self.simudb.get_rungroup_status(simugroupid) == "new":
                res = self._handle_defaultXML(simugroupid)
                if not res["OK"]:
                    self.log.error("Failed to upload default XML for the group \n   Won't submit anything!")
                    continue
                if self.simudb.get_rungroup_type(simugroupid) == "lastip":
                    res = self._handle_simulase_db(simugroupid)
                    if not res["OK"]:
                        self.log.error("Failed to upload simulase DB for the group \n   Won't submit anything!")
                        continue
                if self.simudb.get_rungroup_type(simugroupid) == "generic":
                    res = self._handle_generic_inputs(simugroupid)
                    if not res["OK"]:
                        self.log.error("Failed to upload generic app inputs for the group \n   Won't submit anything!")
                        continue
            sims = simusdict[simugroupid]["simulations"]
            if not sims:
                self.log.info("RunGroup doesn't have any jobs to submit")
                self.simudb.set_rungroup_status(simugroupid, "submitted")
                continue
            simus_ids[simugroupid].extend(sims)
            total_tasks += len(sims)
        self.log.info("Found tasks to submit:", total_tasks)
        return S_OK(simus_ids)

    def put_file(self, simugroupid, file_lfn, data_file, fcn_handle):
        """
        Small local utility to upload files to a SE
        :param simugroupid: a simu group ID
        :param file_lfn: a file LFN
        :param data_file: a data file path to upload
        :param fcn_handle: A function handle to get the uploaded file
        :return: S_OK
        """
        self.log.info("Will attempt to upload %s to %s" % (data_file, file_lfn))
        res = self.fc.getReplicas(file_lfn)
        if res["OK"]:
            if file_lfn in res['Value']['Successful']:
                existing = fcn_handle(simugroupid)
                if file_lfn == existing:
                    self.log.info("Found pre existing file for that group.")
                    return S_OK()
        dm = DataManager()
        res = dm.putAndRegister(file_lfn, data_file, self.storageElement)
        if not res["OK"]:
            if not res["Message"].count("This file GUID already exists for another file"):
                self.log.error("Failed to upload file to SE:", res["Message"])
                return S_ERROR("Failed to upload file")
        self.log.info("Uploaded following file:", file_lfn)
        return S_OK()

    def _handle_generic_inputs(self, simugroupid):
        """
        Put the generic app files on the SE
        :param simugroupid:
        :return: S_OK
        """
        input_data = self.simudb.get_generic_app_input_data(simugroupid)
        fname = os.path.join("/tmp", os.path.basename(input_data.get("name", "data.dat")))
        self.log.info("File Name is %s " % fname)
        with open(fname, "w") as input_f:
            input_f.write(input_data["content"])
        self.simudb.close_session()  # because the following can take time
        basepath = "/alpeslasers/simu/"
        final_path = os.path.join(basepath, str(simugroupid), os.path.basename(fname))
        self.log.info("Dest LFN is %s" % final_path)
        res = self.put_file(simugroupid, final_path, fname, self.simudb.get_rungroup_lfnpath)
        os.unlink(fname)
        if not res['OK']:
            self.log.error(res['Message'])
            return res
        self.simudb.set_rungroup_lfnpath(simugroupid, final_path)
        execscript = self.simudb.get_generic_app_execfile(simugroupid)
        fname = os.path.join("/tmp", os.path.basename(execscript.get("name", "execf")))
        self.log.info("File Name is %s " % fname)
        with open(fname, "w") as input_f:
            input_f.write(execscript["content"])
        final_path = os.path.join(basepath, str(simugroupid), os.path.basename(fname))
        self.log.info("Dest LFN is %s" % final_path)
        res = self.put_file(simugroupid, final_path, fname, self.simudb.get_generic_app_execfile_lfn)
        os.unlink(fname)
        if not res['OK']:
            self.log.error(res['Message'])
            return res
        self.simudb.set_generic_app_execfile_lfn(simugroupid, final_path)
        return S_OK()

    def _handle_defaultXML(self, simugroupid):
        """ Upload the default XML for this group. Usually the design XML, but can be other things like the input
        data for the generic app
        """
        input_xml = self.combined.get_rungroup_fullxml(simugroupid)
        if not input_xml:
            return S_OK()
        input_xml_file = "./default.xml"
        with open(input_xml_file, "w") as xml_file:
            xml_file.write(tostring(input_xml))
        self.simudb.close_session()  # because the following can take time
        basepath = "/alpeslasers/simu/"
        final_path = os.path.join(basepath, str(simugroupid), "default.xml")
        res = self.put_file(simugroupid, final_path, input_xml_file, self.simudb.get_rungroup_lfnpath)
        os.unlink(input_xml_file)
        if not res['OK']:
            self.log.error(res['Message'])
            return res
        self.simudb.set_rungroup_lfnpath(simugroupid, final_path)
        return S_OK()

    def _handle_simulase_db(self, simugroupid):
        """
        For lastip runs, the simulase DB need to be obtained then shipped to the ISB
        :param simugroupid: a simu group ID
        :return: S_OK
        """
        database_tag = self.simudb.get_lastip_group_dbtag(simugroupid)
        if not database_tag:
            return S_OK()
        if not os.path.isdir("/tmp/lastip"):
            os.mkdir("/tmp/lastip")
        dest_file = '/tmp/lastip/large_db.txt'
        design_id = self.simudb.get_rungroup_designID(simugroupid)
        cmd = "simulase_wrapper_retrieve -v -D cldb --database_tag %s --design_id %s " \
              "--output %s" % (database_tag, design_id, dest_file)
        try:
            res = subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as error:
            self.log.error("Bad simulase DB run:", str(error))
            return S_ERROR(str(error))
        basepath = "/alpeslasers/simu/"
        final_path = os.path.join(basepath, str(simugroupid), "simulase_db.txt")
        res = self.put_file(simugroupid, final_path, dest_file, self.simudb.get_lastip_simulase_lfn)
        os.unlink(dest_file)
        if not res['OK']:
            self.log.error(res['Message'])
            return res
        self.simudb.set_lastip_simulase_lfn(simugroupid, final_path)
        return S_OK()

    def _submit(self, simulations):
        """ Create and submit the tasks
        """
        self.log.info("_submit: Submitting tasks")
        res = getProxyInfo(False, False)
        if not res['OK']:
            self.log.error("_submit: Failed to determine credentials for submission", res['Message'])
            return res
        proxyInfo = res['Value']
        owner = proxyInfo['username']
        ownerGroup = proxyInfo['group']
        self.log.info("_submit: Tasks will be submitted with the credentials %s:%s" % (owner, ownerGroup))
        for simgroupid, simulations_id in simulations.items():
            for simids in breakListIntoChunks(simulations_id, self.group_size):
                #before = time.time()
                res = self._make_job(simgroupid, simids)
                #after = time.time()
                #self.log.notice("Making jobs took", after - before)
                if not res["OK"]:
                    self.log.error("Failed to make task", res['Message'])
                    continue
                oJob = res['Value']
                oJob._addToWorkflow()
                resolvedFiles = oJob._resolveInputSandbox(oJob.inputsandbox)
                fileList = ";".join(resolvedFiles)
                description = 'Input sandbox file list'
                oJob._addParameter( oJob.workflow, 'InputSandbox', 'JDL', fileList, description)
                workflowFile = open("jobDescription.xml", 'w')
                workflowFile.write(oJob._toXML())
                workflowFile.close()
                jdl = oJob._toJDL()
                res = self.submissionClient.submitJob(jdl)
                if not res["OK"]:
                    os.unlink("jobDescription.xml")
                    self.log.error("Failed submitting task", res["Message"])
                    continue
                jobid = res["Value"]
                for simid in simids:
                    self.simudb.set_run_status(simid, "waiting")
                    self.simudb.set_jobid(simid, jobid)
                os.unlink("jobDescription.xml")
            self.simudb.set_rungroup_status(simgroupid, "submitting")
        return S_OK()
    
    def _make_job(self, simgroupid, simids):
        """ Make a job given the input simulation
        """
        job = UserJob()
        #here, get CPUTime, type (version) from sim
        #clock = time.time()
        jobtype = ""
        group_name = "%s" % str(simgroupid)
        job.setJobGroup(group_name)
        job.setName("%s-%s" % (simids[0], simids[-1]))
        max_prio = 0
        is_sewlab = False
        n_sub_jobs = len(simids)
        for simid in simids:
            resdict = self.simudb.get_run_submission_properties(simid)
            #after = time.time()
            #self.log.verbose("Query took :", after - clock)
            #group_name = "%s_%s" % (str(resdict["simname"]), str(simgroupid))
            #self.log.notice("Submitting task for group", group_name)
            #job.setJobGroup(group_name)
            path = resdict.get("lfnpath", "")
            path = path.strip()
            if resdict["priority"] > max_prio:
                #select the highest priority as the job's priority
                max_prio = resdict["priority"]
            #job.setName("%s" % (simid))
            app_dict = {resdict["type"]: resdict["version"]}
            res = get_app_list(app_dict)
            if not res["OK"]:
                self.log.error("Couldn't get the applications:", res["Message"])
                continue
            failed = False
            my_params = {}
            for app in res["Value"]:
                self.log.info("Found app", app.appname)
                if app.appname.lower() == "setjobname":
                    app.setNewName(str(simid))
                if app.appname.lower() == "sewlab":
                    is_sewlab = True
                    jobtype = "sewlab"
                    if not path:
                        self.log.error("LFN Path is empty, not submitting")
                        failed = True
                        continue
                    app.setSteeringFile("LFN:"+path)
                    my_params = self.simudb.get_sewlabrun_parameters(simid)
                    app.setAlteredParameters("%s = %s" % (my_params['name'], my_params['value']))
                if app.appname.lower() == "simulase":
                    is_sewlab = True
                    jobtype = "simulase"
                    if not path:
                        self.log.error("LFN Path is empty, not submitting")
                        failed = True
                        continue
                    app.setDesignXML("LFN:"+path)
                    my_params = self.simudb.get_simulase_parameters(simid)
                    app.setModifiers(my_params['modifiers'])
                    app.setTemperature(my_params['temperature'])
                    app.setField(my_params['efield'])
                    app.setSheetDensity(my_params['sheet_density'])
                    app.setBroadening(my_params['broadening'])
                    app.setPolarization(my_params['polarization'])
                if app.appname.lower() == "lastip":
                    is_sewlab = True
                    jobtype = "lastip"
                    if not path:
                        self.log.error("LFN Path is empty, not submitting")
                        failed = True
                        continue
                    app.setDesignXML("LFN:" + path)
                    my_params = self.simudb.get_lastip_parameters(simid)
                    app.setRunParameters(my_params)
                    simulase_db = self.simudb.get_lastip_simulase_lfn(simgroupid)
                    if simulase_db:
                        app.setSimulaseDB("LFN:" + simulase_db)
                if app.appname.lower() == "analysis":
                    if "store" in my_params and my_params['store']:
                        app.setStore()
                if app.appname.lower() == "any":
                    jobtype = "generic"
                    my_params = self.simudb.get_generic_app_params(simid)
                    self.log.info("Using %s as parameters" % my_params)
                    app.appname = my_params.get("ApplicationName", "generic")
                    app.setVersion(my_params.get("ApplicationVersion", "1.0"))
                    if path:
                        app.setInputFile("LFN:" + path)
                    my_params['InputFile'] = path
                    app.setParameters(my_params)
                    app.setOutputFile(my_params.get("OutputFile", "output.pkl"))
                    exec_module = my_params.get("ExecutionModulePath", "")
                    if exec_module:
                        exec_module = "LFN:"+exec_module
                        app.setExecutionModule(exec_module)
                res = job.append(app)
                if not res['OK']:
                    self.log.error("Error adding task:", res['Message'])
                    return S_ERROR("Failed adding application %s" % app.appname)
            if failed:
                return S_ERROR("Failed adding the applications")
        if self.store_output and is_sewlab:
            job.setOutputData(["*.pkl"], "%s" % simgroupid, self.storageElement)
        job.setPriority(max_prio)
        job.setDestination(self.destination_sites[jobtype])
        #if self.submit_pools[jobtype]:
        job.setSubmitPool(self.submit_pools[jobtype])
        job.setCPUTime(n_sub_jobs * int(self.cpu_times[jobtype]))
        if jobtype == "sewlab":
            outsb = ["*.log", "*.sample", "*.script"]
        else:
            outsb = ['*.log', "*.sh"]
        job.setOutputSandbox(outsb)
        job.setLogLevel(self.verbosity)
        return S_OK(job)
