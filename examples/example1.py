# CURRENT basic concepts (fdprint, sktime, skpath)

# fdprint.fprint
from suitkaise.fdprint import fprint

# fprint() - Clean Printed Output

# What it does: Prints data in a clean, user-friendly way
# When to use: For normal output, logs, user messages

# Basic usage
data = {"name": "Alice", "scores": [95, 87, 92]}
fprint("Student info: {}", data)
# Output: Student info: name: Alice
#                       scores: 95, 87, 92

# Multiple values
fprint("Processing {} items for user {}", [1,2,3], "Bob")
# Output: Processing 1, 2, 3 items for user Bob

# Time and date

# Report generated at 16:48:09
fprint("Report generated at {time:now}")

# Current time: 4:48 PM
fprint("Current time: {hm12:now}")

# Today is 2025-07-06
fprint("Today is {date:now}")

# Today is Sunday, July 06, 2025
fprint("Today is {dateword:now}")

my_dict = {"key1": "value1", "key2": "value2"}
fprint("My dictionary: {}", my_dict)

# dprint() - Debug with Details

# What it does: Prints data with type information and timestamps
# When to use: For debugging, development, detailed analysis

from suitkaise.fdprint import dprint

# Basic debug output
user_data = {"name": "Alice", "age": 30}
dprint("User login", (user_data,))
# Output: User login [(dict) {
#           (string) 'name': (string) 'Alice',
#           (string) 'age': (integer) 30
#         }] - 14:30:45.123

# Multiple variables
name = "Bob"
numbers = [1, 2, 3]
dprint("Variables", (name, numbers))
# Output: Variables [(string) 'Bob', (list) [
#           (integer) 1,
#           (integer) 2, 
#           (integer) 3
#         ]] - 14:30:45.123

# Priority levels (1=low, 5=high)
dprint("Minor detail", (), 1)      # Low priority
dprint("Important event", (), 4)   # High priority - shows [P4]





# FINALIZED basic processing concepts, before adding data syncing with Manager
#   or creating the api












# expanded SKGlobal and SKTree concepts
