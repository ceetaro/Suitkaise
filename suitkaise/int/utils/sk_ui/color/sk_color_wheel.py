# -------------------------------------------------------------------------------------
# Copyright 2025 Casey Eddings
# Copyright (C) 2025 Casey Eddings
#
# This file is a part of the Suitkaise application, available under either
# the Apache License, Version 2.0 or the GNU General Public License v3.
#
# ~~ Apache License, Version 2.0 (http://www.apache.org/licenses/LICENSE-2.0)
#
#       Licensed under the Apache License, Version 2.0 (the "License");
#       you may not use this file except in compliance with the License.
#       You may obtain a copy of the License at
#
#           http://www.apache.org/licenses/LICENSE-2.0
#
#       Unless required by applicable law or agreed to in writing, software
#       distributed under the License is distributed on an "AS IS" BASIS,
#       WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#       See the License for the specific language governing permissions and
#       limitations under the License.
#
# ~~ GNU General Public License, Version 3 (http://www.gnu.org/licenses/gpl-3.0.html)
#
#       This program is free software: you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation, either version 3 of the License, or
#       (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# -------------------------------------------------------------------------------------

# suitkaise/int/utils/sk_ui/color/sk_color_wheel.py

"""
Module providing a customizable color wheel widget.

This module contains the SKColorWheel class which provides a circular
color selection widget that works with the SKColor system.
"""

import math
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QStyleOption, QStyle, QStyleOptionSlider,
    QSlider
)
from PyQt6.QtGui import QPainter, QColor, QPen, QConicalGradient, QRadialGradient
from PyQt6.QtCore import QPoint, QRect, QEvent, pyqtSignal, Qt


from suitkaise.int.utils.sk_ui.color.sk_color import SKColor

class PrecisionSlider(QSlider):
    """A custom slider that provides more precise control for fine adjustments."""
    
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        
        # Set smaller page step for finer control when clicking on the track
        self.setPageStep(5)
        
        # Add properties to reduce jitter
        self._last_value = 0
        self._update_threshold = 1  # Only update when change is >= this amount
        
        # Same styling as before
        self.setStyleSheet("""
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #b4b4b4, stop:1 #8f8f8f);
                border: 1px solid #5c5c5c;
                width: 18px;  /* Larger handle is easier to control */
                height: 18px;
                margin: -9px 0;
                border-radius: 9px;
            }
            QSlider::groove:horizontal {
                background: #d6d6d6;
                height: 6px;  /* Slightly thicker groove */
                border-radius: 3px;
            }
        """)
    
    def mousePressEvent(self, event):
        """Override to implement smoother clicking behavior."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Calculate position with better precision
            val = self._pixelPosToRangeValue(event.position().x())
            # Only update if the change is significant
            if abs(val - self.value()) >= self._update_threshold:
                self._last_value = val
                self.setValue(val)
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def _pixelPosToRangeValue(self, pos):
        """Convert pixel position to slider value with better precision."""
        # Create a style option for the slider
        option = QStyleOptionSlider()
        self.initStyleOption(option)
        
        # Get the slider's style object
        style = self.style()
        
        # Get the slider groove and handle rectangles
        if style is None:
            raise RuntimeError("Style object is None. Ensure the widget is properly initialized.")
        groove_rect = style.subControlRect(QStyle.ComplexControl.CC_Slider, option, QStyle.SubControl.SC_SliderGroove, self)
        handle_rect = style.subControlRect(QStyle.ComplexControl.CC_Slider, option, QStyle.SubControl.SC_SliderHandle, self)
        
        # Calculate the slider length and range
        slider_length = groove_rect.width()
        slider_min = self.minimum()
        slider_max = self.maximum()
        
        # Calculate the position adjusted for handle width
        handle_width = handle_rect.width()
        available_space = slider_length - handle_width
        
        # Calculate the relative position (0.0 to 1.0)
        if available_space > 0:
            # Adjust for handle position and constrain within valid range
            adjusted_pos = max(0, min(pos - groove_rect.x() - handle_width / 2, available_space))
            pos_ratio = adjusted_pos / available_space
            return int(slider_min + pos_ratio * (slider_max - slider_min))
        
        return slider_min

    def mouseMoveEvent(self, event):
        """Override to implement dragging behavior with less jitter."""
        if event.buttons() & Qt.MouseButton.LeftButton:
            # Calculate position with better precision
            val = self._pixelPosToRangeValue(event.position().x())
            # Only update if the change is significant
            if abs(val - self._last_value) >= self._update_threshold:
                self._last_value = val
                self.setValue(val)
            event.accept()
        else:
            super().mouseMoveEvent(event)

class SKColorWheel(QWidget):
    # Signal emitted when color changes
    colorChanged = pyqtSignal(object)  # Use object instead of SKColor for PyQt compatibility
    
    def __init__(self, parent=None, wheel_width=200, wheel_height=200, 
                 show_selector=True, selector_size=10):
        super().__init__(parent)
        
        # Create the main container widget
        self.main_container = QWidget(self)
        
        # Create the main vertical layout
        main_layout = QVBoxLayout(self.main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create the wheel area widget (this will be painted on)
        self.wheel_area = QWidget()
        self.wheel_area.setFixedSize(wheel_width, wheel_height - 50)  # Reserve space for slider
        
        # Add wheel area to main layout
        main_layout.addWidget(self.wheel_area)
        
        # Create slider area widget
        slider_widget = QWidget()
        slider_layout = QHBoxLayout(slider_widget)
        
        # Add slider components
        self.sat_label = QLabel("Saturation:")
        self.sat_slider = PrecisionSlider(Qt.Orientation.Horizontal, self)
        self.sat_slider.setMinimum(0)
        self.sat_slider.setMaximum(100)
        self.sat_slider.setValue(0)
        self.sat_value_label = QLabel("0%")
        
        slider_layout.addWidget(self.sat_label)
        slider_layout.addWidget(self.sat_slider)
        slider_layout.addWidget(self.sat_value_label)
        
        # Add slider widget to main layout
        main_layout.addWidget(slider_widget)
        
        # Set the size of the entire widget
        self.setFixedSize(wheel_width, wheel_height)
        
        # Configure wheel parameters
        self.wheel_width = wheel_width
        self.wheel_height = wheel_height - 50  # Adjusted for slider space
        self.wheel_margin = 5
        self.show_selector = show_selector
        self.selector_size = selector_size
        
        # Wheel geometry calculations
        self.center = QPoint(wheel_width // 2, self.wheel_height // 2)
        self.radius = min(wheel_width, self.wheel_height) // 2 - self.wheel_margin
        
        # Color properties
        self._hue = 0
        self._saturation = 0
        self._value = 100
        self._selector_pos = QPoint(self.center.x(), self.center.y() - self.radius // 2)
        self._current_color = SKColor((255, 0, 0))
        
        # Connect slider signal
        self.sat_slider.valueChanged.connect(self._update_from_slider)
        
        # Install event filter on wheel area for mouse events
        self.wheel_area.installEventFilter(self)
        
        # Enable mouse tracking
        self.wheel_area.setMouseTracking(True)
    
    def eventFilter(self, watched, event):
        """Handle events from the wheel area widget."""
        if watched == self.wheel_area:
            if event.type() == QEvent.Type.Paint:
                # Handle painting the wheel
                self._paint_wheel(watched)
                return True
            elif event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self._update_color_from_position(event.position().toPoint())
                    return True
            elif event.type() == QEvent.Type.MouseMove:
                if event.buttons() & Qt.MouseButton.LeftButton:
                    self._update_color_from_position(event.position().toPoint())
                    return True
        
        # Let the event propagate
        return super().eventFilter(watched, event)
    
    def _paint_wheel(self, widget):
        """Paint the color wheel on the wheel area widget."""
        painter = QPainter(widget)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw the color wheel
        self._draw_hue_saturation_wheel(painter)
        
        # Draw selector if enabled
        if self.show_selector:
            self._draw_selector(painter)
        
    def _draw_hue_saturation_wheel(self, painter):
        """Draw the hue and saturation wheel."""
        # Extract x and y coordinates from center point
        center_x = self.center.x()
        center_y = self.center.y()
        
        # Create gradient with separate coordinates
        conical_gradient = QConicalGradient(center_x, center_y, 0)
        
        # Add color stops for the hue circle (all at 100% saturation and value)
        for i in range(36):  # 36 segments for smooth gradient
            # Convert position (0-35) to angle (0-359)
            angle = i * 10
            # Convert angle to position in gradient (0.0-1.0)
            position = angle / 360.0
            # Create color from HSV
            color = QColor()
            color.setHsv(angle, 255, 255)  # Using 0-255 range for QColor
            # Add color stop
            conical_gradient.setColorAt(position, color)
        
        # Draw the hue circle
        painter.setBrush(conical_gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(self.center, self.radius, self.radius)
        
        # Now draw a white-to-transparent radial gradient for saturation
        # Use separate coordinates here too
        radial_gradient = QRadialGradient(center_x, center_y, self.radius)
        radial_gradient.setColorAt(0, QColor(255, 255, 255, 255))  # White at center
        radial_gradient.setColorAt(1, QColor(255, 255, 255, 0))    # Transparent at edge
        
        # Draw the saturation overlay
        painter.setBrush(radial_gradient)
        painter.drawEllipse(self.center, self.radius, self.radius)
    
    def _draw_selector(self, painter):
        """Draw the selector indicator at the current position."""
        # Create a contrasting pen color
        h, s, v = self.get_hsv()
        contrast_color = QColor()
        # For dark colors use white selector, for light colors use black
        if v < 50:
            contrast_color.setRgb(255, 255, 255)
        else:
            contrast_color.setRgb(0, 0, 0)
        
        pen = QPen(contrast_color)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # Draw circle at selector position
        painter.drawEllipse(self._selector_pos, 
                           self.selector_size, self.selector_size)
    
    def mousePressEvent(self, event):
        """Handle mouse press to select colors."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Only process clicks in the wheel area
            if event.position().y() <= self.wheel_height:
                self._update_color_from_position(event.position().toPoint())
    
    def mouseMoveEvent(self, event):
        """Handle mouse move while pressed to update colors."""
        if event.buttons() & Qt.MouseButton.LeftButton:
            # Only process drags in the wheel area
            if event.position().y() <= self.wheel_height:
                self._update_color_from_position(event.position().toPoint())
    
    def _update_color_from_position(self, pos):
        """
        Update the color based on mouse position.
        
        Args:
            pos: QPoint containing mouse coordinates
        """
        # Calculate vector from center
        dx = pos.x() - self.center.x()
        dy = pos.y() - self.center.y()
        
        # Calculate distance from center (for saturation)
        distance = math.sqrt(dx*dx + dy*dy)
        
        # Limit selection to within the wheel
        if distance > self.radius:
            # Project the point to the edge of the wheel
            dx = dx * (self.radius / distance)
            dy = dy * (self.radius / distance)
            distance = self.radius
            # Update position based on projection
            pos = QPoint(int(self.center.x() + dx), int(self.center.y() + dy))
        
        # Update selector position
        self._selector_pos = pos
        
        # Calculate angle (for hue)
        angle = math.degrees(math.atan2(dy, dx))
        # Convert to positive angle (0-360)
        if angle < 0:
            angle += 360
        
        # Update color values
        self._hue = int(angle) % 360
        self._saturation = int((distance / self.radius) * 100)
        
        # Update the slider (without triggering signals)
        self.sat_slider.blockSignals(True)
        self.sat_slider.setValue(self._saturation)
        self.sat_slider.blockSignals(False)
        
        # Update the saturation label
        self.sat_value_label.setText(f"{self._saturation}%")
        
        # Create new color
        qcolor = QColor()
        qcolor.setHsv(self._hue, int(self._saturation * 2.55), int(self._value * 2.55))
        rgb = (qcolor.red(), qcolor.green(), qcolor.blue())
        self._current_color = SKColor(rgb)
        
        # Emit signal with new color
        self.colorChanged.emit(self._current_color)
        
        # Trigger a redraw of the wheel area
        self.wheel_area.update()
    
    def _update_from_slider(self, value):
        """Update the color when the slider value changes."""
        # Use a larger threshold to prevent jitteriness
        if abs(self._saturation - value) < 1.0:
            return
            
        # Update saturation with less frequent updates
        self._saturation = value
        
        # Update the saturation label only for significant changes
        if abs(int(self._saturation) - int(float(self.sat_value_label.text().rstrip('%')))) >= 1:
            self.sat_value_label.setText(f"{value}%")
        
        # Don't update the selector position on every tiny change
        if abs(self._saturation - value) > 5.0:
            self._update_selector_position()
        
        # Create new color with smoother interpolation
        self._update_current_color()
        
        # Only update when necessary - use a flag to track if we need to repaint
        self.wheel_area.update()

    def _update_current_color(self):
        """Update the current color based on HSV values with smooth interpolation."""
        # Convert percentages to QColor range (0-255)
        h = self._hue
        s = int(self._saturation * 2.55 + 0.5)  # Add 0.5 for proper rounding
        v = int(self._value * 2.55 + 0.5)       # Add 0.5 for proper rounding
        
        # Create color with proper rounding
        qcolor = QColor()
        qcolor.setHsv(h, s, v)
        
        # Convert to RGB
        rgb = (qcolor.red(), qcolor.green(), qcolor.blue())
        self._current_color = SKColor(rgb)
        
        # Emit signal with new color
        self.colorChanged.emit(self._current_color)
    
    def get_color(self):
        """
        Get the currently selected color.
        
        Returns:
            SKColor object representing the selected color
        """
        return self._current_color
    
    def set_color(self, color):
        """
        Set the current color.
        
        Args:
            color: SKColor, QColor, hex string, or RGB tuple
        """
        # Convert to SKColor if needed
        if not isinstance(color, SKColor):
            color = SKColor(color)
        
        # Get RGB values and convert to HSV
        color_hex = color.color
        r, g, b = self._hex_to_rgb(color_hex)
        qcolor = QColor(r, g, b)
        
        # Update HSV values
        self._hue = qcolor.hue()
        self._saturation = int(qcolor.saturation() / 2.55)  # Convert 0-255 to 0-100
        self._value = int(qcolor.value() / 2.55)  # Convert 0-255 to 0-100
        
        # Update slider position
        self.sat_slider.blockSignals(True)
        self.sat_slider.setValue(self._saturation)
        self.sat_slider.blockSignals(False)
        
        # Update the saturation label
        self.sat_value_label.setText(f"{self._saturation}%")
        
        # Update selector position
        self._update_selector_position()
        
        # Update current color
        self._current_color = color
        
        # Trigger a redraw of the wheel area
        self.wheel_area.update()
    
    def _hex_to_rgb(self, hex_color):
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join([c*2 for c in hex_color])
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def get_hsv(self):
        """
        Get the current HSV values.
        
        Returns:
            Tuple of (hue, saturation, value) each in range 0-100
        """
        return (self._hue, self._saturation, self._value)
    
    def set_hsv(self, h, s, v):
        """
        Set the color using HSV values.
        
        Args:
            h: Hue (0-359)
            s: Saturation (0-100)
            v: Value (0-100)
        """
        # Update internal values
        self._hue = h % 360
        self._saturation = max(0, min(100, s))
        self._value = max(0, min(100, v))
        
        # Update slider position
        self.sat_slider.blockSignals(True)
        self.sat_slider.setValue(self._saturation)
        self.sat_slider.blockSignals(False)
        
        # Update the saturation label
        self.sat_value_label.setText(f"{self._saturation}%")
        
        # Update selector position
        self._update_selector_position()
        
        # Update current color
        qcolor = QColor()
        qcolor.setHsv(self._hue, int(self._saturation * 2.55), int(self._value * 2.55))
        rgb = (qcolor.red(), qcolor.green(), qcolor.blue())
        self._current_color = SKColor(rgb)
        
        # Trigger a redraw of the wheel area
        self.wheel_area.update()
    
    def set_saturation(self, saturation):
        """
        Set only the saturation while keeping the current hue and value.
        
        Args:
            saturation: Saturation value (0-100)
        """
        # Update the slider (which will trigger _update_from_slider)
        self.sat_slider.setValue(saturation)
    
    def _update_selector_position(self):
        """Update the selector position based on current HSV values."""
        # Convert hue to radians
        angle_rad = math.radians(self._hue)
        
        # Calculate distance from center based on saturation
        distance = (self._saturation / 100.0) * self.radius
        
        # Calculate position
        x = self.center.x() + distance * math.cos(angle_rad)
        y = self.center.y() + distance * math.sin(angle_rad)
        
        # Update selector position
        self._selector_pos = QPoint(int(x), int(y))