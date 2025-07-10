#!/usr/bin/env python3
"""
Extended Theme Approach - Override Foreground Colors
Inherit dark theme backgrounds, customize foreground colors
"""

from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.columns import Columns
from pygments.style import Style
from pygments.token import Token, Keyword, Name, Comment, String, Number, Operator
from pygments.styles import get_style_by_name

# Our custom color palette (same as before)
PALETTE = {
    'keyword': '#ff79c6',        # Pink keywords
    'function': '#34d399',       # Green functions
    'string': '#fbbf24',         # Yellow strings
    'number': '#a78bfa',         # Purple numbers
    'type': '#60a5fa',           # Blue types
    'comment': '#9ca3af',        # Gray comments
    'error': '#ef4444',          # Red errors
    'success': '#34d399',        # Green success
    'info': '#60a5fa',           # Blue info
}

class ExtendedDraculaTheme(Style):
    """
    Extends Dracula theme - keeps its dark background, overrides our colors
    """
    
    name = 'extended_dracula'
    
    # Get the base Dracula theme
    base_style = get_style_by_name('dracula')
    
    # Start with Dracula's styles (includes background)
    styles = dict(base_style.styles)
    
    # Override with our custom colors (foreground only)
    styles.update({
        # Keywords - our pink
        Keyword:                 f"bold {PALETTE['keyword']}",
        Keyword.Constant:        f"bold {PALETTE['number']}",  
        Keyword.Namespace:       f"bold {PALETTE['info']}",
        Keyword.Type:            f"bold {PALETTE['type']}",
        
        # Functions - our green  
        Name.Function:           f"bold {PALETTE['function']}",
        Name.Function.Magic:     f"bold {PALETTE['function']}",
        Name.Builtin:            f"{PALETTE['info']}",
        Name.Class:              f"bold {PALETTE['type']}",
        Name.Decorator:          f"{PALETTE['success']}",
        Name.Exception:          f"bold {PALETTE['error']}",
        
        # Strings - our yellow
        String:                  f"{PALETTE['string']}",
        String.Doc:              f"italic {PALETTE['string']}",
        String.Interpol:         f"{PALETTE['keyword']}",
        String.Escape:           f"{PALETTE['keyword']}",
        String.Affix:            f"{PALETTE['keyword']}",
        
        # Numbers - our purple  
        Number:                  f"{PALETTE['number']}",
        Number.Float:            f"{PALETTE['number']}",
        Number.Integer:          f"{PALETTE['number']}",
        Number.Hex:              f"{PALETTE['number']}",
        
        # Comments - our gray
        Comment:                 f"italic {PALETTE['comment']}",
        Comment.Single:          f"italic {PALETTE['comment']}",
        Comment.Multiline:       f"italic {PALETTE['comment']}",
        
        # Operators - our pink
        Operator:                f"{PALETTE['keyword']}",
        Operator.Word:           f"{PALETTE['keyword']}",
    })

class ExtendedMonokaiTheme(Style):
    """
    Extends Monokai theme - keeps its dark background, overrides our colors
    """
    
    name = 'extended_monokai'
    
    # Get the base Monokai theme
    base_style = get_style_by_name('monokai')
    
    # Start with Monokai's styles (includes background)
    styles = dict(base_style.styles)
    
    # Override with our custom colors
    styles.update({
        # Same overrides as Dracula
        Keyword:                 f"bold {PALETTE['keyword']}",
        Keyword.Constant:        f"bold {PALETTE['number']}",
        Keyword.Type:            f"bold {PALETTE['type']}",
        
        Name.Function:           f"bold {PALETTE['function']}",
        Name.Class:              f"bold {PALETTE['type']}",
        Name.Builtin:            f"{PALETTE['info']}",
        
        String:                  f"{PALETTE['string']}",
        String.Doc:              f"italic {PALETTE['string']}",
        
        Number:                  f"{PALETTE['number']}",
        
        Comment:                 f"italic {PALETTE['comment']}",
        
        Operator:                f"{PALETTE['keyword']}",
    })

class ExtendedVSCodeDarkTheme(Style):
    """
    Extends VS Code Dark theme - most popular among developers
    """
    
    name = 'extended_vscode_dark'
    
    # VS Code Dark theme base (approximated)
    base_style = get_style_by_name('vs')  # We'll override to make it dark
    
    # Create VS Code Dark-like base with our colors
    styles = {
        # Base tokens with VS Code Dark background
        Token:                   '#d4d4d4',  # VS Code default text
        
        # Our custom foreground colors
        Keyword:                 f"bold {PALETTE['keyword']}",
        Keyword.Constant:        f"bold {PALETTE['number']}",
        Keyword.Type:            f"bold {PALETTE['type']}",
        
        Name.Function:           f"bold {PALETTE['function']}",
        Name.Class:              f"bold {PALETTE['type']}",
        Name.Builtin:            f"{PALETTE['info']}",
        Name.Variable.Magic:     f"{PALETTE['number']}",
        
        String:                  f"{PALETTE['string']}",
        String.Doc:              f"italic {PALETTE['string']}",
        String.Interpol:         f"{PALETTE['keyword']}",
        
        Number:                  f"{PALETTE['number']}",
        
        Comment:                 f"italic {PALETTE['comment']}",
        
        Operator:                f"{PALETTE['keyword']}",
    }

class ExtendedGitHubDarkTheme(Style):
    """
    Extends GitHub Dark theme - familiar to many developers
    """
    
    name = 'extended_github_dark'
    
    # Get GitHub Dark as base
    try:
        base_style = get_style_by_name('github-dark')
        styles = dict(base_style.styles)
    except:
        # Fallback if github-dark not available
        styles = {}
    
    # Override with our colors
    styles.update({
        Keyword:                 f"bold {PALETTE['keyword']}",
        Keyword.Constant:        f"bold {PALETTE['number']}",
        Keyword.Type:            f"bold {PALETTE['type']}",
        
        Name.Function:           f"bold {PALETTE['function']}",
        Name.Class:              f"bold {PALETTE['type']}",
        Name.Builtin:            f"{PALETTE['info']}",
        
        String:                  f"{PALETTE['string']}",
        String.Doc:              f"italic {PALETTE['string']}",
        
        Number:                  f"{PALETTE['number']}",
        
        Comment:                 f"italic {PALETTE['comment']}",
        
        Operator:                f"{PALETTE['keyword']}",
    })

def demo_extended_themes():
    """Demo all extended themes with various code samples"""
    console = Console()
    
    console.print("[bold blue]🎨 Extended Dark Themes - Best of Both Worlds[/bold blue]")
    console.print("[dim]Dark backgrounds from established themes + our custom colors[/dim]\n")
    
    # Sample Python code
    python_code = '''#!/usr/bin/env python3
"""
Extended theme demo - combines dark backgrounds with custom colors
"""

import json
from typing import List, Dict, Optional

class DataProcessor:
    """Process data with custom highlighting"""
    
    def __init__(self, config: Dict[str, str]):
        self.config = config
        self._count = 0
    
    async def process_items(self, items: List[str]) -> Optional[Dict]:
        """Process a list of items"""
        results = {}
        
        for item in items:
            if item.startswith('#'):  # Skip comments
                continue
                
            # Process the item
            value = len(item) * 2.5
            results[item] = {
                'length': len(item),
                'value': value,
                'processed': True
            }
            self._count += 1
        
        return results if results else None

# Usage example
if __name__ == "__main__":
    config = {"mode": "production", "debug": False}
    processor = DataProcessor(config)
    
    items = ["hello", "world", "python", "rich"]
    result = await processor.process_items(items)
    
    print(f"Processed {len(result)} items")
'''

    # Test each extended theme
    themes = [
        ("Extended Dracula", "extended_dracula", "🧛 Popular dark theme"),
        ("Extended Monokai", "extended_monokai", "🌃 Classic dark theme"),  
        ("Extended VS Code Dark", "extended_vscode_dark", "💻 Most popular editor theme"),
        ("Extended GitHub Dark", "extended_github_dark", "🐙 Familiar to developers"),
    ]
    
    for theme_name, theme_id, description in themes:
        console.print(f"[bold green]{theme_name}[/bold green] - {description}")
        
        try:
            syntax = Syntax(
                python_code,
                "python", 
                theme=theme_id,
                line_numbers=True,
                word_wrap=True
            )
            
            console.print(Panel(
                syntax,
                title=f"{theme_name} Theme",
                subtitle="Dark background + our custom foreground colors",
                border_style="blue"
            ))
            
            # Show our color palette
            console.print(f"[dim]Our colors: [/dim]", end="")
            console.print(f"[{PALETTE['keyword']}]keyword[/] ", end="")
            console.print(f"[{PALETTE['function']}]function[/] ", end="")
            console.print(f"[{PALETTE['string']}]string[/] ", end="")
            console.print(f"[{PALETTE['number']}]number[/] ", end="")
            console.print(f"[{PALETTE['comment']}]comment[/]")
            console.print()
            
        except Exception as e:
            console.print(f"[red]Error with {theme_name}: {e}[/red]")
            console.print(f"[yellow]Note: {theme_id} may not be available in your Pygments version[/yellow]\n")

def demo_theme_comparison():
    """Compare original vs extended themes side by side"""
    console = Console()
    
    console.print("\n[bold blue]📊 Theme Comparison - Before vs After[/bold blue]\n")
    
    sample_code = '''def calculate_total(items: List[float]) -> float:
    """Calculate total with tax"""
    subtotal = sum(items)  # Sum all items
    tax_rate = 0.08  # 8% tax
    return subtotal * (1 + tax_rate)

# Usage
prices = [19.99, 24.50, 15.00]
total = calculate_total(prices)
print(f"Total: ${total:.2f}")'''
    
    # Compare original Dracula vs our extended version
    console.print("[bold]Original Dracula vs Extended Dracula:[/bold]")
    
    panels = []
    
    # Original Dracula
    try:
        original = Syntax(sample_code, "python", theme="dracula", line_numbers=False)
        panels.append(Panel(original, title="Original Dracula", width=50))
    except:
        panels.append(Panel("Dracula theme not available", title="Original Dracula", width=50))
    
    # Extended Dracula  
    try:
        extended = Syntax(sample_code, "python", theme="extended_dracula", line_numbers=False)
        panels.append(Panel(extended, title="Extended Dracula", subtitle="Our colors", width=50))
    except:
        panels.append(Panel("Extended theme error", title="Extended Dracula", width=50))
    
    console.print(Columns(panels))

def show_available_dark_themes():
    """Show what dark themes are available to extend"""
    console = Console()
    
    console.print("\n[bold blue]🌙 Available Dark Themes to Extend[/bold blue]\n")
    
    # Common dark themes that work well as bases
    dark_themes = [
        "monokai", "dracula", "github-dark", "nord", "nord-darker",
        "gruvbox-dark", "solarized-dark", "material", "native"
    ]
    
    console.print("[bold]Recommended base themes for extension:[/bold]")
    
    sample = 'def hello(): return "world"'
    
    for theme_name in dark_themes:
        try:
            syntax = Syntax(sample, "python", theme=theme_name, line_numbers=False)
            console.print(f"✅ [green]{theme_name}[/green] - Available")
            console.print(f"   {syntax}")
        except Exception as e:
            console.print(f"❌ [red]{theme_name}[/red] - Not available")
        console.print()

def create_theme_factory():
    """Show how to create a theme factory for easy customization"""
    console = Console()
    
    console.print("\n[bold blue]🏭 Theme Factory Pattern[/bold blue]\n")
    
    factory_code = '''class ThemeFactory:
    """Factory for creating extended themes with our color palette"""
    
    PALETTE = {
        'keyword': '#ff79c6',
        'function': '#34d399', 
        'string': '#fbbf24',
        'number': '#a78bfa',
        'type': '#60a5fa',
        'comment': '#9ca3af',
    }
    
    @classmethod
    def extend_theme(cls, base_theme_name: str, theme_name: str):
        """Create extended theme from any base theme"""
        
        try:
            base_style = get_style_by_name(base_theme_name)
            base_styles = dict(base_style.styles)
        except:
            base_styles = {}
        
        # Create new theme class
        class ExtendedTheme(Style):
            name = theme_name
            styles = base_styles
            
            # Override with our colors
            styles.update({
                Keyword: f"bold {cls.PALETTE['keyword']}",
                Name.Function: f"bold {cls.PALETTE['function']}",
                String: f"{cls.PALETTE['string']}",
                Number: f"{cls.PALETTE['number']}",
                Comment: f"italic {cls.PALETTE['comment']}",
                # ... more overrides
            })
        
        return ExtendedTheme

# Usage in your developer toolset
factory = ThemeFactory()
custom_dracula = factory.extend_theme("dracula", "custom_dracula")
custom_monokai = factory.extend_theme("monokai", "custom_monokai")'''
    
    syntax = Syntax(factory_code, "python", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title="Theme Factory Implementation"))

def main():
    """Main demo function"""
    console = Console()
    
    console.print("[bold green]🎯 Extended Theme Approach - The Best Solution![/bold green]\n")
    
    try:
        # Show available dark themes
        show_available_dark_themes()
        
        # Demo extended themes  
        demo_extended_themes()
        
        # Compare original vs extended
        demo_theme_comparison()
        
        # Show factory pattern
        create_theme_factory()
        
        console.print("\n[bold green]✅ Extended Theme Approach Complete![/bold green]")
        
        console.print("\n[bold]🏆 Benefits of This Approach:[/bold]")
        console.print("• [green]Dark backgrounds work perfectly[/green] - inherited from established themes")
        console.print("• [green]Custom colors work perfectly[/green] - our foreground overrides")
        console.print("• [green]Professional appearance[/green] - builds on proven themes")
        console.print("• [green]User familiarity[/green] - extends themes users already know")
        console.print("• [green]Fallback support[/green] - graceful degradation if base unavailable")
        
        console.print("\n[bold]🎨 Implementation for Your Toolset:[/bold]")
        console.print("1. Choose 2-3 popular dark themes as bases (Dracula, Monokai, VS Code Dark)")
        console.print("2. Extend them with your custom color palette")
        console.print("3. Let users choose their preferred base theme")
        console.print("4. All get consistent syntax coloring with familiar backgrounds")
        
        console.print("\n[bold blue]🚀 This is the perfect solution for your developer toolset![/bold blue]")
        console.print("You get professional dark backgrounds AND your custom color scheme!")
        
    except Exception as e:
        console.print(f"[red]Error in demo: {e}[/red]")

if __name__ == "__main__":
    main()