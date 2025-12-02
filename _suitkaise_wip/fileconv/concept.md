# fileconv

## CRITICAL: Piece-by-Piece Parsing Architecture

**The fundamental principle of fileconv is ATOMIC PIECE PARSING.**

### Parser Flow (MANDATORY):
1. Parser examines content character by character or token by token
2. Every time a new element is encountered (emoji, image, link, formatting change), create a NEW TextFile sub-object
3. Content must be broken down to the SMALLEST possible pieces:
   - "**bold text** regular text" becomes TWO pieces:
     - TextFile.Text(content="bold text", formatting=["bold"])
     - TextFile.Text(content=" regular text", formatting=[])
   - "- **PyYAML** - For parsing" becomes THREE pieces:
     - TextFile.Text(content="PyYAML", formatting=["bold", "list_item"])
     - TextFile.Text(content=" - For parsing", formatting=["list_item"])
   - Each emoji, image, link = separate piece

### Converter Flow (MANDATORY):
1. Converter receives TextFile object with ordered list of atomic pieces
2. Converter processes pieces ONE BY ONE in order
3. Each piece type has dedicated conversion method
4. Final output reconstructed by concatenating converted pieces

### What This Achieves:
- Perfect formatting preservation across all output formats
- Clean separation of parsing logic from output formatting
- Consistent behavior regardless of source/target format

**If parsers are not following this atomic approach, the entire pipeline is broken.**

---

fileconv is a utility that allows you to convert text files to different formats, with a consistent output result for the given output type.

it uses a special object, `TextFile`, that acts as an intermediate step between the input file and the output file.

inputs: markdown, txt, yaml, docx

outputs: markdown, txt, yaml, docx, html, pdf

```python
from suitkaise import fileconv

to_docx = []
to_html = []
to_pdf = []

location = "/Users/user/Documents/converted"

for file in files:
	text_file = fileconv.parse(file) # this creates a TextFile object that holds the original content
	
	docx_file = fileconv.convert(text_file, format=fileconv.Format.DOCX)
	html_file = fileconv.convert(text_file, format=fileconv.Format.HTML)
	pdf_file = fileconv.convert(text_file, format=fileconv.Format.PDF)
	
	# these return references to the created files
	
	to_docx.append(docx_file)
	to_html.append(html_file)
	to_pdf.append(pdf_file)

fileconv.save_all(to_docx, location)
fileconv.save_all(to_html, location)
fileconv.save_all(to_pdf, location)
```

## Using fileconv

### Approach

1. Parse input file to TextFile object
2. Convert TextFile object to desired format(s)
3. Save converted files

### TextFile

The TextFile object is the core of fileconv. It represents a document as a collection of pieces, where each piece has specific formatting and content.

#### Pieces

A TextFile is made up of pieces. Each piece represents a specific type of content:

- **Text**: Plain text with optional formatting
- **Heading**: Heading text with level (1-6)
- **Link**: URL link with display text
- **List**: Ordered or unordered list of items
- **CodeBlock**: Code block with optional language
- **ImageFromFile**: Image from local file
- **ImageFromUrl**: Image from URL

#### Example

A markdown file like:
```markdown
# My Document

This is **bold** text and this is *italic* text.

- Item 1
- Item 2

![Image](image.png)
```

Would be parsed into a TextFile with these pieces:
1. Heading: "My Document" (level 1)
2. Text: "This is " (no formatting)
3. Text: "bold" (bold formatting)
4. Text: " text and this is " (no formatting)
5. Text: "italic" (italic formatting)
6. Text: " text." (no formatting)
7. List: ["Item 1", "Item 2"] (unordered)
8. ImageFromFile: "image.png" with alt text "Image"