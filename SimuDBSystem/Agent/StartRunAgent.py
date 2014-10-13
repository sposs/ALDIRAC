from ConfigurationSystem.private.Modificator import Modificator
from Core.Security import ProxyInfo
from Core.Utilities import Time
from DIRAC.Core.DISET.RPCClient import RPCClient
from DIRAC.Core.Base.AgentModule import AgentModule
from DIRAC import S_OK, S_ERROR, gConfig
from simudb.db.simu_interface import SimuInterface
from simudb.helpers.script_base import create_connection
from DIRAC.FrameworkSystem.Client.SystemAdministratorClient import SystemAdministratorClient

__author__ = 'stephanep'

__RCSID__ = "$Id$"


def get_modificator():
    rpcClient = RPCClient(gConfig.getValue("/DIRAC/Configuration/MasterServer", "Configuration/Server"))
    res = ProxyInfo.getProxyInfo()
    if not res['OK']:
        return res
    proxy_info = res['Value']
    committer = "%s@%s - %s" % (proxy_info.get('username', "unknown"),
                                proxy_info.get("group", "unknown"),
                                Time.dateTime().strftime("%Y-%m-%d %H:%M:%S"))
    return Modificator(rpcClient, committer)


class StartRunAgent(AgentModule):
    def __init__(self, *args, **kwargs):
        """ c'tor
        """
        AgentModule.__init__(self, *args, **kwargs)
        self.vmdb = None
        self.systemAdmin = None
        self.shifterProxy = "VMManager"

    def initialize(self):
        self.am_setOption('shifterProxy', self.shifterProxy)

    def execute(self):
        self.vmdb = RPCClient("SimuDB/VMDB")
        host = self.am_getOption("SubmitAgentHost", "dirac.internal.alp")
        self.systemAdmin = SystemAdministratorClient(host)

        res = self._check_jobs()
        if not res['OK']:
            return res
        jobs = res['Value']
        if not jobs:
            self.log.info("No jobs waiting in DB, skip.")
            return S_OK()

        # Polling time needs to be long, like 10 minutes otherwise there is a risk to have many
        # instances in parallel
        res = self._check_instance()
        if not res['OK']:
            return res
        instanceID = res['Value']
        if instanceID:
            self.log.info("Instance already up and running, don't need to continue.")
            return S_OK()

        res = self.vmdb.startServerInstance()
        if not res['OK']:
            self.log.error(res['Message'])
            # In case of failure, wait until next iteration to try again
            return res

        res = self._update_CS()
        if not res['OK']:
            self.log.error("Failed to update the CS:", res['Message'])
            # try again
            res = self._update_CS()
            if not res['OK']:
                self.log.error("Failed again to update the CS:", res['Message'])
                # Don't start the submit agent as it will submit jobs that will fail in nasty ways.
                return S_ERROR(res)

        res = self._start_submit_agent()
        if not res['OK']:
            self.log.error("Failed to start the agent:", res['Message'])
            #TODO: fix me
            pass

        self.log.info("Everything is OK, finished")
        return S_OK()

    def _check_jobs(self):
        """
        Ask the SimuDB if there are any waiting jobs to be processed
        :return: S_OK
        """
        testmode = self.am_getOption("TestMode", False)
        simudb = SimuInterface(create_connection(testmode=testmode))
        try:
            simusdict = simudb.get_runs_with_status_in_group_with_status(status=["new"],
                                                                         gstat=["new", "submitting"])
        except:
            return S_ERROR("Couldn't get the simu dict")
        simudb.close_session()
        return S_OK(len(simusdict.keys()))

    def _check_instance(self):
        """
        Check if there is already an instance that is registered
        :return: S_OK(instance_ID)
        """
        res = self.vmdb.running_instance()
        return res

    def _update_CS(self):
        """
        Update the CS: Remove Systems and copy the Systems_amazon to Systems. The reverting back to Systems_AL is done
        in the other agent
        :return: S_OK
        """
        modificator = get_modificator()
        res = modificator.loadFromRemote()
        if not res['OK']:
            return res
        try:
            if not modificator.removeSection("/Systems"):
                self.log.error("Failed to remove the /Systems option, won't proceed.")
                return S_ERROR("Failed to remove the /Systems option, won't proceed.")
        except KeyError:
            # as this means the section was already deleted before
            pass
        try:
            if not modificator.copyKey("/Systems_amazon", "/Systems"):
                self.log.error("Failed to copy the Systems_amazon to Systems")
                return S_ERROR("Failed to copy the Systems_amazon to Systems")
        except KeyError as error:
            return S_ERROR("Problems with the path: %s" % str(error))
        res = modificator.commit()
        if not res['OK']:
            return res
        return S_OK()

    def _start_submit_agent(self):
        """
        Start the SubmitAgent that processes new jobs in SimuDB.
        :return: S_OK()
        """
        res = self.systemAdmin.restartComponent("WorkloadManagement", "Matcher")
        if not res['OK']:
            return res
        res = self.systemAdmin.restartComponent("WorkloadManagement", "SandboxStore")
        if not res['OK']:
            return res
        res = self.systemAdmin.restartComponent("WorkloadManagement", "JobManager")
        if not res['OK']:
            return res
        res = self.systemAdmin.startComponent("SimuDB", "SubmitAgent")
        if not res['OK']:
            return res
        return self.systemAdmin.startComponent("SimuDB", "StopRunAgent")