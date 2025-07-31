"""
Comprehensive tests for FDL Command Element Processor.

Tests the command element processor that handles command strings like </bold, red>
and delegates to registered command processors, including parsing, validation, and visual demonstrations.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch
from wcwidth import wcswidth

# Add the suitkaise package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from suitkaise.fdl._int.elements.command_element import (
    _CommandElement, _create_command_element, _get_available_command_processors
)
from suitkaise.fdl._int.core.format_state import _FormatState, _create_format_state
from suitkaise.fdl._int.core.command_registry import (
    _CommandRegistry, _CommandProcessor, UnknownCommandError
)


class MockCommandProcessor(_CommandProcessor):
    """Mock command processor for testing."""
    
    @classmethod
    def can_process(cls, command: str) -> bool:
        """Mock can process - handles test commands."""
        return command.lower() in ['test', 'mock', 'sample']
    
    @classmethod
    def process(cls, command: str, format_state: _FormatState) -> _FormatState:
        """Mock process - just sets a flag."""
        format_state.text_color = "test_processed"
        return format_state


class TestCommandElement:
    """Test suite for the command element processor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.format_state = _create_format_state()
        
        # Clear registry and register mock processor
        _CommandRegistry.clear_registry()
        _CommandRegistry.register(MockCommandProcessor, priority=50)
    
    def teardown_method(self):
        """Clean up after tests."""
        _CommandRegistry.clear_registry()
    
    def test_command_element_initialization(self):
        """Test command element initialization with various command strings."""
        # Simple command
        element = _CommandElement("bold")
        assert element.command_string == "bold"
        assert element.commands == ["bold"]
        
        # Multiple commands
        element = _CommandElement("bold, red, italic")
        assert element.command_string == "bold, red, italic"
        assert element.commands == ["bold", "red", "italic"]
        
        # Command with whitespace
        element = _CommandElement("  bold  ,  red  ")
        assert element.commands == ["bold", "red"]
        
        # Empty command string
        element = _CommandElement("")
        assert element.commands == []
        
        # Single command with extra spaces
        element = _CommandElement("   test   ")
        assert element.command_string == "test"
        assert element.commands == ["test"]
    
    def test_command_parsing_basic(self):
        """Test basic command parsing functionality."""
        test_cases = [
            ("bold", ["bold"]),
            ("bold, red", ["bold", "red"]),
            ("bold, red, italic", ["bold", "red", "italic"]),
            ("  bold  ,  red  ,  italic  ", ["bold", "red", "italic"]),
            ("", []),
            ("single", ["single"]),
        ]
        
        for command_string, expected_commands in test_cases:
            element = _CommandElement(command_string)
            assert element.commands == expected_commands
    
    def test_command_parsing_end_commands(self):
        """Test parsing of end commands."""
        # End command should add 'end' prefix to all commands
        element = _CommandElement("end bold, red")
        # The first command already has 'end', others should get it added
        expected = ["end bold", "end red"]
        assert element.commands == expected
        
        # Reset command should be normalized
        element = _CommandElement("reset")
        assert element.commands == ["reset"]
        
        # Mixed end commands
        element = _CommandElement("end bold, italic, underline")
        expected = ["end bold", "end italic", "end underline"]
        assert element.commands == expected
    
    def test_command_parsing_box_commands(self):
        """Test parsing of box commands (special case - no splitting on commas)."""
        # Box commands should not be split even if they contain commas
        box_commands = [
            "box rounded, title Important Message",
            "box double, title Error, color red",
            "end box",
        ]
        
        for box_command in box_commands:
            element = _CommandElement(box_command)
            # Box commands should be kept as single command
            assert len(element.commands) == 1
            assert element.commands[0] == box_command
    
    def test_is_end_command_string_detection(self):
        """Test detection of end command strings."""
        element = _CommandElement("test")
        
        # End commands
        assert element._is_end_command_string("end bold")
        assert element._is_end_command_string("end bold, red")
        assert element._is_end_command_string("reset")
        assert element._is_end_command_string("END BOLD")  # Case insensitive
        
        # Not end commands
        assert not element._is_end_command_string("bold")
        assert not element._is_end_command_string("bold, red")
        assert not element._is_end_command_string("box rounded")
    
    def test_is_box_command_string_detection(self):
        """Test detection of box command strings."""
        element = _CommandElement("test")
        
        # Box commands
        assert element._is_box_command_string("box rounded")
        assert element._is_box_command_string("box double, title Test")
        assert element._is_box_command_string("BOX ROUNDED")  # Case insensitive
        assert element._is_box_command_string("end box")
        
        # Not box commands
        assert not element._is_box_command_string("bold")
        assert not element._is_box_command_string("red, blue")
        assert not element._is_box_command_string("reset")
    
    def test_process_with_mock_processor(self):
        """Test processing commands with mock processor."""
        element = _CommandElement("test")
        
        result_state = element.process(self.format_state)
        
        # Mock processor should have set text_color
        assert result_state.text_color == "test_processed"
    
    def test_process_multiple_commands(self):
        """Test processing multiple commands in sequence."""
        # Register additional mock processor
        class SecondMockProcessor(_CommandProcessor):
            @classmethod
            def can_process(cls, command: str) -> bool:
                return command.lower() == 'second'
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                format_state.bold = True
                return format_state
        
        _CommandRegistry.register(SecondMockProcessor, priority=60)
        
        element = _CommandElement("test, second")
        result_state = element.process(self.format_state)
        
        # Both processors should have been called
        assert result_state.text_color == "test_processed"
        assert result_state.bold is True
    
    def test_process_unknown_command_error(self):
        """Test that unknown commands raise UnknownCommandError."""
        element = _CommandElement("unknown_command")
        
        with pytest.raises(UnknownCommandError):
            element.process(self.format_state)
    
    def test_process_mixed_known_unknown_commands(self):
        """Test processing mixed known and unknown commands."""
        element = _CommandElement("test, unknown_command")
        
        # Should fail on the unknown command
        with pytest.raises(UnknownCommandError):
            element.process(self.format_state)
    
    def test_get_command_summary(self):
        """Test getting command summary."""
        # Single command
        element = _CommandElement("test")
        summary = element.get_command_summary()
        assert "Command: test" in summary
        
        # Multiple commands
        element = _CommandElement("test, mock")
        summary = element.get_command_summary()
        assert "Commands: test, mock" in summary
        
        # No commands
        element = _CommandElement("")
        summary = element.get_command_summary()
        assert "No commands" in summary
    
    def test_get_command_info(self):
        """Test getting detailed command information."""
        element = _CommandElement("test, mock")
        info = element.get_command_info()
        
        assert info['command_string'] == "test, mock"
        assert info['parsed_commands'] == ["test", "mock"]
        assert info['total_commands'] == 2
        assert 'command_details' in info
        assert len(info['command_details']) == 2
    
    def test_validate_commands(self):
        """Test command validation without processing."""
        # Valid commands
        element = _CommandElement("test, mock")
        results = element.validate_commands()
        
        assert results['all_valid'] is True
        assert len(results['valid_commands']) == 2
        assert len(results['invalid_commands']) == 0
        
        # Invalid commands
        element = _CommandElement("test, unknown")
        results = element.validate_commands()
        
        assert results['all_valid'] is False
        assert len(results['valid_commands']) == 1
        assert len(results['invalid_commands']) == 1
    
    def test_create_command_element_factory(self):
        """Test the factory function for creating command elements."""
        # Valid creation
        element = _create_command_element("test, mock")
        assert isinstance(element, _CommandElement)
        assert element.commands == ["test", "mock"]
        
        # Empty command string should raise ValueError
        with pytest.raises(ValueError):
            _create_command_element("")
        
        # Whitespace-only command string should raise ValueError
        with pytest.raises(ValueError):
            _create_command_element("   ")
    
    def test_get_available_command_processors(self):
        """Test getting information about available command processors."""
        info = _get_available_command_processors()
        
        assert 'total_processors' in info
        assert 'processors' in info
        assert info['total_processors'] >= 1  # At least our mock processor
        
        # Should contain our mock processor
        processor_names = [p['name'] for p in info['processors']]
        assert 'MockCommandProcessor' in processor_names
    
    def test_command_element_repr(self):
        """Test string representation of command element."""
        element = _CommandElement("test, mock")
        repr_str = repr(element)
        
        assert "_CommandElement" in repr_str
        assert "test" in repr_str
        assert "mock" in repr_str
    
    def test_edge_case_whitespace_handling(self):
        """Test edge cases with whitespace handling."""
        # Leading/trailing whitespace
        element = _CommandElement("  test  ,  mock  ")
        assert element.commands == ["test", "mock"]
        
        # Multiple spaces between commands
        element = _CommandElement("test   ,   mock")
        assert element.commands == ["test", "mock"]
        
        # Empty commands in list (should be filtered out)
        element = _CommandElement("test, , mock")
        assert element.commands == ["test", "mock"]
    
    def test_edge_case_special_characters(self):
        """Test handling of special characters in commands."""
        # Commands with numbers
        element = _CommandElement("12hr, tz pst")
        assert element.commands == ["12hr", "tz pst"]
        
        # Commands with underscores
        element = _CommandElement("text_color, bg_color")
        assert element.commands == ["text_color", "bg_color"]
        
        # Commands with dashes (common in CSS-like syntax)
        element = _CommandElement("font-weight, text-align")
        assert element.commands == ["font-weight", "text-align"]
    
    def test_complex_box_command_parsing(self):
        """Test complex box command parsing with commas in titles."""
        complex_box_commands = [
            "box rounded, title Error: Connection failed, please try again",
            "box double, title Status: OK, color green, width 50",
            "box heavy, title Multi, Word, Title, With, Commas",
        ]
        
        for box_command in complex_box_commands:
            element = _CommandElement(box_command)
            # Should be treated as single command despite internal commas
            assert len(element.commands) == 1
            assert element.commands[0] == box_command
    
    def test_command_processing_order(self):
        """Test that commands are processed in the correct order."""
        # Register processors that track order
        class OrderTrackingProcessor(_CommandProcessor):
            order_log = []
            
            @classmethod
            def can_process(cls, command: str) -> bool:
                return command.startswith('order')
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                cls.order_log.append(command)
                return format_state
        
        _CommandRegistry.register(OrderTrackingProcessor, priority=70)
        
        # Clear the log
        OrderTrackingProcessor.order_log = []
        
        element = _CommandElement("order1, order2, order3")
        element.process(self.format_state)
        
        # Commands should be processed in order
        assert OrderTrackingProcessor.order_log == ["order1", "order2", "order3"]


class TestCommandElementVisualDemonstration:
    """Visual demonstration tests for command element processor."""
    
    def setup_method(self):
        """Set up test fixtures with visual mock processors."""
        _CommandRegistry.clear_registry()
        
        # Register visual mock processors
        class VisualFormattingProcessor(_CommandProcessor):
            @classmethod
            def can_process(cls, command: str) -> bool:
                return command.lower() in ['bold', 'italic', 'underline', 'red', 'green', 'blue']
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                cmd = command.lower()
                if cmd == 'bold':
                    format_state.bold = True
                elif cmd == 'italic':
                    format_state.italic = True
                elif cmd == 'underline':
                    format_state.underline = True
                elif cmd in ['red', 'green', 'blue']:
                    format_state.text_color = cmd
                return format_state
        
        class VisualEndProcessor(_CommandProcessor):
            @classmethod
            def can_process(cls, command: str) -> bool:
                return command.lower().startswith('end ')
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                cmd = command.lower().replace('end ', '')
                if cmd == 'bold':
                    format_state.bold = False
                elif cmd == 'italic':
                    format_state.italic = False
                elif cmd == 'underline':
                    format_state.underline = False
                elif cmd in ['red', 'green', 'blue']:
                    format_state.text_color = None
                return format_state
        
        _CommandRegistry.register(VisualFormattingProcessor, priority=50)
        _CommandRegistry.register(VisualEndProcessor, priority=60)
    
    def teardown_method(self):
        """Clean up after tests."""
        _CommandRegistry.clear_registry()
    
    def test_visual_basic_command_demonstration(self):
        """Visual demonstration of basic command processing."""
        print("\n" + "="*60)
        print("COMMAND ELEMENT - BASIC COMMAND DEMONSTRATION")
        print("="*60)
        
        test_commands = [
            "bold",
            "italic",
            "underline",
            "red",
            "green",
            "blue",
            "bold, red",
            "italic, green",
            "bold, italic, underline",
            "bold, red, underline",
        ]
        
        for command_string in test_commands:
            print(f"\nCommand: '{command_string}'")
            
            element = _CommandElement(command_string)
            format_state = _create_format_state()
            
            print(f"  Parsed commands: {element.commands}")
            
            try:
                result_state = element.process(format_state)
                
                # Show the format state changes
                changes = []
                if result_state.bold:
                    changes.append("bold=True")
                if result_state.italic:
                    changes.append("italic=True")
                if result_state.underline:
                    changes.append("underline=True")
                if result_state.text_color:
                    changes.append(f"color={result_state.text_color}")
                
                print(f"  Format changes: {', '.join(changes) if changes else 'None'}")
                
                # Demonstrate visual output
                from suitkaise.fdl._int.elements.text_element import _TextElement
                text_element = _TextElement("Sample text")
                text_result = text_element.process(result_state)
                outputs = text_result.get_final_outputs()
                
                print(f"  Visual result: ", end="")
                print(outputs['terminal'], end="")
                print("\033[0m")
                
            except Exception as e:
                print(f"  Error: {e}")
    
    def test_visual_command_parsing_demonstration(self):
        """Visual demonstration of command parsing."""
        print("\n" + "="*60)
        print("COMMAND ELEMENT - PARSING DEMONSTRATION")
        print("="*60)
        
        parsing_examples = [
            ("Simple command", "bold"),
            ("Multiple commands", "bold, red, italic"),
            ("Commands with spaces", "  bold  ,  red  ,  italic  "),
            ("End commands", "end bold, red"),
            ("Reset command", "reset"),
            ("Box command", "box rounded, title Important Message"),
            ("Complex box", "box double, title Error: Failed, color red"),
            ("Empty command", ""),
            ("Single with spaces", "   bold   "),
        ]
        
        for description, command_string in parsing_examples:
            print(f"\n{description}:")
            print(f"  Input: '{command_string}'")
            
            if command_string.strip():
                element = _CommandElement(command_string)
                print(f"  Parsed: {element.commands}")
                print(f"  Count: {len(element.commands)}")
                
                # Show command summary
                summary = element.get_command_summary()
                print(f"  Summary: {summary}")
            else:
                print("  Parsed: []")
                print("  Count: 0")
    
    def test_visual_end_command_demonstration(self):
        """Visual demonstration of end command processing."""
        print("\n" + "="*60)
        print("COMMAND ELEMENT - END COMMAND DEMONSTRATION")
        print("="*60)
        
        print("\nDemonstrating format state changes with end commands:")
        
        # Start with formatting
        format_state = _create_format_state()
        
        print("\n1. Apply formatting:")
        start_element = _CommandElement("bold, red, italic")
        format_state = start_element.process(format_state)
        
        print(f"   Commands: {start_element.commands}")
        print(f"   State: bold={format_state.bold}, italic={format_state.italic}, color={format_state.text_color}")
        
        # Show visual result
        from suitkaise.fdl._int.elements.text_element import _TextElement
        text_element = _TextElement("Formatted text")
        text_result = text_element.process(format_state.copy())
        outputs = text_result.get_final_outputs()
        print(f"   Visual: ", end="")
        print(outputs['terminal'], end="")
        print("\033[0m")
        
        print("\n2. Remove some formatting:")
        end_element = _CommandElement("end bold, italic")
        format_state = end_element.process(format_state)
        
        print(f"   Commands: {end_element.commands}")
        print(f"   State: bold={format_state.bold}, italic={format_state.italic}, color={format_state.text_color}")
        
        # Show visual result
        text_result = text_element.process(format_state.copy())
        outputs = text_result.get_final_outputs()
        print(f"   Visual: ", end="")
        print(outputs['terminal'], end="")
        print("\033[0m")
    
    def test_visual_command_validation_demonstration(self):
        """Visual demonstration of command validation."""
        print("\n" + "="*60)
        print("COMMAND ELEMENT - VALIDATION DEMONSTRATION")
        print("="*60)
        
        validation_examples = [
            ("Valid commands", "bold, red, italic"),
            ("Mixed valid/invalid", "bold, unknown, red"),
            ("All invalid", "unknown1, unknown2"),
            ("Empty commands", ""),
            ("Box command", "box rounded, title Test"),
        ]
        
        for description, command_string in validation_examples:
            print(f"\n{description}: '{command_string}'")
            
            if command_string.strip():
                element = _CommandElement(command_string)
                validation_result = element.validate_commands()
                
                print(f"  All valid: {'✅' if validation_result['all_valid'] else '❌'}")
                print(f"  Valid commands: {len(validation_result['valid_commands'])}")
                print(f"  Invalid commands: {len(validation_result['invalid_commands'])}")
                
                if validation_result['valid_commands']:
                    valid_names = [cmd['command'] for cmd in validation_result['valid_commands']]
                    print(f"  Valid: {valid_names}")
                
                if validation_result['invalid_commands']:
                    invalid_names = [cmd['command'] for cmd in validation_result['invalid_commands']]
                    print(f"  Invalid: {invalid_names}")
            else:
                print("  Empty command string")
    
    def test_visual_box_command_demonstration(self):
        """Visual demonstration of box command parsing."""
        print("\n" + "="*60)
        print("COMMAND ELEMENT - BOX COMMAND DEMONSTRATION")
        print("="*60)
        
        box_examples = [
            "box rounded",
            "box double, title Simple",
            "box heavy, title Complex Message",
            "box rounded, title Error: Connection failed, please retry",
            "box double, title Status: OK, All systems operational",
            "end box",
        ]
        
        for box_command in box_examples:
            print(f"\nBox command: '{box_command}'")
            
            element = _CommandElement(box_command)
            print(f"  Is box command: {'✅' if element._is_box_command_string(box_command) else '❌'}")
            print(f"  Parsed as: {element.commands}")
            print(f"  Command count: {len(element.commands)}")
            
            # Show that it's treated as single command despite commas
            if ',' in box_command and not box_command.startswith('end'):
                comma_count = box_command.count(',')
                print(f"  Contains {comma_count} comma(s) but treated as 1 command ✅")
    
    def test_visual_error_handling_demonstration(self):
        """Visual demonstration of error handling."""
        print("\n" + "="*60)
        print("COMMAND ELEMENT - ERROR HANDLING DEMONSTRATION")
        print("="*60)
        
        error_examples = [
            ("Unknown single command", "unknown_command"),
            ("Mixed known/unknown", "bold, unknown_command, red"),
            ("All unknown commands", "unknown1, unknown2, unknown3"),
            ("Typo in command", "blod, red"),  # 'bold' misspelled
        ]
        
        for description, command_string in error_examples:
            print(f"\n{description}: '{command_string}'")
            
            element = _CommandElement(command_string)
            format_state = _create_format_state()
            
            print(f"  Parsed commands: {element.commands}")
            
            try:
                result_state = element.process(format_state)
                print("  Result: ✅ Processed successfully")
            except UnknownCommandError as e:
                print(f"  Result: ❌ UnknownCommandError: {e}")
            except Exception as e:
                print(f"  Result: ❌ Other error: {e}")
    
    def test_visual_registry_information_demonstration(self):
        """Visual demonstration of registry information."""
        print("\n" + "="*60)
        print("COMMAND ELEMENT - REGISTRY INFORMATION DEMONSTRATION")
        print("="*60)
        
        # Show available processors
        processor_info = _get_available_command_processors()
        
        print(f"\nTotal registered processors: {processor_info['total_processors']}")
        print("\nProcessor details:")
        
        for processor in processor_info['processors']:
            print(f"  • {processor['name']} (priority: {processor['priority']})")
        
        # Show command info for specific commands
        print("\nCommand routing information:")
        test_commands = ["bold", "red", "unknown", "italic"]
        
        for command in test_commands:
            info = _CommandRegistry.get_command_info(command)
            processor_name = info['processor'] or "None"
            can_process = "✅" if info['can_process'] else "❌"
            
            print(f"  '{command}' -> {processor_name} {can_process}")


if __name__ == "__main__":
    # Run visual demonstrations
    demo = TestCommandElementVisualDemonstration()
    demo.test_visual_basic_command_demonstration()
    demo.test_visual_command_parsing_demonstration()
    demo.test_visual_end_command_demonstration()
    demo.test_visual_command_validation_demonstration()
    demo.test_visual_box_command_demonstration()
    demo.test_visual_error_handling_demonstration()
    demo.test_visual_registry_information_demonstration()
    
    print("\n" + "="*60)
    print("✅ COMMAND ELEMENT PROCESSOR TESTS COMPLETE")
    print("="*60)