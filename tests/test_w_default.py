import unittest
from unittest import TestCase

import mo_json_config
from mo_json_config import configuration


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

        config_data = {
            "host": "example.com",
            "port": 8080,
            "user_config": {"$ref": "#default_config", "$default": {"username": "default_user", "password": "default_pass"}}
        }

        configuration |= config_data
        self.assertEqual(configuration.userConfig.username, "default_user")
        self.assertEqual(configuration.userConfig.password, "default_pass")

    def test_file_ref_with_default(self):
        global configuration

        # Mocking file read
        mo_json_config.get = lambda url: self.file_config if url == "file:///path/to/config.json" else None

        config_data = {
            "user_config": {"$ref": "file:///path/to/config.json", "$default": {"username": "default_user", "password": "default_pass"}}
        }

        configuration |= config_data
        self.assertEqual(configuration.userConfig.username, "file_user")
        self.assertEqual(configuration.userConfig.password, "file_pass")

    def test_file_ref_without_default(self):
        # Mocking file read
        mo_json_config.get = lambda url: self.file_config if url == "file:///path/to/config.json" else None

        config_data = {
            "user_config": {"$ref": "file:///path/to/config.json"}
        }

        configuration |= config_data
        self.assertEqual(configuration.userConfig.username, "file_user")
        self.assertEqual(configuration.userConfig.password, "file_pass")

    def test_env_ref_with_default(self):
        import os
        os.environ["TEST_ENV_VAR"] = "env_value"
        config_data = {
            "env_config": {"$ref": "env://TEST_ENV_VAR", "$default": "default_value"}
        }

        configuration |= config_data
        self.assertEqual(configuration.envConfig, "env_value")

    def test_env_ref_without_default(self):
        import os
        del os.environ["TEST_ENV_VAR"]
        config_data = {
            "env_config": {"$ref": "env://TEST_ENV_VAR", "$default": "default_value"}
        }

        configuration |= config_data
        self.assertEqual(configuration.envConfig, "default_value")
