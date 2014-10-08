import datetime
from ALDIRAC.SimuDBSystem.Agent.StartRunAgent import StartRunAgent, get_modificator
from DIRAC.FrameworkSystem.Client.SystemAdministratorClient import SystemAdministratorClient
from DIRAC.Core.DISET.RPCClient import RPCClient

from DIRAC import S_OK, S_ERROR

__author__ = 'stephanep'
__RCSID__ = "$Id$"


class StopRunAgent(StartRunAgent):
    def __init__(self, *args, **kwargs):
        StartRunAgent.__init__(*args, **kwargs)

    def execute(self):
        self.vmdb = RPCClient("SimuDB/VMDB")
        host = self.am_getOption("SubmitAgentHost", "dirac.internal.alp")
        self.systemAdmin = SystemAdministratorClient(host)

        res = self.vmdb.running_instance()
        if not res['OK']:
            self.log.error("Couldn't get the instance", res['Message'])
        instance_id = res['Value']
        if not instance_id:
            self.log.info("No instance is running, skip")
            return S_OK()

        res = self._check_jobs()
        if not res['OK']:
            self.log.error("Failed to check for new jobs")
            return res
        if res['Value']:
            self.log.info("Still jobs in the DB to be treated, stop here.")
            return S_OK()

        res = self._check_WMS_Jobs()
        if not res['OK']:
            self.log.error("Failed to retrieve job info, can't continue.", res['Message'])
            return res
        jobs = res['Value']
        if jobs:
            self.log.info("Still jobs waiting and/or running, need to wait")
            return S_OK()

        res = self._stop_submit_agent()
        if not res['OK']:
            self.log.error("Failed to stop the agent, will shut down anyway")

        res = self._check_age(instance_id)
        if not res['OK']:
            self.log.error("Couldn't proceed with age check", res['Message'])
            return res
        if res['Value']:
            self.log.info("Machine isn't old enough to be killed, wait a bit more")
            return S_OK()

        res = self.vmdb.stopServerInstance(instance_id)
        if not res['OK']:
            self.log.error("Failed shutting down the instance %s." % instance_id, res['Message'])
            return res

        res = self._update_CS()
        if not res['OK']:
            return res

        return S_OK()

    def _check_age(self, instance_id):
        res = self.vmdb.instanceProperties(instance_id)
        if not res['OK']:
            self.log.error("Instance properties cannot be obtained")
            return res
        properties = res['Value']
        now = datetime.datetime.utcnow()
        try:
            started = datetime.datetime.strptime(properties["Started"], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return S_ERROR("Failed to convert the started time: %s" % str(properties["Started"]))
        lifetime = now - started
        if 3600 - (lifetime.total_seconds() % 3600) > 5*60:
            # machine is too young
            return S_OK(1)
        return S_OK(0)

    def _check_WMS_Jobs(self):
        return S_OK()

    def _stop_submit_agent(self):
        return self.systemAdmin.stopComponent("SimuDB", "SubmitAgent")

    def _update_CS(self):
        """
        Update the CS: Remove Systems and copy the Systems_al to Systems.
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
            if not modificator.copyKey("/Systems_al", "/Systems"):
                self.log.error("Failed to copy the Systems_amazon to Systems")
                return S_ERROR("Failed to copy the Systems_amazon to Systems")
        except KeyError as error:
            return S_ERROR("Problems with the path: %s" % str(error))
        res = modificator.commit()
        if not res['OK']:
            return res
        return S_OK()