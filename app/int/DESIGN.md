| -------------------------------------------------------------------------------------
| Copyright 2025 Casey Eddings
| Copyright (C) 2025 Casey Eddings
|
| This file is a part of the Suitkaise application, available under either
| the Apache License, Version 2.0 or the GNU General Public License v3.
|
| ~~ Apache License, Version 2.0 (http://www.apache.org/licenses/LICENSE-2.0)
|
|       Licensed under the Apache License, Version 2.0 (the "License");
|       you may not use this file except in compliance with the License.
|       You may obtain a copy of the License at
|
|           http://www.apache.org/licenses/LICENSE-2.0
|
|       Unless required by applicable law or agreed to in writing, software
|       distributed under the License is distributed on an "AS IS" BASIS,
|       WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
|       See the License for the specific language governing permissions and
|       limitations under the License.
|
| ~~ GNU General Public License, Version 3 (http://www.gnu.org/licenses/gpl-3.0.html)
|
|       This program is free software: you can redistribute it and/or modify
|       it under the terms of the GNU General Public License as published by
|       the Free Software Foundation, either version 3 of the License, or
|       (at your option) any later version.
|
|       This program is distributed in the hope that it will be useful,
|       but WITHOUT ANY WARRANTY; without even the implied warranty of
|       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
|       GNU General Public License for more details.
|
|       You should have received a copy of the GNU General Public License
|       along with this program.  If not, see <https://www.gnu.org/licenses/>.
|
| -------------------------------------------------------------------------------------

~ suitkaise/int/DESIGN.md

# Suitkaise

## Main Features
Suitkaise offers a comprehensive set of tools for developers to use in their projects.
It is designed to be easily understandable and widely accessible, making the lives
of both new and experienced developers easier. Tools will be able to visualize data or 
relationships, automate tasks, and provide useful information about the project. It 
will be your best friend.

It can integrate with any project, and can run standalone or alongside the main application.

Suitkaise's name derives from suitecases, which are used to carry tools and equipment,
and the Japanese words "kaihatsu" (development) and "kaiseki", which can mean the 
collection of skills a traditional Japanese chef needs to make a "kaiseki" meal.

Pronounced like "suitcase". Abbreviated as "SK".

It does this with a special feature, Gate, which allows the use of a generalized set 
of developer tools, but keeps the devtools separate from the main application.
The Gate gathers all of the events sent out from the Suitkaise, and converts them into
signals and formats that the main application can understand. It also converts signals
from the main application into events that the Suitkaise can understand.

While the user has to do this themselves, as every project is different, the Gate
comes with a comprehensive Ruleset feature that provides the user with the correct
format for the events and signals.

## Gate
The Gate needs 5 main components to function:

1. The Gate itself, which converts data or signals from the devtools into a format
that the main application can understand, and vice versa.

2. DevBus, which is the event bus that comes with the Suitkaise.

3. An event bus for the main application to communicate with Gate.

4. A Ruleset that matches events from the DevWindow to events made in the main application.

5. A Switch that opens and closes the Gate.

## Main Directories

### App
App is where the main application content and handling will go.

The Suitkaise application is an application that can also generate code to 
add to directories in a user's project.

### Default
Default is where default objects, functions, utilities, and other components will go.
This is separate from App for the sake of organization and separation of concerns.

### Setup
Setup is where the project root will be defined, so that absolute imports can be used.
It will run in App/main to initalize the project structure.

It will also be able to print the project structure to the console, and file contents.
(including warnings or missing filepaths)

### Test
Test is where the test files will go. It will mirror App and automatically update
when App's structure changes.

### Docs
Docs is where the documentation for the project will go.


## Tools

### Dprint
Dprint is a tool that streamlines and collates debug prints within the project.
It displays them in a table format with searching and filtering options, and can
also print them to the console.

### FileImporter 
FileImporter is a tool that generates filepath imports for a user's main
application using either Importlib or absolute imports. Before the user interacts
with FileImporter for the first time, they will be prompted to select the type of 
import they want to use.

### Finder
Finder is a package tool that contains multiple tools for finding and displaying
different elements of a project and their relationships within the code.

It contains a Class Finder, Function Finder, Import Finder, and Variable Finder.

### Subscriber
Subscriber is a tool that visualizes events that objects are subscribed to, and
allows you to manage and edit them. By adding the Subscriber to an object, you can
visually create events that the object can subscribe to. Multiple instances of the 
object can be created, and they can all subscribe to different events at different
times.

### Lighthouse
Similar to Subscriber, Lighthouse is a tool that visualizes signals that objects are
sending and receiving. By adding the Lighthouse to an object, you can visually create
and view signals and their connections.

### Ledger
Ledger is a tool that visualizes transactions and data flow within the project.
Using the ACID principles, Ledger can manage and display data transactions and 
information about them.

### Permissions
Permissions is a tool that manages and displays permissions for different objects.
By registering objects with Permissions, you can manage what objects can interact with 
data, and how much access they have.

### Tree
Tree is a tool that visualizes the project structure in a tree format. It can be
edited to look cool, and can be exported to a file or copied to the clipboard.
It can also do this for lower levels of the project structure.

It also checks for errors or potential issues in the project structure.

### Utilities
Manages and visualizes both created utilities registered here and shows when they are
used and how many times in real time. Can also show the code for the utility.

### TestGen
TestGen is a tool that generates test files for the project. It can generate and 
automatically update test files for the project. However, it will not generate
file contents, only the file structure and imports.

### Tester
Tester is a tool that runs tests for the project. It can run tests for the entire
project, or for specific files or directories. It can also run tests for specific
functions or classes.

### UIB (UI Builder)
UIB is a suite of tools that help build and visualize the UI of the project, and 
edit it in real time. It contains the following tools:

#### Snapshot
Snapshot is a tool that separates every UI element registered with it into individual
snapshots. It can run and display these individual elements by themselves, so that 
you can see how they look on their own. you can select multiple snapshots in the same 
layout or lower level layout and view them together.

#### Layout
Visualizes the UI layout of an application. Instead of displaying the UI elements
themselves, it displays simple boxes named after each element. This can be used to
easily check and understand issues in the layout of the application. Also allows for 
the user to drag the boxes around to change the layout. Uses a scene similar to using
collapsed graph nodes from Unreal Engine.

#### Style
Style manages and allows you to edit the style of the UI elements in an easy to 
understand way. It does this 

#### Presets
Saves and changes created setups for the UI.

#### UIT (UI Tester)
UIT is a tool that tests the UI of the project. It can run tests for the entire app, or 
for specific combinations of components. It can tell the user things like if parts of a 
component are being cut off, and show the whole component and simple data on hover.

### Matrixer

Tool for creating matrixes with an easier visual representation.


### Minmaxer
Scans the code and manages diagnostics and performance. Finds issues where code is
inefficient or duplicate. Can also find memory leaks.

### Publisher
Handles licensing and publishing of the project in a simpler way. Generates official
documents and E-signatures that the user can use as well.

### Docu
Helps the user create .md files for project documentation. It can also generate a
report-like summary of the README contents.

### Commenter
Helps the user create comments for their code and formats them in a cleaner visual.

### Crypt
Encrypts and decrypts files and data. Can also generate keys and manage them.

### GoldenSafe
Manages and stores sensitive data in a secure way. Helps the user "lock" data that they
don't want any prospective consumers to access. Does its best to enhance cybersecurity.

### Accounter
Manages and stores user accounts and data. Can also generate and manage user data.
Holds this as cloud data.

### Converter
responsible for the conversion of application content to different sources, like 
to GitHub.

### not yet named
Visualizes different processes to help with things like tracking if an object data type
is properly validated at the correct times. can track certain data or objects and see how they travel. this works by having objects and attributes registered in .sk files.

### C10UD
Creates and manages the project data and files in the cloud for the user, so they 
don't have to worry about data loss, and can access their project from anywhere.
Also helps with collaboration.

### Editor
Helps the user create an editor window for their application. Can choose from several
options, like text editor, code editor, image editor, node canvas, or spreadsheet. Editors
are all supported and accounted for in the Suitkaise, and will be designed to be scalable
and adaptable to the user's needs. 

~ Sound and video editors coming soon ~ 
~ Graph coming soon ~

#### Text Editor
Text Editor is a tool that allows the user to create and edit text files in a simple
to understand way. Can format the text easily, and leads to options to export to places
like Word or Google Docs. Intended (but not limited to) be used to let companies have
customizable text editors and document writers, with the special feature, Format,
a toggle that allows much more dynamic and intuitive formatting.

#### Code Editor (currently only Python and SQL supported)
Code Editor is a tool that allows the user to create and edit code files in a simple
to understand way. Can format the code easily, and leads to options to export to places
like Visual Studio Code. Makes it really easy to edit color schemes and themes, for things
like user preference or accessibility. Also has a special feature, Sink, that automatically
syncs the code in VSCode, can send it to emails, upload to Github, an internal serverm 
or a cloud service.

#### Image Editor
Image Editor is a tool that allows the user to create and edit images in simple ways.
Contains: Transparent Backgrounder, RPP (Reference Pictures Packager), Pallet (Palette),
and PrinterPress (for export conversion).

#### Node Canvas
Node Canvas is a tool that initializes a powerful node editor for the user. Has similarites
to Unreal Engine's Blueprint system, and can be used to create and manage complex systems
with custom properties. However, the Node Canvas is different from Unreal Engine's Blueprint
system in its structure design, using Levels, Paths, and Tunnels to organize the nodes in a
more row/column type format. It sets up the Node Designer, which allows the user to create and
move node components to create custom nodes.

#### Spreadsheet
Allows the user to create and edit spreadsheets in a simple to understand way. Can
format the data easily, and leads to options to export to Excel.

#### Db
Creates and manages a database for the user. Can create and manage tables, and
manipulate data in the tables. Contains Table, Ship, and Querie, and is created
in SQL.

##### Table
Allows for the creation and management of tables in the database. Allows prospective
users to create and manage tables in the database. Contains columns and rows.

##### Ship
Manages relationships between tables in the database.

##### Querie
Allows for the creation and management of queries in the database. Simplifies the process
and UI for creating and managing queries in a database.

#### Sound Editor
~ coming soon ~

#### Video Editor
~ coming soon ~

#### Graph
Graph is a tool similar to Desmos, that allows the user to create and edit graphs. It has features
that allow the user to more easily create, import, export and edit math data being displayed.
Graph can connect to other editors, like the Code Editor, Spreadsheet, and Node Canvas, to make
the creation of formulas, expressions, numbers, and equations easier.

### CheatSheet
CheatSheet is a tool that references and displays code snippets and information about how 
to use certain Python libraries and functions. It can also be tagged to filter if someone
searches up a question or a specific library. I will make this tool as I create the other
tools, so that someone else in the development process might find the info relevant.

### Theater
Theater is a tool that allows the user to create input actions from multiple devices.
Supports keyboard, mouse, and trackpad inputs. Comes with the tool Combo, which allows
the user to create combinations of inputs that can be used to trigger events.

~ Controller support coming soon ~
~ Touchscreen support coming soon ~
~ VR support coming soon ~
~ Voice support coming soon ~

### Ai-Chan
Ai-Chan is a tool that allows the user to create and manage AI for their project. An interface allows
the user to develop and resolve solutions to teach Ai-Chan how to specifially interact with 
the application. Contains a special feature that allows the user to create animated
models of the AI to interact with, and Screen, which allows the AI to watch the application
and suggest improvements to code. Ai-chan will become a VSCode extension in the future, once
AI priveledges and general understanding of data privacy and security are improved. Ai-chan can 
also be used with an AI model API from a current AI service.

The specialization of AI models for specific applications is something that does not really 
exist in the current landscape of AI services. I want to try and create something that will
allow the user to create and manage AI models that are specifically tailored to their project,
to help consumer understand the application better.

Ai-Chan works with the Suitkaise devtools while the user is developing the project, and can
be a feature of the main application once the project is finished. Ai-Chan's name and base
model can be changed to Ai-sama, Ai-san, Ai-kun, or Ai, depending on the user's preference.
The model will change its appearance and personality to match the name.

Note: AI services will not come installed, so that those who feel that AI is a threat to their
personal data have the option to not use it.

### Backup
Backs up project data and files in a secure way. Helps the user "lock" data that they want
to restrict access to.

Also has a feature that allows the user to implement a backup system for their project.


## Internal Features for Suitkaise

### DevBus
DevBus is the event bus that comes with the Suitkaise. It is used to manage and send events from
the devtools to the Gate.

### DevWindow
DevWindow is the main window that contains all of the tools in the Suitkaise. It is the main
application interface for managing and using tools in the Suitkaise.

#### Context Menu
Right click context menus depending on where you click in the DevWindow. Manages all 
context menus for the Suitkaise.

#### OS Menu Bar
Manages the OS menu bar for the DevWindow (example, the top bar on a Mac, or the right click options
on an open Windows application). Manages all OS menu bar options for the Suitkaise.

#### Tool Bar
Manages the tab bar for the DevWindow. Manages all open tabs and the tools instanced in each tab's
window. Also manages the logic for standard tab functionality.

#### Command Line
Users can run set commands from the command line using /(command). Commands will filter when
the user types to match possible commands.

#### In house file manager

### Ruleset (Gate)
Ruleset is a feature that comes with the Gate. It allows the user to connect events from the 
DevBus to the main application's event bus. It also allows the user to connect signals from the
main application to the DevBus. Generates or updates code to connect the events and signals.
Also displays conversions of arguments or data types in a simpler way.

### Switch (Gate)
Turns the gate on and off. Gate should be turned off once main application is finished.
Gate being off will not affect imported objects from devtools, but it stops the DevBus from
sending signals to the main application. When Gate is locked, a password is required to unlock it,
and there is no way for a consumer to access any option to even try to reopen the Gate, thanks to 
the feature Dispel.

#### Dispel (Gate)
Dispel is a feature that comes with the Gate, and only can be used while Gate is locked. 
It allows the user to disconnect the Gate from the main application, and generates an 
updated code structure for the main application. The updated code structure is a copy, 
that can be used to patch the main app, while keeping Gate in the dev environment. Once 
Dispel is used and a copy is successfully made, the Gate can be reopened with Summon.

#### Summon (Gate)
Reinializes the Gate into a locked state.

### Tutorials
Manages tutorial links for all tools in the Suitkaise.

~ Tutorial AI coming soon ~

### Toggle
Toggles access for tools to work on the Suitkaise project during development.



### 

## File structure of subdirectories
Note: I want these to make sense to my brain, and others too, so they will not all be industry
standard naming practices. If you have an issue with this, then you are probably not the 
target audience for this project (you are too high level!). If you want to fork this project
and make it more industry standard, please email me at ----- (not made yet)

Naming conventions will be as follows:
All folders will be PascalCase, and all files will be snake_case. each class and function
will have a docstring (''' ''') at the top of the code block, listing arguments, return values,
and a brief description of the function.

For specific components (the Tools) of the Suitkaise, the file structure will be as follows:

### top of section
the top layer of a subdirectory will contain a manager file that will collect all of the
components of the section, named (section).py. 

### Features
Features is my name for "core" folders. It will contain a manager file, MGR.py, that will
collect the features and manage them. It will also have a README.md file that will contain
detailed information about the features present. Each separate feature will have its own 
README.md file that will contain things like code examples, use cases, arguments, etc, present
in Docs.

#### Val
Val is where the validation logic for this section will go. Communicates with VALS.py.

### UI
UI is where components that are used in the UI for this section will go. It will always have a
Style, Layout, Misc, Settings, and Content subfolder.

#### UIP
The UIP packages and sends this sections data to UIB, or temporarily to the devbus.

#### Content
Content is where the actual UI elements will go. each individual component will be separated, 
and empty widgets that get attached to layouts will be created separately.

#### Layout
Layout is where the layout logic for this section will go. It will contain layout00.py, and then
layout11, layout12, etc. for each layout that is created and where they go. 11 means the leftmost
part of the highest vertical layout. There will also be a file that sends this layout organization
to UIB. note that main application layouts should follow this same pattern that the Suitkaise uses,
as the Suitkaise will be able to read and understand the layout structure of the main application.

#### Style
Style is where the style logic for this section will go. It will contain style.py, the main organizer
for the style of the section. It will have a manager class, and then a class that holds the style
registry. The style registry will contain the styles for each individual component in the section,
and can be edited in real time using the UIB. Until UIB is created, barebones styles will be created
to just visualize the components.

#### Settings
Settings is where the settings logic for this section will go. Things that would usually go in a 
"config" file.

#### Misc
Misc is where miscellaneous media like PNGs or animations will go. It will also contain a file that
sends this media to UIB.

#### Val
Val is where the validation logic for this section will go. Communicates with VALS.py.

### Data
Data is where the data logic for this section will go. It will contain a manager file that will
collect the data logic. It will also contain a README.md file that will contain detailed information
about how data storage and formatting will work. Contains Format, Storage, Cache, and Meta.

#### Format
This is where data formatting will be handled. It will contain a manager file that will collect 
all of the different formats that the section uses.

#### Storage
Handles the logic for storing data. Only the storage subfolder can send authorized signals and 
transfer data to be stored.

#### Cache
Handles the logic for caching data. Handles caching data in files or in memory.

#### Meta
Handles the information or tags that are attached to data. Can be used to organize data and
validate it. Or ensure it filters correctly.

#### Val
Handles the validation of data. Communicates with VALS.py to validate data.


### Events
Handles the events that are sent and received in this section. Outside this folder will contain 
a manager file that will collect all of the events that the section uses. It will also contain a 
README.md file that will explain the events that are used in the section, their types, and how 
they are used. Contains Send, Receive, and Queue.

Events can be registered to EVENTS.py just by creating an event anywhere in the section. Every event
must be sandwiched between 2 validation checks. Created events can use Add_Signal to add signals 
to the event, and can use Add_Data to add data to the event. Events can also use Add_Event to add 
subevents to the event.

#### Send
Handles the sending of events. Only the send subfolder can send authorized signals and transfer data
to be sent to the DevBus.

#### Receive
Handles the receiving of events. Only the receive subfolder can receive authorized signals and data
from the DevBus.

#### Queue
Handles the queuing of events. When validations are created, they can include logic that will 
handle the queuing of events. This is useful for when the main application is busy and cannot 
handle the event, or if events must be sent in a specific order.

#### Val
Handles the validation of events. Communicates with VALS.py to validate events.

### Signals
Handles the signals that are sent and received in this section. Outside this folder will contain
a manager file that will collect all of the signals that the section uses. It will also contain a 
README.md file that will explain the signals that are used in the section, their types, and how they
are used. Contains Send and Receive.

This is similar to the Events folder, but deals with the more direct signals instead of events.

### Utils
Contains utility functions that are used in the section. It will contain a manager file that will
collect all of the utility functions that the section uses. Sends the utility functions to the
Utilities tool. For a set of default utility functions, see the Default folder.


### Transactions
Transactions are the data that is sent and received in the Suitkaise. They will be stored here, and
have a set of tags that will allow them to be easily searched and filtered in Ledger.


## Connections to other Tools
While implementing the Suitkaise, I will be connecting things like events and signals to relevant
tools to implement smaller scale concepts. For example, I will be connecting the signals from
everywhere to the Lighthouse. This will allow me to see the signals that are being sent and received,
and refine the logic to initialize these signals to work with LightHouse. 

While developing, I should still be able to let the devtools use each other, as if the Suitkaise
and the Devwindow are the main application. This will allow me to test the tools and see how they
interact with each other. Additionally, it makes it simpler to update the tools, as I don't have
to create a fake main application to test the tools.

I also want SK to be a somewhat of a project management tool, so later on I will add a code editor for creating applications (not the same as the code editor tool)








