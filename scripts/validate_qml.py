#!/usr/bin/env python3
"""
QML signal validation script for Syllablaze.
Checks for common QML signal misconfigurations that cause runtime errors.
"""

import re
import sys
from pathlib import Path

# QML control -> valid signals mapping
CONTROL_SIGNALS = {
    "Slider": ["onMoved", "onValueChanged", "onPressedChanged", "onHoveredChanged"],
    "SpinBox": ["onValueModified", "onValueChanged", "onTextChanged"],
    "CheckBox": ["onCheckedChanged", "onToggled"],
    "Switch": ["onCheckedChanged", "onToggled"],
    "ComboBox": ["onActivated", "onCurrentIndexChanged", "onCurrentTextChanged"],
    "Button": ["onClicked", "onPressed", "onReleased"],
}

# Signals that are commonly misused
PROBLEMATIC_PATTERNS = [
    # Slider doesn't have onValueModified (use onMoved or onValueChanged instead)
    (r"QQC2\.Slider\s*\{[^{}]*\{[^{}]*\}[^{}]*\}|QQC2\.Slider\s*\{[^}]*onValueModified", "Slider does not have 'onValueModified', use 'onMoved' or 'onValueChanged'"),
]


def validate_qml_file(filepath: Path) -> list:
    """Validate a QML file and return list of errors."""
    errors = []
    content = filepath.read_text()

    for pattern, message in PROBLEMATIC_PATTERNS:
        matches = re.finditer(pattern, content, re.DOTALL)
        for match in matches:
            # Get line number
            line_num = content[:match.start()].count('\n') + 1
            errors.append(f"  Line {line_num}: {message}")

    return errors


def main():
    qml_dir = Path(__file__).parent / "blaze" / "qml"

    if not qml_dir.exists():
        print(f"Error: QML directory not found: {qml_dir}")
        sys.exit(1)

    all_errors = []

    for qml_file in qml_dir.rglob("*.qml"):
        errors = validate_qml_file(qml_file)
        if errors:
            all_errors.append((qml_file, errors))

    if all_errors:
        print("❌ QML validation failed:")
        for filepath, errors in all_errors:
            print(f"\n{filepath}:")
            for error in errors:
                print(error)
        sys.exit(1)
    else:
        print("✅ All QML files validated successfully")
        sys.exit(0)


if __name__ == "__main__":
    main()
