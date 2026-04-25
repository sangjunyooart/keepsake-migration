"""
Core inference runtime for one lens on a Raspberry Pi 5.

Loads Qwen 2.5 1.5B base + LoRA adapter, runs inference on CPU.
Supports hot-reload when Mac pushes a new adapter.
"""
import logging
import sys
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

PI_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PI_ROOT.parent
sys.path.insert(0, str(REPO_ROOT))

from shared.ethics_filter import EthicsFilter
from pi.inference.adapter_loader import AdapterLoader
from pi.inference.ai_hat_accelerator import AIHatAccelerator


class LensRuntime:
    """
    Manages the full inference lifecycle for one lens:
    - Load base model + adapter on startup
    - Generate responses
    - Reload adapter on signal from Mac
    """

    BASE_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"

    def __init__(self, lens_name: str, adapter_base: Path, config: dict):
        self.lens_name = lens_name
        self.config = config
        self.adapter_loader = AdapterLoader(adapter_base, lens_name)
        self.accelerator = AIHatAccelerator(use_ai_hat=config.get("use_ai_hat", True))
        self.ethics = EthicsFilter()
        self._lock = threading.Lock()
        self.model = None
        self.tokenizer = None
        self._loaded_adapter: Optional[Path] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def load(self):
        """Load base model + latest adapter. Blocks until ready."""
        logger.info("Loading %s (CPU inference)...", self.BASE_MODEL)
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.tokenizer = AutoTokenizer.from_pretrained(self.BASE_MODEL)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # CPU inference — fp32 (Pi has no MPS/CUDA)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.BASE_MODEL,
            torch_dtype=torch.float32,
            low_cpu_mem_usage=True,
        )

        adapter_path = self.adapter_loader.latest_path()
        if adapter_path:
            self._apply_adapter(adapter_path)
        else:
            logger.info("No adapter found for %s — running base model only", self.lens_name)

        logger.info("LensRuntime ready: %s", self.lens_name)

    def reload_adapter(self) -> bool:
        """
        Hot-reload the latest adapter without restarting the process.
        Called by adapter_receiver when Mac pushes a new adapter.
        Returns True if reloaded, False if nothing new.
        """
        if not self.adapter_loader.has_new_adapter():
            return False
        new_path = self.adapter_loader.latest_path()
        if not new_path:
            return False
        with self._lock:
            self._apply_adapter(new_path)
        return True

    def unload(self):
        with self._lock:
            self.model = None
            self.tokenizer = None
        logger.info("LensRuntime unloaded: %s", self.lens_name)

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def generate(self, prompt: str, max_tokens: int = 200, temperature: float = 0.8) -> str:
        """
        Generate a response for the given prompt.
        Output is ethics-checked before returning.
        """
        if self.model is None or self.tokenizer is None:
            return ""

        import torch

        with self._lock:
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
            with torch.no_grad():
                output_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                )
            generated = self.tokenizer.decode(
                output_ids[0][inputs["input_ids"].shape[1]:],
                skip_special_tokens=True,
            )

        if not self.ethics.is_safe(generated):
            logger.warning("Ethics filter triggered on output for %s", self.lens_name)
            return self.ethics.scrub(generated)
        return generated

    def is_ready(self) -> bool:
        return self.model is not None

    def adapter_info(self) -> dict:
        return self.adapter_loader.current_version_info()

    # ------------------------------------------------------------------

    def _apply_adapter(self, adapter_path: Path):
        from peft import PeftModel
        logger.info("Applying adapter from %s", adapter_path)
        # If a PEFT model is already loaded, merge/re-apply
        # For simplicity: reload base and wrap with new adapter
        if hasattr(self.model, "disable_adapter"):
            # Already a PeftModel — load new config
            self.model = self.model.base_model.model
        self.model = PeftModel.from_pretrained(
            self.model, str(adapter_path), is_trainable=False
        )
        self.adapter_loader.mark_loaded(adapter_path)
        self._loaded_adapter = adapter_path
        logger.info("Adapter loaded: %s", adapter_path.name)
