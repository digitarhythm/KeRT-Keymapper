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

    def test_os_dance_labels(self):
        """ Tap dance entries reserved for OS Dance move to KEYCODES_OS_DANCE as OD(n), keeping their TD(x) id """
        kb = FakeKeyboard(6)
        kb.tap_dance_count = 4
        kb.os_dance = {"base": 2, "count": 2}
        recreate_keyboard_keycodes(kb)

        self.assertEqual([(k.qmk_id, k.label) for k in KEYCODES_TAP_DANCE], [("TD(0)", "TD(0)"), ("TD(1)", "TD(1)")])
        self.assertEqual([(k.qmk_id, k.label) for k in KEYCODES_OS_DANCE], [("TD(2)", "OD(0)"), ("TD(3)", "OD(1)")])

        # labels resolve through the global keycode map (what the keymap and the tray display)
        self.assertEqual(Keycode.label("TD(1)"), "TD(1)")
        self.assertEqual(Keycode.label("TD(2)"), "OD(0)")
        self.assertEqual(Keycode.label("TD(3)"), "OD(1)")
        # the tooltip still tells the user which tap dance entry is behind the label
        self.assertIn("TD(2)", Keycode.tooltip("TD(2)"))
        # the wire format is untouched: OD(n) is only a label
        self.assertEqual(Keycode.serialize(Keycode.deserialize("TD(2)")), "TD(2)")

        # without osDance every entry stays a plain tap dance
        kb.os_dance = None
        recreate_keyboard_keycodes(kb)
        self.assertEqual([k.qmk_id for k in KEYCODES_TAP_DANCE], ["TD(0)", "TD(1)", "TD(2)", "TD(3)"])
        self.assertEqual(KEYCODES_OS_DANCE, [])
        self.assertEqual(Keycode.label("TD(2)"), "TD(2)")
