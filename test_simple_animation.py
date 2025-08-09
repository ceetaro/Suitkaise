#!/usr/bin/env python3

from suitkaise.fdl._int.classes.progress_bar import ProgressBar
import time

def test_simple_animation():
    print("Testing simple animation...")
    
    # Create a simple progress bar
    bar = ProgressBar(100, "  Test:", ratio=True, percent=True)
    
    # Test basic animation
    print("Starting animation...")
    bar.animate_smooth(50, "Halfway", duration=1.0)
    bar.animate_smooth(50, "Complete!", duration=1.0)
    
    print("Animation test complete!")

if __name__ == "__main__":
    test_simple_animation() 