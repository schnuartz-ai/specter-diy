from unittest import TestCase
from embit.bip32 import HDKey
from bip85_passwords import derive_password

# Public BIP85 test root, never use it for real secrets.
ROOT = (
    "xprv9s21ZrQH143K2LBWUUQRFXhucrQqBpKdRRxNVq2zBqsx8HVqFk2uYo8kmba"
    "LLHRdqtQpUm98uKfu3vca1LqdGhUtyoFnCNkfmXRyPXLjbKb"
)


class Bip85PasswordTest(TestCase):
    def test_official_vectors(self):
        root = HDKey.from_base58(ROOT)
        self.assertEqual(derive_password(root, 64, 21, 0), "dKLoepugzdVJvdL56ogNV")
        self.assertEqual(derive_password(root, 85, 12, 0), "_s`{TW89)i4`")

    def test_boundaries(self):
        root = HDKey.from_base58(ROOT)
        # Independently generated using hardened BIP32 and CPython base64/b85.
        vectors = (
            (64, 20, 0, "RrH7uVI0XlpddCbiuYV+"),
            (64, 86, 2147483647, "hVrDDtAYc67PjwM1eZDydb8UCf/NKer31Rc6JJF0eY46wFOR7Ks/zEaCVaOZLSOmyNsmTmXlWPGhaHx9Mm28/A"),
            (85, 10, 0, "@;HdO2<rpP"),
            (85, 80, 2147483647, ";7rLjyf~!x<q}JJh99s+wTUg2v#!es@V4o)+#LodIJ!iFfV^il;4ahNUQ9@^M1_?Q$Ra2x7XI`)d+(C6"),
        )
        for base, length, index, expected in vectors:
            self.assertEqual(derive_password(root, base, length, index), expected)

    def test_index_and_application(self):
        root = HDKey.from_base58(ROOT)
        self.assertEqual(derive_password(root, 64, 24), "vtV6sdNQTKpuefUMOHOKwUp1")
        self.assertEqual(derive_password(root, 64, 24, 1), "ZAokrpZk+3CYzFAO+ZuZ/gqo")
        self.assertEqual(derive_password(root, 85, 24, 0), "GS~ifyX#e53ssnkpRZCAgo`f")
        self.assertEqual(derive_password(root, 85, 24, 1), "Mk~J1UxK_z|1}Jvabp8AMCg(")
        self.assertNotEqual(derive_password(root, 64, 21)[:20], derive_password(root, 64, 20))
        self.assertNotEqual(derive_password(root, 85, 12)[:10], derive_password(root, 85, 10))

    def test_invalid_parameters(self):
        # No root required: invalid inputs must fail before derivation.
        for base, length, index in (
            (65, 24, 0), (64.0, 24, 0), (64, 19, 0), (64, 87, 0),
            (85, 9, 0), (85, 81, 0), (64, 24, -1),
            (85, 24, 2147483648), (64, 24, True),
            (85, 24.0, 0), (64, 24, "0"),
        ):
            try:
                derive_password(None, base, length, index)
            except ValueError:
                continue
            self.fail("Invalid BIP85 parameters were accepted")
