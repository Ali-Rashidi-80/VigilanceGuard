# app.py
import logging
from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSizePolicy, QMessageBox
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QImage, QPixmap
from src.settings import SettingsDialog
from src.frame_processor import FrameProcessor
from src.alert_handler import AlertHandler
from src.utils import get_texts
from src.constants import FRAME_WIDTH, FRAME_HEIGHT, EYE_AR_THRESH, EYE_AR_CONSEC_FRAMES, HEAD_ROLL_THRESH, HEAD_PITCH_THRESH, ALERT_MIN_DURATION, ALERT_COOLDOWN

class DrowsinessApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.language = "fa"
        self.theme = "dark"
        self.texts = get_texts()
        # دیباگ: بررسی کلیدهای موجود
        logging.debug(f"Language: {self.language}, Available text keys: {list(self.texts[self.language].keys())}")
        self.setWindowTitle(self.texts[self.language]["window_title"])
        self.setMinimumSize(1200, 600)

        # Detection thresholds
        self.EYE_AR_THRESH = EYE_AR_THRESH
        self.EYE_AR_CONSEC_FRAMES = EYE_AR_CONSEC_FRAMES
        self.HEAD_ROLL_THRESH = HEAD_ROLL_THRESH
        self.HEAD_PITCH_THRESH = HEAD_PITCH_THRESH
        self.ALERT_MIN_DURATION = ALERT_MIN_DURATION
        self.ALERT_COOLDOWN = ALERT_COOLDOWN

        # Frame processing attributes
        self.left_eye_points = []
        self.right_eye_points = []
        self.current_roll = 0.0
        self.current_pitch = 0.0
        self.direction_text = "---"
        self.roll_dir = ""
        self.pitch_dir = ""
        self.alert_severity = "none"
        self.brightness = 0.0
        self.animation_frame = 0
        self.pending_alert_message = None

        # Initialize modules
        self.frame_processor = FrameProcessor(self)
        self.alert_handler = AlertHandler(self)

        # Setup UI
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(15)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignRight if self.language == "fa" else Qt.AlignmentFlag.AlignLeft)

        # Video container
        self.video_container = QWidget()
        self.video_container.setObjectName("videoFrame")
        self.video_layout = QVBoxLayout(self.video_container)
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setScaledContents(True)
        self.video_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.video_layout.addWidget(self.video_label)
        self.main_layout.addWidget(self.video_container, stretch=3)

        # Info container
        self.info_container = QWidget()
        self.info_layout = QVBoxLayout(self.info_container)
        self.info_layout.setAlignment(Qt.AlignmentFlag.AlignRight if self.language == "fa" else Qt.AlignmentFlag.AlignLeft)
        self.info_layout.setSpacing(20)
        self.info_layout.setContentsMargins(15, 15, 15, 15)

        self.settings_btn = QPushButton(self.texts[self.language]["settings_btn"])
        self.settings_btn.setFont(QFont("BNazanin" if self.language == "fa" else "Arial", 14))
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #3182CE;
                color: #FFFFFF;
                font-size: 18px;
                font-weight: bold;
                padding: 12px;
                border-radius: 10px;
                min-height: 50px;
            }
            QPushButton:hover {
                background-color: #2B6CB0;
            }
        """)
        self.settings_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft if self.language == "fa" else Qt.LayoutDirection.LeftToRight)
        self.settings_btn.clicked.connect(self.open_settings)
        self.info_layout.addWidget(self.settings_btn)

        # Main tab
        self.main_tab = QWidget()
        self.main_tab_layout = QVBoxLayout(self.main_tab)
        self.main_tab_layout.setAlignment(Qt.AlignmentFlag.AlignRight if self.language == "fa" else Qt.AlignmentFlag.AlignLeft)
        self.main_tab_layout.setSpacing(20)
        self.main_tab_layout.setContentsMargins(15, 15, 15, 15)

        self.alert_label = QLabel(self.texts[self.language]["alert_count"].format(self.alert_handler.alert_count))
        self.ear_label = QLabel(self.texts[self.language]["ear_ratio"].format(0.00))
        self.tilt_label = QLabel(self.texts[self.language]["tilt_info"].format(0.00, 0.00))
        self.direction_label = QLabel(self.texts[self.language]["direction"].format("---"))
        try:
            self.blink_rate_label = QLabel(self.texts[self.language]["blink_rate"].format(0))
        except KeyError:
            logging.error(f"Key 'blink_rate' not found in texts for language {self.language}")
            self.blink_rate_label = QLabel("نرخ پلک زدن: 0" if self.language == "fa" else "Blink Rate: 0")

        for label in [self.alert_label, self.ear_label, self.tilt_label, self.direction_label, self.blink_rate_label]:
            label.setObjectName("infoLabel")
            label.setFont(QFont("BNazanin" if self.language == "fa" else "Arial", 14))
            label.setAlignment(Qt.AlignmentFlag.AlignRight if self.language == "fa" else Qt.AlignmentFlag.AlignLeft)
            label.setLayoutDirection(Qt.LayoutDirection.RightToLeft if self.language == "fa" else Qt.LayoutDirection.LeftToRight)
            self.main_tab_layout.addWidget(label)

        self.alert_label.setStyleSheet("""
            background-color: #FF6B6B;
            color: #FFFFFF;
            font-size: 18px;
            font-weight: bold;
            padding: 15px;
            border-radius: 12px;
            border: 1px solid #E53E3E;
            min-height: 60px;
            min-width: 300px;
            text-align: center;
        """)
        self.ear_label.setStyleSheet("""
            background-color: #4FD1C5;
            color: #1A202C;
            font-size: 16px;
            font-weight: bold;
            padding: 15px;
            border-radius: 12px;
            border: 1px solid #38B2AC;
            min-height: 50px;
            min-width: 300px;
            text-align: center;
        """)
        self.tilt_label.setStyleSheet("""
            background-color: #F6AD55;
            color: #1A202C;
            font-size: 16px;
            font-weight: bold;
            padding: 15px;
            border-radius: 12px;
            border: 1px solid #DD6B20;
            min-height: 50px;
            min-width: 300px;
            text-align: center;
        """)
        self.direction_label.setStyleSheet("""
            background-color: #63B3ED;
            color: #1A202C;
            font-size: 16px;
            font-weight: bold;
            padding: 15px;
            border-radius: 12px;
            border: 1px solid #3182CE;
            min-height: 50px;
            min-width: 300px;
            text-align: center;
        """)
        self.blink_rate_label.setStyleSheet("""
            background-color: #A0AEC0;
            color: #1A202C;
            font-size: 16px;
            font-weight: bold;
            padding: 15px;
            border-radius: 12px;
            border: 1px solid #718096;
            min-height: 50px;
            min-width: 300px;
            text-align: center;
        """)

        self.info_layout.addWidget(self.main_tab)
        self.main_layout.addWidget(self.info_container, stretch=1)

        self.update_theme()

        # Start frame processing timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(15)

    def show_warning(self, message):
        QMessageBox.warning(self, "Warning" if self.language == "en" else "هشدار", message)

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def update_theme(self):
        try:
            stylesheet = """
                QMainWindow {
                    background-color: %s;
                }
                QLabel {
                    font-family: 'BNazanin', 'Arial';
                    font-size: 16px;
                    color: %s;
                    font-weight: bold;
                }
                QLabel#infoLabel {
                    color: %s;
                }
                QSlider::groove:horizontal {
                    height: 12px;
                    background: %s;
                    border-radius: 6px;
                }
                QSlider::handle:horizontal {
                    background: #63B3ED;
                    width: 24px;
                    height: 24px;
                    margin: -6px 0;
                    border-radius: 12px;
                    border: 2px solid #3182CE;
                }
                QSlider::sub-page:horizontal {
                    background: #3182CE;
                    border-radius: 6px;
                }
                QFrame {
                    background-color: %s;
                    border-radius: 12px;
                    border: %s;
                }
                QWidget#videoFrame {
                    background-color: #000000;
                    border-radius: 12px;
                    border: 2px solid %s;
                }
                QComboBox {
                    background-color: %s;
                    color: %s;
                    border: %s;
                    border-radius: 6px;
                    padding: 8px;
                    font-size: 14px;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 20px;
                }
                QComboBox::down-arrow {
                    width: 12px;
                    height: 12px;
                }
                QComboBox QAbstractItemView {
                    background-color: %s;
                    color: %s;
                    selection-background-color: #63B3ED;
                    selection-color: #FFFFFF;
                    border: %s;
                }
                QCheckBox {
                    color: %s;
                    font-size: 16px;
                    font-weight: bold;
                }
                QDialog {
                    background-color: %s;
                }
                QScrollArea {
                    border: none;
                }
            """
            if self.theme == "dark":
                self.setStyleSheet(stylesheet % (
                    "#1A202C", "#E2E8F0", "#FFFFFF", "#4A5568", "#2D3748", "none",
                    "#4A5568", "#4A5568", "#E2E8F0", "none", "#4A5568", "#E2E8F0",
                    "none", "#E2E8F0", "#1A202C"
                ))
            else:
                self.setStyleSheet(stylesheet % (
                    "#F7FAFC", "#1A202C", "#1A202C", "#CBD5E0", "#FFFFFF", "1px solid #CBD5E0",
                    "#CBD5E0", "#FFFFFF", "#1A202C", "1px solid #CBD5E0", "#FFFFFF", "#1A202C",
                    "1px solid #CBD5E0", "#FFFFFF", "#F7FAFC"
                ))

            labels = [self.alert_label, self.ear_label, self.tilt_label, self.direction_label, self.blink_rate_label]
            for label in labels:
                label.setFont(QFont("BNazanin" if self.language == "fa" else "Arial", 14))
                label.setLayoutDirection(Qt.LayoutDirection.RightToLeft if self.language == "fa" else Qt.LayoutDirection.LeftToRight)
                label.setAlignment(Qt.AlignmentFlag.AlignRight if self.language == "fa" else Qt.AlignmentFlag.AlignLeft)
            self.settings_btn.setFont(QFont("BNazanin" if self.language == "fa" else "Arial", 14))
            self.settings_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft if self.language == "fa" else Qt.LayoutDirection.LeftToRight)
        except Exception as e:
            logging.error(f"Error updating theme: {e}")

    def update_ui_layout(self):
        try:
            self.setWindowTitle(self.texts[self.language]["window_title"])
            self.settings_btn.setText(self.texts[self.language]["settings_btn"])

            alignment = Qt.AlignmentFlag.AlignLeft if self.language == "en" else Qt.AlignmentFlag.AlignRight
            direction = Qt.LayoutDirection.LeftToRight if self.language == "en" else Qt.LayoutDirection.RightToLeft

            self.main_layout.setAlignment(alignment)
            self.main_tab_layout.setAlignment(alignment)
            self.info_layout.setAlignment(alignment)
            self.setLayoutDirection(direction)
            self.central_widget.setLayoutDirection(direction)
            self.video_container.setLayoutDirection(direction)
            self.info_container.setLayoutDirection(direction)
            self.main_tab.setLayoutDirection(direction)

            self.alert_label.setText(self.texts[self.language]["alert_count"].format(self.alert_handler.alert_count))
            self.ear_label.setText(self.texts[self.language]["ear_ratio"].format(0.00))
            self.tilt_label.setText(self.texts[self.language]["tilt_info"].format(0.00, 0.00))
            self.direction_label.setText(self.texts[self.language]["direction"].format("---"))
            self.blink_rate_label.setText(self.texts[self.language]["blink_rate"].format(self.alert_handler.calculate_blink_rate()))

            labels = [self.alert_label, self.ear_label, self.tilt_label, self.direction_label, self.blink_rate_label]
            for label in labels:
                label.setFont(QFont("BNazanin" if self.language == "fa" else "Arial", 14))
                label.setAlignment(alignment)
                label.setLayoutDirection(direction)

            self.settings_btn.setFont(QFont("BNazanin" if self.language == "fa" else "Arial", 14))
            self.settings_btn.setLayoutDirection(direction)

            for i in range(self.main_tab_layout.count()):
                item = self.main_tab_layout.itemAt(i)
                if item.widget():
                    item.widget().setAlignment(alignment)
                    item.widget().setLayoutDirection(direction)
        except Exception as e:
            logging.error(f"Error updating UI layout: {e}")

    def update_frame(self):
        try:
            frame_data = self.frame_processor.process_frame()
            if frame_data is None:
                return

            frame, smoothed_ear, current_roll, current_pitch, direction_text, alert_flag, left_eye_points, right_eye_points, roll_dir, pitch_dir, alert_severity, brightness = frame_data
            self.left_eye_points = left_eye_points
            self.right_eye_points = right_eye_points
            self.current_roll = current_roll
            self.current_pitch = current_pitch
            self.direction_text = direction_text
            self.roll_dir = roll_dir
            self.pitch_dir = pitch_dir
            self.alert_severity = alert_severity
            self.brightness = brightness

            self.ear_label.setText(self.texts[self.language]["ear_ratio"].format(smoothed_ear))
            self.tilt_label.setText(self.texts[self.language]["tilt_info"].format(current_roll, current_pitch))
            self.direction_label.setText(self.texts[self.language]["direction"].format(direction_text))
            self.blink_rate_label.setText(self.texts[self.language]["blink_rate"].format(self.alert_handler.calculate_blink_rate()))

            self.alert_handler.handle_alerts(frame, smoothed_ear, current_roll, current_pitch, direction_text, alert_flag, alert_severity, brightness)
            self.alert_label.setText(self.texts[self.language]["alert_count"].format(self.alert_handler.alert_count))

            final_frame = self.frame_processor.finalize_frame(frame, alert_flag, alert_severity)
            height, width, channel = final_frame.shape
            bytes_per_line = 3 * width
            q_img = QImage(final_frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(q_img).scaled(self.video_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.video_label.setPixmap(pixmap)
        except Exception as e:
            logging.error(f"Error updating frame: {e}")

    def closeEvent(self, event):
        logging.info("Closing application...")
        try:
            self.frame_processor.cleanup()
            self.alert_handler.cleanup()
            event.accept()
        except Exception as e:
            logging.error(f"Error during close event: {e}")
            event.accept()