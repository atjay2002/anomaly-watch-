"""
GPIO controller for Raspberry Pi hardware alerts.

Provides platform-agnostic GPIO control with mock implementation for non-Pi systems.
"""

import platform
import threading
import time
from typing import Optional

from config import get_logger

logger = get_logger(__name__)


# Try to import RPi.GPIO
try:
    import RPi.GPIO as GPIO
    RPI_GPIO_AVAILABLE = True
except ImportError:
    RPI_GPIO_AVAILABLE = False
    logger.info("RPi.GPIO not available, using mock GPIO implementation")


class GPIOController:
    """
    GPIO controller for LED and buzzer alerts on Raspberry Pi.

    Falls back to mock implementation on non-Pi platforms.
    """

    # GPIO pin assignments
    LED_GREEN_PIN = 17
    LED_YELLOW_PIN = 27
    LED_RED_PIN = 22
    BUZZER_PIN = 23

    def __init__(self):
        """Initialize GPIO controller."""
        self.is_raspberry_pi = self._is_raspberry_pi()
        self.gpio_initialized = False
        self.current_level = 'normal'
        self.blink_thread: Optional[threading.Thread] = None
        self.stop_blink = threading.Event()

        if self.is_raspberry_pi and RPI_GPIO_AVAILABLE:
            try:
                self._initialize_gpio()
                self.gpio_initialized = True
                logger.info("GPIO initialized successfully")
            except Exception as e:
                logger.error(f"GPIO initialization failed: {e}", exc_info=True)
                self.gpio_initialized = False
        else:
            logger.info("Running in mock GPIO mode (non-Raspberry Pi or GPIO unavailable)")

    def _is_raspberry_pi(self) -> bool:
        """
        Detect if running on Raspberry Pi.

        Returns:
            True if on Raspberry Pi.
        """
        try:
            with open('/proc/device-tree/model', 'r') as f:
                model = f.read()
                return 'Raspberry Pi' in model
        except FileNotFoundError:
            return False

    def _initialize_gpio(self):
        """Initialize GPIO pins."""
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        GPIO.setup(self.LED_GREEN_PIN, GPIO.OUT)
        GPIO.setup(self.LED_YELLOW_PIN, GPIO.OUT)
        GPIO.setup(self.LED_RED_PIN, GPIO.OUT)
        GPIO.setup(self.BUZZER_PIN, GPIO.OUT)

        self._all_leds_off()
        GPIO.output(self.BUZZER_PIN, GPIO.LOW)

    def _all_leds_off(self):
        """Turn off all LEDs."""
        if not self.gpio_initialized:
            return

        GPIO.output(self.LED_GREEN_PIN, GPIO.LOW)
        GPIO.output(self.LED_YELLOW_PIN, GPIO.LOW)
        GPIO.output(self.LED_RED_PIN, GPIO.LOW)

    def set_alert_level(self, level: str):
        """
        Set alert level and activate corresponding LED pattern.

        Args:
            level: Alert level ('normal', 'warning', 'critical').
        """
        if level == self.current_level:
            return

        logger.info(f"Setting alert level: {level}")
        self.current_level = level

        if self.blink_thread and self.blink_thread.is_alive():
            self.stop_blink.set()
            self.blink_thread.join(timeout=2)

        if self.gpio_initialized:
            self._all_leds_off()

            if level == 'normal':
                GPIO.output(self.LED_GREEN_PIN, GPIO.HIGH)

            elif level == 'warning':
                self.stop_blink.clear()
                self.blink_thread = threading.Thread(
                    target=self._blink_led,
                    args=(self.LED_YELLOW_PIN, 1.0),
                    daemon=True
                )
                self.blink_thread.start()

            elif level == 'critical':
                self.stop_blink.clear()
                self.blink_thread = threading.Thread(
                    target=self._blink_led_and_beep,
                    args=(self.LED_RED_PIN, 0.3),
                    daemon=True
                )
                self.blink_thread.start()

        else:
            self._mock_alert(level)

    def _blink_led(self, pin: int, interval: float):
        """
        Blink an LED at specified interval.

        Args:
            pin: GPIO pin number.
            interval: Blink interval in seconds.
        """
        while not self.stop_blink.is_set():
            GPIO.output(pin, GPIO.HIGH)
            time.sleep(interval)
            GPIO.output(pin, GPIO.LOW)
            time.sleep(interval)

    def _blink_led_and_beep(self, pin: int, interval: float):
        """
        Blink LED and sound buzzer for critical alerts.

        Args:
            pin: GPIO pin number.
            interval: Blink interval in seconds.
        """
        while not self.stop_blink.is_set():
            GPIO.output(pin, GPIO.HIGH)
            GPIO.output(self.BUZZER_PIN, GPIO.HIGH)
            time.sleep(interval)
            GPIO.output(pin, GPIO.LOW)
            GPIO.output(self.BUZZER_PIN, GPIO.LOW)
            time.sleep(interval)

    def _mock_alert(self, level: str):
        """
        Mock GPIO alert for non-Pi systems.

        Args:
            level: Alert level.
        """
        logger.info(f"[MOCK GPIO] Alert level: {level}")

        if level == 'normal':
            logger.debug("[MOCK GPIO] Green LED: ON")
        elif level == 'warning':
            logger.debug("[MOCK GPIO] Yellow LED: BLINKING (1s interval)")
        elif level == 'critical':
            logger.debug("[MOCK GPIO] Red LED: BLINKING + BUZZER (0.3s interval)")

    def test_pattern(self):
        """Run a test pattern through all LEDs and buzzer."""
        logger.info("Running GPIO test pattern")

        if not self.gpio_initialized:
            logger.info("[MOCK GPIO] Test pattern: All LEDs and buzzer sequence")
            return

        try:
            self._all_leds_off()

            GPIO.output(self.LED_GREEN_PIN, GPIO.HIGH)
            time.sleep(0.5)
            GPIO.output(self.LED_GREEN_PIN, GPIO.LOW)

            GPIO.output(self.LED_YELLOW_PIN, GPIO.HIGH)
            time.sleep(0.5)
            GPIO.output(self.LED_YELLOW_PIN, GPIO.LOW)

            GPIO.output(self.LED_RED_PIN, GPIO.HIGH)
            GPIO.output(self.BUZZER_PIN, GPIO.HIGH)
            time.sleep(0.5)
            GPIO.output(self.LED_RED_PIN, GPIO.LOW)
            GPIO.output(self.BUZZER_PIN, GPIO.LOW)

            logger.info("GPIO test pattern completed")

        except Exception as e:
            logger.error(f"GPIO test pattern failed: {e}", exc_info=True)

    def cleanup(self):
        """Cleanup GPIO resources."""
        logger.info("Cleaning up GPIO")

        if self.blink_thread and self.blink_thread.is_alive():
            self.stop_blink.set()
            self.blink_thread.join(timeout=2)

        if self.gpio_initialized:
            try:
                self._all_leds_off()
                GPIO.output(self.BUZZER_PIN, GPIO.LOW)
                GPIO.cleanup()
                logger.info("GPIO cleanup completed")
            except Exception as e:
                logger.error(f"GPIO cleanup failed: {e}", exc_info=True)
