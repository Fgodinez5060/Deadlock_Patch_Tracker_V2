"""Sanity checks for parser.py against known BBCode shapes.

Run: python scrape/tests/test_parser.py
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import parser as p  # noqa: E402

ROSTER = json.loads(
    (Path(__file__).resolve().parents[2] / "data" / "roster.json").read_text(encoding="utf-8")
)


class ParseBodyTests(unittest.TestCase):
    def test_flat_hero_and_item_bullets(self):
        body = (
            "[p][/p][p]- Urn Runner sprint bonus reduced from +2m to 0[/p]"
            "[p][/p][p]- Scourge: Max Health Per Second reduced from 2.6% to 2.5%[/p]"
            "[p][/p][p]- Billy: Rising Ram T3 spirit scaling reduced from 0.035 to 0.03[/p]"
        )
        result = p.parse_body(body, ROSTER)
        self.assertEqual(
            result["heroes"],
            {"Billy": ["Rising Ram T3 spirit scaling reduced from 0.035 to 0.03"]},
        )
        self.assertEqual(
            result["items"],
            {"Scourge": ["Max Health Per Second reduced from 2.6% to 2.5%"]},
        )
        self.assertEqual(result["general"], ["Urn Runner sprint bonus reduced from +2m to 0"])

    def test_multiword_hero_and_item_names(self):
        body = (
            "[p]- Grey Talon: Rain of Arrows cooldown increased from 23s to 25s[/p]"
            "[p]- Mo & Krill: Sand Blast T2 slow increased from -25% to -30%[/p]"
            "[p]- High Velocity Rounds: Damage increased from 10 to 12[/p]"
        )
        result = p.parse_body(body, ROSTER)
        self.assertIn("Grey Talon", result["heroes"])
        self.assertIn("Mo & Krill", result["heroes"])
        self.assertIn("High Velocity Rounds", result["items"])

    def test_bold_section_headers_are_ignored_for_routing_and_dropped(self):
        body = (
            "[p][b]\\[ Heroes ][/b][/p][p][/p]"
            "[p]- Abrams: Siphon Life T3 reduced from +3m Radius to +2m[/p]"
            "[p][b]\\[ Items ][/b][/p][p][/p]"
            "[p]- Mystic Shot: Cooldown increased from 8s to 9s[/p]"
        )
        result = p.parse_body(body, ROSTER)
        self.assertEqual(list(result["heroes"].keys()), ["Abrams"])
        self.assertEqual(list(result["items"].keys()), ["Mystic Shot"])
        self.assertEqual(result["general"], [])

    def test_unknown_and_typo_names_fall_to_general(self):
        body = (
            "[p]- Vindcita: Stake T2 reduced from -20s Cooldown to -22s[/p]"
            "[p]- Street Brawl: All ability and item range/radius values are reduced by 10%[/p]"
        )
        result = p.parse_body(body, ROSTER)
        self.assertEqual(result["heroes"], {})
        self.assertEqual(result["items"], {})
        self.assertEqual(len(result["general"]), 2)

    def test_multiple_bullets_for_same_hero_accumulate_in_order(self):
        body = (
            "[p]- Shiv: Alt Fire ammo cost reduced from 5 to 4[/p]"
            "[p]- Shiv: Weapon now has fixed pellet spread[/p]"
        )
        result = p.parse_body(body, ROSTER)
        self.assertEqual(
            result["heroes"]["Shiv"],
            [
                "Alt Fire ammo cost reduced from 5 to 4",
                "Weapon now has fixed pellet spread",
            ],
        )

    def test_prose_paragraph_without_leading_dash_is_kept(self):
        body = "[p]Urn mechanics have been reworked.[/p][p]Primary details:[/p]"
        result = p.parse_body(body, ROSTER)
        self.assertEqual(
            result["general"], ["Urn mechanics have been reworked.", "Primary details:"]
        )

    def test_embedded_image_is_stripped_not_left_as_garbage_bullet(self):
        body = (
            '[p][img src="{STEAM_CLAN_LOC_IMAGE}/123/abc.png"][/img][/p]'
            "[p]- Reworked Boon reward table[/p]"
        )
        result = p.parse_body(body, ROSTER)
        self.assertEqual(result["general"], ["Reworked Boon reward table"])

    def test_derive_patch_type(self):
        self.assertEqual(p.derive_patch_type("Minor Update - 07-09-2026"), "update")
        self.assertEqual(p.derive_patch_type("Balance Update - 07-09-2026"), "balance")
        self.assertEqual(p.derive_patch_type("New Hero: Doorman"), "hero_release")


if __name__ == "__main__":
    unittest.main()
