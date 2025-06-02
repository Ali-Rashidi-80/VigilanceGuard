import os
import json
import logging
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QFrame, QComboBox, QCheckBox, QPushButton, QScrollArea, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from src.utils import get_texts
from src.constants import CONFIG_FILE, TEXTS

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.texts = get_texts()
        self.setWindowTitle(self.texts[parent.language]["window_title_settings"])
        self.setFixedSize(500, 600)
        self.pending_settings = {}

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignRight if parent.language == "fa" else Qt.AlignmentFlag.AlignLeft)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        self.scroll_widget = QFrame()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignRight if parent.language == "fa" else Qt.AlignmentFlag.AlignLeft)
        self.scroll_layout.setSpacing(15)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_area.setWidget(self.scroll_widget)
        main_layout.addWidget(scroll_area)

        self.scale_ear_thresh = QSlider(Qt.Orientation.Horizontal)
        self.scale_ear_thresh.setRange(10, 50)
        self.scale_ear_thresh.setValue(int(parent.EYE_AR_THRESH * 100))
        self.ear_thresh_value = QLabel(str(self.scale_ear_thresh.value()))
        self.add_slider(self.texts[parent.language]["eye_threshold"], self.scale_ear_thresh, self.ear_thresh_value)

        self.scale_consec = QSlider(Qt.Orientation.Horizontal)
        self.scale_consec.setRange(10, 200)
        self.scale_consec.setValue(parent.EYE_AR_CONSEC_FRAMES)
        self.consec_value = QLabel(str(self.scale_consec.value()))
        self.add_slider(self.texts[parent.language]["consec_frames"], self.scale_consec, self.consec_value)

        self.scale_roll_tilt = QSlider(Qt.Orientation.Horizontal)
        self.scale_roll_tilt.setRange(0, 30)
        self.scale_roll_tilt.setValue(parent.HEAD_ROLL_THRESH)
        self.roll_tilt_value = QLabel(str(self.scale_roll_tilt.value()))
        self.add_slider(self.texts[parent.language]["roll_tilt"], self.scale_roll_tilt, self.roll_tilt_value)

        self.scale_pitch_tilt = QSlider(Qt.Orientation.Horizontal)
        self.scale_pitch_tilt.setRange(0, 40)
        self.scale_pitch_tilt.setValue(parent.HEAD_PITCH_THRESH)
        self.pitch_tilt_value = QLabel(str(self.scale_pitch_tilt.value()))
        self.add_slider(self.texts[parent.language]["pitch_tilt"], self.scale_pitch_tilt, self.pitch_tilt_value)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems([self.texts[parent.language]["night_theme"], self.texts[parent.language]["day_theme"]])
        self.theme_combo.setCurrentText(self.texts[parent.language]["night_theme"] if parent.theme == "dark" else self.texts[parent.language]["day_theme"])
        self.theme_combo.currentTextChanged.connect(self.store_pending_theme)
        self.add_setting(self.texts[parent.language]["theme_label"], self.theme_combo)

        self.language_combo = QComboBox()
        self.language_combo.addItems([self.texts[parent.language]["persian"], self.texts[parent.language]["english"]])
        self.language_combo.setCurrentText(self.texts[parent.language]["persian"] if parent.language == "fa" else self.texts[parent.language]["english"])
        self.language_combo.currentTextChanged.connect(self.store_pending_language)
        self.add_setting(self.texts[parent.language]["language_label"], self.language_combo)

        self.sensitivity_combo = QComboBox()
        self.sensitivity_combo.addItems([
            self.texts[parent.language]["sensitivity_high"],
            self.texts[parent.language]["sensitivity_normal"],
            self.texts[parent.language]["sensitivity_low"]
        ])
        self.sensitivity_combo.setCurrentText(self.texts[parent.language]["sensitivity_normal"])
        self.sensitivity_combo.currentTextChanged.connect(self.store_pending_sensitivity)
        self.add_setting(self.texts[parent.language]["sensitivity_label"], self.sensitivity_combo)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(int(parent.alert_handler.alarm_sound.get_volume() * 100) if parent.alert_handler.alarm_sound else 50)
        self.volume_value = QLabel(str(self.volume_slider.value()))
        self.volume_slider.valueChanged.connect(lambda: self.volume_value.setText(str(self.volume_slider.value())))
        self.volume_slider.valueChanged.connect(self.store_pending_volume)
        self.add_setting(self.texts[parent.language]["volume_label"], self.volume_slider, self.volume_value)

        self.sound_alert_check = QCheckBox(self.texts[parent.language]["sound_alert_label"])
        self.sound_alert_check.setChecked(parent.alert_handler.sound_enabled)
        self.sound_alert_check.stateChanged.connect(self.store_pending_sound_alert)
        self.sound_alert_check.setStyleSheet(
            "color: #E2E8F0; font-size: 16px; font-weight: bold;" if parent.theme == "dark" else
            "color: #FFFFFF; font-size: 16px; font-weight: bold;"
        )
        self.sound_alert_check.setFont(QFont("BNazanin" if parent.language == "fa" else "Arial", 14))
        self.sound_alert_check.setLayoutDirection(Qt.LayoutDirection.RightToLeft if parent.language == "fa" else Qt.LayoutDirection.LeftToRight)
        self.scroll_layout.addWidget(self.sound_alert_check)

        self.save_button = QPushButton(self.texts[parent.language]["save_settings"])
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #2ECC71;
                color: #FFFFFF;
                font-size: 16px;
                font-weight: bold;
                padding: 8px;
                border-radius: 8px;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #27AE60;
            }
        """)
        self.save_button.setFont(QFont("BNazanin" if parent.language == "fa" else "Arial", 14))
        self.save_button.setLayoutDirection(Qt.LayoutDirection.RightToLeft if parent.language == "fa" else Qt.LayoutDirection.LeftToRight)
        self.save_button.clicked.connect(self.save_settings)
        main_layout.addWidget(self.save_button)

        self.load_config()

    def store_pending_theme(self, theme_text):
        self.pending_settings["theme"] = "dark" if theme_text == self.texts[self.parent.language]["night_theme"] else "light"

    def store_pending_language(self, lang_text):
        new_language = "fa" if lang_text == self.texts[self.parent.language]["persian"] else "en"
        self.pending_settings["language"] = new_language
        self.update_ui_texts(new_language)
        self.update_layout_direction(new_language)

    def store_pending_sensitivity(self, sensitivity_text):
        if sensitivity_text == self.texts[self.parent.language]["sensitivity_high"]:
            self.pending_settings["sensitivity_mode"] = "high"
        elif sensitivity_text == self.texts[self.parent.language]["sensitivity_normal"]:
            self.pending_settings["sensitivity_mode"] = "normal"
        else:
            self.pending_settings["sensitivity_mode"] = "low"

    def store_pending_volume(self):
        self.pending_settings["volume"] = self.volume_slider.value()

    def store_pending_sound_alert(self, state):
        self.pending_settings["sound_alert"] = bool(state)

    def update_ui_texts(self, language):
        self.setWindowTitle(self.texts[language]["window_title_settings"])
        self.save_button.setText(self.texts[language]["save_settings"])
        for i in range(self.scroll_layout.count()):
            item = self.scroll_layout.itemAt(i)
            if item.widget() and isinstance(item.widget(), QFrame):
                layout = item.widget().layout()
                if layout:
                    label = layout.itemAt(0).widget()
                    if label and isinstance(label, QLabel):
                        if "eye_threshold" in label.text().lower():
                            label.setText(self.texts[language]["eye_threshold"])
                        elif "consec_frames" in label.text().lower():
                            label.setText(self.texts[language]["consec_frames"])
                        elif "roll_tilt" in label.text().lower():
                            label.setText(self.texts[language]["roll_tilt"])
                        elif "pitch_tilt" in label.text().lower():
                            label.setText(self.texts[language]["pitch_tilt"])
                        elif "theme_label" in label.text().lower():
                            label.setText(self.texts[language]["theme_label"])
                        elif "language_label" in label.text().lower():
                            label.setText(self.texts[language]["language_label"])
                        elif "volume_label" in label.text().lower():
                            label.setText(self.texts[language]["volume_label"])
                        elif "sensitivity_label" in label.text().lower():
                            label.setText(self.texts[language]["sensitivity_label"])
        self.sound_alert_check.setText(self.texts[language]["sound_alert_label"])
        self.theme_combo.blockSignals(True)
        self.language_combo.blockSignals(True)
        self.sensitivity_combo.blockSignals(True)
        self.theme_combo.clear()
        self.language_combo.clear()
        self.sensitivity_combo.clear()
        self.theme_combo.addItems([self.texts[language]["night_theme"], self.texts[language]["day_theme"]])
        self.language_combo.addItems([self.texts[language]["persian"], self.texts[language]["english"]])
        self.sensitivity_combo.addItems([
            self.texts[language]["sensitivity_high"],
            self.texts[language]["sensitivity_normal"],
            self.texts[language]["sensitivity_low"]
        ])
        self.theme_combo.setCurrentText(self.texts[language]["night_theme"] if self.pending_settings.get("theme", self.parent.theme) == "dark" else self.texts[language]["day_theme"])
        self.language_combo.setCurrentText(self.texts[language]["persian"] if self.pending_settings.get("language", self.parent.language) == "fa" else self.texts[language]["english"])
        self.sensitivity_combo.setCurrentText(self.texts[language]["sensitivity_normal"] if self.pending_settings.get("sensitivity_mode", self.parent.alert_handler.sensitivity_mode) == "normal" else
                                             self.texts[language]["sensitivity_high"] if self.pending_settings.get("sensitivity_mode") == "high" else
                                             self.texts[language]["sensitivity_low"])
        self.theme_combo.blockSignals(False)
        self.language_combo.blockSignals(False)
        self.sensitivity_combo.blockSignals(False)
        self.update_layout_direction(language)

    def update_layout_direction(self, language):
        alignment = Qt.AlignmentFlag.AlignLeft if language == "en" else Qt.AlignmentFlag.AlignRight
        direction = Qt.LayoutDirection.LeftToRight if language == "en" else Qt.LayoutDirection.RightToLeft
        self.layout().setAlignment(alignment)
        self.scroll_layout.setAlignment(alignment)
        self.setLayoutDirection(direction)
        self.scroll_widget.setLayoutDirection(direction)
        self.save_button.setLayoutDirection(direction)
        self.sound_alert_check.setLayoutDirection(direction)
        for i in range(self.scroll_layout.count()):
            item = self.scroll_layout.itemAt(i)
            if item.widget():
                widget = item.widget()
                widget.setLayoutDirection(direction)
                if isinstance(widget, QFrame):
                    layout = widget.layout()
                    if layout:
                        layout.setAlignment(alignment)
                        for j in range(layout.count()):
                            sub_item = layout.itemAt(j)
                            if sub_item.widget():
                                sub_item.widget().setLayoutDirection(direction)
                                if isinstance(sub_item.widget(), QLabel):
                                    sub_item.widget().setAlignment(alignment)

    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.scale_ear_thresh.setValue(config.get("ear_threshold", 18))
                    self.scale_consec.setValue(config.get("consec_frames", 60))
                    self.scale_roll_tilt.setValue(config.get("roll_tilt", 15))
                    self.scale_pitch_tilt.setValue(config.get("pitch_tilt", 32))
                    self.volume_slider.setValue(config.get("volume", 50))
                    self.sound_alert_check.setChecked(config.get("sound_alert", True))
                    self.sensitivity_combo.setCurrentText(
                        self.texts[self.parent.language]["sensitivity_high"] if config.get("sensitivity_mode", "normal") == "high" else
                        self.texts[self.parent.language]["sensitivity_low"] if config.get("sensitivity_mode") == "low" else
                        self.texts[self.parent.language]["sensitivity_normal"]
                    )
                    self.pending_settings.update(config)
                    logging.info("Configuration loaded successfully.")
            else:
                logging.info("No configuration file found, using default settings.")
        except Exception as e:
            logging.error(f"Error loading configuration: {e}")
            QMessageBox.warning(self, "Error" if self.parent.language == "en" else "خطا", f"Error loading settings: {e}")

    def save_settings(self):
        try:
            config = {
                "language": self.pending_settings.get("language", self.parent.language),
                "theme": self.pending_settings.get("theme", self.parent.theme),
                "ear_threshold": self.scale_ear_thresh.value(),
                "consec_frames": self.scale_consec.value(),
                "roll_tilt": self.scale_roll_tilt.value(),
                "pitch_tilt": self.scale_pitch_tilt.value(),
                "volume": self.volume_slider.value(),
                "sound_alert": self.sound_alert_check.isChecked(),
                "sensitivity_mode": self.pending_settings.get("sensitivity_mode", self.parent.alert_handler.sensitivity_mode)
            }
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            logging.info("Settings saved successfully.")

            self.parent.EYE_AR_THRESH = self.scale_ear_thresh.value() / 100.0
            self.parent.EYE_AR_CONSEC_FRAMES = self.scale_consec.value()
            self.parent.HEAD_ROLL_THRESH = self.scale_roll_tilt.value()
            self.parent.HEAD_PITCH_THRESH = self.scale_pitch_tilt.value()
            self.parent.theme = config["theme"]
            self.parent.language = config["language"]
            self.parent.alert_handler.sensitivity_mode = config["sensitivity_mode"]
            self.parent.alert_handler.sound_enabled = config["sound_alert"]
            if self.parent.alert_handler.alarm_sound:
                self.parent.alert_handler.alarm_sound.set_volume(config["volume"] / 100.0)
            if not config["sound_alert"] and self.parent.alert_handler.alarm_playing:
                self.parent.alert_handler.alarm_channel.stop()
                self.parent.alert_handler.alarm_playing = False
                logging.debug("Stopped alarm sound due to sound_alert disabled")

            self.parent.update_theme()
            self.parent.update_ui_layout()

            QMessageBox.information(self, "Success" if self.parent.language == "en" else "موفقیت", self.texts[self.parent.language]["settings_saved"])
            self.accept()
        except Exception as e:
            logging.error(f"Error saving settings: {e}")
            QMessageBox.critical(self, "Error" if self.parent.language == "en" else "خطا", f"Error saving settings: {e}")

    def add_slider(self, label_text, slider, value_label):
        try:
            container = QFrame()
            container.setStyleSheet(
                "border: 1px solid #4A5568; border-radius: 8px; padding: 10px;" if self.parent.theme == "dark" else
                "border: 1px solid #CBD5E0; border-radius: 8px; padding: 10px;"
            )
            layout = QHBoxLayout(container)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.setSpacing(10)
            layout.setAlignment(Qt.AlignmentFlag.AlignRight if self.parent.language == "fa" else Qt.AlignmentFlag.AlignLeft)
            label = QLabel(label_text)
            label.setFont(QFont("BNazanin" if self.parent.language == "fa" else "Arial", 14))
            label.setStyleSheet(
                "font-size: 14px; font-weight: bold; color: #E2E8F0;" if self.parent.theme == "dark" else
                "font-size: 14px; font-weight: bold; color: #1A202C;"
            )
            label.setWordWrap(True)
            label.setAlignment(Qt.AlignmentFlag.AlignRight if self.parent.language == "fa" else Qt.AlignmentFlag.AlignLeft)
            label.setLayoutDirection(Qt.LayoutDirection.RightToLeft if self.parent.language == "fa" else Qt.LayoutDirection.LeftToRight)
            layout.addWidget(label)
            slider_layout = QVBoxLayout()
            slider.setStyleSheet("height: 15px; max-width: 150px;")
            slider_layout.addWidget(slider)
            value_label.setFont(QFont("BNazanin" if self.parent.language == "fa" else "Arial", 14))
            value_label.setStyleSheet(
                "font-size: 14px; min-width: 40px; font-weight: bold; color: #E2E8F0; text-align: center;" if self.parent.theme == "dark" else
                "font-size: 14px; min-width: 40px; font-weight: bold; color: #1A202C; text-align: center;"
            )
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            slider_layout.addWidget(value_label, alignment=Qt.AlignmentFlag.AlignCenter)
            layout.addLayout(slider_layout)
            slider.valueChanged.connect(lambda: value_label.setText(str(slider.value())))
            self.scroll_layout.addWidget(container)
        except Exception as e:
            logging.error(f"Error adding slider: {e}")

    def add_setting(self, label_text, widget, value_label=None):
        try:
            container = QFrame()
            container.setStyleSheet(
                "border: 1px solid #4A5568; border-radius: 8px; padding: 10px;" if self.parent.theme == "dark" else
                "border: 1px solid #CBD5E0; border-radius: 8px; padding: 10px;"
            )
            layout = QHBoxLayout(container)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.setSpacing(10)
            layout.setAlignment(Qt.AlignmentFlag.AlignRight if self.parent.language == "fa" else Qt.AlignmentFlag.AlignLeft)
            label = QLabel(label_text)
            label.setFont(QFont("BNazanin" if self.parent.language == "fa" else "Arial", 14))
            label.setStyleSheet(
                "font-size: 14px; font-weight: bold; color: #E2E8F0; max-width: 200px;" if self.parent.theme == "dark" else
                "font-size: 14px; font-weight: bold; color: #1A202C; max-width: 200px;"
            )
            label.setWordWrap(True)
            label.setAlignment(Qt.AlignmentFlag.AlignRight if self.parent.language == "fa" else Qt.AlignmentFlag.AlignLeft)
            label.setLayoutDirection(Qt.LayoutDirection.RightToLeft if self.parent.language == "fa" else Qt.LayoutDirection.LeftToRight)
            layout.addWidget(label)
            widget.setFont(QFont("BNazanin" if self.parent.language == "fa" else "Arial", 14))
            widget.setStyleSheet("font-size: 14px; padding: 6px; min-width: 120px;")
            widget.setLayoutDirection(Qt.LayoutDirection.RightToLeft if self.parent.language == "fa" else Qt.LayoutDirection.LeftToRight)
            layout.addWidget(widget)
            if value_label:
                value_label.setFont(QFont("BNazanin" if self.parent.language == "fa" else "Arial", 14))
                value_label.setStyleSheet(
                    "font-size: 14px; min-width: 40px; font-weight: bold; color: #E2E8F0; text-align: center;" if self.parent.theme == "dark" else
                    "font-size: 14px; min-width: 40px; font-weight: bold; color: #1A202C; text-align: center;"
                )
                value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(value_label, alignment=Qt.AlignmentFlag.AlignCenter)
            self.scroll_layout.addWidget(container)
        except Exception as e:
            logging.error(f"Error adding setting: {e}")