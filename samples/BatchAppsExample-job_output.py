#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the MIT License (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------

"""
A sample script showing use of the batch_apps module to download the
output of a completed job.
"""

import getpass
import sys
import webbrowser

from batch_apps import (
    FileManager,
    JobManager,
    Credentials,
    Configuration)

from batch_apps.credentials import AzureOAuth

from batch_apps.exceptions import (
    AuthenticationException,
    RestCallException,
    InvalidConfigException)

LOG_LEVEL = "debug" 
DOWNLOAD_DIR = "C:\\Path\\To\\Download\\Directory"

def authentication(mode):
    """
    Authenticates a username against a stored password, if any, otherwise
    requires a password is to be entered.

    :Args:
        - cfg (:class:`.Configuration`): an instance of class Configuration as
          returned by create_config()

    :Returns:
        - a :class:`.Credentials` instance object
    """

    try:
        return AzureOAuth.get_session(config=mode)

    except (AuthenticationException, InvalidConfigException) as e:
        print("Could not get existing session: {0}".format(e))
        
    try:
        auth_url = AzureOAuth.get_authorization_url(config=mode)[0]
        webbrowser.open(auth_url)
        redirect_url = input("Please enter authentication url: ")
        return AzureOAuth.get_authorization_token(redirect_url,
                                                  config=mode,
                                                  state=None)

    except (AuthenticationException, InvalidConfigException) as e:
        print("Failed to get authorization: {0}".format(e))

def logging_mode():
    """
    Sets configuration to chosen log_level using existing congifuration setup.
    
    :Returns:
        - a :class:`.Configuration` instance object
    """

    global LOG_LEVEL

    if input("Run in debug mode? (yes/no)")[0].lower() == 'n':
        LOG_LEVEL = "info"

    try:
        return Configuration(log_level=LOG_LEVEL)

    except InvalidConfigException as e:
        print("Invalid Configuration: {0}".format(e))

def download_ouput(auth, config):
    """
    Downloads final job output as to specified location.

    :Args:
        - auth (:class:`.Credentials`): instance of the Credentials class
          as returned by authentication()
    """
    
    job_mgr = JobManager(auth, cfg=config)
    jobid = input("Please enter the job ID: ")

    try:
        job = job_mgr.get_job(jobid=jobid)
        print("Downloading output of {0} job called {1}".format(
            job.type, job.name))

        output = job.get_output(DOWNLOAD_DIR, overwrite=True)
        print("Job output successfully downloaded to: {0}".format(output))

    except RestCallException as exc:
        print("Download failed: {0}".format(exc.msg))

if __name__ == "__main__":
    mode = logging_mode()
    creds = authentication(mode)
    download_ouput(creds, mode)