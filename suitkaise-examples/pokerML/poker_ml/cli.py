from __future__ import annotations

# python imports
from typing import Optional, Any
import json
import random

# SUITKAISE IMPORTS
from suitkaise import cerial, paths

# example-specific imports
from .cards import Deck, format_cards, Card
from .policy import (
    PolicyTable, hand_strength_bucket, build_state_key, select_best_policy,
    estimate_win_rate, optimal_action, calculate_hand_potential, calculate_spr,
    calculate_position_value, calculate_implied_odds,
)
from .state import RunState


# card parsing (for scenario mode)
def _parse_cards(card_str: str) -> list:
    """parse "Ah Kd" into Card objects. supports various formats."""
    # rank -> internal value (2-14, ace high)
    rank_map = {
        '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
        'T': 10, 't': 10, '10': 10, 'J': 11, 'j': 11, 'Q': 12, 'q': 12,
        'K': 13, 'k': 13, 'A': 14, 'a': 14,
    }
    
    # suit -> internal letter (H, D, S, C)
    suit_map = {
        'h': 'H', 'H': 'H', 'd': 'D', 'D': 'D',
        's': 'S', 'S': 'S', 'c': 'C', 'C': 'C',
        '♥': 'H', '♦': 'D', '♠': 'S', '♣': 'C',
    }
    
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
def interactive_scenario_mode(best_policy_snapshot: dict, seed: int, strength_samples: int, verbose: bool) -> None:
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
        print(f"     Chance your hand wins at showdown right now.\n")
        
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


# print cli intro
def print_intro() -> None:

    print("\nPokerML - A suitkaise demo\n")
    print("This demo trains AI agents to play poker, showcasing suitkaise features:")
    print("  • Share - Cross-process shared memory for policies and stats")
    print("  • Pool - Parallel worker execution")
    print("  • Skprocess - Process lifecycle management")
    print("  • timing - Easy performance measurement")
    print("  • @sk.blocking - Async/background method wrappers")
    print("  • cerial - Serialization for saving state")
    print("")
    print("Target: ~80% accuracy (human-level). This is a demo, not a poker solver.")
    print("Higher accuracy is limited by state bucketing, not suitkaise.")
    print("")
    input("Press Enter to start...")


# choose mode based on cli input
def choose_mode(cli_mode: Optional[str]) -> str:

    if cli_mode:
        return cli_mode

    print("Choose a mode:")
    print("1) Train models from scratch")
    print("2) Play the best model")

    choice = input("> ").strip()
    if choice == "2":
        return "play"
    return "train"


# find latest run directory
def find_latest_run_dir() -> Optional[str]:
    runs_dir: Any = paths.Skpath("suitkaise-examples/pokerML/runs")  # type: ignore[call-arg]
    if not runs_dir.exists:  # type: ignore[attr-defined]
        return None
    candidates = sorted(
        [p for p in runs_dir.iterdir() if p.is_dir],
        key=lambda p: p.stat.st_mtime,  # type: ignore[attr-defined]
        reverse=True,
    )
    return candidates[0].ap if candidates else None


# find best run directory by best_policy_score (falls back to latest)
def find_best_run_dir() -> Optional[str]:
    runs_dir: Any = paths.Skpath("suitkaise-examples/pokerML/runs")  # type: ignore[call-arg]
    if not runs_dir.exists:  # type: ignore[attr-defined]
        return None
    
    def _score_from_run(run_path: Any) -> Optional[float]:
        metrics_path = run_path / "metrics.json"  # type: ignore[operator]
        if metrics_path.exists:  # type: ignore[attr-defined]
            try:
                with open(metrics_path.platform, "r") as f:
                    data = json.load(f)
                stats = data.get("stats", {})
                score = stats.get("best_policy_score", None)
                if score is not None:
                    return float(score)
            except Exception:
                pass
        
        state_json_path = run_path / "state.json"  # type: ignore[operator]
        if state_json_path.exists:  # type: ignore[attr-defined]
            try:
                with open(state_json_path.platform, "r") as f:
                    data = json.load(f)
                stats = data.get("stats", {})
                score = stats.get("best_policy_score", None)
                if score is not None:
                    return float(score)
            except Exception:
                pass
        
        state_path = run_path / "state.bin"  # type: ignore[operator]
        if state_path.exists:  # type: ignore[attr-defined]
            try:
                with open(state_path.platform, "rb") as f:
                    run_state: RunState = cerial.deserialize(f.read())
                return float(run_state.stats.get("best_policy_score", 0.0))
            except Exception:
                pass
        
        return None
    
    best_dir = None
    best_score = float("-inf")
    for run_path in runs_dir.iterdir():  # type: ignore[attr-defined]
        if not run_path.is_dir:
            continue
        score = _score_from_run(run_path)
        if score is None:
            continue
        if score > best_score:
            best_score = score
            best_dir = run_path.ap
    
    return best_dir or find_latest_run_dir()


# load run state from bin file
@paths.autopath()
def load_run_state(run_dir: Any) -> RunState:

    run_path: Any = run_dir if hasattr(run_dir, "__truediv__") else paths.Skpath(run_dir)  # type: ignore[arg-type]
    path = run_path / "state.bin"  # type: ignore[operator]

    with open(path.platform, "rb") as f:
        return cerial.deserialize(f.read())


# play the best model
def play_best_model(run_state: RunState, verbose: bool) -> None:

    # check if policies are available
    if not run_state.policies:
        print("No policies found to play.")
        return

    # prefer stored best policy from training stats
    stats = run_state.stats or {}
    best_id = stats.get("best_policy_id")
    stored_score = stats.get("best_policy_score")
    if isinstance(best_id, str) and best_id in run_state.policies:
        score = float(stored_score) if stored_score is not None else 0.0
    else:
        # fallback: re-score policies if no stored winner exists
        best_id, score = select_best_policy(
            run_state.policies,
            run_state.config.seed,
            run_state.config.strength_samples,
            50,
        )

    # print the best policy and score
    print(f"Best policy: {best_id} (score {score:.3f})")

    # run interactive scenario mode (same as training flow)
    interactive_scenario_mode(
        run_state.policies[best_id],
        run_state.config.seed,
        run_state.config.strength_samples,
        verbose,
    )


# prompt for scenario input
def _prompt_scenario(run_state: RunState) -> tuple[list[Card], list[Card], int, int, int]:

    print("Scenario input (press Enter for defaults):")
    stage = _prompt_int("Stage (0=preflop, 1=flop, 2=turn, 3=river)", 1)
    stack = _prompt_int("Stack size", run_state.config.starting_stack)
    
    bet_mode = getattr(run_state.config, "bet_mode", "blinds")
    ante = getattr(run_state.config, "ante", 0)
    if bet_mode == "ante":
        default_pot = max(0, ante * run_state.config.players_per_table)
        default_to_call = 0
    else:
        default_pot = max(0, run_state.config.small_blind + run_state.config.big_blind)
        default_to_call = max(0, run_state.config.big_blind)
    
    pot = _prompt_int("Pot size", default_pot)
    to_call = _prompt_int("To call", default_to_call)
    hole = _prompt_cards("Hole cards (e.g., As Kd)", 2)

    # get needed community cards based on stage
    needed = {0: 0, 1: 3, 2: 4, 3: 5}[stage]
    community = _prompt_cards(f"Community cards ({needed} cards)", needed) if needed else []

    # if no hole cards, deal from deck
    if not hole:
        deck = Deck(random.Random(run_state.config.seed))
        hole = deck.deal(2)
        community = deck.deal(needed)
    print(f"Using stack={stack}, pot={pot}, to_call={to_call}")
    return hole, community, pot, to_call, stage


# helper prompt for int input
def _prompt_int(label: str, default: int) -> int:
    
    raw = input(f"{label} [{default}]: ").strip()

    if not raw:
        return default

    try:
        return int(raw) 
    except ValueError:
        return default


# helper prompt for card input
def _prompt_cards(label: str, count: int) -> list[Card]:

    raw = input(f"{label}: ").strip()

    if not raw:
        return []
        
    # replace unneeded chars
    parts = raw.replace(",", " ").split()

    cards: list[Card] = []
    for part in parts:
        card = _parse_card(part)
        if card:
            cards.append(card)

    if count and len(cards) != count:
        return []

    return cards


# parse card input into Card object
def _parse_card(token: str) -> Card | None:

    token = token.strip()
    if len(token) < 2:
        return None

    # get rank and suit
    rank_str = token[:-1].upper()
    suit = token[-1].upper()
    rank_map = {"A": 14, "K": 13, "Q": 12, "J": 11, "T": 10}
    rank = rank_map.get(rank_str, None)

    if rank is None:
        try:
            rank = int(rank_str)
        except ValueError:
            return None

    if suit not in ("S", "H", "D", "C"):
        return None

    return Card(rank, suit)
