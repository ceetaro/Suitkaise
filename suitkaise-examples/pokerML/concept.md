Texas Hold'em Poker ML demo (concept)

Goal
Create a runnable, real-world demo where multiple agents play Texas Hold'em in parallel, learn a simple policy, and share state. The demo should show every suitkaise feature in a believable workflow: web-like I/O, data processing, parallelization, circuit breaking, timing, and robust serialization, as well as file storage and lookup for model persistence

Program goal:
- a user gives a scenario (N $, hand, cards in center)
- AI is given state of scenario and outlines the most likely outcome after asking some clarifying questions
- gives recommendations for next actions and why

Audience outcome
- "I can build a real system with suitkaise."
- "This looks like real ML experimentation, not toy code."
- "I see why each module exists and how to use it."

Scope
- Keep the game loop lightweight and deterministic.
- Use a simplified evaluator (rank categories only) or a small lookup table; no heavy poker libraries.
- Keep training lightweight (frequency-based or tabular policy update).
- Use small, reproducible data sizes so the demo runs fast.

Texas Hold'em rules (compact)
- Each hand starts with two private hole cards per player.
- Five community cards are dealt in stages: flop (3), turn (1), river (1).
- Players form their best 5-card hand using any combination of hole + community cards.
- Betting rounds happen after each stage: pre-flop, flop, turn, river.
- Actions are fold, call/check, raise; the hand ends at showdown or when all but one fold.
- In this demo: keep blind sizes fixed, cap raises, and avoid complex side-pot logic.

What is machine learning, and how does it work? (plain language)
- Machine learning is a way to improve decisions by learning patterns from data.
- You start with a simple model that makes guesses (like which action to take).
- You run it, measure the outcome, and update the model to do better next time.
- Repeating this loop over many examples is called "training."
- In this demo, the model is a small table of action probabilities that shifts based on wins and losses.

Core flow
1) Configure experiment
   - Define run settings (num agents, hands per match, seeds, output paths).
   - Validate and normalize output folders with `paths`.
2) Simulate matches in parallel
   - Run batches of hands per worker process.
   - Use `Pool.unordered_imap` for fast return of results.
3) Aggregate stats + update policy
   - Compute win rates, action frequencies, and feature summary.
   - Update a tiny policy (e.g., action probabilities by hand strength).
4) Serialize and report
   - Save full run state with `cerial` and write a JSON snapshot.
   - Print timings, circuit status, and top metrics.

Feature mapping by module

timing
- `@timethis` on core phases: `deal_hand`, `evaluate_hand`, `choose_action`, `simulate_hand`.
- `TimeThis` around each match batch to show aggregate timing.
- `Sktimer` for overall training loop metrics (mean/median per epoch).

circuits
- `Circuit` to rate-limit "bad inputs" (invalid actions or corrupted hands).
- `BreakingCircuit` to halt an agent after repeated invalid moves or errors.
- Demonstrate `short()` on recoverable failures and `trip()` on critical issues.

paths
- Use `Skpath` to build `artifacts/`, `logs/`, and `results/`.
- Use `streamline_path` to sanitize run IDs.
- Use `is_valid_filename` to validate experiment names.
- Capture a tree snapshot with `get_formatted_project_tree()` at the end.

processing
- `Skprocess` for `MatchWorker` that simulates a fixed number of hands.
- `Pool.unordered_imap` to run multiple `MatchWorker` instances in parallel.
- `Share` to aggregate counters and timing across workers in real time.
- Use `tell()` to send per-hand summaries back to the parent for streaming metrics.

cerial
- Serialize a full `TournamentState` containing:
  - agent policies
  - win/loss counts
  - timing snapshots
  - error history and circuit trip counts
- Use `to_json()` to emit a readable debug snapshot.
- Use `debug=True` once to show error path reporting.

sk
- Decorate agent and simulator with `@sk` to get modifiers.
- Demonstrate `.retry()`, `.timeout()`, `.background()`, `.asynced()` on action selection.
- Print `.blocking_methods` to show detected blocking calls.

Texas Hold'em game model (simplified but real)
- Stages: pre-flop, flop, turn, river.
- Actions: fold, call, raise, check (discrete, small set).
- Hand strength: no evaluation. AIs figure out what hands are good and bad.
- pot logic: fixed blinds

Agent design
- Each agent has:
  - `policy`: mapping from (stage, strength_bucket, position) -> action probabilities.
  - `stats`: wins, losses, folds, raises, invalid actions.
  - `circuit`: `BreakingCircuit` to disable agent on repeated invalid outputs.
- Agents are updated after each epoch using observed outcomes.

Training loop
- For each epoch:
  - Run N matches in parallel using `Pool`.
  - Aggregate results into `Share` and local summary.
  - Update policies with a simple rule:
    - Increase probability of actions leading to positive outcomes.
    - Decay actions that correlate with losses.
  - Record timing and metrics.

Artifacts
- `artifacts/poker_run_<id>/`
  - `state.bin` (cerial serialized)
  - `state.json` (cerial IR as JSON)
  - `metrics.json` (summary metrics)
  - `tree.txt` (formatted project tree)
  - `errors.log` (if any)

Minimal CLI idea
- `python examples/pokerML/run_demo.py --agents 6 --epochs 5 --hands 200 --seed 42`

Success criteria
- Runs in under 30 seconds on a laptop.
- Uses every suitkaise module at least once.
- Clear output showing: win rates, timing stats, circuit events, and serialized state.

Possible stretch
- Add a "replay" mode that loads `state.bin` and prints a summary.
