from portal.plugins.av_lta.utils import clean_nones
from portal.plugins.av_lta.utils import str_to_bool
from portal.utils.test_case import PortalBaseTestCase


class TestCleanNones(PortalBaseTestCase):
    def test_clean_nones_list(self):
        input_list = [1, None, 2, None, 3]
        expected_output = [1, 2, 3]
        self.assertEqual(clean_nones(input_list), expected_output)

    def test_clean_nones_nested_list(self):
        input_list = [1, [None, 2, None], 3]
        expected_output = [1, [2], 3]
        self.assertEqual(clean_nones(input_list), expected_output)

    def test_clean_nones_dict(self):
        input_dict = {"a": 1, "b": None, "c": 3}
        expected_output = {"a": 1, "c": 3}
        self.assertEqual(clean_nones(input_dict), expected_output)

    def test_clean_nones_nested_dict(self):
        input_dict = {"a": 1, "b": {"x": None, "y": 2}, "c": None}
        expected_output = {"a": 1, "b": {"y": 2}}
        self.assertEqual(clean_nones(input_dict), expected_output)

    def test_clean_nones_mixed_nested(self):
        input_data = {"a": 1, "b": [None, {"x": None, "y": 2}, 3], "c": None, "d": {"p": None, "q": [1, None, 3]}}
        expected_output = {"a": 1, "b": [{"y": 2}, 3], "d": {"q": [1, 3]}}
        self.assertEqual(clean_nones(input_data), expected_output)

    def test_clean_nones_non_container(self):
        self.assertEqual(clean_nones(42), 42)
        self.assertEqual(clean_nones("hello"), "hello")
        self.assertEqual(clean_nones(3.14), 3.14)
        self.assertEqual(clean_nones(True), True)


class TestStrToBool(PortalBaseTestCase):
    def test_boolean_inputs(self):
        self.assertTrue(str_to_bool(True))
        self.assertFalse(str_to_bool(False))

    def test_falsy_inputs(self):
        self.assertFalse(str_to_bool(""))
        self.assertFalse(str_to_bool(None))
        self.assertFalse(str_to_bool(0))

    def test_truthy_string_inputs(self):
        self.assertTrue(str_to_bool("true"))
        self.assertTrue(str_to_bool("t"))
        self.assertTrue(str_to_bool("yes"))
        self.assertTrue(str_to_bool("y"))
        self.assertTrue(str_to_bool("1"))
        self.assertTrue(str_to_bool("on"))

    def test_falsy_string_inputs(self):
        self.assertFalse(str_to_bool("false"))
        self.assertFalse(str_to_bool("f"))
        self.assertFalse(str_to_bool("no"))
        self.assertFalse(str_to_bool("n"))
        self.assertFalse(str_to_bool("0"))
        self.assertFalse(str_to_bool("off"))

    def test_case_insensitivity(self):
        self.assertTrue(str_to_bool("TRUE"))
        self.assertTrue(str_to_bool("True"))
        self.assertTrue(str_to_bool("YES"))
        self.assertTrue(str_to_bool("Yes"))
        self.assertTrue(str_to_bool("ON"))
        self.assertTrue(str_to_bool("On"))
