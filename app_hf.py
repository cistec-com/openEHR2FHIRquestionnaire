#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This is a special version of app.py for Hugging Face Spaces deployment
# It simplifies the launch configuration to work properly on Hugging Face

import os
from app import create_gradio_interface, ensure_sample_dir

if __name__ == "__main__":
    # Create sample directory and file when app starts
    ensure_sample_dir()

    # Create and launch the Gradio interface
    demo = create_gradio_interface()

    # Launch with Hugging Face Spaces compatible settings
    demo.launch(
        server_name="0.0.0.0",  # Listen on all network interfaces
        share=False,
        server_port=7860  # Default port used by Hugging Face Spaces
    )
