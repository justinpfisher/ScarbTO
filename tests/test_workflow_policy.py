import unittest

from scripts.check_workflow_policy import EXPECTED_RUNNER, validate_workflow_text


def workflow(job: str) -> str:
    return f"name: fixture\non:\n  workflow_dispatch:\njobs:\n  check:\n{job}"


class WorkflowPolicyTests(unittest.TestCase):
    def test_accepts_explicit_gmktec_labels_with_main_guard(self):
        self.assertEqual(
            validate_workflow_text(
                workflow(
                    "    if: github.ref == 'refs/heads/main'\n"
                    f"    runs-on: {EXPECTED_RUNNER}\n"
                )
            ),
            [],
        )

    def test_rejects_step_level_main_guard(self):
        job = (
            f"    runs-on: {EXPECTED_RUNNER}\n"
            "    steps:\n"
            "      - name: nested guard\n"
            "        if: github.ref == 'refs/heads/main'\n"
            "        run: echo test\n"
        )
        errors = validate_workflow_text(workflow(job))
        self.assertTrue(any("restricted to refs/heads/main" in error for error in errors))

    def test_rejects_missing_main_ref_guard(self):
        errors = validate_workflow_text(workflow(f"    runs-on: {EXPECTED_RUNNER}\n"))
        self.assertTrue(any("restricted to refs/heads/main" in error for error in errors))

    def test_rejects_hosted_runner(self):
        errors = validate_workflow_text(workflow("    runs-on: ubuntu-latest\n"))
        self.assertTrue(any("unapproved runs-on" in error for error in errors))

    def test_rejects_matrix_runner_expression(self):
        errors = validate_workflow_text(workflow("    runs-on: ${{ matrix.os }}\n"))
        self.assertTrue(any("unapproved runs-on" in error for error in errors))

    def test_rejects_reusable_workflow(self):
        errors = validate_workflow_text(
            workflow("    runs-on: [self-hosted, linux, x64, scarbto-gmktec]\n")
            .replace("  check:\n", "  check:\n    uses: someone/repo/.github/workflows/build.yml@main\n")
        )
        self.assertTrue(any("reusable workflow" in error for error in errors))

    def test_rejects_missing_runner_declaration(self):
        errors = validate_workflow_text(workflow("    steps: []\n"))
        self.assertTrue(any("explicit runs-on" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
