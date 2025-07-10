#!/usr/bin/env python3
"""
Complete Pygments Token Types Reference
Shows every token type with example code and explanations
"""

from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from pygments.style import Style
from pygments.token import (
    Token, Whitespace, Error, Other, Keyword, Name, Literal, String, Number, 
    Punctuation, Operator, Comment, Generic, Escape
)

# Complete custom theme showing ALL token types
class CompleteTokenTheme(Style):
    """
    Complete theme showing every possible token type
    Each token type gets a unique color/style for demonstration
    """
    
    name = 'complete_tokens'
    
    styles = {
        # Base tokens
        Token:                    '#f8f8f2',           # Default text color
        Whitespace:              '',                   # Whitespace (usually transparent)
        Error:                   'bg:#ff0000 #ffffff', # Errors - white text on red background
        Other:                   '#f8f8f2',           # Other/unknown tokens
        
        # Comment tokens
        Comment:                 'italic #6272a4',     # Base comment style
        Comment.Hashbang:        'italic bold #6272a4', # #!/usr/bin/env python
        Comment.Multiline:       'italic #6272a4',     # /* multiline comments */
        Comment.Preproc:         'italic #ff79c6',     # #include, #define
        Comment.PreprocFile:     'italic #ff79c6',     # #include <file.h>
        Comment.Single:          'italic #6272a4',     # // single line comments
        Comment.Special:         'italic bold #6272a4', # TODO, FIXME, etc.
        
        # Keyword tokens
        Keyword:                 'bold #ff79c6',       # Base keyword
        Keyword.Constant:        'bold #bd93f9',       # true, false, null
        Keyword.Declaration:     'bold #ff79c6',       # var, let, const
        Keyword.Namespace:       'bold #ff79c6',       # import, from, namespace
        Keyword.Pseudo:          'bold #ff79c6',       # self, this
        Keyword.Reserved:        'bold #ff79c6',       # Reserved keywords
        Keyword.Type:            'bold #8be9fd',       # int, str, bool
        
        # Name tokens (identifiers)
        Name:                    '#f8f8f2',           # Base name/identifier
        Name.Attribute:          '#50fa7b',           # object.attribute
        Name.Builtin:            '#8be9fd',           # print, len, range
        Name.Builtin.Pseudo:     '#8be9fd',           # __name__, __main__
        Name.Class:              'bold #8be9fd',      # class ClassName
        Name.Constant:           '#bd93f9',           # CONSTANT_NAME
        Name.Decorator:          '#50fa7b',           # @decorator
        Name.Entity:             '#f1fa8c',           # HTML entities &amp;
        Name.Exception:          'bold #ff5555',      # Exception, ValueError
        Name.Function:           'bold #50fa7b',      # def function_name
        Name.Function.Magic:     'bold #50fa7b',      # __init__, __str__
        Name.Label:              '#f8f8f2',           # goto labels
        Name.Namespace:          '#f8f8f2',           # module names
        Name.Other:              '#f8f8f2',           # Other names
        Name.Property:           '#50fa7b',           # @property
        Name.Tag:                '#ff79c6',           # HTML/XML tags
        Name.Variable:           '#f8f8f2',           # variable names
        Name.Variable.Class:     '#f8f8f2',           # cls, self
        Name.Variable.Global:    '#f8f8f2',           # global variables
        Name.Variable.Instance:  '#f8f8f2',           # instance variables
        Name.Variable.Magic:     '#bd93f9',           # __file__, __doc__
        
        # Literal tokens (values)
        Literal:                 '#f1fa8c',           # Base literal
        Literal.Date:            '#f1fa8c',           # Date literals
        
        # String tokens
        String:                  '#f1fa8c',           # Base string
        String.Affix:            '#ff79c6',           # r"", u"", b""
        String.Backtick:         '#f1fa8c',           # `backtick strings`
        String.Char:             '#f1fa8c',           # 'c' character literals
        String.Delimiter:        '#f1fa8c',           # String delimiters
        String.Doc:              'italic #f1fa8c',    # """docstrings"""
        String.Double:           '#f1fa8c',           # "double quoted"
        String.Escape:           '#ff79c6',           # \n, \t, \\
        String.Heredoc:          '#f1fa8c',           # Heredoc strings
        String.Interpol:         '#ff79c6',           # f"string {interpolation}"
        String.Other:            '#f1fa8c',           # Other string types
        String.Regex:            '#f1fa8c',           # /regex/patterns/
        String.Single:           '#f1fa8c',           # 'single quoted'
        String.Symbol:           '#f1fa8c',           # :symbol (Ruby)
        
        # Number tokens
        Number:                  '#bd93f9',           # Base number
        Number.Bin:              '#bd93f9',           # 0b1010 binary
        Number.Float:            '#bd93f9',           # 3.14 floats
        Number.Hex:              '#bd93f9',           # 0xFF hex
        Number.Integer:          '#bd93f9',           # 42 integers
        Number.Integer.Long:     '#bd93f9',           # 42L long integers
        Number.Oct:              '#bd93f9',           # 0o755 octal
        
        # Operator tokens
        Operator:                '#ff79c6',           # Base operator
        Operator.Word:           '#ff79c6',           # and, or, not, in
        
        # Punctuation tokens
        Punctuation:             '#f8f8f2',           # Base punctuation
        Punctuation.Marker:      '#f8f8f2',           # Markup punctuation
        
        # Generic tokens (for diffs, markup, etc.)
        Generic:                 '#f8f8f2',           # Base generic
        Generic.Deleted:         '#ff5555',           # - deleted lines
        Generic.Emph:            'italic',            # *emphasis*
        Generic.Error:           'bold #ff5555',      # Error messages
        Generic.Heading:         'bold #8be9fd',      # # Headings
        Generic.Inserted:        '#50fa7b',           # + inserted lines
        Generic.Output:          '#f8f8f2',           # Program output
        Generic.Prompt:          'bold #f8f8f2',      # >>> prompts
        Generic.Strong:          'bold',              # **strong**
        Generic.Subheading:      'bold #f1fa8c',      # ## Subheadings
        Generic.Traceback:       '#ff5555',           # Traceback info
        
        # Escape tokens
        Escape:                  '#ff79c6',           # Escape sequences
    }

def create_comprehensive_examples():
    """Create code examples that trigger every token type"""
    
    examples = {
        "Python Complete": '''#!/usr/bin/env python3
"""
This is a docstring showing String.Doc tokens.
It demonstrates various Python token types.
TODO: This comment shows Comment.Special
"""

# Single line comment (Comment.Single)
# -*- coding: utf-8 -*- (Comment.Special)

import os  # Keyword.Namespace, Name.Namespace
from typing import List, Dict, Optional  # Name.Builtin

# Global constant (Name.Constant)
GLOBAL_CONSTANT = 42

class ExampleClass:  # Keyword, Name.Class
    """Class docstring (String.Doc)"""
    
    def __init__(self, value: int = 0):  # Name.Function.Magic, Keyword.Type
        self.value = value  # Name.Variable.Instance
        self._private = "private"  # String.Double
        
    @property  # Name.Decorator
    def formatted_value(self) -> str:  # Name.Property, Keyword.Type
        """Property docstring"""
        return f"Value: {self.value}"  # String.Interpol
    
    @staticmethod  # Name.Decorator
    def static_method():  # Name.Function
        pass  # Keyword
    
    def __str__(self) -> str:  # Name.Function.Magic
        return f"ExampleClass({self.value})"

# Various number types
binary_num = 0b1010  # Number.Bin
hex_num = 0xFF  # Number.Hex
oct_num = 0o755  # Number.Oct
float_num = 3.14159  # Number.Float
int_num = 42  # Number.Integer

# String types
single_string = 'single quotes'  # String.Single
double_string = "double quotes"  # String.Double
raw_string = r"raw string with \\n"  # String.Affix
byte_string = b"byte string"  # String.Affix
f_string = f"formatted {int_num}"  # String.Interpol

# Escape sequences (String.Escape)
escaped_string = "newline\\n tab\\t quote\\""

# Boolean constants (Keyword.Constant)
is_true = True
is_false = False
is_none = None

# Operators (Operator, Operator.Word)
result = 1 + 2 * 3 / 4 - 5  # Operator
logical = True and False or not None  # Operator.Word
membership = "x" in "example"  # Operator.Word

# Built-in functions (Name.Builtin)
length = len([1, 2, 3])
printed = print("hello")
ranged = range(10)

# Exception handling (Name.Exception)
try:
    raise ValueError("example error")  # Name.Exception
except Exception as e:  # Name.Exception
    pass

# Magic variables (Name.Variable.Magic)
if __name__ == "__main__":  # Name.Variable.Magic
    print(__file__)  # Name.Variable.Magic
''',

        "JavaScript/TypeScript": '''#!/usr/bin/env node
/**
 * Multiline comment (Comment.Multiline)
 * Shows JavaScript/TypeScript tokens
 */

// Single line comment (Comment.Single)

// Import statements (Keyword.Namespace)
import { Component } from 'react';
import * as fs from 'fs';

// Type declarations (TypeScript)
interface User {  // Keyword, Name.Class
    id: number;  // Name.Attribute, Keyword.Type
    name: string;  // Keyword.Type
    email?: string;  // Keyword.Type, Operator
}

// Class declaration
class UserManager {  // Keyword, Name.Class
    private users: User[] = [];  // Keyword, Name.Attribute
    
    constructor(config: object) {  // Name.Function, Keyword.Type
        this.users = [];  // Keyword.Pseudo
    }
    
    // Method with various number types
    processNumbers(): void {  // Name.Function, Keyword.Type
        const binary = 0b1010;  // Number.Bin
        const hex = 0xFF;  // Number.Hex
        const float = 3.14;  // Number.Float
        const integer = 42;  // Number.Integer
    }
    
    // String types
    processStrings(): void {
        const single = 'single quotes';  // String.Single
        const double = "double quotes";  // String.Double
        const template = `template ${this.users.length}`;  // String.Interpol
        const escaped = "escaped\\n\\t\\"";  // String.Escape
    }
    
    // Async function
    async fetchData(url: string): Promise<User[]> {  // Keyword, Name.Function
        try {
            const response = await fetch(url);  // Keyword
            return await response.json();
        } catch (error) {  // Name.Exception
            throw new Error("Failed to fetch");  // Name.Exception
        }
    }
}

// Constants and operators
const TRUE_VALUE = true;  // Name.Constant, Keyword.Constant
const FALSE_VALUE = false;  // Keyword.Constant
const NULL_VALUE = null;  // Keyword.Constant
const UNDEFINED_VALUE = undefined;  // Keyword.Constant

// Operators
const result = 1 + 2 * 3 / 4 - 5;  // Operator
const logical = true && false || !null;  // Operator
const comparison = 5 > 3 && 2 < 4;  // Operator
''',

        "SQL": '''-- Single line comment (Comment.Single)
/* 
 * Multiline comment (Comment.Multiline)
 * SQL token examples
 */

-- DDL Keywords (Keyword)
CREATE TABLE users (  -- Keyword, Name.Table
    id INTEGER PRIMARY KEY,  -- Name.Attribute, Keyword.Type, Keyword
    name VARCHAR(255) NOT NULL,  -- Keyword.Type, Keyword
    email TEXT UNIQUE,  -- Keyword.Type, Keyword
    created_at TIMESTAMP DEFAULT NOW(),  -- Keyword.Type, Keyword, Name.Builtin
    age DECIMAL(3,0) CHECK (age >= 0)  -- Keyword.Type, Number.Integer, Operator
);

-- DML Keywords
INSERT INTO users (name, email, age)  -- Keyword, Name.Table, Name.Attribute
VALUES ('John Doe', 'john@example.com', 25);  -- Keyword, String.Single, Number.Integer

-- Query with various elements
SELECT   -- Keyword
    u.id,  -- Name.Attribute
    u.name,
    u.email,
    COUNT(o.id) as order_count,  -- Name.Builtin, Name.Attribute
    SUM(o.total) as total_spent,  -- Name.Builtin
    AVG(o.total) as avg_order  -- Name.Builtin
FROM users u  -- Keyword, Name.Table
LEFT JOIN orders o ON u.id = o.user_id  -- Keyword, Name.Table, Operator
WHERE u.created_at >= '2024-01-01'  -- Keyword, Name.Attribute, Operator, String.Single
    AND u.age BETWEEN 18 AND 65  -- Operator.Word, Keyword
    AND u.email IS NOT NULL  -- Operator.Word, Keyword
GROUP BY u.id, u.name  -- Keyword, Name.Attribute
HAVING COUNT(o.id) > 5  -- Keyword, Name.Builtin, Operator, Number.Integer
ORDER BY total_spent DESC  -- Keyword, Name.Attribute, Keyword
LIMIT 100;  -- Keyword, Number.Integer

-- String types and escapes
UPDATE users 
SET name = 'O''Brien',  -- String.Single with String.Escape
    email = "user@domain.com"  -- String.Double
WHERE id = 1;

-- Numbers
SELECT 
    42 as integer_num,  -- Number.Integer
    3.14159 as float_num,  -- Number.Float
    0xFF as hex_num,  -- Number.Hex
    1.5e10 as scientific  -- Number.Float
FROM dual;
''',

        "HTML/XML": '''<!DOCTYPE html>  <!-- Comment -->
<!-- This is an HTML comment (Comment) -->
<html lang="en">  <!-- Name.Tag, Name.Attribute -->
<head>
    <meta charset="utf-8">  <!-- Name.Tag, Name.Attribute, String -->
    <title>Token Examples</title>  <!-- Name.Tag -->
    <style type="text/css">  <!-- Name.Tag, Name.Attribute, String -->
        /* CSS comment (Comment.Multiline) */
        body { color: #ff0000; }  /* Name.Tag, Name.Attribute, Number.Hex */
    </style>
</head>
<body class="main-content" id="page">  <!-- Name.Attribute, String -->
    <h1>Title with &amp; entity</h1>  <!-- Name.Tag, Name.Entity -->
    <p>Regular text with <em>emphasis</em></p>  <!-- Name.Tag -->
    
    <script type="text/javascript">  <!-- Name.Tag, Name.Attribute -->
        // JavaScript in HTML (Comment.Single)
        const message = "Hello, world!";  // String.Double
        console.log(message);  // Name.Builtin
    </script>
</body>
</html>
''',

        "JSON": '''{
  "name": "example",          // String key, String value
  "version": "1.0.0",         // String value
  "number": 42,               // Number.Integer
  "float": 3.14,              // Number.Float
  "boolean": true,            // Keyword.Constant
  "null_value": null,         // Keyword.Constant
  "array": [1, 2, 3],         // Number.Integer
  "nested": {                 // Object
    "key": "value"            // String key-value
  }
}''',

        "Regex": r'''# Regular expression examples (String.Regex)

# Email validation
email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

# Phone number with groups
phone_pattern = r"(\d{3})-(\d{3})-(\d{4})"

# URL matching with named groups
url_pattern = r"(?P<scheme>https?)://(?P<domain>[^/]+)(?P<path>/.*)?$"

# Character classes and quantifiers
complex_pattern = r"[A-Za-z]\w{2,15}[!@#$%^&*]+"
''',

        "Diff Example": '''--- old_file.py  (Generic.Deleted context)
+++ new_file.py  (Generic.Inserted context)
@@ -1,5 +1,6 @@  (Generic.Heading)
 def old_function():  (unchanged line)
-    return "old"  (Generic.Deleted)
+    return "new"  (Generic.Inserted)
+    # Added comment  (Generic.Inserted)
     pass
     
 # This line unchanged
'''
    }
    
    return examples

def demo_all_token_types():
    """Demonstrate every token type with examples"""
    console = Console()
    
    console.print("[bold blue]🎨 Complete Pygments Token Types Reference[/bold blue]\n")
    console.print("[dim]Every token type with real code examples[/dim]\n")
    
    examples = create_comprehensive_examples()
    
    for title, code in examples.items():
        # Determine language
        lang_map = {
            "Python Complete": "python",
            "JavaScript/TypeScript": "typescript", 
            "SQL": "sql",
            "HTML/XML": "html",
            "JSON": "json",
            "Regex": "python",  # Show regex in Python context
            "Diff Example": "diff"
        }
        
        language = lang_map.get(title, "text")
        
        console.print(f"[bold green]📝 {title}[/bold green]")
        
        # Show with complete token theme
        syntax = Syntax(
            code, 
            language, 
            theme="complete_tokens",
            line_numbers=True,
            word_wrap=True
        )
        
        console.print(Panel(
            syntax, 
            title=f"{title} - All Token Types",
            subtitle=f"Language: {language}"
        ))
        console.print()

def create_token_reference_table():
    """Create a reference table of all token types"""
    console = Console()
    
    console.print("\n[bold blue]📋 Token Types Quick Reference[/bold blue]\n")
    
    # Group tokens by category
    token_categories = {
        "Base Tokens": [
            ("Token", "Default text color"),
            ("Whitespace", "Whitespace (usually invisible)"),
            ("Error", "Syntax errors"),
            ("Other", "Unknown/other tokens"),
        ],
        
        "Comments": [
            ("Comment", "Base comment style"),
            ("Comment.Hashbang", "#!/usr/bin/env shebang"),
            ("Comment.Multiline", "/* */ block comments"),
            ("Comment.Preproc", "#include preprocessor"),
            ("Comment.Single", "// line comments"),
            ("Comment.Special", "TODO, FIXME, etc."),
        ],
        
        "Keywords": [
            ("Keyword", "if, def, class, etc."),
            ("Keyword.Constant", "true, false, null"),
            ("Keyword.Declaration", "var, let, const"),
            ("Keyword.Namespace", "import, from"),
            ("Keyword.Pseudo", "self, this"),
            ("Keyword.Reserved", "Reserved words"),
            ("Keyword.Type", "int, str, bool"),
        ],
        
        "Names/Identifiers": [
            ("Name", "Variable names"),
            ("Name.Attribute", "object.attribute"),
            ("Name.Builtin", "print, len, range"),
            ("Name.Class", "class ClassName"),
            ("Name.Constant", "CONSTANT_NAME"),
            ("Name.Decorator", "@decorator"),
            ("Name.Exception", "ValueError, Exception"),
            ("Name.Function", "def function_name"),
            ("Name.Function.Magic", "__init__, __str__"),
            ("Name.Variable.Magic", "__name__, __file__"),
        ],
        
        "Strings": [
            ("String", "Base string style"),
            ("String.Affix", "r'', u'', b''"),
            ("String.Doc", "\"\"\"docstrings\"\"\""),
            ("String.Double", "\"double quoted\""),
            ("String.Escape", "\\n, \\t, \\\\"),
            ("String.Interpol", "f\"string {var}\""),
            ("String.Regex", "/regex/patterns/"),
            ("String.Single", "'single quoted'"),
        ],
        
        "Numbers": [
            ("Number", "Base number style"),
            ("Number.Bin", "0b1010 binary"),
            ("Number.Float", "3.14 floats"),
            ("Number.Hex", "0xFF hexadecimal"),
            ("Number.Integer", "42 integers"),
            ("Number.Oct", "0o755 octal"),
        ],
        
        "Operators": [
            ("Operator", "+, -, *, /"),
            ("Operator.Word", "and, or, not, in"),
        ],
        
        "Generic (Markup/Diffs)": [
            ("Generic.Deleted", "- deleted lines"),
            ("Generic.Emph", "*emphasis*"),
            ("Generic.Error", "Error messages"),
            ("Generic.Heading", "# Headings"),
            ("Generic.Inserted", "+ inserted lines"),
            ("Generic.Strong", "**strong**"),
        ]
    }
    
    for category, tokens in token_categories.items():
        table = Table(title=f"[bold]{category}[/bold]", show_header=True)
        table.add_column("Token Type", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Example", style="green")
        
        for token_name, description in tokens:
            # Create simple examples for each token
            examples = {
                "Comment": "# This is a comment",
                "Keyword": "def, class, if",
                "Name.Function": "my_function()",
                "String": "'hello world'",
                "Number.Integer": "42",
                "Operator": "+ - * /",
            }
            
            # Get example or use description
            example = examples.get(token_name.split('.')[-1], description.split()[0])
            table.add_row(token_name, description, example)
        
        console.print(table)
        console.print()

def main():
    """Main demo function"""
    console = Console()
    
    console.print("[bold green]🎯 Complete Token Types Guide[/bold green]")
    console.print("[dim]See every Pygments token type in action[/dim]\n")
    
    try:
        # Show all examples
        demo_all_token_types()
        
        # Show reference table
        create_token_reference_table()
        
        console.print("\n[bold green]✅ Complete Token Reference Done![/bold green]")
        console.print("\n[bold]Key Takeaways:[/bold]")
        console.print("• Each token type controls a specific code element")
        console.print("• You can style each token independently")
        console.print("• Some tokens are language-specific")
        console.print("• Use this reference when creating custom themes")
        console.print("• Test your themes with multiple languages")
        
    except Exception as e:
        console.print(f"[red]Error in demo: {e}[/red]")

if __name__ == "__main__":
    main()