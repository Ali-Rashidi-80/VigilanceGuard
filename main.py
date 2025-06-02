import sys
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from src.app import DrowsinessApp

# تنظیم لاگ‌گذاری
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        window = DrowsinessApp()
        font = QFont("BNazanin" if window.language == "fa" else "Arial", 14)
        app.setFont(font)
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        logging.error(f"Error starting application: {e}")
        sys.exit(1)