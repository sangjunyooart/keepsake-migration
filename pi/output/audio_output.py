"""
Audio output module.

PLACEHOLDER — not yet implemented.
To be designed with Seungho Lee during Plexus residency (July 2026).

Planned: text-to-speech or generative audio triggered by lens output.
Hardware: TBD (USB audio, I2S DAC, or Pi's built-in audio).
"""
import logging

logger = logging.getLogger(__name__)


class AudioOutput:
    def __init__(self, lens_name: str):
        self.lens_name = lens_name
        self.available = False
        logger.debug("AudioOutput: placeholder, not implemented")

    def emit(self, text: str, metadata: dict | None = None):
        logger.debug("AudioOutput.emit called (placeholder) for %s", self.lens_name)
