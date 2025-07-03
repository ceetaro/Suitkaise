my_list = [
    "hello",
    "world",
    "this",
    "is",
    "a",
    "test",
    "of",
    "the",
    "list",
    "functionality"
]

my_dict = {
    "key1": "value1",
    "key2": "value2",
    "key3": "value3",
    "key4": "value4",
    "key5": "value5"
}

my_set = {
    "apple",
    "banana",
    "cherry",
    "date",
    "elderberry"
}

my_tuple = (
    "first",
    "second",
    "third",
    "fourth",
    "fifth"
)

my_int = 42
my_float = 3.14
my_bool = True
my_none = None
my_bytes = b"byte string"
my_complex = 1 + 2j
my_range = range(10)
my_frozenset = frozenset(["frozen1", "frozen2", "frozen3"])
my_bytearray = bytearray(b"bytearray string")
my_dict_of_lists = {
    "list1": ["item1", "item2", "item3"],
    "list2": ["item4", "item5", "item6"]
}
my_dict_of_sets = {
    "set1": {"item1", "item2", "item3"},
    "set2": {"item4", "item5", "item6"}
}
my_dict_of_tuples = {
    "tuple1": ("item1", "item2", "item3"),
    "tuple2": ("item4", "item5", "item6")
}

def nlprint(*args, **kwargs):
    """
    Print each argument on a new line.
    
    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments (not used).
    """
    for arg in args:
        try:
            print(arg)
        except Exception as e:
            print(f"Error printing argument {arg}: {e}")


nlprint(
    my_list,
    my_dict,
    my_set,
    my_tuple,
    my_int,
    my_float,
    my_bool,
    my_none,
    my_bytes,
    my_complex,
    my_range,
    my_frozenset,
    my_bytearray,
    my_dict_of_lists,
    my_dict_of_sets,
    my_dict_of_tuples
)