import logging
import sys
from pathlib import Path
from typing import Optional

import torch

logger = logging.getLogger(__name__)

MAC_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MAC_ROOT.parent))

from shared.ethics_filter import EthicsFilter


class LensLoRATrainer:
    """
    LoRA fine-tuning for one lens on Mac mini M4 (MPS device).

    dtype priority: bf16 → fp32 (fp16 skipped — MPS bf16 is more stable).
    Saves adapter weights only (base model unchanged).
    """

    def __init__(self, lens_name: str, global_config: dict, lens_config: dict, mac_root: Path):
        self.lens_name = lens_name
        self.global_config = global_config
        self.lens_config = lens_config
        self.mac_root = mac_root
        self.adapter_dir = mac_root / global_config["adapter_dir"] / lens_name
        self.adapter_dir.mkdir(parents=True, exist_ok=True)
        self.ethics = EthicsFilter()

        self.device = self._resolve_device(global_config.get("device", "mps"))
        self.model = None
        self.tokenizer = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_model(self):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import LoraConfig, get_peft_model, PeftModel, TaskType

        base_model_id = self.global_config["base_model"]

        self.tokenizer = AutoTokenizer.from_pretrained(base_model_id)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        base = self._load_base_model(base_model_id)

        latest_ckpt = self._find_latest_checkpoint()
        if latest_ckpt:
            logger.info("Loading existing adapter from %s", latest_ckpt)
            self.model = PeftModel.from_pretrained(base, str(latest_ckpt), is_trainable=True)
        else:
            logger.info("Initialising new LoRA adapter for %s", self.lens_name)
            lc = self.lens_config["lora"]
            lora_cfg = LoraConfig(
                r=lc["r"],
                lora_alpha=lc["alpha"],
                target_modules=lc["target_modules"],
                lora_dropout=lc["dropout"],
                bias="none",
                task_type=TaskType.CAUSAL_LM,
            )
            self.model = get_peft_model(base, lora_cfg)

        self.model.print_trainable_parameters()

    def train_session(self, corpus_path: Path, checkpoint_tag: str) -> Optional[Path]:
        """
        Run one training session on the given corpus.
        Returns the saved adapter path, or None on failure.
        """
        from transformers import Trainer, TrainingArguments, DataCollatorForLanguageModeling
        from datasets import Dataset

        if self.model is None:
            raise RuntimeError("Call load_model() before train_session()")

        texts = self._load_corpus(corpus_path)
        if not texts:
            logger.warning("No training texts found in %s", corpus_path)
            return None

        lc = self.lens_config["learning"]
        encodings = self.tokenizer(
            texts,
            truncation=True,
            max_length=1024,
            padding="max_length",
            return_tensors="pt",
        )
        dataset = Dataset.from_dict({
            "input_ids": encodings["input_ids"],
            "attention_mask": encodings["attention_mask"],
            "labels": encodings["input_ids"].clone(),
        })

        output_dir = self.adapter_dir / checkpoint_tag
        training_args = TrainingArguments(
            output_dir=str(output_dir),
            num_train_epochs=lc["max_epochs_per_session"],
            per_device_train_batch_size=lc["batch_size"],
            gradient_accumulation_steps=lc["gradient_accumulation"],
            learning_rate=lc["learning_rate"],
            save_strategy="epoch",
            logging_steps=10,
            report_to="none",
            # MPS: use no_cuda=True so HF doesn't try CUDA; MPS is picked via device_map
            no_cuda=True,
            bf16=False,  # Trainer bf16 flag is for CUDA; MPS bf16 set via model dtype
            dataloader_pin_memory=False,
        )

        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer, mlm=False
        )

        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=dataset,
            data_collator=data_collator,
        )

        try:
            trainer.train()
        except Exception as e:
            logger.error("Training failed for %s: %s", self.lens_name, e)
            return None

        # Save only the LoRA adapter (not the full base model)
        self.model.save_pretrained(str(output_dir))
        self.tokenizer.save_pretrained(str(output_dir))
        logger.info("Adapter saved to %s", output_dir)

        self._write_version(output_dir, checkpoint_tag)
        return output_dir

    def unload_model(self):
        """Free GPU/MPS memory between sessions."""
        self.model = None
        self.tokenizer = None
        if self.device.type == "mps":
            torch.mps.empty_cache()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_device(self, preference: str) -> torch.device:
        if preference == "mps" and torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")

    def _load_base_model(self, model_id: str):
        from transformers import AutoModelForCausalLM

        # Try bf16 first (M4 native), fall back to fp32
        for dtype in [torch.bfloat16, torch.float32]:
            try:
                model = AutoModelForCausalLM.from_pretrained(
                    model_id,
                    torch_dtype=dtype,
                )
                model = model.to(self.device)
                logger.info("Loaded %s in %s on %s", model_id, dtype, self.device)
                return model
            except Exception as exc:
                logger.warning("Failed to load in %s: %s", dtype, exc)

        raise RuntimeError(f"Could not load base model {model_id}")

    def _load_corpus(self, corpus_path: Path) -> list[str]:
        texts = []
        if not corpus_path.exists():
            return texts
        for f in sorted(corpus_path.glob("*.txt")):
            raw = f.read_text(encoding="utf-8", errors="ignore").strip()
            if raw and self.ethics.is_safe(raw):
                texts.append(raw)
        logger.info("Loaded %d training texts from %s", len(texts), corpus_path)
        return texts

    def _find_latest_checkpoint(self) -> Optional[Path]:
        checkpoints = sorted(self.adapter_dir.glob("checkpoint_*"))
        return checkpoints[-1] if checkpoints else None

    def _write_version(self, ckpt_dir: Path, tag: str):
        import json
        from datetime import datetime, timezone
        (ckpt_dir / "version.json").write_text(json.dumps({
            "lens_name": self.lens_name,
            "checkpoint": tag,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }, indent=2))
