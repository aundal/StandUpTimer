import importlib.util
import pathlib
import unittest

MODULE_PATH = pathlib.Path(__file__).parent / "standup_timer.13.py"
SPEC = importlib.util.spec_from_file_location("standup_timer_module", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Failed to load standup_timer.13.py module specification.")
standup_timer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(standup_timer)


class StandupTimerHelperTests(unittest.TestCase):
    def test_get_active_indices_excludes_removed(self):
        colleagues = [{"removed": False}, {"removed": True}, {"removed": False}]
        self.assertEqual(standup_timer.get_active_indices(colleagues), [0, 2])

    def test_compute_avg_time_limit_with_active(self):
        self.assertEqual(standup_timer.compute_avg_time_limit(600, 4), 150)

    def test_compute_avg_time_limit_with_no_active(self):
        self.assertEqual(standup_timer.compute_avg_time_limit(600, 0), 600)
        self.assertEqual(standup_timer.compute_avg_time_limit(600, -1), 600)

    def test_get_next_active_index(self):
        self.assertEqual(standup_timer.get_next_active_index([0, 2, 4], 1), 2)
        self.assertIsNone(standup_timer.get_next_active_index([0, 2, 4], 4))

    def test_get_queue_layout_initial(self):
        colleagues = [{"removed": False}, {"removed": True}, {"removed": False}, {"removed": False}]
        next_up, upcoming, spoken, removed = standup_timer.get_queue_layout(colleagues, set(), -1)
        self.assertEqual(next_up, 0)
        self.assertEqual(upcoming, [2, 3])
        self.assertEqual(spoken, [])
        self.assertEqual(removed, [1])

    def test_get_queue_layout_midway(self):
        colleagues = [{"removed": False}, {"removed": True}, {"removed": False}, {"removed": False}]
        next_up, upcoming, spoken, removed = standup_timer.get_queue_layout(colleagues, {0}, 2)
        self.assertEqual(next_up, 3)
        self.assertEqual(upcoming, [])
        self.assertEqual(spoken, [0])
        self.assertEqual(removed, [1])

    def test_get_queue_layout_all_spoken(self):
        colleagues = [{"removed": False}, {"removed": True}, {"removed": False}]
        next_up, upcoming, spoken, removed = standup_timer.get_queue_layout(colleagues, {0, 2}, 2)
        self.assertIsNone(next_up)
        self.assertEqual(upcoming, [])
        self.assertEqual(spoken, [0])
        self.assertEqual(removed, [1])

    def test_get_queue_layout_excludes_current_speaker(self):
        colleagues = [{"removed": False}, {"removed": False}, {"removed": False}]
        next_up, upcoming, spoken, removed = standup_timer.get_queue_layout(colleagues, {0, 1}, 1)
        self.assertEqual(next_up, 2)
        self.assertEqual(upcoming, [])
        self.assertEqual(spoken, [0])
        self.assertEqual(removed, [])

    def test_get_queue_layout_jump_does_not_auto_mark_in_between(self):
        colleagues = [
            {"removed": False},
            {"removed": False},
            {"removed": False},
            {"removed": False},
        ]
        next_up, upcoming, spoken, removed = standup_timer.get_queue_layout(colleagues, {0}, 3)
        self.assertEqual(next_up, 1)
        self.assertEqual(upcoming, [2])
        self.assertEqual(spoken, [0])
        self.assertEqual(removed, [])

    def test_get_next_pending_index_prefers_first_unspoken(self):
        self.assertEqual(standup_timer.get_next_pending_index([0, 1, 2], {0}, 0), 1)

    def test_get_next_pending_index_skips_current_even_if_unspoken(self):
        self.assertEqual(standup_timer.get_next_pending_index([0, 1, 2], set(), 0), 1)

    def test_get_next_pending_index_none_when_all_done(self):
        self.assertIsNone(standup_timer.get_next_pending_index([0, 1], {1}, 0))

    def test_compute_orbit_angle_offsets(self):
        angle_center = standup_timer.compute_orbit_angle(0, 16, 25)
        angle_right = standup_timer.compute_orbit_angle(1, 16, 25)
        angle_left = standup_timer.compute_orbit_angle(-1, 16, 25)
        self.assertEqual(angle_center, 45)
        self.assertEqual(angle_right, 45 - 25)
        self.assertEqual(angle_left, 45 + 25)

    def test_compute_orbit_angle_multiple_offsets(self):
        angle_right = standup_timer.compute_orbit_angle(2, 16, 25)
        angle_left = standup_timer.compute_orbit_angle(-2, 16, 25)
        self.assertEqual(angle_right, 45 - 25 - 16)
        self.assertEqual(angle_left, 45 + 25 + 16)

    def test_accumulate_elapsed_seconds_partial(self):
        elapsed, carry = standup_timer.accumulate_elapsed_seconds(0.2, 0.3)
        self.assertEqual(elapsed, 0)
        self.assertAlmostEqual(carry, 0.5)

    def test_accumulate_elapsed_seconds_crosses_one_second(self):
        elapsed, carry = standup_timer.accumulate_elapsed_seconds(0.7, 0.5)
        self.assertEqual(elapsed, 1)
        self.assertAlmostEqual(carry, 0.2)

    def test_accumulate_elapsed_seconds_multiple_seconds(self):
        elapsed, carry = standup_timer.accumulate_elapsed_seconds(0.4, 2.7)
        self.assertEqual(elapsed, 3)
        self.assertAlmostEqual(carry, 0.1)

    def test_accumulate_elapsed_seconds_clamps_negative_inputs(self):
        elapsed, carry = standup_timer.accumulate_elapsed_seconds(-1.0, -0.3)
        self.assertEqual(elapsed, 0)
        self.assertAlmostEqual(carry, 0.0)

    def test_accumulate_elapsed_seconds_caps_large_delta(self):
        elapsed, carry = standup_timer.accumulate_elapsed_seconds(0.0, 3.2, max_delta_seconds=1.0)
        self.assertEqual(elapsed, 1)
        self.assertAlmostEqual(carry, 0.0)

    def test_parse_hhmm_valid(self):
        self.assertEqual(standup_timer.parse_hhmm("07:30"), (7, 30))

    def test_parse_hhmm_invalid(self):
        self.assertIsNone(standup_timer.parse_hhmm("25:00"))
        self.assertIsNone(standup_timer.parse_hhmm("bad"))

    def test_normalize_hhmm(self):
        self.assertEqual(standup_timer.normalize_hhmm("7:5"), "07:05")
        self.assertEqual(standup_timer.normalize_hhmm("bad", default_value="08:15"), "08:15")

    def test_normalize_timer_mode(self):
        self.assertEqual(standup_timer.normalize_timer_mode("countup"), "countup")
        self.assertEqual(standup_timer.normalize_timer_mode("other"), "countdown")

    def test_format_timer_value_countdown(self):
        self.assertEqual(standup_timer.format_timer_value(125, "countdown"), "2:05")
        self.assertEqual(standup_timer.format_timer_value(-5, "countdown"), "-0:05")

    def test_format_timer_value_countup(self):
        self.assertEqual(standup_timer.format_timer_value(125, "countup"), "2:05")
        self.assertEqual(standup_timer.format_timer_value(-5, "countup"), "0:00")

    def test_build_finished_delta_message_extra_time(self):
        first_line, second_line = standup_timer.build_finished_delta_message_lines(600, 300)
        self.assertEqual(
            first_line,
            [
                ("You just got ", False),
                ("5 minutes", True),
                (" for free,", False),
            ],
        )
        self.assertEqual(
            second_line,
            [("or you just lost ", False), ("0 minutes", True), (".", False)],
        )

    def test_build_finished_delta_message_lost_time(self):
        first_line, second_line = standup_timer.build_finished_delta_message_lines(600, 1200)
        self.assertEqual(
            first_line,
            [
                ("You just got ", False),
                ("0 minutes", True),
                (" for free,", False),
            ],
        )
        self.assertEqual(
            second_line,
            [("or you just lost ", False), ("10 minutes", True), (".", False)],
        )

    def test_build_finished_delta_message_rounds_small_nonzero_delta(self):
        first_line, second_line = standup_timer.build_finished_delta_message_lines(600, 590)
        self.assertEqual(first_line[1][0], "1 minute")
        self.assertEqual(second_line[1][0], "0 minutes")

    def test_format_minutes_label(self):
        self.assertEqual(standup_timer.format_minutes_label(1), "1 minute")
        self.assertEqual(standup_timer.format_minutes_label(0), "0 minutes")
        self.assertEqual(standup_timer.format_minutes_label(8), "8 minutes")

    def test_active_name_rect_for_main_circle(self):
        rect = standup_timer.active_name_rect_for_main_circle(standup_timer.QRect(120, 120, 300, 300))
        self.assertEqual(rect.left(), 120)
        self.assertEqual(rect.top(), 84)
        self.assertEqual(rect.width(), 300)
        self.assertEqual(rect.height(), 28)

    def test_should_auto_start_now_true_at_or_after_time(self):
        now_dt = standup_timer.datetime(2026, 3, 27, 9, 0)
        self.assertTrue(
            standup_timer.should_auto_start_now(True, "09:00", now_dt, None, False, False)
        )

    def test_should_auto_start_now_false_before_time(self):
        now_dt = standup_timer.datetime(2026, 3, 27, 8, 59)
        self.assertFalse(
            standup_timer.should_auto_start_now(True, "09:00", now_dt, None, False, False)
        )

    def test_should_auto_start_now_false_when_already_started_today(self):
        now_dt = standup_timer.datetime(2026, 3, 27, 9, 30)
        self.assertFalse(
            standup_timer.should_auto_start_now(
                True, "09:00", now_dt, now_dt.date(), False, False
            )
        )

    def test_should_auto_start_now_allows_when_finished(self):
        now_dt = standup_timer.datetime(2026, 3, 27, 9, 0)
        self.assertTrue(
            standup_timer.should_auto_start_now(True, "09:00", now_dt, None, False, True)
        )

    def test_should_skip_today_autostart_on_launch_after_time(self):
        now_dt = standup_timer.datetime(2026, 3, 27, 9, 1)
        self.assertTrue(
            standup_timer.should_skip_today_autostart_on_launch(True, "09:00", now_dt)
        )

    def test_should_skip_today_autostart_on_launch_before_time(self):
        now_dt = standup_timer.datetime(2026, 3, 27, 8, 59)
        self.assertFalse(
            standup_timer.should_skip_today_autostart_on_launch(True, "09:00", now_dt)
        )

    def test_should_evaluate_autostart_false_on_first_seen_minute(self):
        now_dt = standup_timer.datetime(2026, 3, 27, 9, 0, 10)
        should_check, current = standup_timer.should_evaluate_autostart(None, now_dt)
        self.assertFalse(should_check)
        self.assertEqual(current, now_dt.replace(second=0, microsecond=0))

    def test_should_evaluate_autostart_true_when_minute_changes(self):
        last_minute = standup_timer.datetime(2026, 3, 27, 9, 0, 0)
        now_dt = standup_timer.datetime(2026, 3, 27, 9, 1, 5)
        should_check, current = standup_timer.should_evaluate_autostart(last_minute, now_dt)
        self.assertTrue(should_check)
        self.assertEqual(current, now_dt.replace(second=0, microsecond=0))

    def test_parse_name_from_filename_underscore_dash_dot(self):
        full_name, first_name = standup_timer.parse_name_from_filename("john_doe-dev.ops.png")
        self.assertEqual(full_name, "John Doe Dev Ops")
        self.assertEqual(first_name, "John")

    def test_parse_name_from_filename_empty(self):
        full_name, first_name = standup_timer.parse_name_from_filename("....jpg")
        self.assertEqual(full_name, "Unknown")
        self.assertEqual(first_name, "Unknown")

    def test_seconds_until_next_auto_start_same_day_future(self):
        now_dt = standup_timer.datetime(2026, 3, 27, 8, 59, 30)
        seconds = standup_timer.seconds_until_next_auto_start(True, "09:00", now_dt, None)
        self.assertEqual(seconds, 30)

    def test_seconds_until_next_auto_start_rolls_to_next_day_after_time(self):
        now_dt = standup_timer.datetime(2026, 3, 27, 9, 1, 0)
        seconds = standup_timer.seconds_until_next_auto_start(True, "09:00", now_dt, None)
        self.assertEqual(seconds, 23 * 3600 + 59 * 60)

    def test_seconds_until_next_auto_start_rolls_when_already_started_today(self):
        now_dt = standup_timer.datetime(2026, 3, 27, 8, 0, 0)
        seconds = standup_timer.seconds_until_next_auto_start(True, "09:00", now_dt, now_dt.date())
        self.assertEqual(seconds, 3600)

    def test_seconds_until_next_auto_start_never_exceeds_24h(self):
        now_dt = standup_timer.datetime(2026, 3, 27, 7, 0, 0)
        seconds = standup_timer.seconds_until_next_auto_start(True, "09:00", now_dt, now_dt.date())
        self.assertLessEqual(seconds, 24 * 3600)

    def test_normalize_int_clamps_and_defaults(self):
        self.assertEqual(standup_timer.normalize_int("bad", 18, 8, 60), 18)
        self.assertEqual(standup_timer.normalize_int(3, 18, 8, 60), 8)
        self.assertEqual(standup_timer.normalize_int(99, 18, 8, 60), 60)

    def test_load_person_totals_parses_and_sanitizes(self):
        raw = '{"Alice": 120, " Bob ": "45", "": 99, "Eve": -10}'
        totals = standup_timer.load_person_totals(raw)
        self.assertEqual(totals["Alice"], 120)
        self.assertEqual(totals["Bob"], 45)
        self.assertEqual(totals["Eve"], 0)
        self.assertNotIn("", totals)

    def test_merge_person_totals_accumulates_positive_values(self):
        merged = standup_timer.merge_person_totals({"Alice": 100}, [("Alice", 20), ("Bob", 30), ("Eve", -5)])
        self.assertEqual(merged["Alice"], 120)
        self.assertEqual(merged["Bob"], 30)
        self.assertNotIn("Eve", merged)

    def test_default_profile_name_from_dir(self):
        self.assertEqual(
            standup_timer.default_profile_name_from_dir(r"C:\Work\MyTeam"),
            "MyTeam",
        )

    def test_sanitize_profile_applies_fallbacks(self):
        profile = standup_timer.sanitize_profile(
            {},
            fallback_dir=r"C:\Images\Alpha",
            fallback_auto_start_enabled=True,
            fallback_auto_start_time="08:30",
            fallback_index=0,
        )
        self.assertEqual(profile["name"], "Alpha")
        self.assertEqual(profile["image_dir"], r"C:\Images\Alpha")
        self.assertTrue(profile["auto_start_enabled"])
        self.assertEqual(profile["auto_start_time"], "08:30")

    def test_load_profiles_uses_single_fallback_profile_when_invalid(self):
        profiles = standup_timer.load_profiles(
            "not-json",
            fallback_dir=r"C:\Images\Default",
            fallback_auto_start_enabled=False,
            fallback_auto_start_time="09:00",
        )
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0]["image_dir"], r"C:\Images\Default")
        self.assertEqual(profiles[0]["auto_start_time"], "09:00")
        self.assertTrue(profiles[0]["profile_id"].startswith("profile-"))

    def test_load_profiles_preserves_per_profile_start_times(self):
        raw = (
            '[{"name":"Team A","image_dir":"C:\\\\A","auto_start_enabled":true,"auto_start_time":"08:15"},'
            '{"name":"Team B","image_dir":"C:\\\\B","auto_start_enabled":false,"auto_start_time":"17:45"}]'
        )
        profiles = standup_timer.load_profiles(raw, fallback_dir=r"C:\Fallback")
        self.assertEqual(len(profiles), 2)
        self.assertEqual(profiles[0]["auto_start_time"], "08:15")
        self.assertEqual(profiles[1]["auto_start_time"], "17:45")
        self.assertNotEqual(profiles[0]["profile_id"], profiles[1]["profile_id"])

    def test_ensure_profiles_have_ids_deduplicates(self):
        profiles = standup_timer.ensure_profiles_have_ids(
            [
                {"name": "A", "image_dir": r"C:\A", "profile_id": "same"},
                {"name": "B", "image_dir": r"C:\B", "profile_id": "same"},
                {"name": "C", "image_dir": r"C:\C"},
            ]
        )
        ids = [profile["profile_id"] for profile in profiles]
        self.assertEqual(ids[0], "same")
        self.assertEqual(len(set(ids)), 3)
        self.assertTrue(ids[1].startswith("profile-"))
        self.assertTrue(ids[2].startswith("profile-"))

    def test_load_profile_person_totals_sanitizes_nested_totals(self):
        raw = '{"profile-1":{"Alice":120," Bob ":"30"},"profile-2":{"Eve":"-9"},"":{"X":1}}'
        totals = standup_timer.load_profile_person_totals(raw)
        self.assertEqual(totals["profile-1"]["Alice"], 120)
        self.assertEqual(totals["profile-1"]["Bob"], 30)
        self.assertEqual(totals["profile-2"]["Eve"], 0)
        self.assertNotIn("", totals)

    def test_merge_profile_person_totals_scopes_to_profile(self):
        merged = standup_timer.merge_profile_person_totals(
            {"profile-1": {"Alice": 100}, "profile-2": {"Bob": 40}},
            "profile-2",
            [("Bob", 10), ("Cara", 5)],
        )
        self.assertEqual(merged["profile-1"]["Alice"], 100)
        self.assertEqual(merged["profile-2"]["Bob"], 50)
        self.assertEqual(merged["profile-2"]["Cara"], 5)

    def test_reset_profile_person_totals_clears_one_profile(self):
        reset = standup_timer.reset_profile_person_totals(
            {"profile-1": {"Alice": 100}, "profile-2": {"Bob": 40}},
            "profile-1",
        )
        self.assertEqual(reset["profile-1"], {})
        self.assertEqual(reset["profile-2"]["Bob"], 40)

    def test_get_profile_person_totals_returns_active_only(self):
        totals = standup_timer.get_profile_person_totals(
            {"profile-1": {"Alice": 100}, "profile-2": {"Bob": 40}},
            "profile-2",
        )
        self.assertEqual(totals, {"Bob": 40})

    def test_profile_folder_name(self):
        self.assertEqual(standup_timer.profile_folder_name(r"C:\Teams\Backend"), "Backend")

    def test_format_profile_display_label(self):
        label = standup_timer.format_profile_display_label(
            {"name": "Morning Team", "image_dir": r"C:\Teams\Morning"},
            1,
        )
        self.assertEqual(label, "2. Morning Team (Morning)")

    def test_remove_profile_by_index_keeps_one_minimum(self):
        profiles, next_index = standup_timer.remove_profile_by_index(
            [{"name": "Only", "image_dir": r"C:\Only"}],
            0,
        )
        self.assertEqual(len(profiles), 1)
        self.assertEqual(next_index, 0)

    def test_remove_profile_by_index_removes_and_reindexes(self):
        source = [
            {"name": "One", "image_dir": r"C:\One"},
            {"name": "Two", "image_dir": r"C:\Two"},
            {"name": "Three", "image_dir": r"C:\Three"},
        ]
        profiles, next_index = standup_timer.remove_profile_by_index(source, 1)
        self.assertEqual(len(profiles), 2)
        self.assertEqual([p["name"] for p in profiles], ["One", "Three"])
        self.assertEqual(next_index, 1)


if __name__ == "__main__":
    unittest.main()
