"""
Light output module.

PLACEHOLDER — not yet implemented.
To be designed with Seungho Lee during Plexus residency (July 2026).

Planned: LED strip or projection control driven by lens output intensity/rhythm.
Hardware: TBD (GPIO, DMX, or serial protocol).
"""
import logging

logger = logging.getLogger(__name__)


class LightOutput:
    def __init__(self, lens_name: str):
        self.lens_name = lens_name
        self.available = False
        logger.debug("LightOutput: placeholder, not implemented")

    def emit(self, text: str, metadata: dict | None = None):
        logger.debug("LightOutput.emit called (placeholder) for %s", self.lens_name)
