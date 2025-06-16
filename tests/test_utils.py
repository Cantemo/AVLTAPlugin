from portal.plugins.av_lta.utils import clean_nones
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
        input_data = {
            "a": 1,
            "b": [None, {"x": None, "y": 2}, 3],
            "c": None,
            "d": {"p": None, "q": [1, None, 3]}
        }
        expected_output = {
            "a": 1,
            "b": [{"y": 2}, 3],
            "d": {"q": [1, 3]}
        }
        self.assertEqual(clean_nones(input_data), expected_output)

    def test_clean_nones_non_container(self):
        self.assertEqual(clean_nones(42), 42)
        self.assertEqual(clean_nones("hello"), "hello")
        self.assertEqual(clean_nones(3.14), 3.14)
        self.assertEqual(clean_nones(True), True)
