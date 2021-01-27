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

import logging
import boto3

from citest.service_testing import base_agent

class S3FileUploadAgent(base_agent.BaseAgent):
    """Specialization to upload files to Amazon S3
    """
    def __init__(self, aws_profile=None, logger=None):
        super(S3FileUploadAgent, self).__init__(logger=logger)
        if aws_profile:
            self._aws_profile = aws_profile
        
        self._s3_resource = self._make_s3_resource()
        self.default_max_wait_secs = 600 # TODO: motivate this with real constraint

    def _make_s3_resource(self):
        # returns an object-oriented interface for interacting with S3
        # see https://boto3.amazonaws.com/v1/documentation/api/latest/guide/resources.html
        if self._aws_profile:
            session = boto3.Session(profile_name=self._aws_profile)
        else:
            session = boto3 # uses default cred chain on host - NOT RECOMMENDED

        try:
            return session.resource('s3')
        except:
            raise ValueError('Unable to instantiate S3 resource interface')
    
    def upload_string(self, bucket_name, upload_path, contents):
        """Uploads a string to a bucket at a relative upload path.
        """
        self._s3_resource.Object(bucket_name, upload_path).put(Body=contents)
        #TODO return s3 filepath to use in artifact


"""
TESTING
 [x] - invoke from ecs_server_group_test.py, comment out SG create/update
 [x] - ensure hardcoded contents is uploaded to specified file
 [x] - generate JSON contents from a class, ensure shows up in specified file
 [x] - use uploaded file as artifact
        -- result: OK, but python is wack



How GcsFileUploadAgent works:

- is instantiated by taking in creds (test binding) & logger (missing)
- instantiate client from creds or default
- set default_max_wait
- upload_string(bucket, path, contents) called by test helper mthd
    -- bucket: from a test binding
    -- path: upload destination/file name
    -- contents: generated manifest string 
- formatted into bound artifact, returned to deploy test



S3 string upload requirements:
- S3 client
    -- https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.put_object
- valid creds. From.. observer, or other?


???
- is there any S3 client instantiation in this pkg anywhere?
    -- no. Other AWS boto clients though, via observer profile
- what is S3 behavior if folder in bucket doesn't exist but path contains args?
- how to create boto3 s3 resource w/ named profile?

"""