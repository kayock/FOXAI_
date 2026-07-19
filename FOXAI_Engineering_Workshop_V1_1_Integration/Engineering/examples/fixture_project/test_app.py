import unittest
import app


class TestApp(unittest.TestCase):
    def test_value(self) -> None:
        self.assertEqual(app.VALUE, 2)


if __name__ == "__main__":
    unittest.main()
