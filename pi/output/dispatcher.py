"""
Output dispatcher — routes lens output to enabled output modules.
Text is always active. Audio and light are placeholders until Plexus residency.
"""
import logging
from pathlib import Path

from pi.output.text_output import TextOutput
from pi.output.audio_output import AudioOutput
from pi.output.light_output import LightOutput

logger = logging.getLogger(__name__)


class OutputDispatcher:
    def __init__(self, lens_name: str, config: dict, log_dir: Path | None = None):
        self.lens_name = lens_name
        self.text = TextOutput(lens_name, log_dir)
        self.audio = AudioOutput(lens_name)
        self.light = LightOutput(lens_name)

        # Which outputs are active — extend in Plexus phase
        self._use_text = config.get("use_text_output", True)
        self._use_audio = config.get("use_audio_output", False)
        self._use_light = config.get("use_light_output", False)

    def dispatch(self, text: str, metadata: dict | None = None):
        """Send lens output to all active output channels."""
        if not text:
            return
        if self._use_text:
            self.text.emit(text, metadata)
        if self._use_audio and self.audio.available:
            self.audio.emit(text, metadata)
        if self._use_light and self.light.available:
            self.light.emit(text, metadata)
