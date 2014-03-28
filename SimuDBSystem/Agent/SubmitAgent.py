'''
SubmitAgent: find and submit new simulations tasks

Created on Mar 6, 2014

@author: stephanep
'''
from DIRAC                                            import S_OK, S_ERROR, gLogger
from DIRAC                                            import gMonitor
from DIRAC.Core.Base.AgentModule                      import AgentModule
from DIRAC.Core.Security.ProxyInfo                    import getProxyInfo
from DIRAC.WorkloadManagementSystem.Client.WMSClient  import WMSClient
from ALDIRAC.Interfaces.API.UserJob                   import UserJob
from ALDIRAC.Interfaces.API.Applications              import get_app_list
from DIRAC.DataManagementSystem.Client.ReplicaManager import ReplicaManager
import os
from simudb.db.simu_interface import SimuInterface
from simudb.db.combined import CombinedInterface
from simudb.helpers.script_base import create_connection
from xml.etree.ElementTree import tostring
from DIRAC.ConfigurationSystem.Client.Helpers.Operations import Operations


__RCSID__ = '$Id: $'
AGENT_NAME = 'SimuDBSystem/SubmitAgent'

class SubmitAgent( AgentModule ):
    
    def __init__( self, *args, **kwargs ):

        AgentModule.__init__( self, *args, **kwargs )
        self.simudb = None
        self.shifterProxy = "ProductionManager"
        self.submissionClient = WMSClient()
        
    def initialize( self ):
        self.am_setOption( 'shifterProxy', self.shifterProxy )
        gMonitor.registerActivity( "SubmittedTasks", 
                                   "Automatically submitted tasks", 
                                   "SimuDB Monitoring", "Tasks",
                                   gMonitor.OP_ACUM )
        testmode = self.am_getOption("TestMode", False)
        self.store_output = self.am_getOption("StoreOutput", True)
        self.simudb = SimuInterface(create_connection(testmode = testmode))
        self.combined = CombinedInterface(create_connection(testmode = testmode))
        self.destination_sites = {}
        self.destination_sites["sewlab"] = Operations().getValue("SewLab/DestinationSite")
        self.cpu_times = {}
        self.cpu_times["sewlab"] = Operations().getValue("SewLab/MaxCPUTime")
        
        return S_OK()
    
    def execute(self):
        res = self._get_new_tasks()
        if not res["OK"]:
            self.log.error("Failed getting the simulations to submit")
            self.simudb.close_session()
            return res
        res = self._submit(res['Value'])
        if not res["OK"]:
            gLogger.error("Submission of simulations failed")
            self.simudb.close_session()
            return res
        self.simudb.close_session()
        return S_OK()
    
    def _get_new_tasks(self):
        """ Get the simu groups that are new/submitting
        In them, get the tasks that are new
        Mark the simugroup as submitted if not task are found
        
        """
        try:
            #TODO: make sure the simu groups that have no simulations are still returned so that they get their final status
            simusdict = self.simudb.get_runs_with_status_in_group_with_status(status = ["new"], gstat = ["new", "submitting"])
            ## session is opened
        except:
            return S_ERROR("Couldn't get the simu dict")
        simus_ids = {}
        for simugroupid in simusdict.keys():
            if not simugroupid in simus_ids:
                simus_ids[simugroupid] = []
            if self.simudb.get_rungroup_status(simugroupid) == "new":
                res = self._handle_defaultXML(simugroupid)
                if not res["OK"]:
                    self.log.error("Failed to upload default XML for the group \n   Won't submit anything!")
                    continue
            sims = simusdict[simugroupid]["simulations"]
            if not sims:
                gLogger.info("RunGroup doesn't have any jobs to submit")
                self.simudb.set_rungroup_status(simugroupid, "submitted")
                continue
            simus_ids[simugroupid].extend(sims)
        return S_OK(simus_ids)
    
    def _handle_defaultXML(self, simugroupid):
        """ Upload the default XML for this group
        """
        input_xml = self.combined.get_rungroup_fullxml(simugroupid)
        input_xml_file = "./default.xml"
        with open(input_xml_file, "w") as xml_file:
            xml_file.write(tostring(input_xml))
        self.simudb.close_session()#because the following can take time
        basepath = "/alpeslasers/simu/"
        final_path  = os.path.join(basepath, str(simugroupid), "default.xml")
        rm = ReplicaManager()
        res = rm.putAndRegister(final_path, input_xml_file, "AL-DIP")
        if not res["OK"]:
            self.log.error("Failed to upload default.xml to SE:", res["Message"])
            return S_ERROR("Failed to upload default xml")
        os.unlink(input_xml_file)
        self.simudb.set_rungroup_lfnpath(simugroupid, final_path)
        return S_OK()
    
    def _submit(self, simulations):
        """ Create and submit the tasks
        """
        gLogger.info( "_submit: Submitting tasks" )
        res = getProxyInfo( False, False )
        if not res['OK']:
            gLogger.error( "_submit: Failed to determine credentials for submission", res['Message'] )
            return res
        proxyInfo = res['Value']
        owner = proxyInfo['username']
        ownerGroup = proxyInfo['group']
        gLogger.info( "_submit: Tasks will be submitted with the credentials %s:%s" % ( owner, ownerGroup ) )
        for simgroupid, simulations_id in simulations.items():
            for simid in simulations_id:
                res = self._make_job(simgroupid, simid)
                if not res["OK"]:
                    self.log.error("Failed to make task", res['Message'])
                    continue
                oJob = res['Value']
                workflowFile = open( "jobDescription.xml", 'w' )
                workflowFile.write( oJob._toXML() )
                workflowFile.close()
                jdl = oJob._toJDL()
                res = self.submissionClient.submitJob( jdl )
                if not res["OK"]:
                    self.log.error("Failed submitting task", res["Message"])
                    continue
                jobid = res["Value"]
                self.simudb.set_run_status(simid, "waiting")
                self.simudb.set_jobid(simid, jobid)
                os.unlink("jobDescription.xml")
            self.simudb.set_rungroup_status(simgroupid, "submitting")
        return S_OK()
    
    def _make_job(self, simgroupid, simid):
        """ Make a job given the input simulation
        """
        job = UserJob()
        #here, get CPUTime, type (version) from sim
        job.setJobGroup(str(simgroupid))
        job.setPriority(self.simudb.get_rungroup_priority(simgroupid))
        job.setName("%s" % (simid))#This is important for the status setting, and output registration
        jobtype = ""
        runtype, version = self.simudb.get_run_type_version(simid)
        app_dict = {}
        app_dict[runtype] = version
        res = get_app_list(app_dict)
        if not res["OK"]:
            self.log.error("Couldn't get the applications:", res["Message"])
            return res
        for app in res["Value"]:
            if app.appname.lower() == "sewlab":
                jobtype = "sewlab"
                path = self.simudb.get_rungroup_lfnpath(simgroupid)
                app.setSteeringFile("LFN:"+path)
                my_params = self.simudb.get_sewlabrun_parameters(simid)
                app.setAlteredParameters("%s = %s" % (my_params['name'], my_params['value']))
                if self.store_output:
                    job.setOutputData(["*.pkl"], 
                                      "%s/s" % (simgroupid, simid), 
                                      "AL-DIP")
            res = job.append(app)
            if not res['OK']:
                gLogger.error("Error adding task:", res['Message'])
                return S_ERROR("Failed adding application %s" % app.appname)

        job.setDestination(self.destination_sites[jobtype])
        job.setCPUTime(self.cpu_times[jobtype])
        
        return S_OK(job)
    