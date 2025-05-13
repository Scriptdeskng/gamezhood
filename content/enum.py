from enum import Enum, IntEnum


# https://stackoverflow.com/questions/50473951/how-can-i-attach-documentation-to-members-of-a-python-enum/50473952#50473952


class DocEnum(Enum):
    def __new__(cls, value, doc=None, *args, **kwargs):
        self = object.__new__(cls)  # calling super().__new__(value) here would fail
        self._value_ = value
        if doc is not None:
            self.__doc__ = doc
        return self

    @classmethod
    def values(cls):
        return [c.value for c in cls]


class DocIntEnum(IntEnum):
    def __new__(cls, value, doc=None, *args, **kwargs):
        self = int.__new__(cls)  # calling super().__new__(value) here would fail
        self._value_ = value
        if doc is not None:
            self.__doc__ = doc
        return self

    @classmethod
    def values(cls):
        return [c.value for c in cls]