# add license here


from suitkaise.int.utils.sk_ui.color.sk_color import SKColor, SKColorRegistry
from suitkaise.int.utils.sk_ui.color.sk_color_wheel import SKColorWheel

def test_sk_color():
    """
    Test the SKColor class.
    
    """

    global sk_color_registry
    sk_color_registry = SKColorRegistry.get_instance()

    # initialize wheel
class ColorWheelDemo(QWidget):
    """Simple demonstration window for the color wheel."""
    
    def __init__(self):
        super().__init__()
        
        # Set up the window
        self.setWindowTitle("Color Wheel Demo")
        self.setMinimumSize(300, 400)
        
        # Create layout
        layout = QVBoxLayout()
        
        # Create and add the color wheel with integrated slider
        self.color_wheel = SKColorWheel(self, wheel_width=280, wheel_height=280)
        layout.addWidget(self.color_wheel)
        
        # Create a label to display the selected color
        self.color_display = QLabel("Select a color")
        self.color_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.color_display.setMinimumHeight(50)
        self.color_display.setStyleSheet("background-color: #CCCCCC; border: 1px solid #999999;")
        layout.addWidget(self.color_display)
        
        # Connect the color wheel's signal
        self.color_wheel.colorChanged.connect(self.update_color_display)
        
        # Set the layout
        self.setLayout(layout)
        
    def update_color_display(self, color):
        """Update the display when color changes."""
        # Get the hex color
        hex_color = color.color
        
        # Set dark or light text based on color brightness
        rgb = self._hex_to_rgb(hex_color)
        brightness = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000
        text_color = "#000000" if brightness > 128 else "#FFFFFF"
        
        # Update the color display
        self.color_display.setStyleSheet(f"background-color: {hex_color}; color: {text_color}; border: 1px solid #999999;")
        self.color_display.setText(f"Selected Color: {hex_color}")
        
    def _hex_to_rgb(self, hex_color):
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join([c*2 for c in hex_color])
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    