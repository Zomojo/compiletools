from __future__ import print_function
import unittest
import utils


class TestOrderedSet(unittest.TestCase):

    def test_initialization(self):
        s1 = utils.OrderedSet([5, 4, 3, 2, 1])
        self.assertEqual(len(s1), 5)
        self.assertTrue(3 in s1)
        self.assertFalse(6 in s1)

    def test_add_uniqueness(self):
        # Create and test expected elements
        s1 = utils.OrderedSet(["five", "four", "three", "two", "one"])
        self.assertEqual(len(s1), 5)
        self.assertIn("four", s1)
        self.assertIn("two", s1)

        # Re-add existing elements and check that nothing occured
        s1.add("four")
        s1.add("two")
        self.assertEqual(len(s1), 5)
        self.assertIn("four", s1)
        self.assertIn("two", s1)

        # Add a new entry and verify it is at the end
        s1.add("newentry")
        self.assertEqual(len(s1), 6)
        self.assertIn("newentry", s1)
        s2 = utils.OrderedSet(
            ["five", "four", "three", "two", "one", "newentry"])
        self.assertEqual(s1, s2)

if __name__ == '__main__':
    unittest.main()
