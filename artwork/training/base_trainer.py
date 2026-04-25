import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class LensLoRATrainer:
    def __init__(self, lens_name: str, lens_config: dict, adapter_dir: Path):
        self.lens_name = lens_name
        self.lens_config = lens_config
        self.adapter_dir = Path(adapter_dir) / lens_name
        self.adapter_dir.mkdir(parents=True, exist_ok=True)
        self.model = None
        self.tokenizer = None

    def load_model(self):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import get_peft_model, LoraConfig, PeftModel, TaskType

        base_model_name = self.lens_config.get("base_model", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")
        lora_cfg = self.lens_config.get("lora", {})

        self.tokenizer = AutoTokenizer.from_pretrained(base_model_name)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        try:
            base_model = AutoModelForCausalLM.from_pretrained(base_model_name, torch_dtype="auto")
        except Exception:
            logger.warning("float16 load failed, falling back to float32")
            import torch
            base_model = AutoModelForCausalLM.from_pretrained(base_model_name, torch_dtype=torch.float32)

        checkpoint = self._find_latest_checkpoint()
        if checkpoint:
            logger.info(f"Loading existing adapter from {checkpoint}")
            self.model = PeftModel.from_pretrained(base_model, str(checkpoint), is_trainable=True)
        else:
            logger.info("No existing checkpoint found, creating new LoRA adapter")
            lora_config = LoraConfig(
                task_type=TaskType.CAUSAL_LM,
                r=lora_cfg.get("r", 8),
                lora_alpha=lora_cfg.get("alpha", 16),
                target_modules=lora_cfg.get("target_modules", ["q_proj", "v_proj"]),
                lora_dropout=lora_cfg.get("dropout", 0.05),
                bias="none",
            )
            self.model = get_peft_model(base_model, lora_config)

    def _find_latest_checkpoint(self) -> Optional[Path]:
        checkpoints = sorted(self.adapter_dir.glob("checkpoint_*"))
        return checkpoints[-1] if checkpoints else None

    def prepare_dataset(self, corpus_path: Path):
        from datasets import Dataset

        records = []
        for jsonl_file in sorted(Path(corpus_path).glob("*.jsonl")):
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))

        if not records:
            return None

        texts = [r["text"] for r in records]

        def tokenize(batch):
            return self.tokenizer(
                batch["text"],
                truncation=True,
                max_length=512,
                padding="max_length",
            )

        ds = Dataset.from_dict({"text": texts})
        ds = ds.map(tokenize, batched=True, remove_columns=["text"])
        ds = ds.map(lambda x: {"labels": x["input_ids"]})
        return ds

    def train_session(self, corpus_path: Path) -> Dict:
        from transformers import Trainer, TrainingArguments

        if self.model is None:
            self.load_model()

        dataset = self.prepare_dataset(corpus_path)
        if dataset is None or len(dataset) == 0:
            return {"status": "no_data", "checkpoint": None, "metadata": {}}

        learning_cfg = self.lens_config.get("learning", {})
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        checkpoint_dir = self.adapter_dir / f"checkpoint_{timestamp}"

        training_args = TrainingArguments(
            output_dir=str(checkpoint_dir),
            num_train_epochs=learning_cfg.get("max_epochs_per_session", 1),
            per_device_train_batch_size=learning_cfg.get("batch_size", 1),
            gradient_accumulation_steps=learning_cfg.get("gradient_accumulation", 4),
            learning_rate=learning_cfg.get("learning_rate", 5e-5),
            fp16=False,
            report_to="none",
            save_strategy="no",
            logging_steps=10,
        )

        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=dataset,
        )

        train_result = trainer.train()
        self.model.save_pretrained(str(checkpoint_dir))

        metadata = {
            "lens_name": self.lens_name,
            "timestamp": timestamp,
            "samples_seen": len(dataset),
            "epochs": learning_cfg.get("max_epochs_per_session", 1),
            "final_loss": train_result.training_loss,
        }
        with open(checkpoint_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Training completed: {checkpoint_dir}, loss={metadata['final_loss']:.4f}")
        return {
            "status": "completed",
            "checkpoint": str(checkpoint_dir),
            "metadata": metadata,
        }
