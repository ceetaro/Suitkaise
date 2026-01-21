from __future__ import annotations

# python imports
from typing import Optional, Any
import random

# SUITKAISE IMPORTS
from suitkaise import cerial, paths

# example-specific imports
from .cards import Deck, format_cards, Card
from .policy import PolicyTable, hand_strength_bucket, build_state_key, select_best_policy, estimate_win_rate, optimal_action
from .state import RunState


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
    candidates = sorted([p for p in runs_dir.iterdir() if p.is_dir], key=lambda p: p.stat().st_mtime, reverse=True)  # type: ignore[attr-defined]
    return candidates[0].ap if candidates else None


# load run state from bin file
@paths.autopath()
def load_run_state(run_dir: str) -> RunState:

    path = run_dir / "state.bin"

    with open(path.platform, "rb") as f:
        return cerial.deserialize(f.read())


# play the best model
def play_best_model(run_state: RunState, verbose: bool) -> None:

    # check if policies are available
    if not run_state.policies:
        print("No policies found to play.")
        return

    # select the best policy
    best_id, score = select_best_policy(
        run_state.policies,
        run_state.config.seed,
        run_state.config.strength_samples,
        50,
    )

    # print the best policy and score
    print(f"Best policy: {best_id} (score {score:.3f})")

    # create Policy table with random seed and load the best policy
    rng = random.Random(run_state.config.seed + 999)
    policy = PolicyTable(["fold", "call", "raise", "all_in"], rng)
    policy.load_snapshot(run_state.policies[best_id])

    # get scenario input from user
    hole, community, pot, to_call, stage = _prompt_scenario(run_state)

    # build state key and choose action
    hand_bucket = hand_strength_bucket(hole, community, rng, run_state.config.strength_samples)
    state_key = build_state_key(stage, 0, run_state.config.starting_stack, pot, to_call, hand_bucket, 1)
    action = policy.choose_action(state_key)

    # calculate win probability, pot odds, and baseline action
    win_prob = estimate_win_rate(hole, community, rng, max(50, run_state.config.strength_samples))
    pot_odds = 0.0 if to_call == 0 else to_call / max(pot + to_call, 1)
    baseline = optimal_action(win_prob, pot_odds, run_state.config.starting_stack, to_call)

    # print verbose details
    if verbose:
        print(f"Hole: {format_cards(hole)}")
        print(f"Flop: {format_cards(community)}")
        print(f"Pot: {pot}, To call: {to_call}")
        print(f"Win prob: {win_prob:.2f}, Pot odds: {pot_odds:.2f}")
        print(f"Baseline action: {baseline}")
    print(f"Best model action: {action}")


# prompt for scenario input
def _prompt_scenario(run_state: RunState) -> tuple[list[Card], list[Card], int, int, int]:

    print("Scenario input (press Enter for defaults):")
    stage = _prompt_int("Stage (0=preflop, 1=flop, 2=turn, 3=river)", 1)
    stack = _prompt_int("Stack size", run_state.config.starting_stack)
    pot = _prompt_int("Pot size", run_state.config.big_blind * 2)
    to_call = _prompt_int("To call", run_state.config.big_blind)
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
