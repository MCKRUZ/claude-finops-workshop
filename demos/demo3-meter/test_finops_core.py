"""Unit tests for finops_core.py — synthetic fixtures only, no real logs.

Run:
    python3 -m unittest test_finops_core.py -v
"""

import unittest

import finops_core as fc


class PriceForModelTests(unittest.TestCase):
    def test_opus_5(self):
        self.assertEqual(fc.price_for_model("claude-opus-5", None), (5.00, 25.00))

    def test_haiku(self):
        self.assertEqual(fc.price_for_model("claude-haiku-4-5", None), (1.00, 5.00))

    def test_dated_model_id_matches_by_prefix(self):
        self.assertEqual(
            fc.price_for_model("claude-sonnet-4-6-20260101", None), (3.00, 15.00)
        )

    def test_longest_prefix_wins(self):
        # claude-opus-4-8 must not fall through to a shorter "claude-opus-4" rule
        self.assertEqual(fc.price_for_model("claude-opus-4-8", None), (5.00, 25.00))

    def test_unknown_model_returns_none(self):
        self.assertIsNone(fc.price_for_model("claude-nonexistent-9", None))

    def test_empty_model_returns_none(self):
        self.assertIsNone(fc.price_for_model("", None))

    def test_sonnet_5_intro_pricing_before_cutoff(self):
        self.assertEqual(
            fc.price_for_model("claude-sonnet-5", "2026-08-15T00:00:00Z"), (2.00, 10.00)
        )

    def test_sonnet_5_standard_pricing_after_cutoff(self):
        self.assertEqual(
            fc.price_for_model("claude-sonnet-5", "2026-09-15T00:00:00Z"), (3.00, 15.00)
        )

    def test_sonnet_5_no_timestamp_prefers_intro_rule(self):
        # Rule order matters when no timestamp is given to disambiguate —
        # this documents current behavior rather than prescribing it.
        self.assertEqual(fc.price_for_model("claude-sonnet-5", None), (2.00, 10.00))


class ComputeMessageCostTests(unittest.TestCase):
    def test_unknown_model_is_unpriced_not_zero_guessed(self):
        cost = fc.compute_message_cost("claude-nonexistent-9", {"input_tokens": 1000})
        self.assertFalse(cost.priced)
        self.assertEqual(cost.total_usd, 0.0)

    def test_basic_input_output(self):
        cost = fc.compute_message_cost(
            "claude-opus-5", {"input_tokens": 1_000_000, "output_tokens": 1_000_000}
        )
        self.assertTrue(cost.priced)
        self.assertAlmostEqual(cost.input_usd, 5.00)
        self.assertAlmostEqual(cost.output_usd, 25.00)
        self.assertAlmostEqual(cost.total_usd, 30.00)

    def test_cache_read_is_tenth_of_input_price(self):
        cost = fc.compute_message_cost(
            "claude-opus-5", {"cache_read_input_tokens": 1_000_000}
        )
        self.assertAlmostEqual(cost.cache_read_usd, 0.50)  # 5.00 * 0.10

    def test_cache_write_flat_field_treated_as_5m_default(self):
        cost = fc.compute_message_cost(
            "claude-opus-5", {"cache_creation_input_tokens": 1_000_000}
        )
        self.assertAlmostEqual(cost.cache_write_usd, 6.25)  # 5.00 * 1.25

    def test_cache_write_breakdown_1h_is_double_5m_rate(self):
        cost = fc.compute_message_cost(
            "claude-opus-5",
            {
                "cache_creation": {
                    "ephemeral_5m_input_tokens": 1_000_000,
                    "ephemeral_1h_input_tokens": 1_000_000,
                }
            },
        )
        # 5m: 5.00 * 1.25 = 6.25 ; 1h: 5.00 * 2.00 = 10.00
        self.assertAlmostEqual(cost.cache_write_usd, 16.25)

    def test_breakdown_present_but_flat_field_also_present_prefers_breakdown(self):
        # A log entry should never carry both, but if it did, the detailed
        # breakdown must win over the flat field — never double-count.
        cost = fc.compute_message_cost(
            "claude-opus-5",
            {
                "cache_creation_input_tokens": 1_000_000,
                "cache_creation": {"ephemeral_5m_input_tokens": 500_000},
            },
        )
        self.assertAlmostEqual(cost.cache_write_usd, 3.125)  # 500k tokens, not 1M

    def test_missing_usage_fields_default_to_zero(self):
        cost = fc.compute_message_cost("claude-opus-5", {})
        self.assertTrue(cost.priced)
        self.assertEqual(cost.total_usd, 0.0)


class ParseJsonlLineTests(unittest.TestCase):
    def test_valid_json(self):
        self.assertEqual(fc.parse_jsonl_line('{"a": 1}'), {"a": 1})

    def test_blank_line_returns_none(self):
        self.assertIsNone(fc.parse_jsonl_line("   \n"))

    def test_malformed_line_returns_none_not_raises(self):
        self.assertIsNone(fc.parse_jsonl_line("{not json"))


class IsBillableAssistantEntryTests(unittest.TestCase):
    def test_valid_assistant_entry(self):
        entry = {
            "type": "assistant",
            "message": {"role": "assistant", "model": "claude-opus-5", "usage": {"input_tokens": 1}},
        }
        self.assertTrue(fc.is_billable_assistant_entry(entry))

    def test_user_entry_is_not_billable(self):
        entry = {"type": "user", "message": {"role": "user", "content": "hi"}}
        self.assertFalse(fc.is_billable_assistant_entry(entry))

    def test_harness_internal_envelope_type_is_not_billable(self):
        # e.g. hook_success, skill_listing, total_tokens_reminder, etc. —
        # anything not type=="assistant" is ignored, not asserted against.
        entry = {"type": "hook_success", "data": {}}
        self.assertFalse(fc.is_billable_assistant_entry(entry))

    def test_assistant_entry_without_usage_is_not_billable(self):
        entry = {"type": "assistant", "message": {"role": "assistant"}}
        self.assertFalse(fc.is_billable_assistant_entry(entry))

    def test_non_dict_entry_is_not_billable(self):
        self.assertFalse(fc.is_billable_assistant_entry("not a dict"))
        self.assertFalse(fc.is_billable_assistant_entry(None))


class MessageIdTests(unittest.TestCase):
    def test_extracts_id_from_billable_entry(self):
        entry = {
            "type": "assistant",
            "message": {"role": "assistant", "id": "msg_abc123", "usage": {"input_tokens": 1}},
        }
        self.assertEqual(fc.message_id(entry), "msg_abc123")

    def test_non_billable_entry_has_no_id(self):
        self.assertIsNone(fc.message_id({"type": "user"}))


class ExtractToolUsesTests(unittest.TestCase):
    def _entry(self, content):
        return {
            "type": "assistant",
            "message": {"role": "assistant", "usage": {"input_tokens": 1}, "content": content},
        }

    def test_skill_invocation_normalized(self):
        entry = self._entry([{"type": "tool_use", "name": "Skill", "input": {"skill": "claude-api"}}])
        self.assertEqual(fc.extract_tool_uses(entry), [{"kind": "skill", "name": "claude-api"}])

    def test_task_invocation_normalized_to_subagent(self):
        entry = self._entry(
            [{"type": "tool_use", "name": "Task", "input": {"subagent_type": "code-reviewer"}}]
        )
        self.assertEqual(fc.extract_tool_uses(entry), [{"kind": "subagent", "name": "code-reviewer"}])

    def test_agent_tool_name_variant_also_normalized_to_subagent(self):
        # Some harnesses rename the subagent-spawning tool "Agent" instead
        # of "Task" — confirmed on a real install during development.
        entry = self._entry(
            [{"type": "tool_use", "name": "Agent", "input": {"subagent_type": "fork"}}]
        )
        self.assertEqual(fc.extract_tool_uses(entry), [{"kind": "subagent", "name": "fork"}])

    def test_ordinary_tool_normalized(self):
        entry = self._entry([{"type": "tool_use", "name": "Bash", "input": {}}])
        self.assertEqual(fc.extract_tool_uses(entry), [{"kind": "tool", "name": "Bash"}])

    def test_text_blocks_are_ignored(self):
        entry = self._entry([{"type": "text", "text": "hello"}])
        self.assertEqual(fc.extract_tool_uses(entry), [])

    def test_multiple_blocks_all_extracted(self):
        entry = self._entry(
            [
                {"type": "text", "text": "hi"},
                {"type": "tool_use", "name": "Read", "input": {}},
                {"type": "tool_use", "name": "Skill", "input": {"skill": "dataviz"}},
            ]
        )
        self.assertEqual(
            fc.extract_tool_uses(entry),
            [{"kind": "tool", "name": "Read"}, {"kind": "skill", "name": "dataviz"}],
        )


class IsHumanUserTurnTests(unittest.TestCase):
    def test_plain_string_content_is_human_turn(self):
        entry = {"type": "user", "message": {"role": "user", "content": "do the thing"}}
        self.assertTrue(fc.is_human_user_turn(entry))

    def test_text_block_content_is_human_turn(self):
        entry = {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "hi"}]}}
        self.assertTrue(fc.is_human_user_turn(entry))

    def test_pure_tool_result_is_not_human_turn(self):
        entry = {
            "type": "user",
            "message": {
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": "toolu_1", "content": "ok"}],
            },
        }
        self.assertFalse(fc.is_human_user_turn(entry))

    def test_sidechain_entry_is_not_human_turn(self):
        entry = {
            "type": "user",
            "isSidechain": True,
            "message": {"role": "user", "content": "delegated task"},
        }
        self.assertFalse(fc.is_human_user_turn(entry))

    def test_empty_string_content_is_not_human_turn(self):
        entry = {"type": "user", "message": {"role": "user", "content": "   "}}
        self.assertFalse(fc.is_human_user_turn(entry))

    def test_assistant_type_is_not_a_user_turn(self):
        entry = {"type": "assistant", "message": {"role": "assistant", "content": "hi"}}
        self.assertFalse(fc.is_human_user_turn(entry))


if __name__ == "__main__":
    unittest.main()
