# Keepsake-Migration

Repository for **Keepsake in Every Hair ~ Migration**, an artwork by Sangjun Yoo in collaboration with Masayoshi Ishikawa.

---

## Two layers

This repository contains two distinct layers. They must not be confused.

### `artwork/` — The artwork itself

Six LoRA-adapted language model lenses, each fine-tuned on a different temporal register of Masayoshi Ishikawa's life trajectory. These run on 6 Raspberry Pi 5 devices during a six-week exhibition in Korea (May–June 2026). The trained adapter weights are what the artwork *is*.

→ See [`artwork/README.md`](artwork/README.md) for setup, ethics statement, and how to run.

### `helper/` — Private monitoring infrastructure (NOT artwork)

Flask status endpoints, a central dashboard, and drift measurement utilities used by the artist to verify the artwork's lenses are training correctly. Not exhibited. Not part of the artwork's conceptual frame.

→ See [`helper/README.md`](helper/README.md) for details.

---

The artwork can run without the helper. The helper only observes — it never modifies the artwork's behavior.
