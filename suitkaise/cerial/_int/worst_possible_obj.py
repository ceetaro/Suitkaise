# there will be 3 levels of nested classes.

# each level will have all cerial-supported objects (primitives and complex objects that handlers can handle) as attributes
# outside of collections

# each level will also generate a random nested collection for every collection type
# - random depth
# - adds random objects (primitives and complex objects) to the collection at each level
# - if the depth is != to random depth generated, adds a random collection to the current level and repeats process

# this randomness from each WorstPossibleObject instance shows that cerial can actually handle everything.

# - tuple
# - list
# - set
# - frozenset
# - dict
# - range objects
# - slice objects
# TODO any others???
COLLECTION_TYPES = [tuple, list, set, frozenset, dict, range, slice]

BASE_PICKLE_SUPPORTED_TYPES = [None, True, False, int, float, complex, str, bytes, bytearray, type, Ellipsis, NotImplemented]

COMPLEX_TYPES_THAT_CERIAL_CAN_HANDLE = 

SUITKAISE_SPECIFIC_TYPES = 

class WorstPossibleObject:

    def __init__(self):
        
        self.init_all_base_pickle_supported_objects()
        self.init_all_complex_types_in_random_order()

        copy = COLLECTION_TYPES.copy()
        random.shuffle(copy)

        for collection_type in copy:
            self.generate_random_nested_collection(collection_type)


    def init_all_base_pickle_supported_objects(self):
        # init all objects that base pickle can handle

    def init_all_complex_types_in_random_order(self):
        # init all complex, unpickleable objects that cerial will handle in random order

    def generate_random_nested_collection(self, collection_type):
        # generate a random nested collection of primitives, collections, and complex objects
        # return the collection

    class Nested1:

        def __init__(self):
            super().__init__()

    
        class Nested2:

            def __init__(self):
                super().__init__()


        
        class Nested3:

            def __init__(self):
                super().__init__()


                class Nested4:

                    def __init__(self):
                        super().__init__()
                        
                        