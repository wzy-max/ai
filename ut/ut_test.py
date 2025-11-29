import unittest

from dao import knowlege_base_dao
from service import  retrieve_service


class TestMath(unittest.TestCase):
    def test_get(self):
        self.assertIsNotNone(knowlege_base_dao.get_knowledeg_base_list('raw'))
    
    def test_retrieve(self):
        self.assertIsNotNone(retrieve_service.retrieve("what is Apple"))

if __name__ == "__main__":
    unittest.main()