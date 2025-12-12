# SKFunction Concept

skfunction is a module that upgrades function calling

there are issues with passing functions as arguments to other functions.
- you have to pass the function with its arguments in the correct order.
- especially annoying if some args aren't needed and you have to pass them as None

```python
def format_text(text, font_size=12, font_family="Arial", bold=False, italic=False, underline=False, color="black", background_color="white"):
    
    # ... format and return text ...
    return formatted_text


def process_data(data, debug_message=None):

    # ... process data ...

    if debug_message:
        print(debug_message)

    return data


# you want bold, black, underlined text with yellow background color
# without skfunction:
process_data(
    "Hello, World!", 
    format_text(
        text="Hello, World!", 
        font_size=12, 
        font_family="Impact", 
        bold=True, 
        underline=True, 
        background_color="yellow"
    )
)

# with skfunction:
args = {
    "font_size": 12, 
    "font_family": "Impact", 
    "bold": True, 
    "underline": True, 
    "background_color": "yellow"
}

debug_format = SKFunction(format_text, args)

process_data("Hello, World!", debug_format("Hello, World!"))
```

pros of skfunction:
- simple dict that uses paramter names instead of perfect positional order
- saves callable + args in one object
- delayed calling
- call multiple times with different args
- easy to override args
- simple and very readable code
- can create skfunctions from other skfunctions
- easy to pass to other functions because it's a single object
- serializable and deserializable

