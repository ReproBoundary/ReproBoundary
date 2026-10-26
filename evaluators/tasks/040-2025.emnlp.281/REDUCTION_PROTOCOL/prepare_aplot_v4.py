#!/usr/bin/env python3
"""Apply two audited release repairs required to execute paper-faithful APLOT."""

import hashlib
import json
from pathlib import Path


trainer_path = Path("reward_models/aplot_trainer.py")
runner_path = Path("reward_models/run_aplot_reward_models_train.py")
trainer = trainer_path.read_text(encoding="utf-8")
runner = runner_path.read_text(encoding="utf-8")

old_forward = 'rewards = model(input_ids=inputs["input_ids"], attention_mask=inputs["attention_mask"])[0]'
new_forward = (
    'outputs = model(input_ids=inputs["input_ids"], attention_mask=inputs["attention_mask"], '
    'output_hidden_states=True, return_dict=True)\n        rewards = outputs.logits'
)
if old_forward in trainer:
    trainer = trainer.replace(old_forward, new_forward, 1)
old_loss = """            # adaptive margin loss
            loss = -nn.functional.logsigmoid(rewards_j - rewards_k - torch.sum(M1, -1)).mean()
            # aplot loss
            a = torch.ones(bsz//2, device=inputs[\"input_ids\"].device) / (bsz//2)
            b = torch.ones(bsz//2, device=inputs[\"input_ids\"].device) / (bsz//2)
            Gs1 = ot.sinkhorn(a, b, M1, 0.1)
            ot_cost = torch.sum(Gs1 * M1, -1)
            loss = -nn.functional.logsigmoid(rewards_j - rewards_k - ot_cost).mean()

        if return_outputs:
"""
new_loss = """            a = torch.ones(bsz//2, device=inputs[\"input_ids\"].device) / (bsz//2)
            b = torch.ones(bsz//2, device=inputs[\"input_ids\"].device) / (bsz//2)
            Gs1 = ot.sinkhorn(a, b, M1, 0.1)
            ot_cost = torch.sum(Gs1 * M1, -1)

        loss = -nn.functional.logsigmoid(rewards_j - rewards_k - ot_cost).mean()
        if return_outputs:
"""
if old_loss in trainer:
    trainer = trainer.replace(old_loss, new_loss, 1)
if "outputs = model(" not in trainer or "loss = -nn.functional.logsigmoid" not in trainer:
    raise SystemExit("APLOT trainer did not match the audited release")
trainer_path.write_text(trainer, encoding="utf-8")

if "from peft import LoraConfig" not in runner:
    runner = runner.replace("import torch.nn as nn\n", "import torch.nn as nn\nfrom peft import LoraConfig\n", 1)
if 'seed: Optional[int] = field(default=42)' not in runner:
    runner = runner.replace(
        'debug: Optional[bool] = field(default=False, metadata={\'help\': \'if debug=True, only train with 100 samples\'})',
        'debug: Optional[bool] = field(default=False, metadata={\'help\': \'if debug=True, only train with 100 samples\'})\n    seed: Optional[int] = field(default=42)',
        1,
    )
if "seed=script_args.seed," not in runner:
    runner = runner.replace("output_dir=os.path.join(output_name,),\n", "output_dir=os.path.join(output_name,),\n    seed=script_args.seed,\n", 1)
if '"peft_config": LoraConfig(' not in runner:
    runner = runner.replace(
        '"data_collator": RewardDataCollatorWithPadding(tokenizer=tokenizer, max_length=script_args.max_length),\n}',
        '"data_collator": RewardDataCollatorWithPadding(tokenizer=tokenizer, max_length=script_args.max_length),\n'
        '    "peft_config": LoraConfig(r=32, lora_alpha=64, lora_dropout=0.05, bias="none", task_type="SEQ_CLS"),\n}',
        1,
    )
if '"peft_config": LoraConfig(' not in runner or "seed=script_args.seed" not in runner:
    raise SystemExit("APLOT runner did not match the audited release")
runner_path.write_text(runner, encoding="utf-8")

payload = {
    "fixes": [
        "request and bind the model output used for semantic hidden states",
        "keep adaptive margin construction detached while restoring gradients through reward loss",
        "wire the paper-reported LoRA r=32, alpha=64, dropout=0.05",
        "expose and freeze the Trainer seed",
    ],
    "trainer_sha256": hashlib.sha256(trainer_path.read_bytes()).hexdigest(),
    "runner_sha256": hashlib.sha256(runner_path.read_bytes()).hexdigest(),
}
output = Path("artifacts/aplot-release-fixes.json")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2))
