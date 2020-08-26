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
Currently a NON-FUNCTIONAL DESIGN AID which aspires to work.
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
    self.ECS_CLUSTER = 'TEST_ECS_CLUSTER'  # not sure if needed here

  def create_app(self):
    """Creates OperationContract that creates a new Spinnaker Application."""
    contract = jc.Contract()
    return st.OperationContract(
        self.agent.make_create_app_operation(
            bindings=self.bindings, application=self.TEST_APP,
            account_name=self.bindings['SPINNAKER_ECS_ACCOUNT'],
            cloud_providers="aws,ecs"),
        contract=contract)
    
  def delete_app(self):
    """Creates OperationContract that deletes a new Spinnaker Application."""
    contract = jc.Contract()
    return st.OperationContract(
        self.agent.make_delete_app_operation(
            application=self.TEST_APP,
            account_name=self.bindings['SPINNAKER_ECS_ACCOUNT']),
        contract=contract)

  def __s3_file_expected_artifact(self):
    # upload file to s3
    dir_path = os.path.dirname(os.path.realpath(__file__))
    # TODO: upload JSON file stored in this repo, return artifact values


  def create_server_group(self):
    # TODO: can we create SG with in-line artifact,
    # or do we need to save a pipeline w/ an expected artifact?
    values_expected_artifact = self.__s3_file_expected_artifact('ECS_ARTIFACT')
    job = [{
      'account': self.bindings['SPINNAKER_ECS_ACCOUNT'],
      'application': self.TEST_APP,
      'availabilityZones': {
        self.TEST_REGION: [self.TEST_ZONE]
      },
      'capacity': {
        'min': 1,
        'max': 1,
        'desired': 1
      },
      'cloudProvider': 'ecs',
      'ecsClusterName': self.ECS_CLUSTER,
      'stack': self.TEST_STACK,
      'credentials': self.bindings['SPINNAKER_ECS_ACCOUNT'],
      'launchType': 'FARGATE',
      'networkMode': 'awsvpc',
      'targetSize': 1,
      'computeUnits': 256,
      'healthCheckType': 'EC2',
      'iamRole': self.ECS_EXECUTION_ROLE, # required to use ECR
      'imageDescription': { # for reference; use w/ 'containerMappings'
        'account': "SPINNAKER_ECR_REGISTRY_ACCOUNT",
        "imageId": "SPINNAKER_ECR_REGISTRY/spinnaker-deployment-images:nginx",
        "registry": "SPINNAKER_ECR_REGISTRY",
        "repository": "SPINNAKER_DOCKER_REPO",
        "tag": "TAG"
      },
      'reservedMemory': 512,
      'subnetType': 'public-subnet', # needs to be tagged in target VPC
      'securityGroupNames': [], # required for FARGATE
      'type': 'createServerGroup',
      'user': 'integration-tests',
      'useTaskDefinitionArtifact': 'true',
      'targetGroupMappings': [{ 
        'containerName': 'test', # should match containerName in task def artifact
        'containerPort': 80,
        'targetGroup': 'test-targetgroup-name' # should match LB in account 
      }],
      'taskDefinitionArtifact': {
        'artifactId': values_expected_artifact 
      },
      'taskDefinitionArtifactAccount': 'SPINNAKER_ECS_ARTIFACT_ACCOUNT',
      'containerMappings': [{}] # map container name to image
    }]
    job[0].update(self.__mig_payload_extra)

    ## TODO: validate service existing in ECS w/ observer

  def destroy_server_group(self, version):
    serverGroupName = '%s-%s' % (self.__cluster_name, version)
    job = [{
      'cloudProvider': 'ecs',
      'serverGroupName': serverGroupName,
      'region': self.TEST_REGION,
      'type': 'destroyServerGroup',
      'credentials': self.bindings['SPINNAKER_ECS_ACCOUNT'],
      'user': 'integration-tests'
    }]
    job[0].update(self.__mig_payload_extra)

    ## TODO: validate service existing in ECS w/ observer

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

  #def test_c_resize_server_group(self):...

  #def test_d_clone_server_group(self):...

  #def test_e_disable_server_group(self):

  def test_c_destroy_server_group(self):
    self.run_test_case(self.scenario.destroy_server_group('v000'), 
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
      'TEST_APP': 'smoketest' + EcsServerGroupTestScenario.DEFAULT_TEST_ID
  }

  return citest.base.TestRunner.main(
      parser_inits=[EcsServerGroupTestScenario.initArgumentParser],
      default_binding_overrides=defaults,
      test_case_list=[EcsServerGroupTest])

if __name__ == '__main__':
  sys.exit(main())