"""
PokerML main entry point - trains AI poker agents using suitkaise features.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import asyncio
import random
import os
import sys
from typing import Any, Optional

# suitkaise imports
from suitkaise import timing, cucumber, paths
from suitkaise.processing import Pool, Share

# pokerml imports
from .cli import print_intro, choose_mode, find_latest_run_dir, find_best_run_dir, load_run_state, play_best_model, interactive_scenario_mode
from .policy import (
    select_best_policy, rank_policies, build_state_key, PolicyTable, 
    hand_strength_bucket, calculate_hand_potential, calculate_spr,
    calculate_position_value, calculate_implied_odds, estimate_win_rate,
    optimal_action,
)
from .training import (
    evaluate_all_policies_parallel, evaluate_policies_simple, 
    EvaluatorWorker, EvalConfig, EvalResult, HAND_RANKINGS
)
from .agent import PokerAgent
from .state import RunConfig, RunState


# helpers

def _validate_run_name(name: str) -> str:
    """validate run name is safe for filesystem."""

    # check name doesn't have invalid chars (slashes, colons, etc)
    if not paths.is_valid_filename(name):
        raise ValueError(f"Invalid run name: {name}")

    # normalize whitespace and remove problematic chars
    return paths.streamline_path(name)


def _ensure_import_paths() -> None:
    """add project paths to sys.path so imports work from anywhere."""

    # resolve paths relative to this file using Skpath
    poker_dir = paths.Skpath(__file__).parent  # type: ignore[arg-type]
    project_root = poker_dir.parent.parent.parent  # type: ignore[union-attr]
    poker_path = str(poker_dir.parent)  # type: ignore[union-attr]
    root_path = str(project_root)

    # add to sys.path for this process
    if poker_path not in sys.path:
        sys.path.insert(0, poker_path)
    if root_path not in sys.path:
        sys.path.insert(0, root_path)

    # update PYTHONPATH for subprocesses
    current = os.environ.get("PYTHONPATH", "")
    parts = [p for p in current.split(os.pathsep) if p]
    if poker_path not in parts:
        parts.insert(0, poker_path)
    if root_path not in parts:
        parts.insert(0, root_path)
    os.environ["PYTHONPATH"] = os.pathsep.join(parts)


def _log_feature(verbose: bool, feature: str, detail: str) -> None:
    """log which suitkaise feature is being demonstrated."""
    if not verbose:
        return
    print(f"  → [{feature}] {detail}")


# card parsing (for scenario mode)

def _parse_cards(card_str: str) -> list:
    """parse "Ah Kd" into Card objects. supports various formats."""
    from .cards import Card
    
    # rank -> internal value (2-14, ace high)
    rank_map = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 
                'T': 10, 't': 10, '10': 10, 'J': 11, 'j': 11, 'Q': 12, 'q': 12, 
                'K': 13, 'k': 13, 'A': 14, 'a': 14}
    
    # suit -> internal letter (H, D, S, C)
    suit_map = {'h': 'H', 'H': 'H', 'd': 'D', 'D': 'D',
                's': 'S', 'S': 'S', 'c': 'C', 'C': 'C',
                '♥': 'H', '♦': 'D', '♠': 'S', '♣': 'C'}
    
    cards = []
    parts = card_str.strip().split()
    
    for part in parts:
        if not part or len(part.strip()) < 2:
            continue
        part = part.strip()
            
        # handle "10*" specially (3 chars)
        if part.startswith('10'):
            rank_str, suit_str = '10', part[2:]
        else:
            rank_str, suit_str = part[:-1], part[-1]
        
        # only add if valid
        if rank_str in rank_map and suit_str in suit_map:
            cards.append(Card(rank_map[rank_str], suit_map[suit_str]))
            
    return cards


# interactive scenario mode

def _interactive_scenario_mode(best_policy_snapshot: dict, seed: int, strength_samples: int, verbose: bool) -> None:
    """let user test trained model with custom poker scenarios."""
    print("\n" + "═" * 50)
    print("🎮 Interactive Scenario Mode")
    print("═" * 50)
    print("   Configure a poker scenario and the trained model will suggest an action.")
    print("   Type 'quit' or 'q' to exit.\n")
    
    # load the best policy into a PolicyTable
    rng = random.Random(seed)
    policy = PolicyTable(["fold", "call", "raise", "all_in"], rng)
    policy.load_snapshot(best_policy_snapshot)
    
    stage_names = {0: "Pre-flop", 1: "Flop", 2: "Turn", 3: "River"}
    position_names = {
        0: "Small Blind",
        1: "Big Blind", 
        2: "Under the Gun",
        3: "Middle Position",
        4: "Cutoff",
        5: "Dealer Button",
    }
    
    while True:
        print("─" * 40)
        print("Enter your scenario (or 'quit' to exit):\n")
        
        # get hole cards
        hole_input = input("   Your hole cards (e.g., 'Ah Kd'): ").strip()
        if hole_input.lower() in ('quit', 'q', 'exit'):
            break
        hole_cards = _parse_cards(hole_input)
        if len(hole_cards) != 2:
            print("   ❌ Please enter exactly 2 hole cards (e.g., 'Ah Kd')")
            continue
        
        # get community cards
        community_input = input("   Community cards (e.g., '7h 8h 9c' or empty for pre-flop): ").strip()
        if community_input.lower() in ('quit', 'q', 'exit'):
            break
        community_cards = _parse_cards(community_input) if community_input else []
        if len(community_cards) not in (0, 3, 4, 5):
            print("   ❌ Community cards must be 0 (pre-flop), 3 (flop), 4 (turn), or 5 (river)")
            continue
        
        # determine stage
        if len(community_cards) == 0:
            stage = 0
        elif len(community_cards) == 3:
            stage = 1
        elif len(community_cards) == 4:
            stage = 2
        else:
            stage = 3
        
        # ask if playing blinds or ante
        game_type = input("   Forced bets (blinds or ante) [blinds]: ").strip().lower() or "blinds"
        using_blinds = game_type.startswith("b")
        
        # get position (only for blinds)
        if using_blinds:
            print("   Position options:")
            print("     0 = Small Blind (forced bet, first after flop)")
            print("     1 = Big Blind (forced bet, second after flop)")
            print("     2 = Under the Gun (first to act pre-flop)")
            print("     3 = Middle Position")
            print("     4 = Cutoff (one seat before dealer)")
            print("     5 = Dealer Button (last to act, best position)")
            try:
                position = int(input("   Your position (default 3): ").strip() or "3")
                position = max(0, min(5, position))
            except ValueError:
                position = 3
            position_label = position_names.get(position, str(position))
        else:
            position = 3
            position_label = "No position (ante)"
        
        # get forced bet amounts to set reasonable defaults
        if using_blinds:
            try:
                small_blind = int(input("   Small blind (default 1): ").strip() or "1")
            except ValueError:
                small_blind = 1
            try:
                big_blind = int(input("   Big blind (default 2): ").strip() or "2")
            except ValueError:
                big_blind = 2
            default_pot = max(0, small_blind + big_blind)
            default_to_call = max(0, big_blind)
        else:
            try:
                ante = int(input("   Ante amount (default 1): ").strip() or "1")
            except ValueError:
                ante = 1
            try:
                players = int(input("   Number of players (default 6): ").strip() or "6")
                players = max(2, players)
            except ValueError:
                players = 6
            default_pot = max(0, ante * players)
            default_to_call = 0
        
        # get stack size
        try:
            stack = int(input("   Your stack size (default 200): ").strip() or "200")
        except ValueError:
            stack = 200
        
        # get pot size
        try:
            pot = int(input(f"   Current pot size (default {default_pot}): ").strip() or str(default_pot))
        except ValueError:
            pot = default_pot
        
        # get to_call amount
        try:
            to_call = int(input(f"   Amount to call (default {default_to_call}): ").strip() or str(default_to_call))
        except ValueError:
            to_call = default_to_call
        
        # calculate all factors
        win_prob = estimate_win_rate(hole_cards, community_cards, rng, strength_samples)
        pot_odds = 0.0 if to_call == 0 else to_call / max(pot + to_call, 1)
        hand_potential = calculate_hand_potential(hole_cards, community_cards, rng, strength_samples)
        spr = calculate_spr(stack, pot)
        position_value = calculate_position_value(position, 6) if using_blinds else 0.5
        implied_odds = calculate_implied_odds(win_prob, hand_potential, spr, to_call, pot)
        hand_bucket = hand_strength_bucket(hole_cards, community_cards, rng, strength_samples)
        
        # get optimal action (what "perfect" play would be)
        optimal = optimal_action(
            win_prob=win_prob,
            pot_odds=pot_odds,
            stack=stack,
            to_call=to_call,
            hand_potential=hand_potential,
            spr=spr,
            position_value=position_value,
            implied_odds=implied_odds,
        )
        
        # build state key and get model's learned action
        state_key = build_state_key(stage, position, stack, pot, to_call, hand_bucket, 1)
        model_action = policy.choose_action(state_key)
        
        # display result
        hole_str = " ".join(f"{c}" for c in hole_cards)
        community_str = " ".join(f"{c}" for c in community_cards) if community_cards else "(none)"
        
        # helper for consistent box rows (44 dashes = 44 inner visual width)
        # format: "│ " + text + "│" means inner = 1 + text_width
        # non-emoji: 1 + 43 = 44 visual
        # emoji: 1 + 42 chars = 43 chars, but emoji adds +1 visual = 44 visual
        def row(text: str, emoji: bool = False) -> str:
            width = 42 if emoji else 43
            return f"   │ {text:<{width}}│"
        
        print(f"\n   ┌{'─' * 44}┐")
        print(row("📊 Scenario Analysis", emoji=True))
        print(f"   ├{'─' * 44}┤")
        print(row(f"Stage: {stage_names[stage]}"))
        print(row(f"Position: {position_label}"))
        print(row(f"Hole cards: {hole_str}"))
        print(row(f"Community: {community_str}"))
        print(row(f"Stack: {stack}"))
        print(row(f"Pot: {pot}"))
        print(row(f"To call: {to_call}"))
        print(f"   └{'─' * 44}┘")
        
        # explain the analysis factors
        print(f"\n   📈 Analysis Factors (what the model considers):\n")
        print(f"   • Win probability: {win_prob*100:.1f}%")
        print(f"     How often you'd win if all cards were dealt now.")
        print(f"     Calculated by simulating many random opponent hands.\n")
        
        print(f"   • Hand potential: {hand_potential*100:.1f}%")
        print(f"     How likely your hand will improve on future cards.")
        print(f"     High with draws (flush/straight possibilities).\n")
        
        print(f"   • Pot odds: {pot_odds*100:.1f}%")
        print(f"     The cost to call vs what you can win: {to_call} / ({pot} + {to_call}).")
        print(f"     You need win% > pot odds% for a profitable call.\n")
        
        print(f"   • Stack-to-pot ratio (SPR): {spr:.1f}x")
        print(f"     How many pots you have left: {stack} / {pot}.")
        print(f"     Low SPR (<4) = commit easier. High SPR (>10) = be cautious.\n")
        
        print(f"   • Implied odds: {implied_odds:.2f}x")
        print(f"     Expected future winnings if you hit your hand.")
        print(f"     Higher when opponent is likely to pay you off.\n")
        
        print(f"   • Position value: {position_value*100:.1f}%")
        print(f"     Advantage from acting later (seeing others act first).")
        print(f"     Dealer Button = 100%, Blinds = low.\n")
        
        # recommendations box using same helper
        print(f"   ┌{'─' * 44}┐")
        print(row("🎯 Recommendations", emoji=True))
        print(f"   ├{'─' * 44}┤")
        print(row(f"Optimal play: {optimal.upper()}"))
        print(row(f"Model suggests: {model_action.upper()}"))
        if model_action == optimal:
            print(f"   │{'✓ Match!':^44}│")
        else:
            print(f"   │{'✗ Differs':^44}│")
        print(f"   └{'─' * 44}┘\n")
    
    print("\nPokerML ended")


# main entry point

def main() -> None:
    """main training loop - demonstrates suitkaise features while training poker agents.
    This is a demo, not a production poker AI."""
    
    # ensure imports work from any directory
    _ensure_import_paths()
    
    # parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, choices=["train", "play"], default=None)
    parser.add_argument("--run-dir", type=str, default=None)
    parser.add_argument("--verbose", action="store_true", default=True)
    parser.add_argument("--quiet", action="store_true", help="Disable verbose output")
    parser.add_argument("--no-wait", action="store_true")
    parser.add_argument("--no-interactive", action="store_true", help="Skip interactive scenario mode after training")
    parser.add_argument("--epochs", type=int, default=None, help="Max epochs (default: unlimited, trains until target score)")
    parser.add_argument("--target-score", type=float, default=0.80, help="Stop training when best model reaches this score (default 0.90 = human-level)")
    parser.add_argument("--tables", type=int, default=6)
    parser.add_argument("--players", type=int, default=6)
    parser.add_argument("--starting-stack", type=int, default=200)
    parser.add_argument("--bet-mode", type=str, choices=["blinds", "ante"], default="blinds")
    parser.add_argument("--ante", type=int, default=0, help="Forced ante per player (0 = no ante)")
    parser.add_argument("--small-blind", type=int, default=1)
    parser.add_argument("--big-blind", type=int, default=2)
    parser.add_argument("--strength-samples", type=int, default=50)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--run-name", type=str, default="pokerml_run")
    args = parser.parse_args()
    if args.quiet:
        args.verbose = False
    
    bet_mode = "ante" if args.bet_mode == "ante" else "blinds"
    if bet_mode == "ante" and args.ante <= 0:
        args.ante = max(1, args.small_blind)

    # show intro and choose mode
    if not args.no_wait:
        print_intro()

    mode = choose_mode(args.mode)
    
    # if play mode, load existing run and play
    if mode == "play":
        run_dir = args.run_dir or find_best_run_dir()
        if not run_dir:
            raise ValueError("No run directory found. Train models first or pass --run-dir.")
        if args.verbose:
            print(f"Using run: {run_dir}")
        run_state = load_run_state(run_dir)
        play_best_model(run_state, args.verbose)
        return

    # create run directory using Skpath
    run_name = _validate_run_name(args.run_name)
    run_id = paths.streamline_path(f"{run_name}_{int(timing.time())}")
    run_dir: Any = paths.Skpath("suitkaise-examples/pokerML/runs") / run_id  # type: ignore[call-arg,operator]
    run_dir.mkdir(parents=True, exist_ok=True)  # type: ignore[attr-defined]
    if args.verbose:
        print(f"\n📁 Setting up run directory...")
    _log_feature(args.verbose, "paths.Skpath", f"Created {run_dir.ap}")

    # create shared memory for cross-process communication
    if args.verbose:
        print(f"\n🔗 Creating shared memory for cross-process communication...")
    share: Any = Share()
    share.stats = {"hands": 0, "wins": 0}
    share.policies = {}
    _log_feature(args.verbose, "processing.Share", "Stats and policies now accessible across all worker processes")

    # start training timer
    if args.verbose:
        print(f"\n⏱️  Starting training timer...")
    start_time = timing.time()
    overall_timer: Any = timing.Sktimer()
    overall_timer.start()  # type: ignore[attr-defined]
    _log_feature(args.verbose, "timing.Sktimer", "Tracking total training duration")

    # create worker pool for parallel execution
    if args.verbose:
        print(f"\n👥 Spawning worker pool for parallel table execution...")
    pool: Any = Pool(args.tables)  # type: ignore[call-arg]
    _log_feature(args.verbose, "processing.Pool", f"{args.tables} worker processes ready to run poker tables in parallel")

    if args.verbose:
        print(f"\n🧪 Running demo of suitkaise features before training...\n")
        
        print("   Demonstrating @blocking decorator:")
        print(f"   Methods marked as blocking on PokerAgent: {PokerAgent.blocking_methods}")
        _log_feature(args.verbose, "sk.blocking", "Automatically detects slow/IO-bound methods for async handling")

        demo_agent = PokerAgent("demo", random.Random(args.seed), 0.5)
        demo_pot = args.ante * args.players if bet_mode == "ante" else args.big_blind * 2
        demo_to_call = 0 if bet_mode == "ante" else args.big_blind
        demo_min_raise = max(1, args.ante) if bet_mode == "ante" else args.big_blind
        demo_key = build_state_key(1, 0, args.starting_stack, demo_pot, demo_to_call, 2, 1)
        
        print("\n   Demonstrating .background() - run blocking code in a thread:")
        future = demo_agent.choose_action.background()(
            demo_key,
            args.starting_stack,
            demo_to_call,
            demo_pot,
            demo_min_raise,
        )
        _ = future.result()
        _log_feature(args.verbose, "sk.background", "Blocking method ran in background thread, returned Future")

        print("\n   Demonstrating .asynced() - convert blocking code to async:")
        async def _demo_async():
            await demo_agent.choose_action.asynced()(
                demo_key,
                args.starting_stack,
                demo_to_call,
                demo_pot,
                demo_min_raise,
            )

        asyncio.run(_demo_async())
        _log_feature(args.verbose, "sk.asynced", "Blocking method awaited as native coroutine")

        print("\n   Demonstrating Skprocess - run code in separate process:")
        demo_share: Any = Share()
        demo_share.policies = {"demo_agent": demo_agent.policy.snapshot()}
        demo_share.eval_results = {}
        demo_worker = EvaluatorWorker(
            demo_share,
            EvalConfig(
                worker_id=0,
                num_workers=1,
                num_models=1,
                base_stack=args.starting_stack,
                samples=5,
                seed=args.seed + 999,
            ),
        )
        demo_worker.start()  # type: ignore[attr-defined]
        _log_feature(args.verbose, "processing.Skprocess", "EvaluatorWorker spawned in isolated process")
        status = demo_worker.listen(timeout=2.0)  # type: ignore[attr-defined]
        if status:
            print(f"   Received message from child process: {status}")
            _log_feature(args.verbose, "processing.listen", "Parent received status from child via IPC")
        demo_worker.stop()  # type: ignore[attr-defined]
        demo_worker.wait()  # type: ignore[attr-defined]
        _log_feature(args.verbose, "processing.Skprocess", "Process gracefully stopped and joined")

    epoch_limit_str = str(args.epochs) if args.epochs else "∞"
    total_agents = args.tables * args.players
    if args.verbose:
        print(f"\n{'═' * 65}")
        print(f"  🎰 POKERML TRAINING")
        print(f"{'═' * 65}")
        print(f"""
  Training {total_agents} agents to play poker.

  This is by no means a perfect poker model trainer.

  It is to show you the features that suitkaise can offer.
  
  Our target is {args.target_score:.0%} accuracy (about as good as the average human player, probably).
  We are using state bucketing, so accuracy will not be super precise.
  Different textures can require different actions for the same hand strength.

  I made this with the help of an AI so that my machine learning actually works.

  It took me maybe an hour to get a running model with suitkaise, and the AI understood
  it very well based on the site content/docs. So I hope you have the same experience.

  It would take me days to replicate this to this technical level without suitkaise, 
  even if I could use an AI.

  Here's what happens each epoch (training iteration):

  ┌─ PHASE 1: EVALUATE ALL 169 CANONICAL HANDS ───────────────────┐
  │                                                               │
  │  "Canonical" means suit-independent: Ah Kh and As Ks are both │
  │  just "AKs" (ace-king suited). This gives 169 unique hands:   │
  │  13 pairs + 78 suited + 78 offsuit.                           │
  │                                                               │
  │  Each agent plays all 169. For each hand, at each stage       │
  │  (pre-flop, flop, turn, river):                               │
  │                                                               │
  │  • Community cards are randomly generated                     │
  │  • Agent chooses an action (fold/call/raise/all-in)           │
  │  • We compare to the mathematically optimal action            │
  │  • Agent's policy weights update based on correctness         │
  │                                                               │
  │  Community cards change each epoch, so agents see the same    │
  │  hole cards in different board contexts over time.            │
  │                                                               │
  │  Once ALL agents master a hand, it's removed from future      │
  │  epochs to speed up training.                                 │
  │                                                               │
  └───────────────────────────────────────────────────────────────┘

  ┌─ PHASE 2: SELECTION ──────────────────────────────────────────┐
  │                                                               │
  │  The top 25% of agents survive. The bottom 75% are replaced   │
  │  with mutated copies of winners. This creates evolutionary    │
  │  pressure toward better play.                                 │
  │                                                               │
  │  We track the global best policy across ALL epochs, so a      │
  │  good policy found early won't be lost to random variance.    │
  │                                                               │
  │  Updated policies sync via suitkaise's Share, so the next     │
  │  epoch starts with improved agents.                           │
  │                                                               │
  └───────────────────────────────────────────────────────────────┘

  Config: {total_agents} agents | Stack: {args.starting_stack} chips
  Hands per epoch: 169 canonical | Max epochs: {epoch_limit_str}
""")
        print(f"{'═' * 65}\n")

    # initialize training state
    epoch = 0
    best_score = 0.0
    
    # track global best policy across ALL epochs (hall of fame)
    global_best_policy: dict = {}
    global_best_score: float = 0.0
    global_best_epoch: int = 0
    global_best_id: str = ""
    
    # create initial agent population
    if args.verbose:
        print(f"\n🤖 Initializing {total_agents} agents...")
    init_policies = {}
    for agent_idx in range(total_agents):
        agent_id = f"agent_{agent_idx}"
        agent_rng = random.Random(args.seed + agent_idx)
        agent = PokerAgent(agent_id, agent_rng, args.learning_rate)
        init_policies[agent_id] = agent.policy.snapshot()

    # assign full dict at once for Share to sync correctly
    share.policies = init_policies
    _log_feature(args.verbose, "processing.Share", f"{len(init_policies)} agent policies stored in shared memory")
    
    # track mastered hands (all agents got these right - skip in future)
    mastered_hands: set = set()
    total_possible_hands = 169
    

    # training loop

    while best_score < args.target_score:
        # check if we've hit max epochs
        if args.epochs and epoch >= args.epochs:
            if args.verbose:
                print(f"\nReached max epochs ({args.epochs}) without hitting target score.")
            break
        
        # each epoch gets a different seed = different community cards
        epoch_seed = args.seed + epoch * 1000
        if args.verbose:
            print(f"\n━━━ Epoch {epoch + 1} (best: {global_best_score:.3f} @ epoch {global_best_epoch} / target: {args.target_score:.2f}) ━━━")
        
        # phase 1: evaluate all agents on all hands
        with timing.TimeThis() as epoch_timer:
            _log_feature(args.verbose, "timing.TimeThis", "Auto-timing this epoch with context manager")
            
            # get current policies from shared memory
            current_policies = dict(share.policies)
            remaining_hands = total_possible_hands - len(mastered_hands)
            if args.verbose:
                print(f"   Evaluating {remaining_hands} remaining hands ({len(mastered_hands)} mastered, skipped)...")
            
            # run evaluation - community cards regenerated each epoch
            # policies learn during eval (online learning)
            precision_mode = best_score >= max(0.0, args.target_score - 0.05)
            eval_samples = max(10, args.strength_samples // 3)
            variations_per_hand = 2
            if precision_mode:
                # boost signal when we're close to target to avoid noisy plateau
                eval_samples = max(eval_samples, args.strength_samples)
                variations_per_hand = 3
            eval_result = evaluate_policies_simple(
                policies=current_policies,
                seed=epoch_seed,
                base_stack=args.starting_stack,
                samples=eval_samples,
                variations_per_hand=variations_per_hand,
                learn=True,
                mastered_hands=mastered_hands,
            )
            
            # unpack results
            scores_dict = eval_result.scores
            learned_policies = eval_result.learned_policies
            
            # add newly mastered hands to skip set
            if eval_result.newly_mastered:
                mastered_hands.update(eval_result.newly_mastered)
                if args.verbose:
                    print(f"   🎯 Mastered {len(eval_result.newly_mastered)} new hands! Total: {len(mastered_hands)}/{total_possible_hands}")
            
            # update stats in shared memory
            stats = share.stats
            stats["hands"] = stats.get("hands", 0) + eval_result.total_hands * len(share.policies) * 2
            stats["mastered_hands"] = len(mastered_hands)
            share.stats = stats
        
        _log_feature(args.verbose, "processing.Pool", f"Evaluated {eval_result.total_hands} hands for {len(share.policies)} agents")
        
        stats = share.stats
        stats["last_epoch_seconds"] = epoch_timer.most_recent  # type: ignore[attr-defined]
        share.stats = stats
        if args.verbose:
            print(f"   ✓ Evaluation complete in {epoch_timer.most_recent:.2f}s")

        # phase 2: selection - rank policies and evolve population
        if scores_dict:
            # use LEARNED policies (weights updated during eval) for scoring
            policy_scores = [
                (agent_id, score, learned_policies.get(agent_id) or share.policies.get(agent_id) or {})
                for agent_id, score in scores_dict.items()
                if agent_id in share.policies
            ]
            policy_scores.sort(key=lambda x: x[1], reverse=True)
            
            if not policy_scores:
                if args.verbose:
                    print("   ⚠️ No scored policies, skipping selection...")
                epoch += 1
                continue
            
            best_epoch_score = policy_scores[0][1]
            
            # update global best if this epoch produced a better policy
            if best_epoch_score > global_best_score:
                global_best_score = best_epoch_score
                global_best_policy = policy_scores[0][2].copy()
                global_best_epoch = epoch + 1
                global_best_id = policy_scores[0][0]
                stats = share.stats
                stats["wins"] = stats.get("wins", 0) + 1
                share.stats = stats
                if args.verbose:
                    print(f"   🌟 NEW GLOBAL BEST! {global_best_id}: {global_best_score:.1%}")
            
            # keep top 1/4 as winners
            top_count = max(1, len(policy_scores) // 4)
            winners = policy_scores[:top_count]
            
            if args.verbose:
                print(f"   Epoch best: {policy_scores[0][0]} ({best_epoch_score:.1%}) | Global best: {global_best_id} ({global_best_score:.1%})")
                print(f"   Keeping top {top_count}, replacing {len(policy_scores) - top_count} underperformers...")
            
            # always include the global best in the winner pool
            winners_snapshots = {agent_id: snap for agent_id, _, snap in winners}
            if global_best_id and global_best_policy:
                winners_snapshots["_global_best_"] = global_best_policy
            
            # mutation parameters - tuned for exploration
            MUTATION_CHANCE = 0.4           # base chance winner mutates
            RADICAL_MUTATION_CHANCE = 0.15  # chance of large mutation
            RANDOM_POLICY_CHANCE = 0.05     # base chance of fresh random policy
            SMALL_MUTATION_RANGE = 0.1      # ±10% weight adjustment
            RADICAL_MUTATION_RANGE = 0.3    # ±30% weight adjustment

            # increase mutation pressure as we approach the target score
            if args.target_score > 0:
                proximity = min(1.0, max(0.0, global_best_score / args.target_score))
            else:
                proximity = 0.0
            mutation_chance = min(0.9, MUTATION_CHANCE + 0.3 * proximity)
            fresh_policy_chance = min(0.2, RANDOM_POLICY_CHANCE + 0.1 * proximity)
            
            def mutate_policy(policy: dict, radical: bool = False) -> dict:
                """apply random mutations to policy weights."""
                mutated = {}
                mutation_range = RADICAL_MUTATION_RANGE if radical else SMALL_MUTATION_RANGE
                for key, weights in policy.items():
                    mutated[key] = [
                        max(0.01, w + random.uniform(-mutation_range, mutation_range))
                        for w in weights
                    ]
                return mutated
            
            def fresh_policy() -> dict:
                """create completely random policy for exploration."""
                fresh_agent = PokerAgent(f"fresh_{epoch}", random.Random(), args.learning_rate)
                return fresh_agent.policy.snapshot()
            
            # build new population with mutations
            new_policies = {}
            mutations_applied = 0
            fresh_injected = 0
            
            for agent_id in share.policies.keys():
                # small chance of completely fresh random policy
                if random.random() < fresh_policy_chance:
                    new_policies[agent_id] = fresh_policy()
                    fresh_injected += 1
                elif agent_id in winners_snapshots:
                    # winners: keep but maybe mutate
                    policy = winners_snapshots[agent_id].copy()
                    if random.random() < mutation_chance:
                        radical = random.random() < RADICAL_MUTATION_CHANCE
                        policy = mutate_policy(policy, radical)
                        mutations_applied += 1
                    new_policies[agent_id] = policy
                else:
                    # losers: replace with mutated copy of random winner
                    replacement = random.choice(list(winners_snapshots.values())).copy()
                    radical = random.random() < RADICAL_MUTATION_CHANCE
                    new_policies[agent_id] = mutate_policy(replacement, radical)
                    mutations_applied += 1
            
            # always preserve ONE pure copy of global best (no mutation)
            if global_best_id and global_best_policy:
                new_policies[global_best_id] = global_best_policy.copy()
            
            # sync new policies to shared memory
            share.policies = new_policies
            mutation_msg = f"{mutations_applied} mutations"
            if fresh_injected:
                mutation_msg += f", {fresh_injected} fresh"
            _log_feature(args.verbose, "processing.Share", f"Updated policies ({mutation_msg})")
        
        # Use global best score for termination check
        best_score = global_best_score
        epoch += 1
    

    # training completed

    total_epochs = epoch

    # stop timer
    overall_timer.stop()  # type: ignore[attr-defined]
    end_time = timing.time()
    _log_feature(args.verbose, "timing.Sktimer", "Training timer stopped")

    # use the global best policy tracked across all epochs
    best_id = global_best_id
    best_score = global_best_score
    
    if args.verbose:
        print(f"\nBest policy from all {total_epochs} epochs:")
        print(f"   Winner: {best_id} with score {best_score:.3f} (found at epoch {global_best_epoch})")
    
    # make sure the global best is in the final policies
    if global_best_policy:
        policies = share.policies
        policies[best_id] = global_best_policy
        share.policies = policies
    
    # record final stats
    stats = share.stats
    stats["best_policy_id"] = best_id
    stats["best_policy_score"] = best_score
    stats["best_policy_epoch"] = global_best_epoch
    share.stats = stats

    # build run state for saving
    config = RunConfig(
        epochs=total_epochs,
        tables=args.tables,
        players_per_table=args.players,
        hands_per_epoch=169, 
        starting_stack=args.starting_stack,
        small_blind=args.small_blind,
        big_blind=args.big_blind,
        strength_samples=args.strength_samples,
        learning_rate=args.learning_rate,
        seed=args.seed,
        bet_mode=bet_mode,
        ante=args.ante,
    )

    run_state = RunState(
        config=config,
        stats=share.stats,
        policies=share.policies,
        started_at=start_time,
        finished_at=end_time,
    )

    # save run state to disk using cucumber
    if args.verbose:
        print(f"\n💾 Saving run state to disk...")

    # save as compact binary
    state_bytes = cucumber.serialize(run_state)
    _log_feature(args.verbose, "cucumber.serialize", "Converted RunState dataclass to compact binary format")
    state_path = run_dir / "state.bin"  # type: ignore[operator]
    with open(state_path.platform, "wb") as f:
        f.write(state_bytes)

    # save as human-readable json
    state_json = cucumber.to_json(run_state)  # type: ignore[attr-defined]
    _log_feature(args.verbose, "cucumber.to_json", "Converted RunState to human-readable JSON")
    with open((run_dir / "state.json").platform, "w") as f:  # type: ignore[operator]
        f.write(state_json)

    # save metrics as standard json
    with open((run_dir / "metrics.json").platform, "w") as f:  # type: ignore[operator]
        json.dump(dataclasses.asdict(run_state), f, indent=2)

    # cleanup shared memory
    if args.verbose:
        print(f"\nCleaning up shared memory...")
    share.exit()  # type: ignore[attr-defined]
    _log_feature(args.verbose, "processing.Share", "Released shared memory and stopped background coordinator")

    # step 16: print final summary
    print("\n" + "═" * 50)
    print("PokerML training complete!")
    print("═" * 50)
    stats = share.stats
    print(f"Run saved to: {run_dir.ap}")
    print(f"Total hands played: {stats['hands']}")
    print(f"New global bests: {stats['wins']}")
    print(f"Best policy: {best_id} (score {best_score:.1%})")
    print(f"Hands mastered: {len(mastered_hands)}/{total_possible_hands} ({100*len(mastered_hands)/total_possible_hands:.1f}%)")
    print(f"Epochs trained: {total_epochs}")
    print(f"Total time: {overall_timer.most_recent:.2f}s")  # type: ignore[attr-defined]
    print("═" * 50)

    # clean empty run dirs
    runs_dir = paths.Skpath("suitkaise-examples/pokerML/runs")
    if runs_dir.exists:
        for path in runs_dir.iterdir():
            if path.name.startswith("pokerml_run") and path.is_dir and path.is_empty:
                path.rmdir()

    # launch interactive scenario mode
    if not args.no_interactive:
        interactive_scenario_mode(share.policies[best_id], args.seed, args.strength_samples, args.verbose)
