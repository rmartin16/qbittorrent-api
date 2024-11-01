# Copyright (c) 2013 Brendan Curran-Johnson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
Functions and Classes from attrdict.

*rmartin Feb 2021
AttrDict finally broke with Python 3.10 since abstract base classes can no
longer be imported from collections but should use collections.abc instead.
Since AttrDict is abandoned, I've consolidated the code here for future use.
AttrMap and AttrDefault were removed altogether.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, MutableMapping, Sequence
from re import compile as re_compile
from typing import Any, TypeVar

K = TypeVar("K")
V = TypeVar("V")
T = TypeVar("T")

VALID_KEY_RE = re_compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def merge(left: Mapping[K, V], right: Mapping[K, V]) -> dict[K, V]:
    """
    Merge two mappings objects together, combining overlapping Mappings, and
    favoring right-values.

    left: The left Mapping object.
    right: The right (favored) Mapping object.

    NOTE: This is not commutative (merge(a,b) != merge(b,a)).
    """
    merged = {}

    left_keys = frozenset(left)
    right_keys = frozenset(right)

    # Items only in the left Mapping
    for key in left_keys - right_keys:
        merged[key] = left[key]

    # Items only in the right Mapping
    for key in right_keys - left_keys:
        merged[key] = right[key]

    # in both
    for key in left_keys & right_keys:
        left_value = left[key]
        right_value = right[key]

        # recursive merge
        if isinstance(left_value, Mapping) and isinstance(right_value, Mapping):
            merged[key] = merge(left_value, right_value)  # type: ignore
        # overwrite with right value
        else:
            merged[key] = right_value

    return merged


class Attr(Mapping[K, V], ABC):
    """
    A ``mixin`` class for a mapping that allows for attribute-style access of
    values.

    A key may be used as an attribute if:
     * It is a string
     * It matches ``^[A-Za-z][A-Za-z0-9_]*$`` (i.e., a public attribute)
     * The key doesn't overlap with any class attributes (for ``Attr``,
       those would be ``get``, ``items``, ``keys``, ``values``, ``mro``, and
       ``register``).

    If a value which is accessed as an attribute is a Sequence-type
    (and is not a string/bytes), it will be converted to a
    _sequence_type with any mappings within it converted to Attrs.

    NOTE:
        This means that if _sequence_type is not None, then a
        sequence accessed as an attribute will be a different object
        than if accessed as an attribute than if it is accessed as an
        item.
    """

    @abstractmethod
    def _configuration(self) -> Any:
        """All required state for building a new instance with the same
        settings as the current object."""

    @classmethod
    @abstractmethod
    def _constructor(cls, mapping: Mapping[K, V], configuration: Any) -> Attr[K, V]:
        """
        A standardized constructor used internally by Attr.

        mapping: A mapping of key-value pairs. It is HIGHLY recommended
            that you use this as the internal key-value pair mapping, as
            that will allow nested assignment (e.g., attr.foo.bar = baz)
        configuration: The return value of Attr._configuration
        """

    def __call__(self, key: K) -> Attr[K, V]:
        """
        Dynamically access a key-value pair.

        key: A key associated with a value in the mapping.

        This differs from __getitem__, because it returns a new instance
        of an Attr (if the value is a Mapping object).
        """
        if key not in self:
            raise AttributeError(
                f"'{self.__class__.__name__} instance has no attribute '{key}'"
            )

        return self._build(self[key])

    def __getattr__(self, key: Any) -> Any:
        """Access an item as an attribute."""
        if key not in self or not self._valid_name(key):
            raise AttributeError(
                f"'{self.__class__.__name__}' instance has no attribute '{key}'"
            )

        return self._build(self[key])

    def __add__(self, other: Mapping[K, V]) -> Attr[K, V]:
        """
        Add a mapping to this Attr, creating a new, merged Attr.

        other: A mapping.

        NOTE: Addition is not commutative. a + b != b + a.
        """
        if not isinstance(other, Mapping):
            return NotImplemented

        return self._constructor(merge(self, other), self._configuration())

    def __radd__(self, other: Mapping[K, V]) -> Attr[K, V]:
        """
        Add this Attr to a mapping, creating a new, merged Attr.

        other: A mapping.

        NOTE: Addition is not commutative. a + b != b + a.
        """
        if not isinstance(other, Mapping):
            return NotImplemented

        return self._constructor(merge(other, self), self._configuration())

    def _build(self, obj: Any) -> Attr[K, V]:
        """
        Conditionally convert an object to allow for recursive mapping access.

        obj: An object that was a key-value pair in the mapping. If obj
            is a mapping, self._constructor(obj, self._configuration())
            will be called. If obj is a non-string/bytes sequence, and
            self._sequence_type is not None, the obj will be converted
            to type _sequence_type and build will be called on its
            elements.
        """
        if isinstance(obj, Mapping):
            obj = self._constructor(obj, self._configuration())
        elif isinstance(obj, Sequence) and not isinstance(obj, (str, bytes)):
            sequence_type = getattr(self, "_sequence_type", None)
            if sequence_type:
                obj = sequence_type(self._build(element) for element in obj)

        return obj  # type: ignore

    @classmethod
    def _valid_name(cls, key: Any) -> bool:
        """
        Check whether a key is a valid attribute name.

        A key may be used as an attribute if:
         * It is a string
         * It matches /^[A-Za-z][A-Za-z0-9_]*$/ (i.e., a public attribute)
         * The key doesn't overlap with any class attributes (for Attr,
            those would be 'get', 'items', 'keys', 'values', 'mro', and
            'register').
        """
        return (
            isinstance(key, str)
            and not hasattr(cls, key)
            and VALID_KEY_RE.match(key) is not None
        )


class MutableAttr(Attr[str, V], MutableMapping[str, V], ABC):
    """A ``mixin`` mapping class that allows for attribute-style access of values."""

    def _setattr(self, key: str, value: Any) -> None:
        """Add an attribute to the object, without attempting to add it as a
        key to the mapping."""
        super().__setattr__(key, value)

    def __setattr__(self, key: str, value: V) -> None:
        """
        Add an attribute.

        key: The name of the attribute
        value: The attributes contents
        """
        if self._valid_name(key):
            self[key] = value
        elif getattr(self, "_allow_invalid_attributes", True):
            super().__setattr__(key, value)
        else:
            raise TypeError(
                f"'{self.__class__.__name__}' does not allow attribute creation."
            )

    def _delattr(self, key: str) -> None:
        """Delete an attribute from the object, without attempting to remove it
        from the mapping."""
        super().__delattr__(key)

    def __delattr__(self, key: str, force: bool = False) -> None:
        """
        Delete an attribute.

        key: The name of the attribute
        """
        if self._valid_name(key):
            del self[key]
        elif getattr(self, "_allow_invalid_attributes", True):
            super().__delattr__(key)
        else:
            raise TypeError(
                f"'{self.__class__.__name__}' does not allow attribute deletion."
            )


class AttrDict(dict[str, V], MutableAttr[V]):
    """A dict that implements MutableAttr."""

    _sequence_type: type
    _allow_invalid_attributes: bool

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._setattr("_sequence_type", tuple)
        self._setattr("_allow_invalid_attributes", False)

    def _configuration(self) -> type:
        """The configuration for an attrmap instance."""
        return self._sequence_type

    def __getstate__(self) -> tuple[Mapping[str, V], type, bool]:
        """Serialize the object."""
        return self.copy(), self._sequence_type, self._allow_invalid_attributes

    def __setstate__(self, state: tuple[Mapping[str, V], type, bool]) -> None:
        """Deserialize the object."""
        mapping, sequence_type, allow_invalid_attributes = state
        self.update(mapping)
        self._setattr("_sequence_type", sequence_type)
        self._setattr("_allow_invalid_attributes", allow_invalid_attributes)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({super().__repr__()})"

    @classmethod
    def _constructor(
        cls,
        mapping: Mapping[str, V],
        configuration: type,
    ) -> AttrDict[V]:
        """A standardized constructor."""
        attr = cls(mapping)
        attr._setattr("_sequence_type", configuration)
        return attr
