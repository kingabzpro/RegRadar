"""
RegRadar - AI Regulatory Compliance Assistant

This application monitors and analyzes regulatory updates, providing
compliance guidance for various industries and regions.
"""

from agents.ui_handler import UIHandler

def main():
    """Initialize and launch the RegRadar application"""
    ui_handler = UIHandler()
    demo = ui_handler.create_ui()
    demo.launch()

if __name__ == "__main__":
    main()

