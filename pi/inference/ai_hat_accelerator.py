"""
Hailo-8L AI HAT+ wrapper for Raspberry Pi 5.

HARDWARE NOTE:
  Hailo-8L (AI HAT+ 13 TOPS) supports CNN-based vision models compiled
  with the Hailo Dataflow Compiler. As of April 2026, it does NOT support
  transformer-based LLM inference for models like Qwen 2.5 1.5B.
  Hailo LLM support begins with Hailo-10H, not Hailo-8L.

  This module always falls back to CPU inference via the transformers library.
  The Hailo accelerator is available for future vision/audio output modules
  if needed, but NOT for the lens inference pipeline.

  If Hailo LLM support for Qwen 2.5 family becomes available, update
  _try_hailo_init() below and remove the early return.
"""
import logging

logger = logging.getLogger(__name__)


class AIHatAccelerator:
    """
    Hailo-8L wrapper. Currently a no-op — always reports unavailable for LLM.
    Kept as a defined interface for future compatibility.
    """

    def __init__(self, use_ai_hat: bool = True):
        self.available = False
        self.reason = "Hailo-8L does not support Qwen 2.5 1.5B transformer inference"
        if use_ai_hat:
            self._try_hailo_init()

    def _try_hailo_init(self):
        # Hailo-8L does not support LLM inference — return immediately.
        # If future SDK adds support, implement here.
        logger.debug("AI HAT+ check: %s — using CPU inference", self.reason)

    def is_available(self) -> bool:
        return self.available

    def status(self) -> dict:
        return {
            "available": self.available,
            "reason": self.reason,
            "inference_device": "cpu",
        }
