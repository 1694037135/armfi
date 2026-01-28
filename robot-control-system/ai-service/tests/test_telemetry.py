import math
import unittest

# Import parser from main; side effects (FastAPI app init) are acceptable for tests
from main import _parse_serial_line


class TestTelemetryParser(unittest.TestCase):
    def test_json_angles_deg(self):
        line = '{"angles_deg": [0, 45.5, -30, 90, 0, 10], "error_code": 7}'
        parsed = _parse_serial_line(line)
        self.assertIsNotNone(parsed)
        self.assertEqual(
            parsed["angles_deg"],
            [0.0, 45.5, -30.0, 90.0, 0.0, 10.0],
        )
        self.assertEqual(parsed["error_code"], 7)

    def test_json_angles_rad_converts_to_deg(self):
        radians = [0.0, math.pi / 2, -math.pi / 4, math.pi, 0.0, math.pi / 6]
        line = '{"angles_rad": %s}' % str(radians).replace("'", "")
        parsed = _parse_serial_line(line)
        self.assertIsNotNone(parsed)
        expected = [0.0, 90.0, -45.0, 180.0, 0.0, 30.0]
        for value, exp in zip(parsed["angles_deg"], expected):
            if value is None:
                self.fail("Expected numeric value, got None")
            self.assertAlmostEqual(value, exp, places=5)

    def test_csv_line(self):
        line = "10, 20, 30, 40, 50, 60, 3"
        parsed = _parse_serial_line(line)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["angles_deg"], [10.0, 20.0, 30.0, 40.0, 50.0, 60.0])
        self.assertEqual(parsed["error_code"], 3)

    def test_invalid_csv_returns_none(self):
        self.assertIsNone(_parse_serial_line("10,20,30"))

    def test_empty_line_returns_none(self):
        self.assertIsNone(_parse_serial_line("\n"))


if __name__ == "__main__":
    unittest.main()
