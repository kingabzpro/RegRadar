"""
RegRadar - AI Regulatory Compliance Assistant

This application monitors and analyzes regulatory updates, providing
compliance guidance for various industries and regions.
"""

from agents.ui_handler import UIHandler


def create_demo():
    ui_handler = UIHandler()  # New user for each session
    return ui_handler.create_ui()


def main():
    """Initialize and launch the RegRadar application"""
    demo = create_demo()
    demo.launch()


if __name__ == "__main__":
    main()
