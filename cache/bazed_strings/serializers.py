from .helpers import (
    KEY_VALUE_SEPARATOR, VALUE_SEPARATOR, WRAPPER_MAP,
    SIMPLE_TYPES, SEQUENCE_TYPES,
    SupportedSimpleTypes, SupportedSequenceTypes, SupportedSerializedTypes)




def dumps(value: SupportedSerializedTypes) -> str:
    """
    Wraps and serializes values of supported types.
    """
    wrapper = WRAPPER_MAP[type(value)]
    return wrap_value(serialize_value(value), wrapper)


def wrap_value(serialized_value: str, wrapper: str) -> str:
    """
    Wraps values of supported types.
    """
    wrapper_start = wrapper + '/'
    wrapper_end = wrapper + '\\'
    return f'{wrapper_start}{serialized_value}{wrapper_end}'


def serialize_simple_value(value: SupportedSimpleTypes) -> str:
    """
    Serializes simple values.
    """
    return f'{value}'


def serialize_builtin_sequence(value: SupportedSequenceTypes) -> str:
    """
    Serializes builtin sequences.
    """
    serialized = []
    for val in value:
        serialized.append(dumps(val))
    return VALUE_SEPARATOR.join(serialized)


def serialize_dict(value: dict) -> str:
    """
    Serializes dicts.
    """
    serialized = []
    for key in value:
        serialized.append(f'{dumps(key)}{KEY_VALUE_SEPARATOR}{dumps(value[key])}')
    return VALUE_SEPARATOR.join(serialized)


def serialize_value(value: SupportedSerializedTypes) -> str:
    """
    Serializes supported values.
    """
    return DATA_SERIALIZERS_MAP[type(value)](value)


DATA_SERIALIZERS_MAP: dict = dict.fromkeys(SIMPLE_TYPES, serialize_simple_value)    # had to annotate here cuz pycharm complaining for no reason.
DATA_SERIALIZERS_MAP |= dict.fromkeys(SEQUENCE_TYPES, serialize_builtin_sequence)   # pycharm type hinting is so bad...
DATA_SERIALIZERS_MAP[dict] = serialize_dict
