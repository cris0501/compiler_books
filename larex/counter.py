class Counter:

    def __init__(self, parent=None):
        self._value = 0
        self._resets = []
        if parent is not None:
            parent._add_reset(self)

    def _add_reset(self, counter):
        self._resets.append(counter)

    def increase(self):
        self._value += 1
        for c in self._resets:
            c.reset()

    def reset(self):
        self._value = 0
        for c in self._resets:
            c.reset()

    def get(self):
        return self._value
