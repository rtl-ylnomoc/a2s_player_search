from typing import TypeVar


KEY_VALUE_SEPARATOR = ':__:'       # Serialized Python colon (:)
VALUE_SEPARATOR = ',__,'           # Serialized Python comma (,)
assert KEY_VALUE_SEPARATOR != VALUE_SEPARATOR

WRAPPERS = [    # Wrappers (length = 4 characters) of values of corresponding supported serialized types:
    '[12]',             # bool
    '[SG]',             # str
    '[IR]',             # int
    '[FT]',             # float
    *['[SE]']*2,        # Sequence(list, tuple).
    '[DY]',             # dict
]

# region TYPING

# It would be cleaner if I could combine typevars or unwrap in their arguments from tuples...
SEQUENCE_TYPES = (tuple, list)
COMPLEX_TYPES = (*SEQUENCE_TYPES, dict)
SIMPLE_TYPES = (bool, str, int, float)
DESERIALIZED_TYPES = (*SIMPLE_TYPES, list, dict)
SERIALIZED_TYPES = (*SIMPLE_TYPES, *COMPLEX_TYPES)

SupportedSequenceTypes = TypeVar('SupportedSequenceTypes', tuple, list)
SupportedComplexTypes = TypeVar('SupportedComplexTypes', tuple, list, dict)
SupportedSimpleTypes = TypeVar('SupportedSimpleTypes', bool, str, int, float)
SupportedDeserializedTypes = TypeVar('SupportedDeserializedTypes', bool, str, int, float, dict, list)  # no tuple.
SupportedSerializedTypes = TypeVar('SupportedSerializedTypes', bool, str, int, float, dict, list, tuple)

# endregion

WRAPPER_MAP = dict(zip(SERIALIZED_TYPES, WRAPPERS))
UNWRAPPER_MAP = dict(zip(WRAPPERS, DESERIALIZED_TYPES))