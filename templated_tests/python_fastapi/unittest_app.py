import unittest

class TestMath(unittest.TestCase):
    
    def test_add(self):
        """Test the addition method."""
        self.assertEqual(1 + 1, 2)

    def test_subtract(self):
        """Test the subtraction method."""
        self.assertEqual(5 - 3, 2)

    def tearDown(self):
        """This method runs after each test."""
        # Clean up resources
        pass

if __name__ == '__main__':
    unittest.main()
