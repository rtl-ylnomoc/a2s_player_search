"""
A package that serializes and deserializes data in and from text for caching and other possible cases.
The format is my creation and it looks like a kind of a single-line XML.

P.S. Writing this package made me switch from PyCharm back to VSCode and reconsider my Python typing approach.
"""


from . import serializers
from . import deserializers
from . import disorders

# region TESTING

# def serialize_deserialize_test(data: SupportedSerializedTypes):
#     serialized_data = dumps(data)
#     print(f'SERIALIZED:\n\n{serialized_data}\n')
#     deserialized_data = loads(serialized_data)
#     print(f'DESERIALIZED:\n\n{deserialized_data}\n')
#     for key, val in data.items():
#         if type(val) is tuple:
#             val = list(val)
#         assert val == deserialized_data[key]
#     print(data == deserialized_data)   # won't be true if serialized data has tuples.


# def order_disorder_test(data: SupportedSerializedTypes):
#     ordered_data = OrderedDict(data)
#     disordered_data = disorder_value(ordered_data)
#     print(disordered_data)


# if __name__ == '__main__':
#     to_test_list = []
#     to_test_list.append(
#         {
#             "stryng": {'cur': ['123', '213', '321'], 'flags': {'on': True, 'off': False}}
#         }
#     )
#     to_test_list.append(
#         {
#             "stryng": ['cur', ['123', '213', '321'], 'flags', {'on': True, 'off': False}]
#         }
#     )
#     # to_test_list.append({
#     #     'k1': {True: 1},
#     #     'k2': 'v2',
#     #     'k3': (3, 2, 1),
#     #     'k4': 4.0,
#     #     '1': {
#     #         'ik1': False,
#     #         'ik2': {'iiv1': [[1]]},
#     #         'ik3': [30],
#     #         'ik4': 4.1
#     #     },
#     #     'k6': 'zdarova',
#     #     'k7': 11,
#     #     'k8': [1, {'ik1': True}, 3]
#     # })
#     # to_test_list.append({'1': {}})
#     # to_test_list.append({})
#     # print(to_test_list[0])
#     # print(OrderedDict(sorted(to_test_list[0].items(), key=lambda x: x[0])))
#     with open(r'data\names_test.txt', encoding='utf-8') as f:

#         print(loads(f.read()[7::]))
#     for to_test in to_test_list:
#         order_disorder_test(to_test)
#         serialize_deserialize_test(to_test)

# endregion
