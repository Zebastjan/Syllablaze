#!/usr/bin/env python3
"""
Test script for SVG element loading and bounds retrieval.
Verifies that the updated SvgRendererBridge can find all four elements.
"""

import sys
import os

# Add blaze to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from blaze.svg_renderer_bridge import SvgRendererBridge


def test_svg_elements():
    """Test that all SVG elements are found."""
    print("=" * 60)
    print("Testing SVG Element Loading")
    print("=" * 60)
    print()

    # Create QApplication (required for Qt)
    app = QApplication(sys.argv)

    # Create bridge
    bridge = SvgRendererBridge()

    print(f"SVG Path: {bridge.svgPath}")
    print(f"ViewBox: {bridge.viewBox}")
    print()

    # Test each element
    elements = {
        "background": bridge.backgroundBounds,
        "input_levels": bridge.inputLevelBounds,
        "waveform": bridge.waveformBounds,
        "active_area": bridge.activeAreaBounds,
    }

    all_found = True
    for name, bounds in elements.items():
        if bounds.isNull():
            print(f"❌ {name}: NOT FOUND (using fallback)")
            all_found = False
        else:
            print(
                f"✅ {name}: ({bounds.x():.1f}, {bounds.y():.1f}) {bounds.width():.1f}x{bounds.height():.1f}"
            )

    print()

    if all_found:
        print("✅ All elements found successfully!")
        return 0
    else:
        print("⚠️  Some elements not found - check SVG file")
        return 1


if __name__ == "__main__":
    sys.exit(test_svg_elements())
