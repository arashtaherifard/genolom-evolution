# Milestone 3 Hotfix 1 — circular import

## Problem

M3 `content.planning` imports the existing `evolution.operator_rules` ordinal
scales. Python initializes the parent `evolution` package first. The previous
`evolution/__init__.py` eagerly imported `session`, while `session` imports the
content operator layer. That re-entered `content.generator` before it finished
initializing and caused the observed `ContentGenerator` circular-import error.

## Fix

`PriorityEvolutionSession` and `AppliedOperatorResult` are now lazy exports from
`evolution.__init__` via module-level `__getattr__`.

This preserves the established public API while avoiding eager import of the
session during `evolution.operator_rules` initialization. No scientific rule,
fitness definition, operator rule, or experiment behavior is changed.

A regression test was added in `tests/test_m3_import_graph.py`.
