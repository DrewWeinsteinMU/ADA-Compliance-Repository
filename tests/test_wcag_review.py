import unittest
from wcag_review import CRITERIA,framework_report
class FrameworkTests(unittest.TestCase):
    def test_complete_inventory_and_statuses(self):
        self.assertEqual(len(CRITERIA),86)
        ids={c['id'] for c in CRITERIA}
        self.assertEqual(len(ids),86)
        self.assertNotIn('4.1.1',ids)
        for id in ['1.1.1','1.4.3','2.4.11','2.5.8','3.3.8','4.1.3']:self.assertIn(id,ids)
        report=framework_report()
        self.assertIn('NOT AUTOMATICALLY TESTED',report)
        self.assertIn('PARTIAL AUTOMATION',report)
        self.assertIn('not evidence',report)
