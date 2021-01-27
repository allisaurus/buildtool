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

import json

class EcsTaskDefinitionFactory(object):
    """Utilities for generating ECS Task Definitions"""

    def __init__(self, scenario):
        self.scenario = scenario

    def get_fargate_task_def_json(self, container_name='test'):
        # for info on available fields, see:
        # https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_RegisterTaskDefinition.html
        
        body = {
            "requiresCompatibilities": [
                "FARGATE"
            ],
            "networkMode": "awsvpc",
            "cpu": "256",
            "memory": "512",
            "family": self.scenario.TEST_APP,
            "containerDefinitions": [
                {
                    "name": container_name,
                    "image": "TO_BE_REPLACED_BY_SPINNAKER",
                    "essential": "true",
                    "portMappings": [
                        {
                            "hostPort": 80,
                            "protocol": "tcp",
                            "containerPort": 80
                        }
                    ],
                    "environment": [
                        {
                            "name": "citest-app",
                            "value": self.scenario.TEST_APP
                        }
                    ]
                }
            ]
        }

        return json.dumps(body)