import mo_json_config

config = mo_json_config.get("https://github.com/klahnakoski/mo-json-config/blob/dev/tests/resources/simple.json")
assert config.test_key == "test_value"
