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
from simudb.helpers.script_base import create_connection


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
        self.simudb = SimuInterface(create_connection())
        return S_OK()
    
    def execute(self):
        res = self._get_new_tasks()
        if not res["OK"]:
            self.log.error("Failed getting the simulations to submit")
            return res
        res = self._submit(res['Value'])
        if not res["OK"]:
            gLogger.error("Submission of simulations failed")
            return res
        return S_OK()
    
    def _get_new_tasks(self):
        """ Get the simu groups that are new/submitting
        In them, get the tasks that are new
        Mark the simugroup as submitted if not task are found
        
        """
        try:
            #TODO: make sure the simu groups that have no simulations are still returned so that they get their final status
            simusdict = self.simudb.get_simulations_with_status_in_group_with_status(status = ["new"], gstat = ["new", "submitting"])
        except:
            return S_ERROR("Couldn't get the simu dict")
        simus_ids = {}
        for simugroupid in simusdict.keys():
            #TODO: handle priorities
            if not simugroupid in simus_ids:
                simus_ids[simugroupid] = []
            if self.simudb.get_simulationgroup_status(simugroupid) == "new":
                res = self._handle_defaultXML(simugroupid)
                if not res["OK"]:
                    self.log.error("Failed to upload default XML for the group \n   Won't submit anything!")
                    continue
            sim = simusdict[simugroupid]["simulations"]
            if not sim:
                gLogger.info("Simugroup doesn't have any jobs to submit")
                self.simudb.set_simulationgroup_status(simugroupid, "submitted")
                continue
            simus_ids[simugroupid].append(sim)
        return S_OK(simus_ids)
    
    def _handle_defaultXML(self, simugroupid):
        """ Upload the default XML for this group
        """
        input_xml_content = self.simudb.get_simulationgroup_xml(simugroupid)
        input_xml = "./default.xml"
        with open(input_xml, "w") as xml_file:
            #TODO: depending on the type of input_xml_content, convert to string
            xml_file.write(input_xml_content)
        
        basepath = "/alpeslasers/simu/"
        final_path  = os.path.join(basepath, simugroupid, "default.xml")
        rm = ReplicaManager()
        res = rm.putAndRegister(final_path, input_xml, "AL-DIP")
        if not res["OK"]:
            self.log.error("Failed to upload default.xml to SE:", res["Message"])
            return S_ERROR("Failed to upload default xml")
        os.unlink(input_xml)
        self.simudb.set_simulationgroup_path(final_path)
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
                res = self._make_job(simid)
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
                self.simudb.set_simulation_status(simid, "waiting")
                self.simudb.set_jobid(simid, jobid)
                os.unlink("jobDescription.xml")
            self.simudb.set_simulationgroup_status(simgroupid, "submitting")
        return S_OK()
    
    def _make_job(self, simid):
        """ Make a job given the input simulation
        """
        job = UserJob()
        #here, get CPUTime, type (version) from sim
        simu_group = self.simudb.get_simulation_group(simid)
        job.setJobGroup(simu_group)
        job.setName("%s" % (simid))#This is important for the status setting, and output registration
        #TODO: get from the XML or simulation the app properties such as name/version
        app_dict = {}
        app_dict[""] = ""
        res = get_app_list(app_dict)
        if not res["OK"]:
            self.log.error("Couldn't get the applications:", res["Message"])
            return res
        for app in res["Value"]:
            if app.appname.lower() == "sewlab":
                path = self.simudb.get_simulationgroup_path(simu_group)
                app.setSteeringFile("LFN:"+path)
                #app.setSomething() #the XML diff WRT the original file
                job.setOutputData(["*.pkl"], 
                                  "%s/s" % (simu_group, simid), 
                                  "AL-DIP")
            res = job.append(app)
            if not res['OK']:
                gLogger.error("Error adding task:", res['Message'])
                return S_ERROR("Failed adding application %s" % app.appname)
        return S_OK(job)
    