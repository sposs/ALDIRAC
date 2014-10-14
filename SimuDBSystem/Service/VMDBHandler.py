import types
import boto
import time
from urlparse import urlparse
from boto.regioninfo import RegionInfo
from ALDIRAC.SimuDBSystem.DB.VMDB import VMDB
from DIRAC.ConfigurationSystem.Client.Helpers.Operations import Operations
from DIRAC.Core.DISET.RequestHandler import RequestHandler
from DIRAC import S_OK, S_ERROR

__author__ = 'stephanep'
__RCSID__ = "$Id$"

gVMDB = None


def initializeVMDBHandler(serviceInfo):
    global gVMDB
    gVMDB = VMDB()
    return S_OK()


def _get_vm_params():
    ops = Operations()
    vm_params = {"AMI": ops.getValue("ServerInstance/AMI", "")}
    if not vm_params["AMI"]:
        return S_ERROR("Cannot find the VM parameters")
    vm_params['Type'] = ops.getValue("ServerInstance/Type", "c3.4xlarge")
    vm_params['Key'] = ops.getValue("ServerInstance/Key", "amazon-ec2")
    vm_params['SecurityGroup'] = [ops.getValue("ServerInstance/SecurityGroup", "dirac-server")]
    vm_params['AccessID'] = ops.getValue("ServerInstance/AccessID", "")
    vm_params['AccessKey'] = ops.getValue("ServerInstance/AccessKey", "")
    vm_params['Region'] = ops.getValue("ServerInstance/Region", "eu-west-1c")
    vm_params['RegionURL'] = ops.getValue("ServerInstance/RegionURL", "https://ec2.eu-west-1.amazonaws.com/")
    vm_params['PublicIP'] = ops.getValue("ServerInstance/PublicIP", "")
    return S_OK(vm_params)


class VMDBHandler(RequestHandler):

    types_registerInstance = [types.StringTypes, types.StringTypes, types.StringTypes]
    def export_registerInstance(self, instance_id, instance_type, instance_image):
        res = gVMDB.register_instance(instance_id, instance_type, instance_image)
        return res

    types_isAlive = [types.StringTypes, types.DictType]
    def export_isAlive(self, instance_id, instance_parameters):
        res = gVMDB.is_alive(instance_id, instance_parameters)
        return res

    types_isStopped = [types.StringTypes]
    def export_isStopped(self, instance_id):
        res = gVMDB.is_stopped(instance_id)
        return res

    types_status = [types.StringTypes]
    def export_status(self, instance_id):
        return gVMDB.status(instance_id)

    types_runningInstance = []
    def export_runningInstance(self):
        return gVMDB.running_instance()

    types_instanceProperties = [types.StringTypes]
    def export_instanceProperties(self, instance_id):
        return gVMDB.instance_properties(instance_id)

    types_startServerInstance = []
    def export_startServerInstance(self):
        """
        Start an EC2 instance using boto
        :return: S_OK
        """
        res = _get_vm_params()
        if not res['OK']:
            return res
        vm_params = res['Value']
        url = urlparse(vm_params['RegionURL'])
        _endpointHostname = url.hostname
        _port = url.port
        _path = url.path
        _regionName = vm_params['Region']
        _region = RegionInfo(name=_regionName, endpoint=_endpointHostname)
        __conn = boto.connect_ec2(aws_access_key_id=vm_params['AccessID'],
                                  aws_secret_access_key=vm_params['AccessKey'],
                                  is_secure=False, region=_region, path=_path,
                                  port=_port, debug=1)
        __vmImage = __conn.get_image(vm_params['AMI'])
        try:
            reservation = __vmImage.run(min_count=1,
                                        max_count=1,
                                        key_name=vm_params['Key'],
                                        security_groups=vm_params['SecurityGroup'],
                                        instance_type=vm_params['Type'])
        except Exception as error:
            self.log.error(error)
            return S_ERROR("Failed to start the image")
        idList = []
        failed_ids = []
        for instance in reservation.instances:
            res = gVMDB.register_instance(instance.id, vm_params['AMI'], vm_params['Type'])
            if not res['OK']:
                self.log.error("Issue with instance registration", res['Message'])
            instance.update()
            while instance.state != u'running':
                if instance.state == u'terminated':
                    self.log.error("New instance terminated while starting", "AMI: %s" % vm_params["AMI"])
                    res = gVMDB.is_stopped(instance.id)
                    if not res['OK']:
                        self.log.error("CCouldn't mark instance as stopped", res['Message'])
                    continue
                self.log.info("Sleeping for 10 secs for instance %s (current state %s)" % (instance, instance.state))
                time.sleep(10)
                instance.update()
                if instance.state != u'terminated':
                    self.log.info("Instance %s started" % instance.id)
            idList.append(instance.id)
            if not __conn.associate_address(instance.id, public_ip=vm_params['PublicIP']):
                self.log.error("Issue setting the elastic IP, will terminate the instance")
                res = gVMDB.is_stopped(instance.id)
                if not res['OK']:
                    self.log.error("CCouldn't mark instance as stopped", res['Message'])
                failed_ids.append(instance.id)
                idList.pop(instance.id)
        if failed_ids:
            __conn.terminate_instances(failed_ids)
        if not idList:
            return S_ERROR("No instance started.")
        return S_OK(idList)

    types_stopServerInstance = [list(types.StringTypes) + [types.ListType]]
    def export_stopServerInstance(self, instance_id):
        """
        Stop a server instance
        :param instance_id: instance ID
        :return: S_OK or S_ERROR if instance wasn't stopped
        """
        if not isinstance(instance_id, list):
            instance_id = [instance_id]
        instance_to_terminate = []
        for inst_id in instance_id:
            res = gVMDB.status(inst_id)
            if not res['OK']:
                self.log.error("Failed to get instance status, will ignore it.", res['Message'])
                continue
            if res['Value'] == "Running":
                instance_to_terminate.append(inst_id)
        res = _get_vm_params()
        if not res['OK']:
            return res
        vm_params = res['Value']
        url = urlparse(vm_params['RegionURL'])
        _endpointHostname = url.hostname
        _port = url.port
        _path = url.path
        _regionName = vm_params['Region']
        _region = RegionInfo(name=_regionName, endpoint=_endpointHostname)
        __conn = boto.connect_ec2(aws_access_key_id=vm_params['AccessID'],
                                  aws_secret_access_key=vm_params['AccessKey'],
                                  is_secure=False, region=_region, path=_path,
                                  port=_port, debug=1)
        if not __conn.terminate_instances(instance_to_terminate):
            return S_ERROR("Instance not terminated")
        res = gVMDB.is_stopped(instance_id)
        return res