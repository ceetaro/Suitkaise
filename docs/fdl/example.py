# FDL examples will be added once the API is implemented

from suitkaise import fdl

# EXAMPLE 1 - variables ------------------------------------------------

# basic, plain string
fdl.print("What's up, World?")

# instead of using f-strings (f"{value} text"), use this to sub variables!
username = "Pickles64"

fdl.print("What's up, <username>?", username)

# result: "What's up, Pickles64?"

# for multiple variables...
username = "Speedman"
login_msg = "Today is a great day,"
end = "!"
# the representation in the <> doesn't have to directly match, it is there to help you organize your vars
# but you should try to match them perfectly!

# best practice
fdl.print("<login_msg> <username><end>", (login_msg, username, end))

# can work, not recommended
fdl.print("<msg> <name><end>", (login_msg, username, end))

# result: "Today is a great day, Speedman!

# does NOT work
fdl.print("<> <><>", (login_msg, username, end))

# EXAMPLE 2 - basic text formatting ------------------------------------

# add bold text to the whole message
username = "Speedman"
login_msg = "Lookin' good,"
end = "!"

# use </command> syntax to format text
# bold: </bold>
fdl.print("</bold><login_msg> <username><end>\n", (login_msg, username, end))

# result: Lookin' good, Speedman! 
# - whole message is bold text.

# use multiple commands at once
# italic: </italic>
fdl.print("</bold, italic><login_msg> <username><end>\n", (login_msg, username, end))

# result: Lookin' good, Speedman! 
# - whole message is bold text.
# - whole message is italicized text.

# EXAMPLE 3 - end commands early --------------------------------------

username = "Speedman"
login_msg = "Lookin' good,"
end = "!"

# use </end command> to end a command
fdl.print("</bold><login_msg></end bold> <username><end>", (login_msg, username, end))

# result: Lookin' good, Speedman! 
# - "Lookin' good" is bold text, rest of message is not.

# use multiple end commands at once
fdl.print(
    "</bold, italic><login_msg></end bold, italic> <username><end>", 
    (login_msg, username, end)
)

# order doesnt matter when ending commands, as long as they have been started
# but we recommend that you order them the same way! (</bold, italic>, </end bold, italic>)

# this still works:
fdl.print(
    "</bold, italic><login_msg></end italic, bold> <username><end>", 
    (login_msg, username, end)
)

# result: Lookin' good, Speedman! 
# - "Lookin' good" is bold text, rest of message is not.
# - "Lookin' good" is italicized text, rest of message is not.

# end one command but keep the others
fdl.print(
    "</bold, italic><login_msg></end italic> <username><end>", 
    (login_msg, username, end)
)

# result: Lookin' good, Speedman! 
# - whole message is bold text.
# - "Lookin' good" is italicized text, rest of message is not.

# EXAMPLE 4 ------------------------------------------------------------

# EXAMPLE 5 ------------------------------------------------------------