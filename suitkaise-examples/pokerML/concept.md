# PokerML

Create a program that trains AI for each scenario to show off suitkaise.

Obviously, all game states in Texas Hold'em can be mathematically calculated. We aren't trying to reinvent the wheel here.

What we are trying to do is create a simple, understandable ML model that can be trained to approximate these outcomes.

Similar real world models that use reward based systems can use this as somewhat of a template, and reference it for how to build their own.

It should show every module in suitkaise in real action.

Goal: Have trained models match the mathematical outcome for a given scenario and show how decision making changes based on chip count.

- a user gives a scenario (N $, hand, cards in center)
- AI is given state of scenario and outlines the most likely outcome after asking some clarifying questions
- gives recommendations for next actions and why

What the audience will learn
- how easy it is to build something real with suitkaise
- how clean the code is
- how flexible suitkaise is
- how suitkaise unlocks another level of parallel processing in python

Scope
- Only Texas Hold'em
- game: faithful to the core Texas Hold'em rules
- eval: action-based. rewards are based on money gained/lost. models update their decision chances based on the previous outcome.
- model goals at start: two axes: chip count and play style (aggressive vs conservative)

Technical scope
- data size doesn't matter - suitkaise makes it easy to handle data because we can use `Share` to share data between processes
- game loop is truthful to the actual Texas Hold'em rules
- 6 models play in each process, 6 total processes. winning policies are sent to shared memory. losing agents are replaced with winners from other processes.

Texas Hold'em rules
- Each hand starts with two private hole cards per player.
- Five community cards are dealt in stages: flop (3), turn (1), river (1).
- Players form their best 5-card hand using any combination of hole + community cards.
- Betting rounds happen after each stage: pre-flop, flop, turn, river.
- Actions are fold, call/check, raise; the hand ends at showdown or when all but one fold.
- Side pot logic included

What is machine learning, and how does it work? (plain language)
- Machine learning is a way to improve decisions by learning patterns from data.
- You start with a simple model that makes guesses (like which action to take).
- You run it, measure the outcome, and update the model to do better next time.
- Repeating this loop over many examples is called "training."

timing
- `@timethis` on core phases: `deal_hand`, `evaluate_hand`, `choose_action`, `simulate_hand`.
- `TimeThis` around each match batch to show aggregate timing.
- `Sktimer` for overall training loop metrics (mean/median, etc), since it powers the aforementioned features

circuits
- `Circuit` to rate-limit "bad inputs" (spamming actions).
- `BreakingCircuit` to halt an agent after repeated invalid moves or errors. That agent gets kicked out.
- Demonstrate `short()` on recoverable failures and `trip()` on critical issues.

paths
- Use `Skpath` to build `models/` and `results/`.
- Use `streamline_path` to sanitize run IDs.
- Use `is_valid_filename` to validate experiment names.
- Use `Skpath` equality to avoid duplicate entries in persistent data.
- Model names are `.id`s based on the file they are in

processing
- `Skprocess` for `Dealer` that runs the game loop
- `Share` to aggregate results and update model policies in real time
- `Pool.unordered_imap` to run multiple `Dealer` instances in parallel
- Use `tell()` and `listen()` for per process status updates and critical feedback

cerial
- Serializes everything we are doing
- we will be using a lot of complex types that can only be serialized with `cerial`

sk
- Decorate agent and simulator with `@sk` to get modifiers.
- Demonstrate `.retry()`, `.timeout()`, `.background()`, `.asynced()` on action selection.
- Print `.blocking_methods` to show detected blocking calls.

Texas Hold'em game model (simplified but real)
- Stages: pre-flop, flop, turn, river.
- Actions: fold, call, raise, all in (discrete, small set).
- Hand strength: built-in evaluation for winner determination and training baseline
- pot logic: fixed blinds and random unbalanced starting stacks, side pot logic included
- goal: agents should be able to identify the card order, and the hierarchy of possible hands, based on what they learn


