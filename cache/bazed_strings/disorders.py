"""
This is a module for deordering nested OrderedDicts for serialization purposes.
"""

from .helpers import (
    SupportedSimpleTypes, SupportedSequenceTypes, SupportedSerializedTypes,
    SIMPLE_TYPES, SEQUENCE_TYPES)
from collections import OrderedDict


def disorder_simple_value(value: SupportedSimpleTypes) -> SupportedSimpleTypes:
    """
    Disorders simple values.
    """
    return value


def disorder_builtin_sequence(value: SupportedSequenceTypes) -> SupportedSequenceTypes:
    """
    Disorders builtin sequences.
    """
    disordered = []
    for val in value:
        disordered.append(disorder_value(val))
    return disordered


def disorder_dict(ordered_dictionary: OrderedDict) -> dict:
    """
    Returns dict from OrderedDict
    """
    disordered_dictionary = {}
    for key, value in ordered_dictionary.items():
        disordered_dictionary[key] = disorder_value(value)
    return disordered_dictionary


def disorder_value(value: SupportedSerializedTypes) -> SupportedSerializedTypes:
    """
    Disorders supported values.
    """
    return DATA_DISORDERERS_MAP[type(value)](value)


DATA_DISORDERERS_MAP = dict.fromkeys(SIMPLE_TYPES, disorder_simple_value)  # don't have to annotate this because finally free from pycharm now
DATA_DISORDERERS_MAP |= dict.fromkeys(SEQUENCE_TYPES, disorder_builtin_sequence)
DATA_DISORDERERS_MAP |= dict.fromkeys((OrderedDict, dict), disorder_dict)
