"""
Anomaly generators for testing detection accuracy.

Generates controlled system anomalies for validation.
"""

import os
import threading
import time
from pathlib import Path
from typing import Optional

from config import get_logger

logger = get_logger(__name__)


class AnomalyGenerator:
    """
    Generates synthetic system anomalies for testing.

    All generators run in background threads with automatic cleanup.
    """

    def __init__(self):
        """Initialize the anomaly generator."""
        self.active_threads = []

    def generate_cpu_spike(self, duration: int = 10, intensity: int = 5):
        """
        Generate CPU spike by running intensive calculations.

        Args:
            duration: Duration in seconds.
            intensity: Intensity level 1-10 (number of threads).
        """
        logger.info(f"Generating CPU spike (duration={duration}s, intensity={intensity})")

        def cpu_load():
            """CPU-intensive calculation."""
            end_time = time.time() + duration
            while time.time() < end_time:
                sum([i ** 2 for i in range(10000)])

        threads = []
        for _ in range(min(intensity, 10)):
            thread = threading.Thread(target=cpu_load, daemon=True)
            thread.start()
            threads.append(thread)

        self.active_threads.extend(threads)

        cleanup_thread = threading.Thread(
            target=self._cleanup_threads,
            args=(threads, duration + 1),
            daemon=True
        )
        cleanup_thread.start()

    def generate_memory_spike(self, duration: int = 10, intensity: int = 5):
        """
        Generate memory spike by allocating large arrays.

        Args:
            duration: Duration in seconds.
            intensity: Intensity level 1-10 (memory size multiplier).
        """
        logger.info(f"Generating memory spike (duration={duration}s, intensity={intensity})")

        def memory_load():
            """Allocate large amounts of memory."""
            try:
                size = intensity * 100 * 1024 * 1024
                data = bytearray(size)

                for i in range(0, len(data), 4096):
                    data[i] = 1

                time.sleep(duration)
                del data

            except MemoryError:
                logger.warning("Memory allocation failed (system memory limit)")

        thread = threading.Thread(target=memory_load, daemon=True)
        thread.start()
        self.active_threads.append(thread)

    def generate_disk_spike(self, duration: int = 10, intensity: int = 5):
        """
        Generate disk I/O spike by writing/reading files.

        Args:
            duration: Duration in seconds.
            intensity: Intensity level 1-10 (file size multiplier).
        """
        logger.info(f"Generating disk spike (duration={duration}s, intensity={intensity})")

        def disk_load():
            """Perform heavy disk I/O."""
            try:
                temp_file = Path('/tmp/anomalywatch_test.dat')
                chunk_size = intensity * 1024 * 1024
                data = os.urandom(chunk_size)

                end_time = time.time() + duration

                while time.time() < end_time:
                    with open(temp_file, 'wb') as f:
                        f.write(data)
                        f.flush()
                        os.fsync(f.fileno())

                    with open(temp_file, 'rb') as f:
                        _ = f.read()

                temp_file.unlink(missing_ok=True)

            except Exception as e:
                logger.error(f"Disk load generation failed: {e}")

        thread = threading.Thread(target=disk_load, daemon=True)
        thread.start()
        self.active_threads.append(thread)

    def generate_network_spike(self, duration: int = 10, intensity: int = 5):
        """
        Generate network spike (placeholder - requires external target).

        Args:
            duration: Duration in seconds.
            intensity: Intensity level 1-10.
        """
        logger.info(
            f"Network spike generation requested (duration={duration}s, intensity={intensity})"
        )
        logger.warning(
            "Network spike generation requires external target. "
            "This is a placeholder implementation."
        )

    def generate_thread_bomb(self, duration: int = 10, intensity: int = 5):
        """
        Generate thread count spike by spawning many threads.

        Args:
            duration: Duration in seconds.
            intensity: Intensity level 1-10 (thread count multiplier).
        """
        logger.info(f"Generating thread bomb (duration={duration}s, intensity={intensity})")

        def thread_worker():
            """Thread that just sleeps."""
            time.sleep(duration)

        threads = []
        thread_count = intensity * 20

        for _ in range(min(thread_count, 200)):
            thread = threading.Thread(target=thread_worker, daemon=True)
            thread.start()
            threads.append(thread)

        self.active_threads.extend(threads)

        cleanup_thread = threading.Thread(
            target=self._cleanup_threads,
            args=(threads, duration + 1),
            daemon=True
        )
        cleanup_thread.start()

    def _cleanup_threads(self, threads: list, wait_time: float):
        """
        Wait for threads to complete and clean up.

        Args:
            threads: List of threads to wait for.
            wait_time: Maximum wait time in seconds.
        """
        time.sleep(wait_time)

        for thread in threads:
            if thread.is_alive():
                try:
                    thread.join(timeout=1)
                except Exception:
                    pass

            if thread in self.active_threads:
                self.active_threads.remove(thread)

        logger.debug(f"Cleaned up {len(threads)} threads")

    def stop_all(self):
        """Stop all active anomaly generators."""
        logger.info(f"Stopping {len(self.active_threads)} active anomaly generators")

        for thread in self.active_threads[:]:
            try:
                thread.join(timeout=0.1)
            except Exception:
                pass

        self.active_threads.clear()

    def get_active_count(self) -> int:
        """
        Get count of active anomaly generator threads.

        Returns:
            Number of active threads.
        """
        return len([t for t in self.active_threads if t.is_alive()])
