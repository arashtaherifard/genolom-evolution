# M4 Hotfix 1 — M3 deterministic-test compatibility

## Why
The proposal-exact M4 planner correctly blocks Source→Target realizations when Appendix A/B has no supported rule. Pre-existing M3 orchestration tests intentionally use `DeterministicTestGenerator` + test validators to test state transitions, target/realized promotion, archives, and libraries independently of scientific content-realization capability. M4 accidentally prevented those test doubles from reaching their validators.

## Fix
- Scientific/default generators remain blocked before generation whenever `ContentPlan.executable == False`.
- `DeterministicTestGenerator` now opts in with `test_only_allow_blocked_plan = True`.
- The operator records `test_only_planning_bypass=True` and `scientific_use_allowed=False` in request metadata.
- The proposal-exact plan itself remains blocked; no Appendix rule is changed or invented.
- Added a regression test covering this compatibility path.

This hotfix changes test plumbing only, not proposal rules or scientific acceptance behavior.
