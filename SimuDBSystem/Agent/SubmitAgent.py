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
        gMonitor.registerActivity( "SubmittedTasks", "Automatically submitted tasks", "SimuDB Monitoring", "Tasks",
                                   gMonitor.OP_ACUM )
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
        simusgroups = self.simudb.get_simulations_groups(status = ["new", "submitting"])
        if not simusgroups:
            simusgroups = []
        simus = {}
        for simugroup in simusgroups:
            if not simugroup in simus:
                simus[simugroup] = []
            if simugroup.get_status() == "new":
                res = self._handle_defaultXML(simugroup)
                if not res["OK"]:
                    self.log.error("Failed to upload default XML for the group \n   Won't submit anything!")
                    continue
            sim = simugroup.get_simulations(status=["new"])
            if not sim:
                gLogger.info("Simugroup doesn't have any jobs to submit")
                simugroup.set_status("submitted")
                continue
            simus[simugroup].append(sim)
        return S_OK(simus)
    
    def _handle_defaultXML(self, simugroup):
        """ Upload the default XML for this group
        """
        input_xml_content = simugroup.xml
        input_xml = "./default.xml"
        with open(input_xml, "w") as xml_file:
            #TODO: depending on the type of input_xml_content, convert to string
            xml_file.write(input_xml_content)
        
        basepath = "/alpeslasers/simu/"
        final_path  = os.path.join(basepath, simugroup.id, "default.xml")
        rm = ReplicaManager()
        res = rm.putAndRegister(final_path, input_xml, "AL-DIP")
        if not res["OK"]:
            self.log.error("Failed to upload default.xml to SE:", res["Message"])
            return S_ERROR("Failed to upload default xml")
        os.unlink(input_xml)
        simugroup.set_default_path(final_path)
        return S_OK()
    
    def _submit(self, simulations):
        gLogger.info( "_submit: Submitting tasks" )
        res = getProxyInfo( False, False )
        if not res['OK']:
            gLogger.error( "_submit: Failed to determine credentials for submission", res['Message'] )
            return res
        proxyInfo = res['Value']
        owner = proxyInfo['username']
        ownerGroup = proxyInfo['group']
        gLogger.info( "_submit: Tasks will be submitted with the credentials %s:%s" % ( owner, ownerGroup ) )
        for simgroup, simulations in simulations.items():
            for sim in simulations:
                res = self._make_job(sim)
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
                sim.set_status("waiting")
                sim.set_jobid(jobid)
                os.unlink("jobDescription.xml")
            simgroup.set_status("submitting")
        return S_OK()
    
    def _make_job(self, sim):
        """ Make a job given the input simulation
        """
        job = UserJob()
        #here, get CPUTime, type (version) from sim
        simu_group = sim.get_group()
        job.setJobGroup(simu_group.name)
        simu_id = sim.id
        job.setName("%s_%s" % (simu_group.name, simu_id))#This is important for the status setting, and output registration
        app_dict = {}
        app_dict[""] = ""
        res = get_app_list(app_dict)
        if not res["OK"]:
            self.log.error("Couldn't get the applications:", res["Message"])
            return res
        for app in res["Value"]:
            if app.appname.lower() == "sewlab":
                app.setSteeringFile("LFN:"+simu_group.default_xml_lfnpath)
                #app.setSomething() #the XML diff WRT the original file
                job.setOutputData(["*.pkl"], 
                                  "%s/s" % (simu_group, simu_id), 
                                  "AL-DIP")
            res = job.append(app)
            if not res['OK']:
                gLogger.error("Error adding task:", res['Message'])
                return S_ERROR("Failed adding application %s" % app.appname)
        return S_OK(job)
    