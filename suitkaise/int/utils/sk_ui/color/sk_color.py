# add license here

# suitkaise/int/utils/sk_ui/color/sk_color.py

"""
Module responsible for streamlining color management.

This allows for you to define a color in many different ways, as well
as pick a contrasting, complementary, or similar color to the one you
defined. This is useful for creating color palettes, and for
creating color schemes that are easy to read and understand.

Also comes with a color picker that allows you to pick a color from
the screen, and a color wheel.

Comes with an SKColorRegistry that allows you to register custom colors
for use later on.


"""

import threading
from typing import Union, Optional

from suitkaise.int.utils.sk_ui.color.register_sk_colors import register_sk_colors


class SKColorRegistry:
    """
    Singleton registry to manage all registered colors.

    This class allows you to register custom colors for use later on.
    
    If you register a color with the same name as a Suitkaise default,
    use 'Suitkaise.color' to access the original color (ex. 'Suitkaise.Pine Green').
    
    """
    _sk_color_registry = None
    _sk_color_registry_lock = threading.RLock()

    def __new__(cls):
        """Ensure that only one instance of SKColorRegistry is created."""
        with cls._sk_color_registry_lock:
            if cls._sk_color_registry is None:
                cls._sk_color_registry = super(SKColorRegistry, cls).__new__(cls)
                cls._sk_color_registry._init_registry()
        return cls._sk_color_registry
    
    
    def _init_registry(self):
        """Initialize the registry with default values."""
        self._colors = {}  # color name -> color object
        self._suitkaise_colors = {}  # color name -> color object

        register_sk_colors()  # Register default colors

    @classmethod
    def get_instance(cls):
        """Get the singleton instance of SKColorRegistry."""
        if cls._sk_color_registry is None:
            cls._sk_color_registry = cls()
        return cls._sk_color_registry


    def register_color(self, color_name, color):
        """Register a new color, using color_name for the name."""
        with self._sk_color_registry_lock:
            if color_name not in self._colors:
                # capitalize the first letter of each word in color_name
                color_name = color_name.title()
                self._colors[color_name] = color
            else:
                raise ValueError(f"Color '{color_name}' is already registered.")
        return self._colors[color_name]
    
    
    def deregister_color(self, color_name):
        """Deregister a color, using color_name for the name."""
        with self._sk_color_registry_lock:
            # capitalize the first letter of each word in color_name
            color_name = color_name.title()
            if color_name in self._colors:
                del self._colors[color_name]
            else:
                raise ValueError(f"Color '{color_name}' is not registered.")
            
    
    def register_suitkaise_color(self, color_name, color):
        """
        Register a new Suitkaise color, using color_name for the name.
        
        For internal use only.
        
        """
        with self._sk_color_registry_lock:
            # capitalize the first letter of each word in color_name
            color_name = color_name.title()
            color_name = "Suitkaise." + color_name
            if color_name not in self._suitkaise_colors:
                self._suitkaise_colors[color_name] = color
            else:
                raise ValueError(f"Color '{color_name}' is already registered.")
            
            
    def add(self, color_name, color):
        """
        Add a color to the registry.
        
        This will register the color if it is not already registered.
        
        """
        self.register_color(color_name, color)


    def get(self, color_name: str) -> Optional['SKColor']:
        """
        Get a color from the registry.
        
        This will return the color if it is registered, otherwise it will
        return None.
        
        """
        with self._sk_color_registry_lock:
            # capitalize the first letter of each word in color_name
            color_name = color_name.title()
            color = self._colors.get(color_name, None)
            if not color:
                for color_key in self._suitkaise_colors:  # Use a different variable name
                    if color_key.endswith(color_name):
                        return self._suitkaise_colors[color_key]
            return color
        
    def remove(self, color_name):
        """
        Remove a color from the registry.
        
        This will remove the color if it is registered.
        
        """
        self.deregister_color(color_name)

            
    def is_registered(self, color_name):
        """
        Check if a color is registered.
        
        This will return True if the color is registered, otherwise it will
        return False.
        
        """
        with self._sk_color_registry_lock:
            # capitalize the first letter of each word in color_name
            color_name = color_name.title()
            registered = color_name in self._colors
            if not registered:
                for color_key in self._suitkaise_colors:  # For consistency
                    if color_key.endswith(color_name):
                        return True
            return registered
            



class SKColor:
    """
    Class representing a color.

    This class allows you to define a color in many different ways,
    and converts it to a hex value color.

    Supported formats:
    - Hex: #RRGGBB, #RGB
    - RGB: (R, G, B)
    - common colors (manually added)
    - any format + lighter n%, darker n%
    - any format + complementary
    - any format + contrasting
    - any format + n% color

    examples:

    primary_color = SKColor('Pine Green') (#008C45)

    (# make a secondary color that is 10% lighter and 10% more red)

    secondary_color = primary_color.lighter(10).more("red", 10)

    (# make a tertiary color that contrasts and is 30% darker)

    tertiary_color = primary_color.contrasting().darker(30)

    (# make a fourth color, a really light blue)

    fourth_color = SKColor('Light Blue').lighter(20)

    (# save the colors for later)
    SKColorRegistry.add('theme1_primary', primary_color)
    SKColorRegistry.add('theme1_secondary', secondary_color)
    SKColorRegistry.add('theme1_tertiary', tertiary_color)
    SKColorRegistry.add('theme1_fourth', fourth_color)

    (# get the colors later)
    primary_color = SKColor('theme1_primary')
    
    """

    def __init__(self, color):
        """
        Initialize the SKColor object.

        Args:
            color: The color to initialize the object with. This can be a
                   hex string, RGB tuple, or a common color name.

        """
        self.color = self._to_hex(color)
        self.color_info = {
            'color': self.color, # hex value
            'original': color, # ex. 'Pine Green'
            'modifiers': [], # ex. 'lighter', 'darker', 'more red', opacity, etc.
            'contrasting': False, # ex. 'contrasting'
            'opacity': 100, # percent
        }
    
    def _to_hex(self, color):
        """
        Convert a color to its hex representation.
        
        Args:
            color: The color to convert. This can be a hex string, RGB tuple,
                an SKColor object, or a common color name.
        
        Returns:
            A hex color string in the format '#RRGGBB'.
        """
        # If it's already an SKColor, get its hex value
        if isinstance(color, SKColor):
            return color.color
            
        # If it's a hex color already
        if isinstance(color, str) and color.startswith('#'):
            # Normalize shorthand hex (#RGB) to full form (#RRGGBB)
            if len(color) == 4:
                return '#' + ''.join([c*2 for c in color[1:]])
            # Return normalized full-form hex
            elif len(color) == 7:
                return color.lower()
            else:
                raise ValueError(f"Invalid hex color format: {color}")
                
        # If it's an RGB tuple
        elif isinstance(color, tuple) and len(color) == 3:
            # Validate RGB values
            if not all(0 <= c <= 255 for c in color):
                raise ValueError(f"RGB values must be between 0 and 255: {color}")
            return self._rgb_to_hex(color)
            
        # If it's a color name
        elif isinstance(color, str):
            # Try to get from registry
            color_reg = SKColorRegistry()
            registered_color = color_reg.get(color)
            if registered_color:
                # If it's an SKColor object, get its hex value
                if isinstance(registered_color, SKColor):
                    return registered_color.color
                # Otherwise assume it's a hex string
                return registered_color
            else:
                raise ValueError(f"Color name not found in registry: {color}")
        
        # Invalid format
        else:
            raise ValueError(f"Invalid color format: {color}")
        
        
    def _hex_to_rgb(self, hex_color):
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        
        # Handle shorthand hex (#RGB)
        if len(hex_color) == 3:
            hex_color = ''.join([c*2 for c in hex_color])
            
        # Convert to RGB
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _rgb_to_hex(self, rgb):
        """Convert RGB tuple to hex color."""
        return '#{:02x}{:02x}{:02x}'.format(*rgb)

    def _clamp(self, value, min_val=0, max_val=255):
        """Clamp a value between min and max."""
        return max(min_val, min(max_val, value))
    
    def _to_sk_color(self, color: str) -> 'SKColor':
        """
        Convert a color to an SKColor object.
        
        Args:
            color: The color to convert. This can be a hex string, RGB tuple,
                or a common color name.
        
        Returns:
            An SKColor object.
        """
        return SKColor(color)


    def lighter(self, percent: int) -> 'SKColor':
        """
        Lighten color by a percentage.

        Args:
            percent: The percentage to lighten the color by.
        
        """
        self.color_info['modifiers'].append({
            'mod_name': 'lighter',
            'percent': percent,
        })

        # apply the modifiers to the color
        rgb = self._hex_to_rgb(self.color)
        lighter_rgb = self._apply_lighter(rgb, percent)
        self.color = self._rgb_to_hex(lighter_rgb)

        return self
    
    def darker(self, percent: int) -> 'SKColor':
        """
        Darken color by a percentage.
        
        Args:
            percent: The percentage to darken the color by.
        
        """
        self.color_info['modifiers'].append({
            'mod_name': 'darker',
            'percent': percent,
        })

        # apply the modifiers to the color
        rgb = self._hex_to_rgb(self.color)
        darker_rgb = self._apply_darker(rgb, percent)
        self.color = self._rgb_to_hex(darker_rgb)

        return self
    
    def more(self, more_color: Union[str, 'SKColor'], percent: int) -> 'SKColor':
        """
        Add more of a color to the current color.
        
        Args:
            color: The color to add more of.
            percent: The percentage to add.

        """
        # see if more_color is a registered color
        if isinstance(more_color, str):
            color_reg = SKColorRegistry()
            if color_reg.is_registered(more_color):
                more_color = color_reg.get(more_color) # type: ignore
            else:
                more_color = self._to_sk_color(more_color)

        self.color_info['modifiers'].append({
            'mod_name': 'more',
            'color': more_color,
            'percent': percent,
        })

        # apply the modifiers to the color
        rgb = self._hex_to_rgb(self.color)
        more_rgb = self._apply_more(rgb, more_color, percent)
        self.color = self._rgb_to_hex(more_rgb)

        return self
    
    def less(self, less_color: Union[str, 'SKColor'], percent: int) -> 'SKColor':
        """
        Remove some of a color from the current color.
        
        Args:
            color: The color to remove some of.
            percent: The percentage to remove.

        """
        # see if less_color is a registered color
        if isinstance(less_color, str):
            color_reg = SKColorRegistry()
            if color_reg.is_registered(less_color):
                less_color = color_reg.get(less_color) # type: ignore
            else:
                less_color = self._to_sk_color(less_color)

        self.color_info['modifiers'].append({
            'mod_name': 'less',
            'color': less_color,
            'percent': percent,
        })

        # apply the modifiers to the color
        rgb = self._hex_to_rgb(self.color)
        less_rgb = self._apply_less(rgb, less_color, percent)
        self.color = self._rgb_to_hex(less_rgb)

        return self
    
    def contrasting(self) -> 'SKColor':
        """
        Make the color its contrasting/complementary color.
        
        """
        self.color_info['contrasting'] = True

        # apply the modifiers to the color
        rgb = self._hex_to_rgb(self.color)
        contrasting_rgb = self._apply_contrasting(rgb)
        self.color = self._rgb_to_hex(contrasting_rgb)

        return self
    

    def opacity(self, percent: int) -> 'SKColor':
        """
        Set the opacity of the color.
        
        Args:
            percent: The percentage to set the opacity to.
        
        """
        # clamp percent
        percent = self._clamp(percent, 0, 100)
        self.color_info['opacity'] = percent

        # no mod, but stores metadata for alpha encoding later

        return self
    

    def _apply_lighter(self, rgb, percent):
        """Apply the lighter modifier to the color."""
        return tuple(self._clamp(int(c + (255 - c) * percent / 100)) for c in rgb)
    
    def _apply_darker(self, rgb, percent):
        """Apply the darker modifier to the color."""
        return tuple(self._clamp(int(c - c * percent / 100)) for c in rgb)
    
    def _apply_more(self, rgb, target_color, percent):
        """
        Move the color towards the target color by a percentage.
        
        Args:
            rgb: The current RGB tuple
            target_color: An SKColor object or string/hex/RGB representing the target color
            percent: Percentage to move towards the target (0-100)
            
        Returns:
            A new RGB tuple moved towards the target color

        """
        
        # Get the target RGB values
        target_rgb = self._hex_to_rgb(target_color.color)
        
        # For each component, move a percentage of the distance towards the target
        result = []
        for curr, target in zip(rgb, target_rgb):
            # Calculate the distance to move
            distance = target - curr
            # Move by the specified percentage of that distance
            new_value = curr + distance * (percent / 100)
            # Ensure the result is in the valid range
            result.append(self._clamp(int(new_value)))
        
        return tuple(result)
    
    def _apply_less(self, rgb, target_color, percent):
        """
        Move the color away from the target color by a percentage.
        
        Args:
            rgb: The current RGB tuple
            target_color: An SKColor object or string/hex/RGB representing the target color
            percent: Percentage to move away from the target (0-100)
            
        Returns:
            A new RGB tuple moved away from the target color

        """
        
        # Get the target RGB values
        target_rgb = self._hex_to_rgb(target_color.color)
        
        # For each component, move a percentage of the distance away from the target
        result = []
        for curr, target in zip(rgb, target_rgb):
            # Calculate the direction and distance to move away
            distance = curr - target
            # Move by the specified percentage further in the same direction
            new_value = curr + distance * (percent / 100)
            # Ensure the result is in the valid range
            result.append(self._clamp(int(new_value)))
        
        return tuple(result)
    
    def _apply_contrasting(self, rgb):
        """Create a contrasting color."""
        return tuple(255 - c for c in rgb) # Invert the color
    
