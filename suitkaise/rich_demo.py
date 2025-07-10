#!/usr/bin/env python3
"""
Rich Library Complete Demo Script
Shows all features, spinners, box styles, themes, and functionality
"""

import time
import random
import json
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn
from rich.status import Status
from rich.panel import Panel
from rich.columns import Columns
from rich.layout import Layout
from rich.tree import Tree
from rich.json import JSON
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.align import Align
from rich.padding import Padding
from rich.rule import Rule
from rich.text import Text
from rich.theme import Theme
from rich import box
from rich.live import Live


def demo_basic_features():
    """Demonstrate basic Rich features"""
    console = Console()
    
    console.print("\n" + "="*60)
    console.print("[bold blue]BASIC FEATURES DEMO[/bold blue]", justify="center")
    console.print("="*60)
    
    # Basic text and styling
    console.print("\n[bold]1. Basic Text Styling:[/bold]")
    console.print("Normal text")
    console.print("[bold]Bold text[/bold]")
    console.print("[italic]Italic text[/italic]")
    console.print("[underline]Underlined text[/underline]")
    console.print("[strikethrough]Strikethrough text[/strikethrough]")
    console.print("[bold red]Bold red text[/bold red]")
    console.print("[green on yellow]Green text on yellow background[/green on yellow]")
    
    # Colors
    console.print("\n[bold]2. Color Examples:[/bold]")
    colors = ["red", "green", "blue", "yellow", "magenta", "cyan", "white"]
    for color in colors:
        console.print(f"[{color}]This is {color} text[/{color}]")
    
    # Hex and RGB colors
    console.print("\n[bold]3. Hex and RGB Colors:[/bold]")
    console.print("[#ff0066]Hex color #ff0066[/#ff0066]")
    console.print("[rgb(255,165,0)]RGB color (255,165,0)[/rgb(255,165,0)]")
    console.print("[#00ff00 on #000080]Green on blue background[/#00ff00 on #000080]")


class SafeBoxFormatter:
    """A formatter that only uses working box styles"""
    
    def __init__(self):
        self.console = Console()
        # Only include verified working styles
        self.safe_styles = {
            "ASCII": box.ASCII,
            "ASCII2": box.ASCII2,
            "ASCII_DOUBLE_HEAD": box.ASCII_DOUBLE_HEAD,
            "SQUARE": box.SQUARE,
            "SQUARE_DOUBLE_HEAD": box.SQUARE_DOUBLE_HEAD,
            "ROUNDED": box.ROUNDED,
            "DOUBLE": box.DOUBLE,
            "DOUBLE_EDGE": box.DOUBLE_EDGE,
            "HEAVY": box.HEAVY,
            "HEAVY_EDGE": box.HEAVY_EDGE,
            "HEAVY_HEAD": box.HEAVY_HEAD,
            "HORIZONTALS": box.HORIZONTALS
        }
        self.broken_styles = [
            "MINIMAL", "MINIMAL_HEAVY_HEAD", "MINIMAL_DOUBLE_HEAD",
            "SIMPLE", "SIMPLE_HEAD", "SIMPLE_HEAVY"
        ]
    
    def validate_box_style(self, box_style):
        """Check if a box style has all required attributes"""
        required_attrs = [
            'top_left', 'top', 'top_right',
            'left', 'right',
            'bottom_left', 'bottom', 'bottom_right'
        ]
        
        missing = []
        for attr in required_attrs:
            if not hasattr(box_style, attr):
                missing.append(attr)
        
        return len(missing) == 0, missing
    
    def create_panel(self, content, style_name, **kwargs):
        """Create a panel with a safe box style"""
        if style_name in self.safe_styles:
            box_style = self.safe_styles[style_name]
            return Panel(content, box=box_style, **kwargs)
        else:
            # Fallback to ASCII if style not found
            return Panel(content, box=box.ASCII, **kwargs)


def demo_all_box_styles():
    """Show only safe, working box styles"""
    console = Console()
    formatter = SafeBoxFormatter()
    
    console.print("\n" + "="*60)
    console.print("[bold blue]SAFE BOX STYLES DEMO[/bold blue]", justify="center")
    console.print("="*60)
    
    console.print("\n[dim]Showing only box styles that work reliably across all terminals[/dim]")
    console.print(f"[dim]Found {len(formatter.safe_styles)} working styles[/dim]")
    console.print(f"[dim red]Excluding {len(formatter.broken_styles)} broken styles: {', '.join(formatter.broken_styles)}[/dim red]\n")
    
    console.print("[bold]Working Box Styles:[/bold]")
    
    for name, box_style in formatter.safe_styles.items():
        # Validate each style
        is_valid, missing = formatter.validate_box_style(box_style)
        
        if is_valid:
            status = "✅ Fully working"
        else:
            status = f"⚠️ Missing: {missing}"
        
        try:
            panel = Panel(
                f"Box style: {name}\nStatus: {status}\nSafe for production use",
                box=box_style,
                width=50,
                title=f"[green]{name}[/green]",
                subtitle="[dim]Reliable[/dim]"
            )
            console.print(panel)
            console.print()
        except Exception as e:
            console.print(f"[red]Unexpected error with {name}: {e}[/red]\n")
        
        time.sleep(0.3)  # Small delay to see each one


def demo_all_spinners():
    """Show all available spinners"""
    console = Console()
    
    console.print("\n" + "="*60)
    console.print("[bold blue]ALL SPINNERS DEMO[/bold blue]", justify="center")
    console.print("="*60)
    
    # List of available spinners
    spinners = [
        "dots", "dots2", "dots3", "dots4", "dots5", "dots6", "dots7", "dots8", 
        "dots9", "dots10", "dots11", "dots12", "line", "line2", "pipe", "simpleDots", 
        "simpleDotsScrolling", "star", "star2", "flip", 
        "bounce",
        "arrow", "arrow2", "arrow3", "bouncingBar", "bouncingBall", 
         "monkey", "hearts", "clock", "earth", "moon", "runner", "pong", 
         "dqpb", 
    ]
    
    console.print(f"\n[bold]Available Spinners ({len(spinners)} total):[/bold]")
    
    for spinner_name in spinners:
        console.print(f"\n[yellow]Testing spinner: {spinner_name}[/yellow]")
        try:
            with console.status(f"[green]{spinner_name}[/green] spinner demo", spinner=spinner_name):
                time.sleep(1.5)
        except Exception as e:
            console.print(f"[red]Error with {spinner_name}: {e}[/red]")


def demo_syntax_themes():
    """Show all syntax highlighting themes"""
    console = Console()
    
    console.print("\n" + "="*60)
    console.print("[bold blue]SYNTAX HIGHLIGHTING THEMES[/bold blue]", justify="center")
    console.print("="*60)
    
    # Sample code
    sample_code = '''def fibonacci(n):
    """Calculate fibonacci number"""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Usage example
result = fibonacci(10)
print(f"Fibonacci(10) = {result}")'''
    
    # Available themes
    themes = [
        "default", "emacs", "friendly", "friendly_grayscale", "colorful", "autumn", 
        "murphy", "manni", "material", "monokai", "perldoc", "pastie", "borland", 
        "trac", "native", "fruity", "bw", "vim", "vs", "tango", "rrt", "xcode", 
        "igor", "paraiso-light", "paraiso-dark", "lovelace", "algol", "algol_nu", 
        "arduino", "rainbow_dash", "abap", "solarized-dark", "solarized-light", 
        "github-dark", "nord", "nord-darker", "gruvbox-dark", "gruvbox-light"
    ]
    
    console.print(f"\n[bold]Syntax Themes ({len(themes)} total):[/bold]")
    
    for theme_name in themes:
        console.print(f"\n[yellow]Theme: {theme_name}[/yellow]")
        try:
            syntax = Syntax(sample_code, "python", theme=theme_name, line_numbers=False)
            console.print(Panel(syntax, title=f"Theme: {theme_name}", width=80))
            time.sleep(1)
        except Exception as e:
            console.print(f"[red]Error with theme {theme_name}: {e}[/red]")


def demo_tables():
    """Demonstrate table functionality"""
    console = Console()
    
    console.print("\n" + "="*60)
    console.print("[bold blue]TABLES DEMO[/bold blue]", justify="center")
    console.print("="*60)
    
    # Basic table
    console.print("\n[bold]1. Basic Table:[/bold]")
    table = Table()
    table.add_column("Name", style="cyan")
    table.add_column("Age", style="magenta")
    table.add_column("City", style="green")
    
    table.add_row("Alice", "30", "New York")
    table.add_row("Bob", "25", "Los Angeles")
    table.add_row("Charlie", "35", "Chicago")
    console.print(table)
    
    # Styled table
    console.print("\n[bold]2. Styled Table with Different Box:[/bold]")
    table2 = Table(
        title="Employee Directory",
        caption="Updated: " + datetime.now().strftime("%Y-%m-%d"),
        box=box.ROUNDED,
        show_lines=True
    )
    table2.add_column("ID", justify="right", style="cyan", no_wrap=True)
    table2.add_column("Name", style="magenta")
    table2.add_column("Department", justify="center", style="green")
    table2.add_column("Salary", justify="right", style="yellow")
    
    table2.add_row("001", "John Doe", "Engineering", "$75,000")
    table2.add_row("002", "Jane Smith", "Marketing", "$65,000")
    table2.add_row("003", "Bob Johnson", "Sales", "$70,000")
    console.print(table2)


def demo_progress_bars():
    """Demonstrate progress bar functionality"""
    console = Console()
    
    console.print("\n" + "="*60)
    console.print("[bold blue]PROGRESS BARS DEMO[/bold blue]", justify="center")
    console.print("="*60)
    
    # Simple progress bar
    console.print("\n[bold]1. Simple Progress Bar:[/bold]")
    with Progress() as progress:
        task = progress.add_task("Processing...", total=50)
        for i in range(50):
            time.sleep(0.02)
            progress.update(task, advance=1)
    
    # Multiple progress bars
    console.print("\n[bold]2. Multiple Progress Bars:[/bold]")
    with Progress() as progress:
        download_task = progress.add_task("Downloading...", total=100)
        process_task = progress.add_task("Processing...", total=80)
        upload_task = progress.add_task("Uploading...", total=60)
        
        for i in range(100):
            time.sleep(0.01)
            if i < 100:
                progress.update(download_task, advance=1)
            if i < 80:
                progress.update(process_task, advance=1)
            if i < 60:
                progress.update(upload_task, advance=1)
    
    # Custom progress bar
    console.print("\n[bold]3. Custom Progress Bar:[/bold]")
    progress = Progress(
        TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        TimeElapsedColumn(),
    )
    
    with progress:
        task = progress.add_task("download", filename="large_file.zip", total=1000)
        for i in range(1000):
            time.sleep(0.001)
            progress.update(task, advance=1)


def demo_panels_and_layout():
    """Demonstrate panels and layout using safe box styles"""
    console = Console()
    formatter = SafeBoxFormatter()
    
    console.print("\n" + "="*60)
    console.print("[bold blue]PANELS AND LAYOUT DEMO[/bold blue]", justify="center")
    console.print("="*60)
    
    # Basic panels with safe styles
    console.print("\n[bold]1. Basic Panels (Safe Styles):[/bold]")
    console.print(formatter.create_panel("Simple ASCII panel", "ASCII"))
    console.print(formatter.create_panel("Success message", "ROUNDED", style="green", title="✓ Success"))
    console.print(formatter.create_panel("Error message", "SQUARE", style="red", title="✗ Error", subtitle="Please try again"))
    
    # Columns with different safe box styles
    console.print("\n[bold]2. Columns Layout (Different Safe Styles):[/bold]")
    panels = [
        formatter.create_panel("ASCII Style\nReliable everywhere", "ASCII", style="blue"),
        formatter.create_panel("Rounded Style\nModern look", "ROUNDED", style="green"),
        formatter.create_panel("Double Style\nClassic appearance", "DOUBLE", style="red")
    ]
    console.print(Columns(panels))
    
    # Complex layout using safe styles
    console.print("\n[bold]3. Complex Layout (Safe Styles Only):[/bold]")
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3)
    )
    layout["body"].split_row(
        Layout(name="left"),
        Layout(name="right")
    )
    
    layout["header"].update(formatter.create_panel("Header Section", "HEAVY", style="blue"))
    layout["left"].update(formatter.create_panel("Left Sidebar\n• Menu item 1\n• Menu item 2", "SQUARE", style="green"))
    layout["right"].update(formatter.create_panel("Main Content\nThis is the main content area.", "ROUNDED", style="yellow"))
    layout["footer"].update(formatter.create_panel("Footer - Status: Ready", "ASCII", style="cyan"))
    
    console.print(layout, height=15)
    
    # Show box style recommendations
    console.print("\n[bold]4. Box Style Recommendations for Developer Tools:[/bold]")
    recommendations = [
        ("Success Messages", "ROUNDED", "green", "Modern, friendly appearance"),
        ("Error Messages", "SQUARE", "red", "Clear, attention-grabbing"),
        ("Debug Info", "ASCII", "dim white", "Always works, minimal"),
        ("Important Notices", "DOUBLE", "yellow", "Professional, prominent"),
        ("Status Panels", "HEAVY", "blue", "Bold, clear hierarchy"),
        ("Separators", "HORIZONTALS", "cyan", "Clean section division")
    ]
    
    for purpose, style_name, color, description in recommendations:
        panel = formatter.create_panel(
            f"Purpose: {purpose}\nDescription: {description}",
            style_name,
            style=color,
            title=f"{purpose} - {style_name}",
            width=60
        )
        console.print(panel)
        console.print()


def demo_trees_and_json():
    """Demonstrate trees and JSON formatting"""
    console = Console()
    
    console.print("\n" + "="*60)
    console.print("[bold blue]TREES AND JSON DEMO[/bold blue]", justify="center")
    console.print("="*60)
    
    # Tree demo
    console.print("\n[bold]1. Tree Structure:[/bold]")
    tree = Tree("📁 Project Root")
    tree.add("📁 src/")
    src_branch = tree.add("📁 src/")
    src_branch.add("📄 main.py")
    src_branch.add("📄 utils.py")
    src_branch.add("📄 config.py")
    
    tests_branch = tree.add("📁 tests/")
    tests_branch.add("📄 test_main.py")
    tests_branch.add("📄 test_utils.py")
    
    tree.add("📄 README.md")
    tree.add("📄 requirements.txt")
    tree.add("📄 .gitignore")
    
    console.print(tree)
    
    # JSON demo
    console.print("\n[bold]2. JSON Formatting:[/bold]")
    sample_data = {
        "name": "Rich Demo",
        "version": "1.0.0",
        "dependencies": {
            "rich": "^13.0.0",
            "python": ">=3.7"
        },
        "features": ["colors", "tables", "progress", "syntax"],
        "config": {
            "debug": True,
            "max_width": 120,
            "theme": "dark"
        },
        "stats": {
            "downloads": 1234567,
            "stars": 42000,
            "forks": 1500
        }
    }
    
    json_obj = JSON.from_data(sample_data)
    console.print(json_obj)


def demo_markdown_and_rules():
    """Demonstrate markdown and rules"""
    console = Console()
    
    console.print("\n" + "="*60)
    console.print("[bold blue]MARKDOWN AND RULES DEMO[/bold blue]", justify="center")
    console.print("="*60)
    
    # Rules
    console.print("\n[bold]1. Rules/Dividers:[/bold]")
    console.print(Rule())
    console.print(Rule("Section 1"))
    console.print(Rule("Important Section", style="red"))
    console.print(Rule("Centered Title", align="center"))
    console.print(Rule("Right Aligned", align="right"))
    
    # Markdown
    console.print("\n[bold]2. Markdown Rendering:[/bold]")
    markdown_text = """
# Sample Markdown

This is a **bold** statement and this is *italic*.

## Code Example

```python
def hello_world():
    print("Hello, World!")
    return True
```

## Lists

### Unordered List
- First item
- Second item  
- Third item

### Ordered List
1. Step one
2. Step two
3. Step three

## Links and More

Check out [Rich](https://github.com/Textualize/rich) for more info!

> This is a blockquote
> with multiple lines

---

**Table Example:**

| Name | Age | City |
|------|-----|------|
| Alice | 30 | NYC |
| Bob | 25 | LA |
"""
    
    md = Markdown(markdown_text)
    console.print(md)


def demo_alignment_and_padding():
    """Demonstrate alignment and padding"""
    console = Console()
    
    console.print("\n" + "="*60)
    console.print("[bold blue]ALIGNMENT AND PADDING DEMO[/bold blue]", justify="center")
    console.print("="*60)
    
    # Alignment
    console.print("\n[bold]1. Text Alignment:[/bold]")
    console.print(Align.left("Left aligned text"))
    console.print(Align.center("Center aligned text"))
    console.print(Align.right("Right aligned text"))
    
    # Padding
    console.print("\n[bold]2. Padding Examples:[/bold]")
    console.print(Padding("No padding", 0))
    console.print(Padding("Padding 1 on all sides", 1))
    console.print(Padding("Padding 2 on all sides", 2))
    console.print(Padding("Vertical 1, Horizontal 4", (1, 4)))
    console.print(Padding("Top 0, Right 2, Bottom 1, Left 3", (0, 2, 1, 3)))


def demo_themes():
    """Demonstrate custom themes"""
    console = Console()
    
    console.print("\n" + "="*60)
    console.print("[bold blue]CUSTOM THEMES DEMO[/bold blue]", justify="center")
    console.print("="*60)
    
    # Custom theme
    custom_theme = Theme({
        "success": "bold green",
        "error": "bold red",
        "warning": "bold yellow",
        "info": "bold blue",
        "debug": "dim white",
        "brand_primary": "#ff6b6b",
        "brand_secondary": "#4ecdc4",
        "highlight": "bold magenta on yellow"
    })
    
    themed_console = Console(theme=custom_theme)
    
    themed_console.print("\n[bold]Custom Theme Colors:[/bold]")
    themed_console.print("This is a success message", style="success")
    themed_console.print("This is an error message", style="error")
    themed_console.print("This is a warning message", style="warning")
    themed_console.print("This is an info message", style="info")
    themed_console.print("This is a debug message", style="debug")
    themed_console.print("Brand primary color", style="brand_primary")
    themed_console.print("Brand secondary color", style="brand_secondary")
    themed_console.print("Highlighted text", style="highlight")


def demo_live_display():
    """Demonstrate live updating display"""
    console = Console()
    
    console.print("\n" + "="*60)
    console.print("[bold blue]LIVE DISPLAY DEMO[/bold blue]", justify="center")
    console.print("="*60)
    
    console.print("\n[bold]Live updating table (5 seconds):[/bold]")
    
    def generate_live_table():
        table = Table(title="Real-time Data")
        table.add_column("ID", style="cyan")
        table.add_column("Value", style="magenta")
        table.add_column("Status", style="green")
        table.add_column("Timestamp", style="yellow")
        
        for i in range(5):
            status = random.choice(["✓ Active", "⚠ Warning", "✗ Error"])
            value = random.randint(1, 100)
            timestamp = datetime.now().strftime("%H:%M:%S")
            table.add_row(str(i+1), str(value), status, timestamp)
        
        return table
    
    with Live(generate_live_table(), refresh_per_second=2) as live:
        for _ in range(10):  # Update for 5 seconds
            time.sleep(0.5)
            live.update(generate_live_table())


def main():
    """Run all demos"""
    console = Console()
    
    console.print("\n" + "🎨" * 20)
    console.print("[bold green]RICH LIBRARY COMPLETE DEMONSTRATION[/bold green]", justify="center")
    console.print("🎨" * 20)
    console.print("\n[dim]This demo will show you all Rich features, styles, and options.[/dim]")
    console.print("[dim]Press Ctrl+C at any time to exit.[/dim]\n")
    
    input("Press Enter to start the demo...")
    
    try:
        demo_basic_features()
        input("\nPress Enter to continue to Box Styles demo...")
        
        demo_syntax_themes()
        input("\nPress Enter to continue to Tables demo...")
        
        demo_tables()
        input("\nPress Enter to continue to Progress Bars demo...")
        
        demo_progress_bars()
        input("\nPress Enter to continue to Panels and Layout demo...")
        
        demo_panels_and_layout()
        input("\nPress Enter to continue to Trees and JSON demo...")
        
        demo_trees_and_json()
        input("\nPress Enter to continue to Markdown and Rules demo...")
        
        demo_markdown_and_rules()
        input("\nPress Enter to continue to Alignment and Padding demo...")
        
        demo_alignment_and_padding()
        input("\nPress Enter to continue to Custom Themes demo...")
        
        demo_themes()
        input("\nPress Enter to continue to Live Display demo...")
        
        demo_live_display()
        
        console.print("\n" + "🎉" * 20)
        console.print("[bold green]DEMO COMPLETE![/bold green]", justify="center")
        console.print("🎉" * 20)
        console.print("\n[dim]You've seen all the Rich library features![/dim]", justify="center")
        
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Demo interrupted by user. Goodbye![/yellow]")
    except Exception as e:
        console.print(f"\n\n[red]Error during demo: {e}[/red]")


if __name__ == "__main__":
    main()
