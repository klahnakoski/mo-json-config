import os
from unittest import TestCase

from mo_testing import add_error_reporting

from mo_json_config import configuration
from mo_json_config.expander import expand
from mo_testing.mocks import mock
from mo_json_config.schemes import _get_file

__all__ = ["configuration"]


@add_error_reporting
class TestWithDefault(TestCase):

    def setUp(self):
        self.default_config = {
            "host": "example.com",
            "port": 8080,
            "username": "user",
            "password": "pass123"
        }
        self.file_config = {
            "username": "file_user",
            "password": "file_pass"
        }

    def test_default_in_ref(self):
        global configuration

        with mock(_get_file, function=self.get_existing_file):
            config_data = expand({
                "host": "example.com",
                "port": 8080,
                "user_config": {"$ref": "#default_config", "$default": {"username": "default_user", "password": "default_pass"}}
            })

            configuration |= config_data
            self.assertEqual(configuration.userConfig.username, "default_user")
            self.assertEqual(configuration.userConfig.password, "default_pass")

    def test_file_ref_with_default(self):
        global configuration

        with mock(_get_file, function=self.get_existing_file):
            config_data = expand({
                "user_config": {"$ref": "file:///path/to/config.json", "$default": {"username": "default_user", "password": "default_pass"}}
            })
            configuration |= config_data
            self.assertEqual(configuration.userConfig.username, "file_user")
            self.assertEqual(configuration.userConfig.password, "file_pass")

    def test_file_ref_without_default(self):
        global configuration

        with mock(_get_file, function=self.get_existing_file):
            config_data = expand({
                "user_config": {"$ref": "file:///path/to/config.json"}
            })
            configuration.clear()
            configuration |= config_data
            self.assertEqual(configuration.userConfig.username, "file_user")
            self.assertEqual(configuration.userConfig.password, "file_pass")

    def test_env_ref_with_default(self):
        global configuration

        os.environ["TEST_ENV_VAR"] = "env_value"
        config_data = expand({
            "env_config": {"$ref": "env://TEST_ENV_VAR", "$default": "default_value"}
        })

        configuration |= config_data
        self.assertEqual(configuration.envConfig, "env_value")

    def test_env_ref_without_default(self):
        global configuration
        try:
            del os.environ["TEST_ENV_VAR"]
        except KeyError:
            pass
        config_data = expand({
            "env_config": {"$ref": "env://TEST_ENV_VAR", "$default": "default_value"}
        })

        configuration.clear().append(config_data)
        self.assertEqual(configuration.envConfig, "default_value")

    def get_existing_file(self, ref, path, url):
        return self.file_config if ref == "file:///path/to/config.json" else None
