# PokerML demo

Run the full Texas Hold'em training demo:

```bash
python suitkaise-examples/pokerML/run_demo.py \
  --epochs 3 \
  --tables 6 \
  --players 6 \
  --hands 50 \
  --starting-stack 200 \
  --small-blind 1 \
  --big-blind 2 \
  --strength-samples 50 \
  --learning-rate 0.05 \
  --seed 42 \
  --run-name pokerml_run
```

Play the best model (with scenario prompts):

```bash
python suitkaise-examples/pokerML/run_demo.py --mode play --verbose
```

Outputs land in:

```
suitkaise-examples/pokerML/runs/<run_id>/
  state.bin
  state.json
  metrics.json
  tree.txt
```

Notes
- `--strength-samples` controls how realistic the hand-strength estimate is. Higher values are slower but more accurate.
- Increase `--hands` and `--epochs` for longer training runs.
