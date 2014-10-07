from urlparse import urlparse
import boto
from boto.regioninfo import RegionInfo
import time
from DIRAC.ConfigurationSystem.Client.CSAPI import CSAPI
from DIRAC.Core.DISET.RPCClient import RPCClient
from DIRAC.Core.Base.AgentModule import AgentModule
from DIRAC import S_OK, S_ERROR
from simudb.simudb.db.simu_interface import SimuInterface
from simudb.helpers.script_base import create_connection
from DIRAC.ConfigurationSystem.Client.Helpers.Operations import Operations
from DIRAC.FrameworkSystem.Client.SystemAdministratorClient import SystemAdministratorClient

__author__ = 'stephanep'


class StartRunAgent(AgentModule):
    def __init__(self, *args, **kwargs):
        """ c'tor
        """
        AgentModule.__init__(self, *args, **kwargs)
        self.simudb = None
        self.vmdb = None
        self.systemAdmin = None
        self.csAPI = None
        self.vm_params = {}
        self.shifterProxy = "ProductionManager"

    def initialize(self):
        self.am_setOption('shifterProxy', self.shifterProxy)

    def execute(self):
        testmode = self.am_getOption("TestMode", False)
        self.simudb = SimuInterface(create_connection(testmode=testmode))
        self.vmdb = RPCClient("SimuDB/VMDB")
        host = self.am_getOption("SubmitAgentHost", "dirac.internal.alp")
        self.systemAdmin = SystemAdministratorClient(host)
        self.csAPI = CSAPI()

        res = self._check_jobs()
        if not res['OK']:
            return res
        jobs = res['Value']
        if not jobs:
            self.log.info("No jobs waiting in DB, skip.")
            return S_OK()

        res = self._check_instance()
        if not res['OK']:
            return res
        instanceID = res['Value']
        if instanceID:
            self.log.info()
            return S_OK("Instance already exists, nothing to do")

        res = self._start_instance()
        if not res['OK']:
            self.log.error(res['Message'])
            # In case of failure, wait until next iteration to try again
            return res

        res = self._update_CS()
        if not res['OK']:
            # try again
            res = self._update_CS()
            if not res['OK']:
                #TODO: Sort this situation out
                pass

        res = self._start_submit_agent()
        if not res['OK']:
            #TODO: fix me
            pass

        self.log.info("Everything is OK, finished")
        self.simudb.close_session()
        return S_OK()

    def _check_jobs(self):
        """
        Ask the SimuDB if there are any waiting jobs to be processed
        :return: S_OK
        """
        try:
            simusdict = self.simudb.get_runs_with_status_in_group_with_status(status=["new"],
                                                                              gstat=["new", "submitting"])
            ## session is opened
        except:
            return S_ERROR("Couldn't get the simu dict")
        return S_OK(len(simusdict.keys()))

    def _check_instance(self):
        """
        Check if there is already an instance that is registered
        :return: S_OK(instance_ID)
        """
        res = self.vmdb.running_instance()
        return res

    def _get_vm_params(self):
        ops = Operations()
        self.vm_params["AMI"] = ops.getValue("ServerInstance/AMI", "")
        if not self.vm_params["AMI"]:
            return S_ERROR("Cannot find the VM parameters")
        self.vm_params['Type'] = ops.getValue("ServerInstance/Type", "c3.4xlarge")
        self.vm_params['Key'] = ops.getValue("ServerInstance/Key", "amazon-ec2")
        self.vm_params['SecurityGroup'] = [ops.getValue("ServerInstance/SecurityGroup", "dirac-server")]
        self.vm_params['AccessID'] = ops.getValue("ServerInstance/AccessID", "")
        self.vm_params['AccessKey'] = ops.getValue("ServerInstance/AccessKey", "")
        self.vm_params['Region'] = ops.getValue("ServerInstance/Region", "eu-west-1c")
        self.vm_params['RegionURL'] = ops.getValue("ServerInstance/RegionURL", "https://ec2.eu-west-1.amazonaws.com/")
        self.vm_params['PublicIP'] = ops.getValue("ServerInstance/PublicIP", "")
        return S_OK()

    def _start_instance(self):
        """
        Start an EC2 instance using boto
        :return: S_OK
        """
        res = self._get_vm_params()
        if not res['OK']:
            return res
        url = urlparse(self.vm_params['RegionURL'])
        _endpointHostname = url.hostname
        _port = url.port
        _path = url.path
        _regionName = self.vm_params['Region']
        _region = RegionInfo(name=_regionName, endpoint=_endpointHostname)
        __conn = boto.connect_ec2(aws_access_key_id=self.vm_params['AccessID'],
                                  aws_secret_access_key=self.vm_params['AccessKey'],
                                  is_secure=False, region=_region, path=_path,
                                  port=_port, debug=1)
        __vmImage = __conn.get_image(self.vm_params['AMI'])
        try:
            reservation = __vmImage.run(min_count=1,
                                        max_count=1,
                                        key_name=self.vm_params['Key'],
                                        security_groups=self.vm_params['SecurityGroup'],
                                        instance_type=self.vm_params['Type'])
        except Exception as error:
            self.log.error(error)
            return S_ERROR("Failed to start the image")
        idList = []
        failed_ids = []
        for instance in reservation.instances:
            instance.update()
            while instance.state != u'running':
                if instance.state == u'terminated':
                    self.log.error("New instance terminated while starting", "AMI: %s" % self.vm_params["AMI"])
                    continue
                self.log.info("Sleeping for 10 secs for instance %s (current state %s)" % (instance, instance.state))
                time.sleep(10)
                instance.update()
                if instance.state != u'terminated':
                    self.log.info("Instance %s started" % instance.id)
            idList.append(instance.id)
            if not __conn.associate_address(instance.id, public_ip=self.vm_params['PublicIP']):
                self.log.error("Issue setting the elastic IP, will terminate the instance")
                failed_ids.append(instance.id)
                idList.pop(instance.id)
        if failed_ids:
            __conn.terminate_instances(failed_ids)
        if not idList:
            return S_ERROR("No instance started.")
        return S_OK()

    def _update_CS(self):
        """
        Update the CS: Remove Systems and copy the Systems_amazon to Systems. The reverting back to Systems_AL is done
        in the other agent
        :return: S_OK
        """
        res = self.csAPI.initialize()
        if not res['OK']:
            return res
        res = self.csAPI.delSection("/Systems")
        if not res['OK']:
            self.log.error("This is really bad, something nasty happened")
            return res
        # res = self.csAPI

        return self.csAPI.commit()

    def _start_submit_agent(self):
        """
        Start the SubmitAgent that processes new jobs in SimuDB.
        :return: S_OK()
        """
        return self.systemAdmin.startComponent("SimuDB", "SubmitAgent")