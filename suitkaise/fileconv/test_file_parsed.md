this is a file showing how the test_file.md file should be parsed.

--------------------------------
line 1: create a new Line object, Header1

"# 🚀 Comprehensive Test Document 测试文档"

since this is a heading1, we strip the # and leading whitespace before parsing this line. a line is defined as text until a newline character.

then, we start adding pieces to the TextLine object, moving until we encounter a valid piece.

when the parser encounters a piece, it adds it to the TextLine object as a TextPiece object, and then moves to the next piece according to what object was found.

1. we got a 🚀
- UnicodePiece("🚀")
2. we find " Comprehensive Test Document " until we encounter a different piece (测)
- AsciiPiece(
    " Comprehensive Test Document ",
    formatting=[]
)
3. we find a 测
- UnicodePiece("测")
4. we find a 试
- UnicodePiece("试")
5. we find a 文
- UnicodePiece("文")
6. we find a 档
- UnicodePiece("档")
7. we find a \n
- NewlinePiece()

so, the TextHeader1 object is created with the following pieces:
- UnicodePiece("🚀")
- AsciiPiece(" Comprehensive Test Document ", formatting=[])
- UnicodePiece("测")
- UnicodePiece("试")
- UnicodePiece("文")
- UnicodePiece("档")
- NewlinePiece()

--------------------------------
line 2: create a Line object

- NewlinePiece()

--------------------------------
line 3: create a new Line object

"This document tests **all formatting elements** with *complex combinations* and ***bold italic*** text."

1. AsciiPiece(
    "This document tests ",
)

fmt=[fmt.BOLD] because of the **
2. AsciiPiece(
    "all formatting elements", fmt
)
fmt=[] because of another **

3. AsciiPiece(" with ", \fmt)
4. AsciiPiece(
    "complex combinations",
    formatting=[fmt.ITALIC]
)
5. AsciiPiece(" and ", formatting=[])
6. AsciiPiece(
    "bold italic",
    formatting=[fmt.BOLD, fmt.ITALIC]
)
7. AsciiPiece(" text.", formatting=[])
8. NewlinePiece()

--------------------------------
line 4: create a Line object

- NewlinePiece()

--------------------------------
line 5: create a new Line object, Header2

"## 📋 Lists with Complex Formatting"

1. UnicodePiece("📋")
2. AsciiPiece(
    " Lists with Complex Formatting",
    formatting=[]
)
3. NewlinePiece()

--------------------------------
line 6: create a Line object

- NewlinePiece()

--------------------------------
line 7: create a new Line object, Header3

### Unordered Lists

1. AsciiPiece("Unordered Lists")
2. NewlinePiece()

line 8: create a new Line object, ListItem

"- **Bold item** with [link to Google](https://google.com)"

1. AsciiPiece("Bold item", formatting=[fmt.BOLD])
2. AsciiPiece(" with ", formatting=[])
3. LinkPiece(
    "link to Google", 
    url="https://google.com"
)
4. NewlinePiece()

NOTE: the text given to the LinkPiece will be parsed further if it contains formatting markers or unicode characters
--------------------------------
line 9: create a new Line object, ListItem

"- *Italic item* with `inline code` and 🎉 emoji"

1. AsciiPiece("Italic item", formatting=[fmt.ITALIC])
2. AsciiPiece(" with ", formatting=[])
3. AsciiPiece("inline code", formatting=[fmt.CODE])
4. AsciiPiece(" and ", formatting=[])
5. UnicodePiece("🎉")
6. UnicodePiece(" emoji")
7. NewlinePiece()

--------------------------------
line 10: create a new Line object, ListItem

"- ***Bold italic*** with ![image from URL](https://via.placeholder.com/150)"

1. AsciiPiece("Bold italic", formatting=[fmt.BOLD, fmt.ITALIC])
2. AsciiPiece(" with ", formatting=[])
3. NewlinePiece()
4. URLImagePiece(
    "image from URL",
    url="https://via.placeholder.com/150"
)
5. NewlinePiece()

--------------------------------
line 11: create a new Line object, ListItem

"- Regular text with ![local image](./random_screenshot.png)"

1. AsciiPiece("Regular text with ", formatting=[])
2. LocalImagePiece(
    "local image",
    file_path="./random_screenshot.png"
)
3. NewlinePiece()

--------------------------------
line 12: create a new Line object, ListItem

"- 东亚文字测试 with **粗体** and *斜体*"

1. UnicodePiece("东")
2. UnicodePiece("亚")
3. UnicodePiece("文")
4. UnicodePiece("字")
5. UnicodePiece("测")
6. UnicodePiece("试")
7. AsciiPiece(" with ", formatting=[])
8. doesn't fit one piece reqs, so we use split_compound_piece()
    --> UnicodePiece("粗", formatting=[fmt.BOLD])
    --> UnicodePiece("体", formatting=[fmt.BOLD])
9. AsciiPiece(" and ", formatting=[])
10. split_compound_piece("*斜体*")
    --> UnicodePiece("斜", formatting=[fmt.ITALIC])
    --> UnicodePiece("体", formatting=[fmt.ITALIC])
11. NewlinePiece()

NOTE: if we recognize that a piece doesn't fit one piece reqs, we use split_compound_piece() to split it into multiple pieces intelligently

How does split_compound_piece() work?

Say we have the following: split_compound_piece("*斜体*")

split_compound_piece() will turn it into:

1. *斜* --> UnicodePiece("斜", formatting=[fmt.ITALIC])
2. *体* --> UnicodePiece("体", formatting=[fmt.ITALIC])

by tracking what formatting is currently active, we can create the correct pieces. pieces will be returned in the order they exist in the original string.

--------------------------------
line 13: create a new Line object, ListItem

"- Code reference: `numpy.array()` in Python"

1. AsciiPiece("Code reference: ", formatting=[])
2. AsciiPiece("numpy.array()", formatting=[fmt.CODE])
3. AsciiPiece(" in Python", formatting=[])
4. NewlinePiece()

--------------------------------
line 14: create a new Line object, ListItem

- NewlinePiece()

--------------------------------
line 15: create a new Line object, Header3

### Ordered Lists

1. AsciiPiece("Ordered Lists")
2. NewlinePiece()

--------------------------------
line 16: create a new Line object, OrderedListItem

"**First step**: Install dependencies with `pip install package`"

1. AsciiPiece("First step", formatting=[fmt.BOLD])
2. AsciiPiece(": Install dependencies with ", formatting=[])
3. AsciiPiece("pip install package", formatting=[fmt.CODE])
4. NewlinePiece()

--------------------------------
line 17: create a new Line object, OrderedListItem

"***Second step***: Run the application 🚀"

1. AsciiPiece("Second step", formatting=[fmt.BOLD, fmt.ITALIC])
2. AsciiPiece(": Run the application ", formatting=[])
3. UnicodePiece("🚀")
4. NewlinePiece()

--------------------------------
line 18: create a new Line object, OrderedListItem

"*Third step*：测试东亚字符支持 with **formatting**"

1. AsciiPiece("Third step", formatting=[fmt.ITALIC])
2. AsciiPiece("：", formatting=[])
3. UnicodePiece("测")
4. UnicodePiece("试")
5. UnicodePiece("东")
6. UnicodePiece("亚")
7. UnicodePiece("文")
8. UnicodePiece("字")
9. UnicodePiece("支")
10. UnicodePiece("持")
11. AsciiPiece(" with ", formatting=[])
12. AsciiPiece("formatting", formatting=[fmt.BOLD])
13. NewlinePiece()

--------------------------------
line 19: create a new Line object, OrderedListItem

"Final step with multiple elements: **bold**, *italic*, `code`, and [link](https://example.com)"

1. AsciiPiece("Final step with multiple elements: ", formatting=[])
2. AsciiPiece("bold", formatting=[fmt.BOLD])
3. AsciiPiece(", ", formatting=[])
4. AsciiPiece("italic", formatting=[fmt.ITALIC])
5. AsciiPiece(", ", formatting=[])
6. AsciiPiece("code", formatting=[fmt.CODE])
7. AsciiPiece(" and ", formatting=[])
8. LinkPiece(
    "link",
    url="https://example.com"
)
9. NewlinePiece()

--------------------------------
line 20: create a new Line object

- NewlinePiece()

--------------------------------
line 21: create a new Line object, Header2

"## 💻 Complex Code Block"

1. UnicodePiece("💻")
2. AsciiPiece(
    " Complex Code Block",
    formatting=[]
)
3. NewlinePiece()

--------------------------------
line 22: create a new Line object

- NewlinePiece()

--------------------------------
line 23: create a new Line object

"Here's a comprehensive Python example with multiple indentation levels:"

1. AsciiPiece("Here's a comprehensive Python example with multiple indentation levels:", formatting=[])
2. NewlinePiece()

--------------------------------
line 24: create a new Line object

- NewlinePiece()

--------------------------------
line 25: create a new Line object, CodeBlockStart

set in_code_block to True

--------------------------------
line 26: create a new Line object

"# Complex class with nested methods and decorators"

since code_block is True...

1. AsciiPiece("# Complex class with nested methods and decorators", formatting=[fmt.CODE])
2. NewlinePiece()

--------------------------------
line 27: create a new Line object

"class DataProcessor:"

since code_block is True...

1. AsciiPiece("class DataProcessor:", formatting=[fmt.CODE])
2. NewlinePiece()

--------------------------------
line 28: create a new Line object

1. TabPiece()
2. AsciiPiece("\"\"\"", formatting=[fmt.CODE])
3. NewlinePiece()

--------------------------------
line 29: create a new Line object

"A comprehensive data processing class"

since code_block is True...

1. TabPiece()
2. AsciiPiece("A comprehensive data processing class", formatting=[fmt.CODE])
3. NewlinePiece()

--------------------------------
line 30: create a new Line object

"支持中文注释和 🐍"

since code_block is True...

1. TabPiece()
2. UnicodePiece("支")
3. UnicodePiece("持")
4. UnicodePiece("中")
5. UnicodePiece("文")
6. UnicodePiece("注")
7. UnicodePiece("释")
8. UnicodePiece("和")
9. AsciiPiece(" ", formatting=[fmt.CODE])
10. UnicodePiece("🐍")
11. NewlinePiece()

--------------------------------
line 31: create a new Line object

1. TabPiece()
2. AsciiPiece("\"\"\"", formatting=[fmt.CODE])
3. NewlinePiece()

--------------------------------
line 32: create a new Line object

- NewlinePiece()

--------------------------------
line 33: create a new Line object

"def __init__(self, config_path: str):"

since code_block is True...

1. TabPiece()
2. AsciiPiece("def __init__(self, config_path: str):", formatting=[fmt.CODE])
3. NewlinePiece()

--------------------------------
line 34: create a new Line object

"self.config = self._load_config(config_path)"

since code_block is True...
1. TabPiece(num_tabs=2)
2. AsciiPiece("self.config = self._load_config(config_path)", formatting=[fmt.CODE])
3. NewlinePiece()

--------------------------------
line 35: create a new Line object

"self.cache = {}"

since code_block is True...

1. TabPiece(num_tabs=2)
2. AsciiPiece("self.cache = {}", formatting=[fmt.CODE])
3. NewlinePiece()
--------------------------------line 36: create a new Line 

...line 63: create a new Line object, CodeBlockEnd

set in_code_block to False

--------------------------------
line 64: create a new Line object

- NewlinePiece()

--------------------------------
...line 68: create a new Line object, ListItem

"Simple link: [Google](https://google.com)"

1. AsciiPiece("Simple link: ", formatting=[])
2. LinkPiece(
    "Google",
    url="https://google.com"
)
3. NewlinePiece()

--------------------------------
line 69: create a new Line object, ListItem

"**Bold link**: [**GitHub**](https://github.com)"

1. AsciiPiece("Bold link: ", formatting=[fmt.BOLD])
2. LinkPiece(
    "**GitHub**",
    url="https://github.com"
)
3. NewlinePiece()

--------------------------------
line 70: create a new Line object, ListItem

"*Italic link*: [*Documentation*](https://docs.python.org)"

1. AsciiPiece("Italic link: ", formatting=[fmt.ITALIC])
2. LinkPiece(
    "*Documentation*",
    url="https://docs.python.org"
)
3. NewlinePiece()

--------------------------------
line 71: create a new Line object, ListItem

"Link with emoji: [🚀 Rocket Launch](https://nasa.gov)"

1. AsciiPiece("Link with emoji: ", formatting=[])
2. LinkPiece(
    "🚀 Rocket Launch",
    url="https://nasa.gov"
)
3. NewlinePiece()

--------------------------------
line 72: create a new Line object, ListItem

"中文链接: [百度搜索](https://baidu.com)"

1. UnicodePiece("中")
2. UnicodePiece("文")
3. UnicodePiece("链")
4. UnicodePiece("接")
5. AsciiPiece(": ", formatting=[])
6. LinkPiece(
    "百度搜索",
    url="https://baidu.com"
)
7. NewlinePiece()

--------------------------------
line 73: create a new Line object

- NewlinePiece()

...line 75: create a new Line object, ListItem

"URL image: ![Placeholder](https://user-images.githubusercontent.com/719564/187257765-4b449f4d-fc41-4abb-88a6-d12308f40bff.png)"


1. AsciiPiece("URL image: ", formatting=[])
2. URLImagePiece(
    "Placeholder",
    url="https://user-images.githubusercontent.com/719564/187257765-4b449f4d-fc41-4abb-88a6-d12308f40bff.png"
)
3. NewlinePiece()

--------------------------------
line 76: create a new Line object, ListItem

"Local image: ![Test Image](./random_screenshot.png)"

1. AsciiPiece("Local image: ", formatting=[])
2. LocalImagePiece(
    "Test Image",
    file_path="./random_screenshot.png"
)
3. NewlinePiece()

--------------------------------
line 77: create a new Line object, ListItem

"Image with emoji alt: ![🖼️ Picture](https://user-images.githubusercontent.com/719564/187257765-4b449f4d-fc41-4abb-88a6-d12308f40bff.png)"

1. AsciiPiece("Image with emoji alt: ", formatting=[])
2. URLImagePiece(
    "🖼️ Picture",
    url="https://user-images.githubusercontent.com/719564/187257765-4b449f4d-fc41-4abb-88a6-d12308f40bff.png"
)
3. NewlinePiece()

NOTE: the text given to the URLImagePiece will be parsed further if it contains formatting markers or unicode characters

--------------------------------
line 78: create a new Line object, ListItem

"中文图片: ![测试图片](./random_screenshot.png)"
1. UnicodePiece("中")
2. UnicodePiece("文")
3. UnicodePiece("图")
4. UnicodePiece("片")
5. AsciiPiece(": ", formatting=[])
6. LocalImagePiece(
    "测试图片",
    file_path="./random_screenshot.png"
)
7. NewlinePiece()

--------------------------------
...line 91: create a new Line object

This paragraph contains **bold text with *nested italic*** and ***bold italic with `inline code`***."

1. AsciiPiece("This paragraph contains ", formatting=[])
2. split_compound_piece("**bold text with *nested italic***")
    --> AsciiPiece("bold text with ", formatting=[fmt.BOLD])
    --> AsciiPiece("nested italic", formatting=[fmt.BOLD, fmt.ITALIC])
3. AsciiPiece(" and ", formatting=[])
4. split_compound_piece("***bold italic with `inline code`***")
    --> AsciiPiece("bold italic with ", formatting=[fmt.BOLD, fmt.ITALIC])
    --> AsciiPiece("inline code", formatting=[fmt.BOLD, fmt.ITALIC, fmt.CODE])
5. NewlinePiece()

--------------------------------
...line 93: create a new Line object

"Here's a sentence with multiple elements: **Bold 粗体**, *italic 斜体*, `code 代码`, [link 链接](https://example.com), and emoji 🌟."

1. AsciiPiece("Here's a sentence with multiple elements: ", formatting=[])
2. split_compound_piece("**Bold 粗体**")
    --> AsciiPiece("Bold ", formatting=[fmt.BOLD])
    --> UnicodePiece("粗", formatting=[fmt.BOLD])
    --> UnicodePiece("体", formatting=[fmt.BOLD])
3. AsciiPiece(", ", formatting=[])
4. split_compound_piece("*italic 斜体*")
    --> AsciiPiece("italic ", formatting=[fmt.ITALIC])
    --> UnicodePiece("斜", formatting=[fmt.ITALIC])
    --> UnicodePiece("体", formatting=[fmt.ITALIC])
5. AsciiPiece(", ", formatting=[])
6. split_compound_piece("`code 代码`")
    --> AsciiPiece("code ", formatting=[fmt.CODE])
    --> UnicodePiece("代", formatting=[fmt.CODE])
    --> UnicodePiece("码", formatting=[fmt.CODE])
7. AsciiPiece(", ", formatting=[])
8. LinkPiece(
    "link 链接",
    url="https://example.com"
)
9. AsciiPiece(", and emoji ", formatting=[])
10. UnicodePiece("🌟")
11. AsciiPiece(".", formatting=[])
12. NewlinePiece()

--------------------------------
...line 131: create a new Line object

"This final section combines everything: **Bold text with [link](https://example.com)**, *italic with `code`*, ***bold italic with emoji 🎉***, and complex formatting with 东亚文字支持."

1. AsciiPiece("This final section combines everything: ", formatting=[])
2. split_compound_piece("**Bold text with [link](https://example.com)**")
    --> AsciiPiece("Bold text with ", formatting=[fmt.BOLD])
    --> LinkPiece(
        "**link**",
        url="https://example.com"
    )
3. AsciiPiece(", ", formatting=[])
4. split_compound_piece("*italic with `code`*")
    --> AsciiPiece("italic with ", formatting=[fmt.ITALIC])
    --> AsciiPiece("code", formatting=[fmt.ITALIC, fmt.CODE])
5. AsciiPiece(", ", formatting=[])
6. split_compound_piece("***bold italic with emoji 🎉***")
    --> AsciiPiece("bold italic with emoji ", formatting=[fmt.BOLD, fmt.ITALIC])
    --> UnicodePiece("🎉", fmt=[fmt.BOLD, fmt.ITALIC])
7. AsciiPiece(", and complex formatting with ", formatting=[])
8. UnicodePiece("东")
9. UnicodePiece("亚")
10. UnicodePiece("文")
11. UnicodePiece("字")
12. UnicodePiece("支")
13. UnicodePiece("持")
14. AsciiPiece(".", formatting=[])
15. NewlinePiece()

--------------------------------
...line 143: create a new Line object, HorizontalSeparator





