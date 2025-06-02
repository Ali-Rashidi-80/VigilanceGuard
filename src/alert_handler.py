import os
import json
import logging
import pygame
import jdatetime
import asyncio
import threading
from collections import deque
import cv2
from src.constants import ALERT_FOLDER, ALARM_SOUND, FOURCC, FPS, CONFIG_FILE, MIN_BRIGHTNESS_THRESH, ALERT_COOLDOWN, GRACE_PERIOD, SENSITIVITY_MODES, BLINK_RATE_MIN, BLINK_RATE_MAX, BLINK_DURATION_THRESH, BLINK_CONSEC_FRAMES

class AlertHandler:
    def __init__(self, parent):
        self.parent = parent
        self.alert_count = 0
        self.alert_start_time = None
        self.last_alert_times = {}
        self.alert_triggered = False
        self.alarm_playing = False
        self.recording = False
        self.log_data = []
        self.current_video_filename = None
        self.ear_history = deque(maxlen=15)
        self.eyes_closed_frames = 0
        self.roll_alert_frames = 0
        self.pitch_alert_frames = 0
        self.no_face_frames = 0
        self.video_writer = None
        self.current_alert_type = None
        self.pending_alert_type = None
        self.grace_period_start = None
        self.is_grace_period = False
        self.sensitivity_mode = "normal"
        self.blink_count = 0
        self.blink_times = deque()
        self.blink_duration = 0.0
        self.was_eyes_closed = False
        self.blink_start_time = None
        self.sound_enabled = True  # متغیر برای ردیابی وضعیت فعال بودن صدا

        try:
            pygame.mixer.init()
            if not os.path.exists(ALARM_SOUND):
                raise FileNotFoundError(f"Alarm sound file not found: {ALARM_SOUND}")
            self.alarm_sound = pygame.mixer.Sound(ALARM_SOUND)
            self.alarm_channel = pygame.mixer.Channel(0)
            self.alarm_sound.set_volume(0.5)
            logging.info("Audio initialized successfully")
        except Exception as e:
            logging.error(f"Error initializing audio: {e}")
            self.parent.show_warning(f"Error initializing audio: {e}")
            self.alarm_sound = None
            self.alarm_channel = None
            self.sound_enabled = False

        try:
            if not os.path.exists(ALERT_FOLDER):
                os.makedirs(ALERT_FOLDER)
            log_filename = os.path.join(ALERT_FOLDER, "alerts_log.json")
            if not os.path.exists(log_filename):
                with open(log_filename, 'w', encoding='utf-8') as file:
                    json.dump([], file, ensure_ascii=False, indent=4)
        except Exception as e:
            logging.error(f"Error setting up alert folder: {e}")
            self.parent.show_warning(f"Error setting up alert folder: {e}")

        self.async_loop = asyncio.new_event_loop()
        threading.Thread(target=self.start_async_loop, daemon=True).start()

        # بارگذاری تنظیمات اولیه
        self.load_config()

    def start_async_loop(self):
        try:
            asyncio.set_event_loop(self.async_loop)
            self.async_loop.run_forever()
        except Exception as e:
            logging.error(f"Error starting async loop: {e}")

    async def async_save_log(self):
        log_filename = os.path.join(ALERT_FOLDER, "alerts_log.json")
        try:
            with open(log_filename, mode='w', encoding='utf-8') as file:
                json.dump(self.log_data, file, ensure_ascii=False, indent=4)
            logging.info(f"Log file updated at {os.path.abspath(log_filename)}")
        except Exception as e:
            logging.error(f"Error saving log file: {e}")

    def schedule_save_log(self):
        try:
            asyncio.run_coroutine_threadsafe(self.async_save_log(), self.async_loop)
        except Exception as e:
            logging.error(f"Error scheduling log save: {e}")

    def calculate_blink_rate(self):
        current_time = jdatetime.datetime.now()
        while self.blink_times and (current_time - self.blink_times[0]).total_seconds() > 60:
            self.blink_times.popleft()
        blink_rate = len(self.blink_times)
        logging.debug(f"Calculated blink rate: {blink_rate}/minute")
        return blink_rate

    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.sensitivity_mode = config.get("sensitivity_mode", "normal")
                    self.sound_enabled = config.get("sound_alert", True)
                    volume = config.get("volume", 50) / 100.0
                    if self.alarm_sound:
                        self.alarm_sound.set_volume(volume)
                    logging.info("Configuration loaded successfully in AlertHandler")
        except Exception as e:
            logging.error(f"Error loading configuration in AlertHandler: {e}")

    def handle_alerts(self, frame, smoothed_ear, current_roll, current_pitch, direction_text, alert_flag, alert_severity, brightness):
        try:
            self.ear_history.append(smoothed_ear)
            current_time = jdatetime.datetime.now()

            # تنظیم آستانه‌ها بر اساس حساسیت
            sensitivity = SENSITIVITY_MODES[self.sensitivity_mode]
            ear_threshold = self.parent.EYE_AR_THRESH * sensitivity["ear_scale"]
            roll_threshold = self.parent.HEAD_ROLL_THRESH * sensitivity["roll_scale"]
            pitch_threshold = self.parent.HEAD_PITCH_THRESH * sensitivity["pitch_scale"]
            consec_frames = sensitivity["consec_frames"]

            if brightness < MIN_BRIGHTNESS_THRESH:
                ear_threshold *= 1.10
                roll_threshold *= 1.05
                pitch_threshold *= 1.05
                logging.debug(f"Low brightness ({brightness}), adjusted thresholds: EAR={ear_threshold}, Roll={roll_threshold}, Pitch={pitch_threshold}")

            # شمارش فریم‌ها
            is_eyes_closed = smoothed_ear < ear_threshold
            is_roll_exceeded = abs(current_roll) > roll_threshold
            is_pitch_exceeded = abs(current_pitch) > pitch_threshold
            is_no_face = alert_severity == "no_face"

            if is_no_face:
                self.no_face_frames += 1
                self.eyes_closed_frames = 0
                self.roll_alert_frames = 0
                self.pitch_alert_frames = 0
            else:
                self.no_face_frames = 0
                if is_eyes_closed:
                    self.eyes_closed_frames += 1
                else:
                    self.eyes_closed_frames = 0
                if is_roll_exceeded:
                    self.roll_alert_frames += 1
                else:
                    self.roll_alert_frames = 0
                if is_pitch_exceeded:
                    self.pitch_alert_frames += 1
                else:
                    self.pitch_alert_frames = 0

            # تشخیص پلک زدن
            if is_eyes_closed and not self.was_eyes_closed:
                self.blink_start_time = current_time
                self.was_eyes_closed = True
            elif not is_eyes_closed and self.was_eyes_closed:
                self.was_eyes_closed = False
                if self.blink_start_time:
                    self.blink_duration = (current_time - self.blink_start_time).total_seconds()
                    self.blink_times.append(current_time)
                    self.blink_count += 1
                    logging.debug(f"Blink detected, duration: {self.blink_duration}, count: {self.blink_count}")
                    if self.blink_duration > BLINK_DURATION_THRESH and not self.pending_alert_type:
                        self.pending_alert_type = "long_blink"
                        self.grace_period_start = current_time
                        self.is_grace_period = True
                        logging.info(f"Long blink detected: {self.blink_duration} seconds")
            self.was_eyes_closed = is_eyes_closed

            # نرخ پلک زدن
            blink_rate = self.calculate_blink_rate()
            if (blink_rate < BLINK_RATE_MIN or blink_rate > BLINK_RATE_MAX) and not self.pending_alert_type:
                self.pending_alert_type = "blink_anomaly"
                self.grace_period_start = current_time
                self.is_grace_period = True
                logging.info(f"Abnormal blink rate detected: {blink_rate}/minute")

            # اولویت‌بندی هشدارها
            new_alert_type = None
            if self.no_face_frames >= consec_frames:
                new_alert_type = "no_face"
            elif self.eyes_closed_frames >= consec_frames:
                if self.roll_alert_frames >= consec_frames and self.pitch_alert_frames >= consec_frames:
                    new_alert_type = "eyes_closed_and_head_tilt_both"
                elif self.roll_alert_frames >= consec_frames:
                    new_alert_type = "eyes_closed_and_head_tilt_roll"
                elif self.pitch_alert_frames >= consec_frames:
                    new_alert_type = "eyes_closed_and_head_tilt_pitch"
                else:
                    new_alert_type = "eyes_closed"
            elif self.roll_alert_frames >= consec_frames and self.pitch_alert_frames >= consec_frames:
                new_alert_type = "head_tilt_both"
            elif self.roll_alert_frames >= consec_frames:
                new_alert_type = "head_tilt_roll"
            elif self.pitch_alert_frames >= consec_frames:
                new_alert_type = "head_tilt_pitch"
            elif self.pending_alert_type in ["long_blink", "blink_anomaly"]:
                new_alert_type = self.pending_alert_type

            # تنظیم پیام هشدار در حال انتظار
            if not self.alert_triggered and not self.is_grace_period:
                try:
                    if new_alert_type == "no_face":
                        self.parent.pending_alert_message = self.parent.texts[self.parent.language]["alert_message_no_face"]
                    elif new_alert_type and "eyes_closed" in new_alert_type:
                        self.parent.pending_alert_message = self.parent.texts[self.parent.language]["alert_warning_sleep"]
                    elif new_alert_type and "head_tilt" in new_alert_type:
                        self.parent.pending_alert_message = self.parent.texts[self.parent.language]["alert_warning_head"]
                    elif new_alert_type in ["long_blink", "blink_anomaly"]:
                        self.parent.pending_alert_message = self.parent.texts[self.parent.language]["alert_warning_blink"]
                    else:
                        self.parent.pending_alert_message = None
                    logging.debug(f"Set pending_alert_message: {self.parent.pending_alert_message}")
                except KeyError as e:
                    logging.error(f"KeyError in setting pending_alert_message: {e}")
                    self.parent.pending_alert_message = None

            # توقف صدا اگر sound_enabled غیرفعال باشد
            if not self.sound_enabled and self.alarm_playing and self.alarm_channel:
                try:
                    self.alarm_channel.stop()
                    self.alarm_playing = False
                    logging.debug("Stopped alarm sound due to sound_enabled=False")
                except Exception as e:
                    logging.error(f"Error stopping alarm due to sound_enabled=False: {e}")
                    self.alarm_playing = False

            # مدیریت هشدار جدید
            if new_alert_type and new_alert_type != self.current_alert_type:
                alert_category = self.get_alert_category(new_alert_type)
                last_alert_time = self.last_alert_times.get(alert_category)
                if last_alert_time and (current_time - last_alert_time).total_seconds() < ALERT_COOLDOWN[alert_category]:
                    logging.debug(f"Alert {new_alert_type} blocked by cooldown")
                    return

                if not self.is_grace_period:
                    self.pending_alert_type = new_alert_type
                    self.grace_period_start = current_time
                    self.is_grace_period = True
                    logging.debug(f"Started grace period for {new_alert_type}")
                elif (current_time - self.grace_period_start).total_seconds() >= GRACE_PERIOD:
                    if self.alert_start_time is None:
                        self.alert_start_time = self.grace_period_start
                    duration = (current_time - self.alert_start_time).total_seconds()

                    if duration >= self.parent.ALERT_MIN_DURATION:
                        self.alert_triggered = True
                        self.last_alert_times[alert_category] = current_time
                        self.alert_count += 1
                        self.current_alert_type = new_alert_type
                        log_entry = {
                            "alert_number": self.alert_count,
                            "alert_start_time": self.alert_start_time.strftime("%Y/%m/%d %H:%M:%S"),
                            "alert_type": new_alert_type,
                            "alert_severity": alert_severity,
                            "video_link": f"file://{os.path.abspath(self.current_video_filename) if self.current_video_filename else ''}",
                            "direction": direction_text,
                            "brightness": brightness,
                            "sensitivity_mode": self.sensitivity_mode,
                            "consecutive_frames": {
                                "eyes_closed": self.eyes_closed_frames,
                                "roll": self.roll_alert_frames,
                                "pitch": self.pitch_alert_frames,
                                "no_face": self.no_face_frames
                            },
                            "blink_rate": blink_rate,
                            "blink_duration": self.blink_duration if new_alert_type == "long_blink" else None
                        }
                        self.log_data.append(log_entry)
                        logging.info(f"Alert #{self.alert_count}: {new_alert_type}, Severity: {alert_severity}, Blink Rate: {blink_rate}")
                        self.schedule_save_log()

                        # مدیریت پخش صدا
                        if (self.sound_enabled and self.alarm_sound and self.alarm_channel and 
                            new_alert_type not in ["no_face", "blink_anomaly", "long_blink"]):
                            try:
                                if self.alarm_playing:
                                    self.alarm_channel.stop()
                                    logging.debug(f"Stopped previous alarm sound before starting new for alert: {new_alert_type}")
                                self.alarm_channel.play(self.alarm_sound, loops=-1)
                                self.alarm_playing = True
                                logging.debug(f"Started alarm sound for alert: {new_alert_type}")
                            except Exception as e:
                                logging.error(f"Error playing alarm: {e}")
                                self.parent.show_warning(f"Error playing alarm: {e}")
                                self.alarm_playing = False

                        if not self.recording and new_alert_type not in ["no_face", "blink_anomaly"]:
                            self.current_video_filename = os.path.join(ALERT_FOLDER, f"alert_{self.alert_start_time.strftime('%Y%m%d_%H%M%S')}.mp4")
                            self.video_writer = cv2.VideoWriter(self.current_video_filename, FOURCC, FPS, (self.parent.frame_processor.frame_width, self.parent.frame_processor.frame_height))
                            self.recording = True
                        if self.recording and new_alert_type != "no_face":
                            self.video_writer.write(frame)
                    self.is_grace_period = False
                    self.pending_alert_type = None

            # پایان هشدار یا توقف صدا در صورت عدم نیاز
            else:
                if self.alarm_playing and (not new_alert_type or new_alert_type in ["no_face", "blink_anomaly", "long_blink"]):
                    try:
                        self.alarm_channel.stop()
                        self.alarm_playing = False
                        logging.debug(f"Stopped alarm sound due to no alert or invalid alert type: {new_alert_type}")
                    except Exception as e:
                        logging.error(f"Error stopping alarm: {e}")
                        self.parent.show_warning(f"Error stopping alarm: {e}")
                        self.alarm_playing = False

                if not new_alert_type and (self.alert_triggered or self.is_grace_period):
                    if self.alert_triggered:
                        alert_end_time = current_time
                        alert_duration = (alert_end_time - self.alert_start_time).total_seconds()
                        self.log_data[-1]["alert_end_time"] = alert_end_time.strftime("%Y/%m/%d %H:%M:%S")
                        self.log_data[-1]["alert_duration"] = alert_duration
                        logging.info(f"Alert #{self.alert_count} ended. Type: {self.current_alert_type}, Duration: {alert_duration}s")
                        self.schedule_save_log()
                    self.reset_alert_state()
                    if self.recording:
                        self.video_writer.release()
                        self.recording = False

        except Exception as e:
            logging.error(f"Error handling alerts: {e}")

    def reset_alert_state(self):
        self.alert_start_time = None
        self.alert_triggered = False
        self.current_alert_type = None
        self.pending_alert_type = None
        self.is_grace_period = False
        self.parent.pending_alert_message = None
        self.eyes_closed_frames = 0
        self.roll_alert_frames = 0
        self.pitch_alert_frames = 0
        self.no_face_frames = 0
        if self.alarm_playing and self.alarm_channel:
            try:
                self.alarm_channel.stop()
                self.alarm_playing = False
                logging.debug("Stopped alarm sound in reset_alert_state")
            except Exception as e:
                logging.error(f"Error stopping alarm in reset_alert_state: {e}")
                self.parent.show_warning(f"Error stopping alarm: {e}")
                self.alarm_playing = False
        logging.debug("Reset alert state")

    def get_alert_category(self, alert_type):
        if alert_type == "no_face":
            return "no_face"
        elif "eyes_closed" in alert_type:
            return "eyes_closed"
        elif "head_tilt" in alert_type:
            return "head_tilt"
        elif alert_type in ["long_blink", "blink_anomaly"]:
            return "blink_anomaly"
        return "other"

    def save_config(self):
        try:
            config = {
                "language": self.parent.language,
                "theme": self.parent.theme,
                "ear_threshold": int(self.parent.EYE_AR_THRESH * 100),
                "consec_frames": self.parent.EYE_AR_CONSEC_FRAMES,
                "roll_tilt": self.parent.HEAD_ROLL_THRESH,
                "pitch_tilt": self.parent.HEAD_PITCH_THRESH,
                "volume": int(self.alarm_sound.get_volume() * 100) if self.alarm_sound else 50,
                "sound_alert": self.sound_enabled,
                "sensitivity_mode": self.sensitivity_mode
            }
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            logging.info("Configuration saved successfully.")
        except Exception as e:
            logging.error(f"Error saving configuration: {e}")

    def cleanup(self):
        try:
            if self.recording and self.video_writer:
                self.video_writer.release()
                self.recording = False
            if self.alarm_playing and self.alarm_channel:
                try:
                    self.alarm_channel.stop()
                    self.alarm_playing = False
                    logging.debug("Stopped alarm sound during cleanup")
                except Exception as e:
                    logging.error(f"Error stopping alarm during cleanup: {e}")
                    self.parent.show_warning(f"Error stopping alarm during cleanup: {e}")
            try:
                pygame.mixer.quit()  # خاتمه کامل میکسر صوتی
                logging.debug("Pygame mixer quit during cleanup")
            except Exception as e:
                logging.error(f"Error quitting pygame mixer: {e}")

            def shutdown_loop():
                try:
                    self.async_loop.stop()
                    self.async_loop.run_until_complete(self.async_loop.shutdown_asyncgens())
                    self.async_loop.close()
                    logging.debug("Async loop shut down successfully")
                except Exception as e:
                    logging.error(f"Error shutting down async loop: {e}")

            self.async_loop.call_soon_threadsafe(shutdown_loop)
            self.save_config()
            log_filename = os.path.join(ALERT_FOLDER, "alerts_log.json")
            try:
                with open(log_filename, mode='w', encoding='utf-8') as file:
                    json.dump(self.log_data, file, ensure_ascii=False, indent=4)
                logging.info(f"Final log file saved at {os.path.abspath(log_filename)}")
            except Exception as e:
                logging.error(f"Error saving log file: {e}")
        except Exception as e:
            logging.error(f"Error cleaning up alert handler: {e}")