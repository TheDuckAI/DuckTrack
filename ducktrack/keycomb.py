from pynput.keyboard import Listener

from .util import name_to_key

# pynput reports left/right variants (e.g. ctrl_l) on some platforms,
# so fold them into the generic modifier for combination matching
CANONICAL_KEY_NAMES = {
    "ctrl_l": "ctrl", "ctrl_r": "ctrl",
    "alt_l": "alt", "alt_r": "alt", "alt_gr": "alt",
    "shift_l": "shift", "shift_r": "shift",
    "cmd_l": "cmd", "cmd_r": "cmd",
}

def canonicalize_key(key):
    name = getattr(key, "name", None)
    if name in CANONICAL_KEY_NAMES:
        return name_to_key(CANONICAL_KEY_NAMES[name])
    return key


class KeyCombinationListener:
    """
    Simple and bad key combination listener.
    """

    def __init__(self):
        self.current_keys = set()
        self.callbacks = {}
        self.listener = Listener(on_press=self.on_key_press, on_release=self.on_key_release)

    def add_comb(self, keys, callback):
        self.callbacks[tuple([name_to_key(key_name) for key_name in sorted(keys)])] = callback

    def on_key_press(self, key):
        self.current_keys.add(canonicalize_key(key))
        for comb, callback in self.callbacks.items():
            if all(k in self.current_keys for k in comb):
                return callback()

    def on_key_release(self, key):
        key = canonicalize_key(key)
        if key in self.current_keys:
            self.current_keys.remove(key)

    def start(self):
        self.listener.start()

    def stop(self):
        self.listener.stop()
