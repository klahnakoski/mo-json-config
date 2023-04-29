import os

from mo_future import first
from mo_testing.fuzzytestcase import FuzzyTestCase

import mo_json_config
from mo_json_config import Configuration


class TestConfiguration(FuzzyTestCase):
    def test_config(self):
        configuration = mo_json_config.configuration
        configuration |= {
            "thisIsATest": "A",
            "another.test": "B",
            "also-a_test999": "C",
            "BIG_WORDS": "D",
        }

        self.assertEqual(configuration.this_is.a.test, "A")
        self.assertEqual(configuration["anotherTest"], "B")
        self.assertEqual(configuration["ALSO_A_TEST999"], "C")
        self.assertEqual(configuration["bigWords"], "D")

        self.assertEqual(
            dict(configuration),
            {
                "this.is.a.test":"A",
                "another.test": "B",
                "also.a.test999": "C",
                "big.words": "D"
            },
        )

        a = configuration.another
        with self.assertRaises("another"):
            b = a.not_exists

        add = configuration.this | {"is": {"not": {"a": {"test": 42}}}}
        self.assertEqual(add.is_not.a.test, 42)

    def test_config_prepend(self):
        configuration = mo_json_config.configuration
        configuration.prepend({
            "thisIsATest": "A",
            "another.test": "B",
            "also-a_test999": "C",
            "BIG_WORDS": "D",
        })
        configuration.prepend({"thisIs_a_test": "B"})

        self.assertEqual(configuration.this.is_a.test, "B")

    def test_env(self):
        c = Configuration({})
        c |= os.environ

        key, value = first(os.environ.items())

        self.assertEqual(c[key], value)



