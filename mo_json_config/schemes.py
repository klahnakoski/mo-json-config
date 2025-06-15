# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at https://www.mozilla.org/en-US/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#

import os

from mo_dots import get_attr
from mo_files import File
from mo_imports import delay_import
from mo_json import json2value
from mo_logs import Except, logger

from mo_json_config.convert import ini2value
from mo_future import mockable
from mo_json_config.ssm import get_ssm as _get_ssm

_replace_foreign_ref = delay_import("mo_json_config.expander._replace_foreign_ref")
_replace_locals = delay_import("mo_json_config.expander._replace_locals")

CAN_NOT_READ_FILE = "Can not read file {filename}"
DEBUG = False


@mockable
def _get_file(ref, path, url):

    if ref.path.startswith("~"):
        home_path = os.path.expanduser("~")
        if os.sep == "\\":
            home_path = "/" + home_path.replace(os.sep, "/")
        if home_path.endswith("/"):
            home_path = home_path[:-1]

        ref.path = home_path + ref.path[1::]
    elif not ref.path.startswith("/"):
        # CONVERT RELATIVE TO ABSOLUTE
        if ref.path[0] == ".":
            num_dot = 1
            while ref.path[num_dot] == ".":
                num_dot += 1

            parent = url.path.rstrip("/").split("/")[:-num_dot]
            ref.path = "/".join(parent) + ref.path[num_dot:]
        else:
            parent = url.path.rstrip("/").split("/")[:-1]
            ref.path = "/".join(parent) + "/" + ref.path

    path = ref.path if os.sep != "\\" else ref.path[1::].replace("/", "\\")

    try:
        DEBUG and logger.note("reading file {path}", path=path)
        content = File(path).read()
    except Exception as e:
        content = None
        logger.error(CAN_NOT_READ_FILE, filename=File(path).os_path, cause=e)

    try:
        new_value = json2value(content, params=ref.query, flexible=True, leaves=True)
    except Exception as e:
        e = Except.wrap(e)
        try:
            new_value = ini2value(content)
        except Exception:
            raise logger.error(CAN_NOT_READ_FILE, filename=path, cause=e)
    new_value = _replace_foreign_ref((new_value, path), ref)
    return new_value


def get_http(ref, doc_path, url):
    import requests

    params = url.query
    new_value = json2value(requests.get(str(ref)).text, params=params, flexible=True, leaves=True)
    return new_value


def _get_env(ref, doc_path, url):
    # GET ENVIRONMENT VARIABLES
    ref = ref.host
    raw_value = os.environ.get(ref)
    if not raw_value:
        logger.error("expecting environment variable with name {env_var}", env_var=ref)

    try:
        new_value = json2value(raw_value)
    except Exception as e:
        new_value = raw_value
    return new_value


def _get_keyring(ref, doc_path, url):
    try:
        import keyring
    except Exception:
        logger.error("Missing keyring: `pip install keyring` to use this feature")

    # GET PASSWORD FROM KEYRING
    service_name = ref.host
    if "@" in service_name:
        username, service_name = service_name.split("@")
    else:
        username = ref.query.username

    raw_value = keyring.get_password(service_name, username)
    if not raw_value:
        logger.error(
            "expecting password in the keyring for service_name={service_name} and username={username}",
            service_name=service_name,
            username=username,
        )

    try:
        new_value = json2value(raw_value)
    except Exception as e:
        new_value = raw_value
    return new_value


def _get_param(ref, doc_path, url):
    # GET PARAMETERS FROM url
    param = url.query
    new_value = param[ref.host]
    return new_value


def _get_value_from_fragment(ref, path, url):
    # REFER TO SELF
    frag = ref.fragment
    if frag[0] == ".":
        doc = (None, path)
        # RELATIVE
        for i, c in enumerate(frag):
            if c == ".":
                if not isinstance(doc, tuple):
                    logger.error("{frag|quote} reaches up past the root document", frag=frag)
                doc = doc[1]
            else:
                break
        new_value = get_attr(doc[0], frag[i::])
    else:
        # ABSOLUTE
        top_doc = path
        while isinstance(top_doc, tuple) and top_doc[1]:
            top_doc = top_doc[1]
        new_value = get_attr(top_doc[0], frag)
    new_value = _replace_locals((new_value, path), url)
    return new_value


def _nothing(ref, doc_path, url):
    return f"{{{ref}}}"


scheme_loaders = {
    "http": get_http,
    "https": get_http,
    "file": _get_file,
    "env": _get_env,
    "param": _get_param,
    "keyring": _get_keyring,
    "ssm": _get_ssm,
    "ref": _get_value_from_fragment,
    "scheme": _nothing,
}
