import unittest
import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skills import RobotSkills
from advanced_ik import AdvancedIKController

# Mock AdvancedIKController to avoid effectively initializing it (though it's lightweight)
# or just use the real one since it's logic-based. The real one requires numpy and ikpy.
# We'll use the real one for integration testing logic, but mock if needed.
# For this test, let's use the real one to ensure end-to-end logic works.

class TestRobotSkills(unittest.TestCase):
    def setUp(self):
        # Initialize RobotSkills with a real IK controller
        # Note: AdvancedIKController init might try to load URDF. 
        # If URDF is missing in test env, this might fail. 
        # But we are in the same repo, so it should work if paths are correct in advanced_ik.py.
        try:
            self.skills = RobotSkills()
        except Exception as e:
            self.fail(f"Failed to initialize RobotSkills: {e}")

    def test_control_joint_valid(self):
        """Test valid joint control"""
        current = [0, 0, 0, 0, 0, 0]
        # Rotate Joint 1 to 90 degrees
        result = self.skills.control_joint(1, 90, current)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['mode'], 'work')
        self.assertEqual(result['action'], 'control_joint')
        self.assertAlmostEqual(result['angles']['joint1'], 90)
        self.assertAlmostEqual(result['angles']['joint2'], 0)

    def test_control_joint_invalid_index(self):
        """Test invalid joint index"""
        result = self.skills.control_joint(7, 90)
        self.assertFalse(result['success'])
        self.assertIn("无效关节索引", result['error'])

    def test_apply_preset_home(self):
        """Test applying 'home' preset"""
        result = self.skills.apply_preset('home')
        self.assertTrue(result['success'])
        self.assertEqual(result['action'], 'home')
        # Check if angles are returned
        self.assertIn('angles', result)
        self.assertEqual(len(result['angles']), 6)

    def test_execute_dispatcher(self):
        """Test the execute method dispatching"""
        # Test executing control_joint via dispatch
        args = {"joint_index": 1, "angle": 45, "current_angles": [0]*6}
        result = self.skills.execute("control_joint", **args)
        
        self.assertTrue(result['success'])
        self.assertAlmostEqual(result['angles']['joint1'], 45)

    def test_perform_action(self):
        """Test perform_action returns correct structure"""
        result = self.skills.perform_action("wave")
        self.assertTrue(result['success'])
        self.assertEqual(result['mode'], 'chat')
        self.assertEqual(result['action'], 'wave')

if __name__ == '__main__':
    unittest.main()
