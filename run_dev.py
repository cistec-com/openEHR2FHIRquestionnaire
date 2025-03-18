#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Development runner for the openEHR to FHIR Questionnaire Converter.
This script runs the app with debug mode enabled and provides a local URL.
"""

import subprocess
import sys
import os

if __name__ == "__main__":
    # Ensure the current directory is in the Python path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    # Run the app with debug mode enabled using uv
    subprocess.run([
        "uv", "run",
        "app.py",
        "--debug",
        "--port", "7860"
    ])
