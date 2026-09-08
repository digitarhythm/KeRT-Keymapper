import unittest

from keycodes.keycodes import Keycode, recreate_keyboard_keycodes, KEYCODES_TAP_DANCE, KEYCODES_HOST_OS


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

    def test_host_os_keycodes(self):
        """ The last host_os_count tap dance slots are shown as HOS(n) while keeping their TD(x) id """
        kb = FakeKeyboard(6)
        kb.tap_dance_count = 4
        kb.host_os_count = 2
        kb.host_os_base = 2
        recreate_keyboard_keycodes(kb)

        self.assertEqual([(k.qmk_id, k.label) for k in KEYCODES_TAP_DANCE], [("TD(0)", "TD(0)"), ("TD(1)", "TD(1)")])
        self.assertEqual([(k.qmk_id, k.label) for k in KEYCODES_HOST_OS], [("TD(2)", "HOS(0)"), ("TD(3)", "HOS(1)")])

        # what the keymap and the picker display
        self.assertEqual(Keycode.label("TD(1)"), "TD(1)")
        self.assertEqual(Keycode.label("TD(2)"), "HOS(0)")
        self.assertEqual(Keycode.label("TD(3)"), "HOS(1)")
        self.assertIn("TD(2)", Keycode.tooltip("TD(2)"))

        # both spellings resolve to the same tap dance keycode; the wire / .vil spelling stays TD(x)
        self.assertEqual(Keycode.deserialize("HOS(1)"), Keycode.deserialize("TD(3)"))
        self.assertEqual(Keycode.deserialize("HOS(1)"), Keycode.resolve("QK_TAP_DANCE") + 3)
        self.assertEqual(Keycode.serialize(Keycode.deserialize("HOS(1)")), "TD(3)")

        # without HostOS every slot stays a plain tap dance
        kb.host_os_count = 0
        kb.host_os_base = 4
        recreate_keyboard_keycodes(kb)
        self.assertEqual([k.qmk_id for k in KEYCODES_TAP_DANCE], ["TD(0)", "TD(1)", "TD(2)", "TD(3)"])
        self.assertEqual(KEYCODES_HOST_OS, [])
        self.assertEqual(Keycode.label("TD(2)"), "TD(2)")
