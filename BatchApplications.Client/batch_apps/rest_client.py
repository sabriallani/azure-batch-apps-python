#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------

from batch_apps.exceptions import (
    RestCallException,
    AuthenticationException)

from .utils import (
    url_from_filename,
    filename_from_url)

try:
    import requests
    from oauthlib import oauth2

except:
    raise ImportError(
        "Cannot find installation of lib Requests. Please install.")

import json
import os

import logging
LOG = logging.getLogger('batch_apps')
RETRIES = 3

def _call(auth, *args, **kwargs):
    """Internal method to open Requests session"""

    try:
        conn_session = auth.get_session()
        conn_adptr = requests.adapters.HTTPAdapter(max_retries=RETRIES)
        conn_session.mount('https://', conn_adptr)

        LOG.info("About to make REST call with args {0}".format(args))
        LOG.debug("About to make REST call with kwargs {0}".format(kwargs))
        LOG.debug(
            "Opened requests session with max retries: {0}".format(RETRIES))

        resp = conn_session.request(*args, verify=True, **kwargs)

    except (requests.RequestException,
            oauth2.rfc6749.errors.OAuth2Error) as exp:

        raise RestCallException(
            type(exp),
            "An {type} error occurred: {error}".format(type=type(exp),
                                                       error=str(exp)),
            exp)

    else:
        LOG.debug("Request response received, status:{0}, headers:{1}, "
                  "encoding:{2}, content:{3}, request_headers:{4}".format(
                      resp.status_code,
                      resp.headers,
                      resp.encoding,
                      resp.content[0:100],
                      resp.request.headers))

        if resp.status_code == 200 or resp.status_code == 202:
            LOG.info(
                "Successful REST call with status: {0}".format(
                    resp.status_code))

            return resp

        elif resp.status_code == 400:
            msg = ("Invalid API request. Some of the supplied data is "
                   "incorrect or malformed.\nStatus {0}.\nServer: {1}".format(
                       resp.status_code,
                       resp.text))

            raise RestCallException(ValueError, msg, resp)

        elif resp.status_code == 401:
            msg = ("Authentication for this call failed, "
                   "please check your credentials")
            raise RestCallException(AuthenticationException, msg, resp)

        elif resp.status_code == 403:
            msg = "API call non-applicable.\nServer: {0}".format(resp.text)
            raise  RestCallException(None, msg, resp, silent=True)

        elif resp.status_code == 404:
            msg = ("Invalid endpoint or api call. Failed with status {0}.\n"
                   "Url: {1}".format(resp.status_code, resp.url))
            raise RestCallException(OSError, msg, resp)

        else:
            msg = "Call failed with status: {status}".format(
                status=resp.status_code)
            raise RestCallException(ValueError, msg, resp)

def get(auth, url, headers, params=None):
    """
    Call GET.

    :Args:
        - url (str): The complete endpoint url.
        - headers (dict): The headers to be used in the request.

    :Kwargs:
        - params (dict): Any additional parameters to be added to the uri as
            required by the specified call.

    :Returns:
        - The data retrieved by the GET call, after json decoding.

    :Raises:
        - :exc:`.RestCallException` is the call failed,
            or returned a non-200 status.
    """
    LOG.debug("Get call url: {0}, headers: {1}, params: "
              "{2}".format(url, headers, params))

    try:
        response = _call(auth, 'GET', url, headers=headers, params=params)
        return response.json()

    except RestCallException:
        raise

    except ValueError as exp:
        raise RestCallException(
            ValueError,
            "No json object to be decoded from GET call.",
            exp)

def head(auth, url, headers, filename=""):
    """
    Call HEAD.
    This call is only used to retrieve the content-length response
    header to get a file size.

    :Args:
        - url (str): The complete endpoint url.
        - headers (dict): The headers to be used in the request.

    :Kwargs:
        - filename (str): Used to add a filename to the end of the url if
            doesn't already have one. Default is an empty string.

    :Returns:
        - The content-length header, as an integer.

    :Raises:
        :exc:`.RestCallException` if the call failed, returned a non200 status,
        or the content-length header was not present in the response object.
    """
    try:
        url = url.format(name=url_from_filename(filename))
        LOG.debug("Head call url: {0}, headers: {1}".format(url, headers))
        response = _call(auth, 'HEAD', url, headers=headers)
        return int(response.headers["content-length"])

    except RestCallException:
        raise

    except KeyError as exp:
        raise RestCallException(KeyError,
                                "No content-length key in response headers.",
                                exp)

    except IndexError as exp:
        raise RestCallException(IndexError,
                                "Incorrectly formatted url supplied.",
                                exp)

def post(auth, url, headers, message=None):
    """
    Call to POST data to the Batch Apps service.
    Used for job submission, job commands and file queries.

    :Args:
        - url (str): The complete endpoint url.
        - headers (dict): The headers to be used in the request.

    :Kwargs:
        - message (dict): Data to be acted on e.g. job submission
            specfication, file query parameters. Format and contents will
            depend on the specific API call.

    :Returns:
        The data in the service response, after json decoding.

    :Raises:
        - :exc:`.RestCallException` is the call failed, or returned a
            non-200 status.
    """
    try:
        if message:
            message = json.dumps(message)

        LOG.debug("Post call url: {0}, headers: {1}, message: "
                  "{2}".format(url, headers, message))

        response = _call(auth, 'POST', url, headers=headers, data=message)
        return json.loads(response.text)

    except RestCallException:
        raise

    except (ValueError, TypeError) as exp:
        raise RestCallException(type(exp),
                                "No json object to be decoded from POST call.",
                                exp)

    except AttributeError as exp:
        raise RestCallException(AttributeError,
                                "Response object has no text attribute.",
                                exp)

def put(auth, url, headers, userfile, description, file_data):
    """
    Call PUT.
    This call is only used to upload files.

    :Args:
        - url (str): The complete endpoint url.
        - headers (dict): The headers to be used in the request.
        - userfile (:class:`.UserFile`): The :class:`.UserFile`
            reference of the file to be uploaded.
        - description (dict): The file data
        - file_data (dict): A dictionary containing the open file handle
            from which the data will be streamed.
            Format: ``{'Filename': open(file_path, 'rb')}``

    :Returns:
        - The raw server response.

    :Raises:
        - :exc:`.RestCallException` if the call failed or returned a
            non-200 status.
    """
    try:
        url = url.format(name=url_from_filename(userfile.name))

        put_headers = dict(headers)
        put_headers.pop("Content-Type")

        LOG.info("url={0}, headers={1}".format(url, put_headers))
        LOG.debug("Put call url: {0}, headers: {1}, "
                  "file: {2}, description: {3}".format(url,
                                                       put_headers,
                                                       userfile,
                                                       description))

        response = _call(auth,
                         'PUT',
                         url,
                         data=description,
                         files=file_data,
                         headers=put_headers)
        return response

    except RestCallException:
        raise

    except IndexError as exp:
        raise RestCallException(IndexError,
                                "Incorrectly formatted url supplied.",
                                exp)

def download(auth, url, headers, output_path, size, overwrite,
             f_name=None,
             ext=None,
             block_size=1024):
    """
    Call GET for a file stream.

    :Args:
        - url (str): The complete endpoint url.
        - headers (dict): The headers to be used in the request.
        - output_path (str): Full file path to download the data to.
        - size (int): File size of the file to be downloaded as retrieved
            by a HEAD request.
        - overwrite (bool): If ``True``, download the new data over an
            existing file.

    :Kwargs:
        - f_name (str): Used to specify a filename if one is not already
            included in the url. Default is ``None``.
        - ext (str): Used to specify a file extension if one is not already
            included in the url. Default is ``None``.
        - block_size (int): Used to vary the upload chunk size.
            Default is 1024 bytes.

    :Returns:
        - The raw server response.

    :Raises:
        - :exc:`.RestCallException` is the call failed, a file operation
            failed, or returned a non-200 status.
    """
    filename = filename_from_url(url, ext) if not f_name else f_name
    downloadfile = os.path.join(output_path, filename)

    if os.path.exists(downloadfile) and not overwrite:
        LOG.warning(
            "File {0} already exists. Not overwriting.".format(downloadfile))

        return True

    LOG.debug("Get call url: {0}, headers: {1}, file: "
              "{2}, size: {3}, overwrite: {4}".format(url,
                                                      headers,
                                                      downloadfile,
                                                      size,
                                                      overwrite))

    LOG.info("Starting download to {0}".format(downloadfile))

    if isinstance(size, int) and size > 0:
        percent_complete = float(0)
        LOG.info("Downloading...{0}%".format(int(percent_complete)))
        percent_incr = float(block_size/size*100)

    try:
        with open(downloadfile, "wb") as handle:
            response = _call(auth, 'GET', url, headers=headers, stream=True)

            for block in response.iter_content(block_size):
                if not block:
                    LOG.warning("Download complete")
                    break

                handle.write(block)

                if isinstance(size, int) and size > 0:
                    percent_complete += percent_incr
                    LOG.info("Downloading...{0}%".format(
                        min(100, int(percent_complete))))

            return response

    except RestCallException:
        raise

    except EnvironmentError as exp:
        raise RestCallException(type(exp), str(exp), exp)