# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#
import os
from unittest import skipIf

import boto3
import keyring
from botocore.exceptions import ClientError
from mo_dots import Data
from mo_files import File
from mo_future import get_function_name, decorate
from mo_logs.exceptions import get_stacktrace
from mo_testing.fuzzytestcase import FuzzyTestCase, add_error_reporting
from mo_threads import stop_main_thread
from moto import mock_ssm

import mo_json_config
from mo_json_config import URL, ini2value
from mo_json_config import ssm as _ssm

IS_TRAVIS = os.environ.get("TRAVIS") or False


def add_throttling_errors(func):
    count = [0]
    func_name = get_function_name(func)

    @decorate(func)
    def output(*args, **kwargs):
        count[0] += 1
        if count[0] < 3:
            raise ClientError({"Error": {"Code": "ThrottlingException", "Message": "Rate limit exceeded"}}, func_name)
        else:
            return func(*args, **kwargs)

    return output


_boto_client = None


class ThrottlingSsm:
    def __init__(self, type):
        self.ssm = _boto_client("ssm")

    def put_parameter(self, Name, Value, Type):
        return self.ssm.put_parameter(Name=Name, Value=Value, Type=Type)

    @add_throttling_errors
    def get_parameter(self, Name, WithDecryption):
        return self.ssm.get_parameter(Name=Name, WithDecryption=WithDecryption)

    @add_throttling_errors
    def describe_parameters(self, **kwargs):
        return self.ssm.describe_parameters(**kwargs)


@add_error_reporting
class TestRef(FuzzyTestCase):
    def __init__(self, *args, **kwargs):
        FuzzyTestCase.__init__(self, *args, **kwargs)
        stack = get_stacktrace(0)
        this_file = stack[0]["file"]
        self.resources = "file://" + (File(this_file) / "../resources").abs_path

    @classmethod
    def tearDownClass(cls):
        stop_main_thread()

    def test_doc1(self):
        os.environ["test_variable"] = "abc"

        doc = mo_json_config.get(self.resources + "/test_ref1.json")

        self.assertEqual(doc.env_variable, "abc")
        self.assertEqual(doc.relative_file1, "*_ts")
        self.assertEqual(doc.relative_file2, "*_ts")
        self.assertEqual(doc.relative_doc, "value")
        self.assertEqual(doc.absolute_doc, "another value")
        self.assertEqual(doc.env_variable, "abc")
        self.assertEqual(
            doc.relative_object_doc, {"key": "new value", "another_key": "another value"},
        )

    def test_doc2(self):
        # BETTER TEST OF RECURSION
        doc = mo_json_config.get(self.resources + "/test_ref2.json")

        self.assertEqual(
            doc, {"a": "some_value", "test_key": "test_value", "b": {"test_key": "test_value"}, },
        )

    def test_empty_object_as_json_parameter(self):
        url = URL(self.resources + "/test_ref_w_parameters.json")
        url.query = {"metadata": Data()}
        result = mo_json_config.get(url)
        self.assertEqual(result, {}, "expecting proper parameter expansion")

    def test_json_parameter(self):
        url = URL(self.resources + "/test_ref_w_parameters.json")
        url.query = {"metadata": ["a", "b"]}
        result = mo_json_config.get(url)
        self.assertEqual(result, {"a": ["a", "b"]}, "expecting proper parameter expansion")

    def test_url_parameter_list(self):
        url = self.resources + "/test_ref_w_parameters.json?test1=a&test1=b&test2=c&test1=d"
        self.assertEqual(
            URL(url).query, {"test1": ["a", "b", "d"], "test2": "c"}, "expecting test1 to be an array",
        )

    def test_leaves(self):
        url = self.resources + "/test_ref_w_deep_parameters.json?&value.one.two=42"
        result = mo_json_config.get(url)
        self.assertEqual(result, {"a": {"two": 42}, "b": 42}, "expecting proper parameter expansion")

    def test_leaves_w_array(self):
        url = URL(self.resources + "/test_ref_w_deep_parameters.json")
        url.query = {"value": {"one": {"two": [{"test": 1}, {"test": 2}, "3"]}}}
        result = mo_json_config.get(url)
        expected = {
            "a": {"two": [{"test": 1}, {"test": 2}, "3"]},
            "b": [{"test": 1}, {"test": 2}, "3"],
        }
        self.assertEqual(result, expected, "expecting proper parameter expansion")

    def test_inner_doc(self):
        doc = mo_json_config.get(self.resources + "/inner.json")

        self.assertEqual(
            doc,
            {
                "area": {
                    "color": {"description": "css color"},
                    "border": {"properties": {"color": {"description": "css color"}}},
                },
                "definitions": {
                    "object_style": {
                        "color": {"description": "css color"},
                        "border": {"properties": {"color": {"description": "css color"}}},
                    },
                    "style": {"properties": {"color": {"description": "css color"}}},
                },
            },
            "expecting proper expansion",
        )

    @skipIf(IS_TRAVIS, "no home travis")
    def test_read_home(self):
        file = "~/___test_file.json"
        source = File.new_instance(get_stacktrace(0)[0]["file"], "../resources/simple.json")
        File.copy(File(source), File(file))
        content = mo_json_config.get("file:///" + file)

        try:
            self.assertEqual(content, {"test_key": "test_value"})
        finally:
            File(file).delete()

    def test_array_expansion(self):
        # BETTER TEST OF RECURSION
        doc = mo_json_config.get(self.resources + "/test_array.json")

        self.assertEqual(
            doc,
            {
                "a": "some_value",
                "list": {"deep": [
                    {"a": "a", "test_key": "test_value"},
                    {"a": "b", "test_key": "test_value"},
                    {"a": "c", "test_key": "test_value"},
                    {"a": "d", "test_key": "test_value"},
                    {"a": "e", "test_key": "test_value"},
                ]},
            },
        )

    def test_grandparent_reference(self):
        doc = mo_json_config.get(self.resources + "/child/grandchild/simple.json")

        self.assertEqual(doc, {"test_key": "test_value"})

    def test_params_simple(self):
        doc = {"a": {"$ref": "param://value"}}
        doc_url = "http://example.com/"
        result = mo_json_config.expand(doc, doc_url, {"value": "hello"})
        self.assertEqual(result, {"a": "hello"})

    def test_params_deep(self):
        doc = {"a": {"$ref": "param://value.name"}}
        doc_url = "http://example.com/"
        result = mo_json_config.expand(doc, doc_url, {"value": {"name": "hello"}})
        self.assertEqual(result, {"a": "hello"})

    def test_params_object(self):
        doc = {"a": {"$ref": "param://value"}}
        doc_url = "http://example.com/"
        result = mo_json_config.expand(doc, doc_url, {"value": {"name": "hello"}})
        self.assertEqual(result, {"a": {"name": "hello"}})

    def test_missing_env(self):
        doc = {"a": {"$ref": "env://DOES_NOT_EXIST"}}
        doc_url = "http://example.com/"
        self.assertRaises(Exception, mo_json_config.expand, doc, doc_url, {"value": {"name": "hello"}})

    @skipIf(IS_TRAVIS, "no keyring on travis")
    def test_keyring(self):
        keyring.set_password("example_service", "ekyle", "password")
        doc = {"a": {"$ref": "keyring://example_service?username=ekyle"}}
        doc_url = "http://example.com/"
        result = mo_json_config.expand(doc, doc_url)
        self.assertEqual(result, {"a": "password"})

    @skipIf(IS_TRAVIS, "no keyring on travis")
    def test_keyring_username(self):
        keyring.set_password("example_service", "ekyle", "password")
        doc = {"a": {"$ref": "keyring://ekyle@example_service"}}
        doc_url = "http://example.com/"
        result = mo_json_config.expand(doc, doc_url)
        self.assertEqual(result, {"a": "password"})

    def test_ssm(self):
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
        _ssm.has_failed = False
        with mock_ssm():
            ssm = boto3.client("ssm")
            ssm.put_parameter(Name="/services/graylog/host", Value="localhost", Type="String")
            ssm.put_parameter(Name="/services/graylog/port", Value="1220", Type="String")
            ssm.put_parameter(Name="/services/graylog1/port", Value="1220", Type="String")
            ssm.put_parameter(Name="/services/graylog2/port", Value="1220", Type="String")
            ssm.put_parameter(Name="/services/graylog3/port", Value="1220", Type="String")
            ssm.put_parameter(Name="/services/graylog4/port", Value="1220", Type="String")
            ssm.put_parameter(Name="/services/graylog5/port", Value="1220", Type="String")
            ssm.put_parameter(Name="/services/graylog6/port", Value="1220", Type="String")
            ssm.put_parameter(Name="/services/graylog7/port", Value="1220", Type="String")
            ssm.put_parameter(Name="/services/graylog8/port", Value="1220", Type="String")
            ssm.put_parameter(Name="/services/graylog9/port", Value="1220", Type="String")
            ssm.put_parameter(Name="/services/graylog0/port", Value="1220", Type="String")

            doc = {"services": {"$ref": "ssm:///services"}}
            result = mo_json_config.expand(doc, "http://example.com/")
            self.assertEqual(result, {"services": {"graylog": {"host": "localhost", "port": "1220"}}})

    def test_ssm_missing(self):
        _ssm.has_failed = False
        with mock_ssm():
            with self.assertRaises("No ssm parameters found at /services"):
                mo_json_config.get("ssm:///services")

    def test_ssm_unreachable(self):
        _ssm.has_failed = False
        result = mo_json_config.get("ssm:///services/tools")
        self.assertEqual(len(result), 0)

    def test_ini(self):
        temp = ini2value(File("tests/.coveragerc").read())
        self.assertEqual(
            temp,
            {
                "run": {"source": "./mo_json_config"},
                "report": {
                    "exclude_lines": """\npragma: no cover\nexcept Exception as\nexcept BaseException as\nLog.error\nlogger.error\nif DEBUG"""
                },
            },
        )

    def test_ssm_value(self):
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
        _ssm.has_failed = False
        print(mock_ssm)
        with mock_ssm():
            ssm = boto3.client("ssm")
            ssm.put_parameter(Name="/services/graylog/host", Value="localhost", Type="String")
            ssm.put_parameter(Name="/services/graylog/port", Value="1220", Type="String")

            doc = {"services": {"$ref": "ssm:///services/graylog/host"}}
            result = mo_json_config.expand(doc, "http://example.com/")
            self.assertEqual(result, {"services": "localhost"})

    def test_ssm_throttling(self):
        global _boto_client
        _ssm.RETRY_SECONDS = 0
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
        _ssm.has_failed = False
        with mock_ssm():
            try:
                _boto_client, boto3.client = boto3.client, ThrottlingSsm

                ssm = boto3.client("ssm")
                ssm.put_parameter(Name="/services/graylog/host", Value="localhost", Type="String")
                ssm.put_parameter(Name="/services/graylog/port", Value="1220", Type="String")

                doc = {"services": {"$ref": "ssm:///services/graylog/host"}}
                result = mo_json_config.expand(doc, "http://example.com/")
                self.assertEqual(result, {"services": "localhost"})
            finally:
                boto3.client = _boto_client

    @mock_ssm
    def test_ssm_prefix(self):
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
        _ssm.has_failed = False
        from mo_json_config import ssm

        ssm.call_counts = Data()

        client = boto3.client("ssm")
        for i in range(100):
            v = f"0{i}"[-2:]
            a, b = v
            client.put_parameter(Name=f"/services/graylog{a}/{b}/port", Value=str(1220 + i), Type="String")

        result = mo_json_config.get("ssm:///services/graylog3")
        self.assertEqual(ssm.call_counts["describe_parameters"], 2)

        self.assertEqual(
            result,
            {
                "0": {"port": "1250"},
                "1": {"port": "1251"},
                "2": {"port": "1252"},
                "3": {"port": "1253"},
                "4": {"port": "1254"},
                "5": {"port": "1255"},
                "6": {"port": "1256"},
                "7": {"port": "1257"},
                "8": {"port": "1258"},
                "9": {"port": "1259"},
            },
        )

    def test_env_var_in_string(self):
        os.environ["ENV"] = "test"
        doc = {"a": "this/is/a/path/{env://ENV}"}
        result = mo_json_config.expand(doc)
        expected = {"a": "this/is/a/path/test"}
        self.assertEqual(result, expected)

    def test_abs_ref_in_string(self):
        os.environ["ENV"] = "test"
        doc = {
            "a": {"b": "world"},
            "b": "hello {ref://#a.b}",
        }
        result = mo_json_config.expand(doc)
        expected = {
            "a": {"b": "world"},
            "b": "hello world",
        }
        self.assertEqual(result, expected)

    def test_rel_ref_in_string(self):
        os.environ["ENV"] = "test"
        doc = {
            "content": {"a": {"b": "world"}, "b": "hello {ref://#.a.b}"},
            "header": "universe",
        }
        result = mo_json_config.expand(doc)
        expected = {"content": {
            "a": {"b": "world"},
            "b": "hello world",
        }}
        self.assertEqual(result, expected)

    def test_rel_ref_in_string2(self):
        os.environ["ENV"] = "test"
        doc = {
            "content": {"a": {"b": "world"}, "b": "hello {ref://#..header}"},
            "header": "universe",
        }
        result = mo_json_config.expand(doc)
        expected = {
            "content": {"a": {"b": "world"}, "b": "hello universe"},
            "header": "universe",
        }
        self.assertEqual(result, expected)

    def test_concat(self):
        os.environ["ENV"] = "test"
        doc = {
            "a": {"b": "world"},
            "b": {"$concat": ["hello ", {"$ref": "#a.b"}]},
        }
        result = mo_json_config.expand(doc)
        expected = {
            "a": {"b": "world"},
            "b": "hello world",
        }
        self.assertEqual(result, expected)

    def test_ref_in_string_in_file(self):
        os.environ["TEST"] = "is-a-test"
        doc = mo_json_config.get(self.resources + "/test_ref_in_string.json")
        expected = {"test": "/resources/is-a-test/dir"}
        self.assertEqual(doc, expected)

    def test_ref_in_ref(self):
        os.environ["FILENAME"] = "simple"
        result = mo_json_config.get("file://tests/resources/test_ref3.json")
        expected = {'a': 'some_value', 'b': {'test_key': 'test_value'}, 'test_key': 'test_value'}
        self.assertEqual(result, expected)

    def test_ref_not_found(self):
        try:
            mo_json_config.get(self.resources + "/test_ref4.json")
            assert False, "should have raised an exception"
        except Exception as cause:
            self.assertIn("not found", cause)

    def test_ref_s3(self):
        found = list(mo_json_config.is_url.finditer("{s3://some_bucket/some_key}"))
        self.assertTrue(bool(found))

    def test_unknown(self):
        os.environ["ENV"] = "test"
        doc = {"content": "hello {blah://header}"}
        try:
            mo_json_config.expand(doc)
            assert False, "should have raised an exception"
        except Exception as cause:
            self.assertIn("unknown", cause)

    def test_ref_5(self):
        os.environ["FILE"] = "simple.json"
        doc = mo_json_config.get("file://resources/test_ref5.json")
        self.assertEqual(doc, {"a":{"test_key": "test_value"}, "b":{"test_key": "test_value"}})