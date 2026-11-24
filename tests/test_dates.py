import unittest

from birthday_bot.dates import announcement, chunk_lines, format_date, join_mentions, parse_birthday


class ParseBirthdayTests(unittest.TestCase):
    def test_slash_and_dash(self):
        self.assertEqual(parse_birthday("04/12"), (4, 12))
        self.assertEqual(parse_birthday("4-12"), (4, 12))
        self.assertEqual(parse_birthday("  12/31 "), (12, 31))

    def test_leap_day_is_accepted(self):
        self.assertEqual(parse_birthday("02/29"), (2, 29))

    def test_impossible_dates_are_rejected(self):
        for text in ("02/30", "13/01", "00/10", "04/31", "4", "04/12/2000", "ab/cd", ""):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_birthday(text)


class MessageTests(unittest.TestCase):
    def test_format_date(self):
        self.assertEqual(format_date(4, 2), "04/02")

    def test_join_mentions(self):
        self.assertEqual(join_mentions(["a"]), "a")
        self.assertEqual(join_mentions(["a", "b"]), "a and b")
        self.assertEqual(join_mentions(["a", "b", "c"]), "a, b, and c")

    def test_announcement_singular_and_plural(self):
        self.assertTrue(announcement(["@a"]).startswith("Today is @a's birthday."))
        self.assertTrue(announcement(["@a", "@b"]).startswith("Today we are celebrating @a and @b's birthdays."))


class ChunkLinesTests(unittest.TestCase):
    def test_short_list_is_one_message(self):
        self.assertEqual(chunk_lines(["a", "b"]), ["a\nb"])

    def test_long_list_is_split_under_the_limit(self):
        lines = [f"line {i:03d}" for i in range(300)]
        chunks = chunk_lines(lines, limit=100)
        self.assertTrue(all(len(c) <= 100 for c in chunks))
        self.assertEqual("\n".join(chunks).split("\n"), lines)

    def test_empty(self):
        self.assertEqual(chunk_lines([]), [])


if __name__ == "__main__":
    unittest.main()
