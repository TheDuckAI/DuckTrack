from pynput.keyboard import HotKey, Key, KeyCode

from ducktrack.keycomb import KeyCombinationListener


def make_listener(keys):
    listener = KeyCombinationListener()
    fired = []
    listener.add_comb(keys, lambda: fired.append(1))
    return listener, fired


def test_combo_fires_with_generic_modifier():
    listener, fired = make_listener(("shift", "esc"))
    listener.on_key_press(Key.shift)
    listener.on_key_press(Key.esc)
    assert fired == [1]


def test_combo_fires_with_left_right_modifier_variants():
    listener, fired = make_listener(("shift", "esc"))
    listener.on_key_press(Key.shift_l)
    listener.on_key_press(Key.esc)
    assert fired == [1]


def test_release_clears_pressed_state():
    listener, fired = make_listener(("shift", "esc"))
    listener.on_key_press(Key.shift_l)
    listener.on_key_release(Key.shift_l)
    listener.on_key_press(Key.esc)
    assert fired == []
    assert listener.current_keys == {listener.canonicalize_key(Key.esc)}


def test_shifted_character_is_canonicalized():
    # with shift held, pynput reports 'R' instead of 'r'
    listener, fired = make_listener(("shift", "r"))
    listener.on_key_press(Key.shift)
    listener.on_key_press(KeyCode.from_char("R"))
    assert fired == [1]


def test_non_matching_combo_does_not_fire():
    listener, fired = make_listener(("shift", "esc"))
    listener.on_key_press(Key.ctrl)
    listener.on_key_press(Key.esc)
    assert fired == []


def test_record_hotkey_spec_parses_and_fires():
    # same spec as the GlobalHotKeys binding in app.py
    fired = []
    hotkey = HotKey(HotKey.parse("<ctrl>+<alt>+r"), lambda: fired.append(1))
    for key in [Key.ctrl, Key.alt, KeyCode.from_char("r")]:
        hotkey.press(key)
    assert fired == [1]
