"""
Entry point for running amplifier-app-transcribe as a module.

Usage:
    python -m amplifier_app_transcribe transcribe <sources>
"""

from .cli import main

if __name__ == "__main__":
    main()
