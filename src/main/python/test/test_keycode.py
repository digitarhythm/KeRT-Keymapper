import unittest

from keycodes.keycodes import Keycode, recreate_keyboard_keycodes, KEYCODES_TAP_DANCE, KEYCODES_OS_DANCE


class FakeKeyboard:

    layers = 4
    macro_count = 16
    custom_keycodes = None
    tap_dance_count = 0
    midi = None

    def __init__(self, protocol):
        self.vial_protocol = protocol
        if protocol >= 6:
            self.supported_features = set([
                "persistent_default_layer", "caps_word", "layer_lock", "repeat_key",
            ])
        else:
            self.supported_features = set()


class TestKeycode(unittest.TestCase):

    def _test_serialize_protocol(self, protocol):
        recreate_keyboard_keycodes(FakeKeyboard(protocol))
        covered = 0

        # at a minimum, we should be able to deserialize/serialize everything
        for x in range(2 ** 16):
            s = Keycode.serialize(x)
            d = Keycode.deserialize(s)
            self.assertEqual(d, x, "{} serialized into {} deserialized into {}".format(x, s, d))
            if s != hex(x):
                covered += 1
        print("[protocol={}] {}/{} covered keycodes, which is {:.4f}%".format(protocol, covered, 2 ** 16, 100 * covered / 2 ** 16))

    def test_serialize_v5(self):
        self._test_serialize_protocol(5)

    def test_serialize_v6(self):
        self._test_serialize_protocol(6)

    def test_os_dance_keycodes(self):
        """ OSD(n) keycodes exist only for the entries the firmware reports and map to 0x7E20 + n """
        kb = FakeKeyboard(6)
        kb.tap_dance_count = 4
        kb.os_dance_count = 3
        recreate_keyboard_keycodes(kb)

        # tap dance is unaffected by OS Dance
        self.assertEqual([k.qmk_id for k in KEYCODES_TAP_DANCE], ["TD(0)", "TD(1)", "TD(2)", "TD(3)"])
        self.assertEqual([(k.qmk_id, k.label) for k in KEYCODES_OS_DANCE],
                         [("OSD(0)", "OSD(0)"), ("OSD(1)", "OSD(1)"), ("OSD(2)", "OSD(2)")])

        # wire format: QK_OS_DANCE = 0x7E20
        self.assertEqual(Keycode.deserialize("OSD(0)"), 0x7E20)
        self.assertEqual(Keycode.deserialize("OSD(2)"), 0x7E22)
        self.assertEqual(Keycode.serialize(0x7E21), "OSD(1)")
        self.assertEqual(Keycode.label("OSD(1)"), "OSD(1)")
        self.assertIn("OS Dance", Keycode.tooltip("OSD(1)"))

        # a keyboard without OS Dance lists nothing
        kb.os_dance_count = 0
        recreate_keyboard_keycodes(kb)
        self.assertEqual(KEYCODES_OS_DANCE, [])
        self.assertEqual([k.qmk_id for k in KEYCODES_TAP_DANCE], ["TD(0)", "TD(1)", "TD(2)", "TD(3)"])
