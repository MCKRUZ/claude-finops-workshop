"""Unit tests for otel_bridge.py's OTLP/HTTP JSON parsing — synthetic
payloads only, no network. Run: python3 -m unittest test_otel_bridge.py -v
"""

import unittest

from otel_bridge import extract_records


def _cost_payload(skill_name, usd, model="claude-opus-5"):
    return {
        "resourceMetrics": [
            {
                "resource": {"attributes": []},
                "scopeMetrics": [
                    {
                        "scope": {"name": "com.anthropic.claude_code"},
                        "metrics": [
                            {
                                "name": "claude_code.cost.usage",
                                "unit": "USD",
                                "sum": {
                                    "aggregationTemporality": 1,  # DELTA
                                    "isMonotonic": True,
                                    "dataPoints": [
                                        {
                                            "attributes": [
                                                {"key": "model", "value": {"stringValue": model}},
                                                {"key": "skill.name", "value": {"stringValue": skill_name}},
                                            ],
                                            "timeUnixNano": "1734000000000000000",
                                            "asDouble": usd,
                                        }
                                    ],
                                },
                            }
                        ],
                    }
                ],
            }
        ]
    }


class ExtractRecordsTests(unittest.TestCase):
    def test_extracts_cost_metric_with_attributes(self):
        payload = _cost_payload("dataviz", 0.0123)
        records = extract_records(payload)
        self.assertEqual(len(records), 1)
        r = records[0]
        self.assertEqual(r["metric"], "claude_code.cost.usage")
        self.assertAlmostEqual(r["value"], 0.0123)
        self.assertEqual(r["attributes"]["skill.name"], "dataviz")
        self.assertEqual(r["attributes"]["model"], "claude-opus-5")

    def test_ignores_untracked_metrics(self):
        payload = {
            "resourceMetrics": [
                {
                    "scopeMetrics": [
                        {
                            "metrics": [
                                {
                                    "name": "claude_code.lines_of_code.count",
                                    "sum": {"dataPoints": [{"asInt": "5"}]},
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        self.assertEqual(extract_records(payload), [])

    def test_int_value_parsed_from_string(self):
        payload = {
            "resourceMetrics": [
                {
                    "scopeMetrics": [
                        {
                            "metrics": [
                                {
                                    "name": "claude_code.token.usage",
                                    "sum": {"dataPoints": [{"attributes": [], "asInt": "128000"}]},
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        records = extract_records(payload)
        self.assertEqual(records[0]["value"], 128000.0)

    def test_gauge_shape_also_extracted(self):
        payload = {
            "resourceMetrics": [
                {
                    "scopeMetrics": [
                        {
                            "metrics": [
                                {
                                    "name": "claude_code.cost.usage",
                                    "gauge": {"dataPoints": [{"attributes": [], "asDouble": 1.5}]},
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        records = extract_records(payload)
        self.assertEqual(records[0]["value"], 1.5)

    def test_empty_payload_returns_no_records(self):
        self.assertEqual(extract_records({}), [])

    def test_multiple_data_points_all_extracted(self):
        payload = _cost_payload("dataviz", 0.01)
        payload["resourceMetrics"][0]["scopeMetrics"][0]["metrics"][0]["sum"]["dataPoints"].append(
            {
                "attributes": [{"key": "skill.name", "value": {"stringValue": "artifact-design"}}],
                "asDouble": 0.02,
            }
        )
        records = extract_records(payload)
        self.assertEqual(len(records), 2)
        self.assertEqual({r["attributes"].get("skill.name") for r in records}, {"dataviz", "artifact-design"})

    def test_data_point_missing_value_is_skipped(self):
        payload = {
            "resourceMetrics": [
                {"scopeMetrics": [{"metrics": [{"name": "claude_code.cost.usage", "sum": {"dataPoints": [{"attributes": []}]}}]}]}
            ]
        }
        self.assertEqual(extract_records(payload), [])

    def test_bool_and_double_attribute_values(self):
        payload = {
            "resourceMetrics": [
                {
                    "scopeMetrics": [
                        {
                            "metrics": [
                                {
                                    "name": "claude_code.cost.usage",
                                    "sum": {
                                        "dataPoints": [
                                            {
                                                "attributes": [
                                                    {"key": "cached", "value": {"boolValue": True}},
                                                    {"key": "ratio", "value": {"doubleValue": 0.5}},
                                                ],
                                                "asDouble": 1.0,
                                            }
                                        ]
                                    },
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        records = extract_records(payload)
        self.assertEqual(records[0]["attributes"]["cached"], True)
        self.assertEqual(records[0]["attributes"]["ratio"], 0.5)


if __name__ == "__main__":
    unittest.main()
