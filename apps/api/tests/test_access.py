import unittest

from app.access import Action, AccessControl, UserPrincipal, UserRole


class AccessControlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.acl = AccessControl()

    def test_admin_can_manage_workflows_and_read_audits(self) -> None:
        admin = UserPrincipal(user_id="user-001", display_name="Wei Hao", role=UserRole.ADMIN)

        self.assertTrue(self.acl.can(admin, Action.MANAGE_WORKFLOWS))
        self.assertTrue(self.acl.can(admin, Action.READ_AUDIT_TRAIL))

    def test_reviewer_can_resolve_cases_but_cannot_manage_workflows(self) -> None:
        reviewer = UserPrincipal(user_id="user-002", display_name="Ops Reviewer", role=UserRole.REVIEWER)

        self.assertTrue(self.acl.can(reviewer, Action.RESOLVE_CASES))
        self.assertFalse(self.acl.can(reviewer, Action.MANAGE_WORKFLOWS))

    def test_viewer_cannot_create_cases(self) -> None:
        viewer = UserPrincipal(user_id="user-003", display_name="Audit Viewer", role=UserRole.VIEWER)

        self.assertFalse(self.acl.can(viewer, Action.CREATE_CASES))


if __name__ == "__main__":
    unittest.main()
