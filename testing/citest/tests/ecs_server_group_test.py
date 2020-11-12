# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Smoke test to see if Spinnaker can interoperate with Amazon ECS.
"""

# Standard python modules.
import sys, os

# citest modules.
import citest.aws_testing as aws
import citest.json_contract as jc
import citest.json_predicate as jp
import citest.service_testing as st
import citest.base
from citest.json_contract import ObservationPredicateFactory
ov_factory = ObservationPredicateFactory()

# Spinnaker modules.
import spinnaker_testing as sk
import spinnaker_testing.gate as gate

from botocore.exceptions import (BotoCoreError, ClientError)

class EcsServerGroupTestScenario(sk.SpinnakerTestScenario):
  """
  Defines the scenario for the ECS server group test.
  """

  @classmethod
  def new_agent(cls, bindings):
    """Implements citest.service_testing.AgentTestScenario.new_agent."""
    return gate.new_agent(bindings)
  
  @classmethod
  def initArgumentParser(cls, parser, defaults=None):
    """Initialize command line argument parser.

    Args:
      parser: argparse.ArgumentParser
    """
    super(EcsServerGroupTestScenario, cls).initArgumentParser(
        parser, defaults=defaults)
    #TODO: use custom args for artifact values

    parser.add_argument(
        '--test_ecs_artifact_account',
        default='ecs-artifact-account',
        help='Spinnaker ECS artifact account name to use for test operations'
             ' against artifacts stored in S3.')

    parser.add_argument(
        '--test_ecs_bucket',
        help='S3 bucket to upload & read task defintions from.')

  def __init__(self, bindings, agent=None):
    """Constructor.

    Args:
      bindings: [dict] The data bindings to use to configure the scenario.
      agent: [GateAgent] The agent for invoking the test operations on Gate.
    """
    super(EcsServerGroupTestScenario, self).__init__(bindings, agent)
    bindings = self.bindings

    aws_observer = self.aws_observer # TODO: specific additional permissions for profile
    self.ecs_client = aws_observer.make_boto_client('ecs')

    # We'll call out the app name because it is widely used
    # because it scopes the context of our activities.
    # pylint: disable=invalid-name
    self.TEST_APP = bindings['TEST_APP']
    self.TEST_STACK = bindings['TEST_STACK']
    self.SERVER_GROUP_NAME = self.TEST_APP + '-' + self.TEST_STACK + '-v000'
    self.ECS_CLUSTER = "spinnaker-deployment-cluster"
    
    # test values. TODO: configure accounts w/ Halyard
    self.ECS_TEST_ACCT = "ecs-my-aws-devel-acct"  # self.bindings['SPINNAKER_ECS_ACCOUNT']
    self.TEST_REGION = "ca-central-1" # self.bindings['TEST_AWS_REGION']
    self.TEST_TARGET_GROUP = 'hello-nlb-1'
    self.ECR_ACCOUNT_NAME = "my-ca-central-1-devel-registry"
    self.ECR_URI = '679273379347.dkr.ecr.ca-central-1.amazonaws.com'
    self.ECR_REGISTRY = "https://" + self.ECR_URI
    self.ECR_REPOSITORY = "https://" + self.ECR_URI + "/nyancat"
    self.ECR_IMAGE_ID = self.ECR_URI + "/nyancat:latest"

  
  def __s3_file_expected_artifact(self):
    # upload file to s3
    dir_path = os.path.dirname(os.path.realpath(__file__))
    # TODO: upload JSON file stored in this repo, return artifact values
  
  
  def create_app(self):
    """Creates OperationContract that creates a new Spinnaker Application."""
    contract = jc.Contract()
    return st.OperationContract(
        self.agent.make_create_app_operation(
            bindings=self.bindings, application=self.TEST_APP,
            account_name=self.ECS_TEST_ACCT,
            cloud_providers="aws,ecs"),
        contract=contract)
    
  
  def delete_app(self):
    """Creates OperationContract that deletes a new Spinnaker Application."""
    contract = jc.Contract()
    return st.OperationContract(
        self.agent.make_delete_app_operation(
            application=self.TEST_APP,
            account_name=self.ECS_TEST_ACCT),
        contract=contract)


  def create_server_group(self):
    # TODO: can we create SG with in-line artifact,
    # or do we need to save a pipeline w/ an expected artifact?

    job = [{
      'account': self.ECS_TEST_ACCT,
      'application': self.TEST_APP,
      'availabilityZones': {
        self.TEST_REGION : [self.TEST_REGION + 'a', self.TEST_REGION + 'b']
      },
      'capacity': {
        'min': 1,
        'max': 2,
        'desired': 1
      },
      'cloudProvider': 'ecs',
      'ecsClusterName': self.ECS_CLUSTER,
      'stack': self.TEST_STACK,
      'credentials': self.ECS_TEST_ACCT,
      'launchType': 'FARGATE',
      'networkMode': 'awsvpc',
      'targetSize': 1,
      'computeUnits': 256,
      'healthCheckType': 'EC2',
      'imageDescription': {
        'account': self.ECR_ACCOUNT_NAME,
        "imageId": self.ECR_IMAGE_ID,
        "registry": self.ECR_REGISTRY,
        "repository": self.ECR_REPOSITORY,
        "tag": "latest"
      },
      'reservedMemory': 512,
      'subnetType': 'private-subnet', # needs to be tagged in target VPC
      'securityGroupNames': ['spinnaker-ecs-demo-public-access','spinnaker-ecs-demo-private-access'],
      'type': 'createServerGroup',
      'user': 'integration-tests',
      'targetGroupMappings': [{ 
        #'containerName': 'test', # should match containerName in task def artifact
        'containerPort': 80,
        'targetGroup': self.TEST_TARGET_GROUP 
      }],
      'placementStrategySequence': []
      #'iamRole': 'SpinnakerManagedCA', # required to use ECR
      #'useTaskDefinitionArtifact': 'false',
      #'taskDefinitionArtifact': {'artifactId': values_expected_artifact },
      #'taskDefinitionArtifactAccount': 'SPINNAKER_ECS_ARTIFACT_ACCOUNT',
      #'containerMappings': [{}] # map container name to image
    }]

    payload = self.agent.make_json_payload_from_kwargs(
      job=job,
      application=self.TEST_APP,
      description='Create Server Group in ' + self.SERVER_GROUP_NAME)
    
    builder = aws.AwsPythonContractBuilder(self.aws_observer)
    (builder.new_clause_builder('ECS service created',
                                retryable_for_secs=200)
     .call_method(
         self.ecs_client.describe_services,
         services=[self.SERVER_GROUP_NAME],cluster='spinnaker-deployment-cluster')
     .EXPECT(
         ov_factory.value_list_path_contains(
             'services',
             jp.LIST_MATCHES([jp.DICT_MATCHES({'serviceName': jp.STR_EQ(self.TEST_APP + '-ecstest-v000')})]))
     ))

    print("\n ---- ASTEST| CSG payload...")
    print(payload)

    return st.OperationContract(
        self.new_post_operation(
            title='create_server_group', data=payload, path='tasks'),
        contract=builder.build())

  def resize_server_group(self):
    #serverGroupName = self.TEST_APP + '-ecstest-v000'
    job = [{
      'cloudProvider': 'ecs',
      'serverGroupName': self.SERVER_GROUP_NAME,
      'region': self.TEST_REGION,
      'type': 'resizeServerGroup',
      'stack': self.TEST_STACK,
      'capacity': {
        'min': 0,
        'max': 2,
        'desired': 2
      },
      'credentials': self.ECS_TEST_ACCT,
      'user': 'integration-tests'
    }]

    payload = self.agent.make_json_payload_from_kwargs(
      job=job,
      application=self.TEST_APP,
      description='ResizeServerGroup: ' + self.SERVER_GROUP_NAME)

    print("\n ---- ASTEST| Resize SG payload...")
    print(payload)

    builder = aws.AwsPythonContractBuilder(self.aws_observer)
    # find named service w/ running count = 2
    (builder.new_clause_builder('ECS service scaled up',
                                retryable_for_secs=400)
     .call_method(
         self.ecs_client.describe_services,
         services=[self.SERVER_GROUP_NAME],cluster='spinnaker-deployment-cluster')
     .EXPECT(
         ov_factory.value_list_path_contains(
             'services',
             jp.LIST_MATCHES([
               jp.DICT_MATCHES({'runningCount': jp.NUM_EQ(2)})])))
      )

    return st.OperationContract(
        self.new_post_operation(
            title='resize_server_group', data=payload, path='tasks'),
        contract=builder.build())


  def disable_server_group(self):
    #serverGroupName = self.TEST_APP + '-ecstest-v000' #'%s-%s' % (self.__cluster_name, version)
    job = [{
      'cloudProvider': 'ecs',
      'serverGroupName': self.SERVER_GROUP_NAME,
      'region': self.TEST_REGION,
      'type': 'disableServerGroup',
      'credentials': self.ECS_TEST_ACCT, #self.bindings['SPINNAKER_ECS_ACCOUNT'],
      'user': 'integration-tests'
    }]

    payload = self.agent.make_json_payload_from_kwargs(
      job=job,
      application=self.TEST_APP,
      description='DisableServerGroup: ' + self.SERVER_GROUP_NAME)

    print("\n ---- ASTEST| Disable SG payload...")
    print(payload)

    builder = aws.AwsPythonContractBuilder(self.aws_observer)
    # look for 'running' = 0
    (builder.new_clause_builder('ECS service scaled to 0',
                                retryable_for_secs=600)
     .call_method(
         self.ecs_client.describe_services,
         services=[self.SERVER_GROUP_NAME],cluster='spinnaker-deployment-cluster')
     .EXPECT(
         ov_factory.value_list_path_contains(
             'services',
             jp.LIST_MATCHES([
               jp.DICT_MATCHES({'runningCount': jp.NUM_EQ(0)})])))
      )

    return st.OperationContract(
        self.new_post_operation(
            title='disable_server_group', data=payload, path='tasks'),
        contract=builder.build())


  def destroy_server_group(self):
    #serverGroupName = self.TEST_APP + '-ecstest-v000' #'%s-%s' % (self.__cluster_name, version)
    job = [{
      'cloudProvider': 'ecs',
      'serverGroupName': self.SERVER_GROUP_NAME,
      'region': self.TEST_REGION,
      'type': 'destroyServerGroup',
      'credentials': self.ECS_TEST_ACCT, #self.bindings['SPINNAKER_ECS_ACCOUNT'],
      'user': 'integration-tests'
    }]
    
    payload = self.agent.make_json_payload_from_kwargs(
      job=job,
      application=self.TEST_APP,
      description='DestroyServerGroup: ' + self.SERVER_GROUP_NAME)

    print("\n ---- ASTEST| DSG payload...")
    print(payload)

    builder = aws.AwsPythonContractBuilder(self.aws_observer)
    # maybe also look for 'failures':{'reason':'MISSING'} ?
    (builder.new_clause_builder('ECS service deleted',
                                retryable_for_secs=600)
     .call_method(
         self.ecs_client.describe_services,
         services=[self.SERVER_GROUP_NAME],cluster='spinnaker-deployment-cluster')
     .EXPECT(
         ov_factory.value_list_path_contains(
             'services',
             jp.LIST_MATCHES([
               jp.DICT_MATCHES({'status': jp.STR_SUBSTR('INACTIVE')})])))
     .OR(
        ov_factory.value_list_path_contains(
            'services',
            jp.LIST_MATCHES([
              jp.DICT_MATCHES({'status': jp.STR_SUBSTR('inactive')})])))
     )

    return st.OperationContract(
        self.new_post_operation(
            title='delete_server_group', data=payload, path='tasks'),
        contract=builder.build())

class EcsServerGroupTest(st.AgentTestCase):
  """The test fixture for the EcsServerGroupTest.

  This is implemented using citest OperationContract instances that are
  created by the EcsServerGroupTestScenario.
  """
  # pylint: disable=missing-docstring

  @property
  def scenario(self):
    return citest.base.TestRunner.global_runner().get_shared_data(
      EcsServerGroupTestScenario)

  def test_a_create_app(self):
    self.run_test_case(self.scenario.create_app())

  def test_b_create_server_group(self):
    self.run_test_case(self.scenario.create_server_group())

  def test_c_resize_server_group(self):
    self.run_test_case(self.scenario.resize_server_group())

  #def test_d_clone_server_group(self):... ?

  def test_d_disable_server_group(self):
    self.run_test_case(self.scenario.disable_server_group())

  def test_e_destroy_server_group(self):
    self.run_test_case(self.scenario.destroy_server_group(),
                      poll_every_secs=5)

  def test_z_delete_app(self):
    # Give a total of 2 minutes because it might also need
    # an internal cache update
    self.run_test_case(self.scenario.delete_app(),
                       retry_interval_secs=8, max_retries=15)


def main():
  """Implements the main method running this ecs test."""

  defaults = {
      'TEST_STACK': 'ecstest',
      'TEST_APP': 'smoketestECS' + EcsServerGroupTestScenario.DEFAULT_TEST_ID
  }

  return citest.base.TestRunner.main(
      parser_inits=[EcsServerGroupTestScenario.initArgumentParser],
      default_binding_overrides=defaults,
      test_case_list=[EcsServerGroupTest])

if __name__ == '__main__':
  sys.exit(main())