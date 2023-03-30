from .helpers import (
    KEY_VALUE_SEPARATOR, VALUE_SEPARATOR, WRAPPERS, WRAPPER_MAP,
    SupportedDeserializedTypes)


def find_excluded_ranges_for_type(string: str, value_type: type) -> list[range]:  # cant use Literals cuz typing in python is insufferable
    """
    Finds ranges on which all outer supported complex data structures of a given type span.
    Note: doesn't find ranges for inner complex data structures and ignores them.
    """
    start_wrapper = WRAPPER_MAP[value_type] + '/'
    end_wrapper = WRAPPER_MAP[value_type] + '\\'
    start_flag = False          # could live with only ignore_end_wrappers var, but it would make me check for 3 possible values
    start_is = []
    end_is = []
    ignore_end_wrappers = 0     # amount of end wrappers for loop has to ignore based on encountered start wrappers
    for i in range(4, len(string)):
        first_bi = i - 4        # first buffer index
        postlast_bi = i + 1     # post-last buffer index
        buffer = string[first_bi:postlast_bi:]

        if not start_flag and buffer == start_wrapper:  # could have nested ifs but apparently it's bad code
            start_flag = True
            start_is.append(first_bi)  # '{i-6}[buffer]{i}' where len buffer == 5
        elif not start_flag and buffer == end_wrapper:
            raise ValueError('Invalid string.')
        elif start_flag and buffer == start_wrapper:
            ignore_end_wrappers += 1
        elif start_flag and buffer == end_wrapper and ignore_end_wrappers:
            ignore_end_wrappers -= 1
        elif start_flag and buffer == end_wrapper and not ignore_end_wrappers:
            end_is.append(postlast_bi)
            start_flag = False
        # print(buffer, ignore_end_wrappers, start_flag)  # uncomment for snake :D
    ranges = [range(start_is[i], end_is[i]) for i in range(len(end_is))]
    return ranges


def is_in_bad_range(i: int, bad_rngs: list[range]) -> tuple[bool, int, int]:
    """
    Checks if indexes are in complex data and returns its boundaries.
    """
    for bad_rng in bad_rngs:
        if i in bad_rng:
            return True, bad_rng.start, bad_rng.stop
    return False, -1, -1


def deserialize_dict(string: str) -> dict:
    """
    Deserializes unwrapped dict strings.
    """
    deserialized_dict = {}
    bad_rngs = find_excluded_ranges_for_type(string, dict) + find_excluded_ranges_for_type(string, list)
    kv_sep_i = 0    # First key value separator index
    v_sep_i = 0     # First value separator index
    # kv_sep_i = string.find(KEY_VALUE_SEPARATOR)     # First key value separator index
    # if kv_sep_i == -1:  # Case when no key value separator -> no values in dict.
    #     return {}
    # wrapped_key = string[:kv_sep_i:]
    # unwrapped_key = loads(wrapped_key)
    # v_sep_i = string.find(VALUE_SEPARATOR, kv_sep_i)    # First value separator index
    # print(string[kv_sep_i:v_sep_i:])
    # if v_sep_i == -1:   # Case when no value separator -> it's only one value in dict.
    #     return {unwrapped_key: loads(string[kv_sep_i + len(KEY_VALUE_SEPARATOR)::])}
    # complex_data_flag, complex_data_start, complex_data_stop = is_in_bad_range(v_sep_i, bad_rngs)
    # if complex_data_flag:
    #     print(string[complex_data_start:complex_data_stop], 'YEBAT MOY HUY\n\n\n\n\n\n')
    #     v_sep_i = complex_data_stop
    #     wrapped_value = string[complex_data_start:complex_data_stop]
    # wrapped_value = string[kv_sep_i + len(KEY_VALUE_SEPARATOR):v_sep_i:]
    # unwrapped_value = loads(wrapped_value)
    # deserialized_dict = {unwrapped_key: unwrapped_value}
    while True:
        kv_sep_i = string.find(KEY_VALUE_SEPARATOR, v_sep_i)
        if kv_sep_i == -1:  # Case when no key value separator -> no values left in dict.
            break
        wrapped_key = string[v_sep_i + len(VALUE_SEPARATOR)*(v_sep_i != 0):kv_sep_i:]
        unwrapped_key = loads(wrapped_key)
        v_sep_i = string.find(VALUE_SEPARATOR, kv_sep_i)
        if v_sep_i == -1:   # Case when no value separator -> it's only one value left in dict.
            v_sep_i = len(string)
        complex_data_flag, complex_data_start, complex_data_stop = is_in_bad_range(v_sep_i, bad_rngs)
        if complex_data_flag:
            v_sep_i = complex_data_stop
            wrapped_value = string[complex_data_start:complex_data_stop]
        else:
            wrapped_value = string[kv_sep_i + len(KEY_VALUE_SEPARATOR):v_sep_i:]
        unwrapped_value = loads(wrapped_value)
        deserialized_dict[unwrapped_key] = unwrapped_value
    return deserialized_dict


def deserialize_builtin_sequence(string: str) -> list:
    """
    Deserializes unwrapped sequence strings.
    """
    if string == '':    # Case when string is empty -> no values in list.
        return []
    bad_rngs = find_excluded_ranges_for_type(string, dict)
    bad_rngs += find_excluded_ranges_for_type(string, list)
    v_sep_i = string.find(VALUE_SEPARATOR)
    if v_sep_i == -1:   # Case when no value separator -> it's only one value in list which takes the entire string argument.
        return [loads(string)]
    wrapped_value = string[:v_sep_i:]
    unwrapped_value = loads(wrapped_value)
    deserialized_seq = [unwrapped_value]
    while v_sep_i != len(string):
        prelast_v_sep_i = v_sep_i   # Prelast value separator index
        v_sep_i = string.find(VALUE_SEPARATOR, v_sep_i + 1)
        if v_sep_i == -1:
            v_sep_i = len(string)
        complex_data_flag, complex_data_start, complex_data_stop = is_in_bad_range(v_sep_i, bad_rngs)
        if complex_data_flag:
            v_sep_i = complex_data_stop
            wrapped_value = string[complex_data_start:complex_data_stop]
        else:
            wrapped_value = string[prelast_v_sep_i + len(VALUE_SEPARATOR):v_sep_i:]
        unwrapped_value = loads(wrapped_value)
        deserialized_seq.append(unwrapped_value)
    return deserialized_seq


def loads(string: str) -> SupportedDeserializedTypes:
    """
    Unwraps and deserializes strings converting their values in the supported deserialized types.
    """
    wrapper, unwrapped = unwrap_value(string)
    return deserialize_value(wrapper, unwrapped)    # type: ignore # random mypy type error


def unwrap_value(string: str) -> tuple[str, str]:
    """
    Unwraps value strings.
    """
    wrapper = string[:4:]
    unwrapped = string[5:-5:]
    return wrapper, unwrapped


def deserialize_bool(string: str) -> bool:
    """
    Deserializes unwrapped bool strings.
    """
    return string == 'True'


def deserialize_str(string: str) -> str:
    """
    Deserializes unwrapped str strings.
    """
    return string


def deserialize_int(string: str) -> int:
    """
    Deserializes unwrapped int strings.
    """
    return int(string)


def deserialize_float(string: str) -> float:
    """
    Deserializes unwrapped float strings.
    """
    return float(string)


def deserialize_value(wrapper: str, unwrapped: str) -> SupportedDeserializedTypes:
    """
    Deserializes unwrapped value strings.
    """
    # print(wrapper, unwrapped)
    return DATA_DESERIALIZERS_MAP[wrapper](unwrapped)   # type: ignore # random mypy type error


DESERIALIZERS = [
    deserialize_bool, deserialize_str, deserialize_int, deserialize_float, deserialize_builtin_sequence, deserialize_dict]
DATA_DESERIALIZERS_MAP = dict(zip(list(dict.fromkeys(WRAPPERS)), DESERIALIZERS))
