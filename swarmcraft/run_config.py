import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from swarmcraft import BlockTypes
from typing import Tuple


def parse_run_args(args: str) -> tuple[str | None, list[str]]:
    """
    Parse the raw CLI argument string for `run`.

    Parameters
    ----------
    args : str
        Raw argument string passed into ServerShell.do_run.

    Returns
    -------
    tuple[str | None, list[str]]
        (preset_id, argv) where:
        - preset_id is the value passed to `--preset` or None if not provided
        - argv is the remaining positional argument tokens for backward-compatible overrides
    """
    tokens = args.split()
    preset_id = None

    if len(tokens) >= 2 and tokens[0] == "--preset":
        preset_id = tokens[1]
        tokens = tokens[2:]

    return preset_id, tokens


def resolve_run_config(args: str) -> dict[str, Any]:
    """
    Resolve the effective run configuration using the precedence:

    1) default_run_config()
    2) optional preset config from experiment_setups.json via `--preset <id>`
    3) optional positional overrides (backward compatible)
    4) finalize_config() to enforce invariants and compute derived values

    Parameters
    ----------
    args : str
        Raw argument string passed into ServerShell.do_run.

    Returns
    -------
    dict[str, Any]
        Fully resolved run configuration dict including derived key "lambda_".
        Note: does not create run directories; do_run remains responsible for logging folders.
    """
    preset_id, argv = parse_run_args(args)

    cfg = default_run_config()

    if preset_id is not None:
        preset_cfg = load_preset_config(preset_id)
        for k, v in preset_cfg.items():
            cfg[k] = v

    cfg = apply_positional_overrides(cfg, argv)
    cfg = finalize_config(cfg)

    # keep preset_id in cfg for logging convenience
    cfg["preset_id"] = preset_id
    return cfg

def create_run_directories(base_logging_dir: Path | None = None) -> dict[str, Any]:
    """
    Create a unique run directory structure and return metadata.

    Directory layout
    ----------------
    ./logging/run_N/
      experiment_setup.txt
      gp_log.csv
      populations/
        gen_<g>.pkl
        latest.pkl

    Variables
    ----------
    base_logging_dir : Path | None
        Base directory under which run_N folders are created.
        If None, defaults to Path(os.getcwd()) / "logging".

    Returns
    -------
    dict[str, Any]
        Dict containing:
        - base_dir : str
        - run_id : int
        - run_dir : str
        - pop_dir : str
        - timestamp : str (ISO-8601)
    """
    base_dir = base_logging_dir or (Path(os.getcwd()) / "logging")
    base_dir.mkdir(parents=True, exist_ok=True)

    run_id = 0
    while (base_dir / f"run_{run_id}").exists():
        run_id += 1

    run_dir = base_dir / f"run_{run_id}"
    pop_dir = run_dir / "populations"

    run_dir.mkdir(parents=True, exist_ok=False)
    pop_dir.mkdir(parents=True, exist_ok=True)

    return {
        "base_dir": str(base_dir),
        "run_id": run_id,
        "run_dir": str(run_dir),
        "pop_dir": str(pop_dir),
        "timestamp": datetime.now().isoformat(),
    }


def print_run_config_summary(cfg: dict[str, Any]) -> None:
    """
    Print a compact, human-readable summary of the resolved run configuration.

    Variables
    ----------
    cfg : dict[str, Any]
        Finalized run configuration (must include derived values such as "lambda_"
        and logging metadata such as "run_dir" if available).
    """
    preset_id = cfg.get("preset_id", None)
    run_dir = cfg.get("run_dir", None)

    print("=== RUN CONFIG ===")
    if preset_id is not None:
        print(f"Preset id: {preset_id}")
    if run_dir is not None:
        print(f"Logging directory: {run_dir}")

    print(
        f"swarm_size={cfg['swarm_size']} "
        f"generations={cfg['generations']} "
        f"mu={cfg['population_count']} "
        f"lambda={cfg['lambda_']} "
        f"arena_count={cfg['arena_count']} "
        f"run_duration={cfg['run_duration']} "
        f"cx={cfg['crossover_rate']} "
        f"mut={cfg['mutation_prob']} "
        f"depth={cfg['min_depth']}-{cfg['max_depth']} "
        f"reps={cfg['number_repetitions']} "
        f"tourn={cfg['tournsize']} "
        f"elites={cfg['n_elites']}"
    )
    print(f"mission={cfg['mission']}")
    print(f"blocks={cfg['blocks']}")


def _preset_file_path() -> Path:
    """
    Return the filesystem path to the JSON file that contains multiple experiment configs.

    Variables
    ----------
    Path(__file__).resolve().parent : Path
        Directory containing this shell module.
    """
    return Path(__file__).resolve().parent / "experiment_setups.json"


def load_all_presets(preset_path: Path | None = None) -> dict[str, Any]:
    """
    Load the full presets dictionary from a JSON file.

    Variables
    ----------
    preset_path : Path | None
        Path to the JSON file containing configs keyed by unique IDs ("0", "1", ...).
        If None, uses the default `_preset_file_path()`.

    Returns
    -------
    dict[str, Any]
        The parsed JSON object (top-level must be a dict mapping IDs to config dicts).
    """
    path = preset_path or _preset_file_path()
    if not path.exists():
        raise FileNotFoundError(f"Preset file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Preset file must contain a JSON object at top-level: {path}")

    return data


def load_preset_config(preset_id: str | int, preset_path: Path | None = None) -> dict[str, Any]:
    """
    Load a single config entry by preset id.

    Variables
    ----------
    preset_id : str | int
        Identifier of the config (e.g. "1" or 1). Stored keys in JSON should be strings.
    preset_path : Path | None
        Optional custom path to the presets JSON file.

    Returns
    -------
    dict[str, Any]
        A config dictionary.
    """
    presets = load_all_presets(preset_path)
    key = str(preset_id)
    if key not in presets:
        raise KeyError(f"Preset id '{key}' not found in {preset_path or _preset_file_path()}")
    cfg = presets[key]
    if not isinstance(cfg, dict):
        raise ValueError(f"Preset id '{key}' must map to an object/dict in JSON.")
    return cfg


def default_run_config() -> dict[str, Any]:
    """
    Construct the default run configuration used when neither preset nor CLI overrides are provided.
    """
    return {
        "exp_name": "ForageExperiment",

        "swarm_size": 15,
        "generations": 200,

        "population_count": 15,
        "offspring_multiplier": 2.0,

        "arena_count": 4,
        "run_duration": 30,

        "crossover_rate": 0.4,
        "mutation_prob": 0.2,

        "min_depth": 1,
        "max_depth": 2,

        "number_repetitions": 1,

        "tournsize": 3,
        "n_elites": 1,

        # --- mission defaults ---
        "mission": BlockTypes.BLUE_WOOL.value,
        "mission_schedule": [
            {"mission": BlockTypes.BLUE_WOOL.value, "generations": 100},
            {"mission": BlockTypes.ORANGE_WOOL.value, "generations": 100},
        ],

        "blocks": {
            BlockTypes.BLUE_WOOL.value: 4,
            BlockTypes.ORANGE_WOOL.value: 4,
            BlockTypes.BROWN_WOOL.value: 0,
            BlockTypes.GREEN_WOOL.value: 0,
        },
    }



def apply_positional_overrides(cfg: dict[str, Any], argv: list[str]) -> dict[str, Any]:
    """
    Apply backward-compatible positional CLI overrides onto cfg.

    Variables
    ----------
    cfg : dict[str, Any]
        The configuration dictionary to mutate.
    argv : list[str]
        Remaining tokens after parsing `--preset` (if present).
        Mapping (index -> key):
          0 swarm_size
          1 generations
          2 population_count
          3 offspring_multiplier
          4 arena_count
          5 run_duration
          6 crossover_rate
          7 mutation_prob
          8 max_depth
          9 min_depth
          10 number_repetitions
          11 tournsize
          12 n_elites
    """
    if len(argv) > 0:
        cfg["swarm_size"] = int(argv[0])
    if len(argv) > 1:
        cfg["generations"] = int(argv[1])
    if len(argv) > 2:
        cfg["population_count"] = max(2, int(argv[2]))
    if len(argv) > 3:
        cfg["offspring_multiplier"] = float(argv[3])
    if len(argv) > 4:
        cfg["arena_count"] = int(argv[4])
    if len(argv) > 5:
        cfg["run_duration"] = int(argv[5])
    if len(argv) > 6:
        cfg["crossover_rate"] = float(argv[6])
    if len(argv) > 7:
        cfg["mutation_prob"] = float(argv[7])
    if len(argv) > 8:
        cfg["max_depth"] = int(argv[8])
    if len(argv) > 9:
        cfg["min_depth"] = int(argv[9])
    if len(argv) > 10:
        cfg["number_repetitions"] = int(argv[10])
    if len(argv) > 11:
        cfg["tournsize"] = int(argv[11])
    if len(argv) > 12:
        cfg["n_elites"] = int(argv[12])

    return cfg

def _normalize_mission_schedule(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Normalize and validate the mission schedule.

    Variables
    ----------
    cfg : dict[str, Any]
        Run config. Reads:
        - cfg["mission_schedule"] : list[{"mission": str, "generations": int}]
        - cfg["mission"] : str fallback

    Returns
    -------
    list[dict[str, Any]]
        Normalized mission schedule phases. Each element is:
        {"mission": <str>, "generations": <int>}
    """
    sched = cfg.get("mission_schedule")

    # Fallback: if no schedule is provided, use single-phase schedule from cfg["mission"]
    if not sched:
        mission = cfg.get("mission")
        if mission is None:
            raise ValueError("Config must define either 'mission' or 'mission_schedule'.")
        return [{"mission": mission, "generations": int(cfg.get("generations", 1))}]

    if not isinstance(sched, list):
        raise ValueError("'mission_schedule' must be a list of phases.")

    normalized: list[dict[str, Any]] = []
    for i, phase in enumerate(sched):
        if not isinstance(phase, dict):
            raise ValueError(f"mission_schedule[{i}] must be an object/dict.")
        if "mission" not in phase or "generations" not in phase:
            raise ValueError(f"mission_schedule[{i}] must contain keys: 'mission' and 'generations'.")
        mission = phase["mission"]
        gens = int(phase["generations"])
        if gens <= 0:
            raise ValueError(f"mission_schedule[{i}].generations must be > 0.")
        normalized.append({"mission": mission, "generations": gens})

    return normalized


def _build_mission_timeline(schedule: list[dict[str, Any]]) -> list[str]:
    """
    Expand a mission schedule into a per-generation timeline.

    Variables
    ----------
    schedule : list[dict[str, Any]]
        List of phases, each with:
        - mission : str
        - generations : int

    Returns
    -------
    list[str]
        missions_by_gen, where missions_by_gen[g] is the mission for generation g.
    """
    missions_by_gen: list[str] = []
    for phase in schedule:
        missions_by_gen.extend([phase["mission"]] * int(phase["generations"]))
    print("Mission array: ", missions_by_gen)
    return missions_by_gen


def mission_for_generation(cfg: dict[str, Any], gen: int) -> str:
    """
    Return the active mission for a given generation index.

    Variables
    ----------
    cfg : dict[str, Any]
        Must contain:
        - cfg["missions_by_gen"] : list[str] computed in finalize_config()
        OR
        - cfg["mission_schedule"] : list phases (will be normalized in finalize_config)
    gen : int
        Current generation (0-based).

    Returns
    -------
    str
        Mission string, e.g. "blue_wool".
    """
    timeline = cfg.get("missions_by_gen")
    if not timeline:
        # Defensive fallback (should not happen if finalize_config() was used)
        schedule = _normalize_mission_schedule(cfg)
        timeline = _build_mission_timeline(schedule)

    if gen < 0:
        gen = 0
    if gen >= len(timeline):
        # Clamp: after schedule ends, keep last mission
        return timeline[-1]
    return timeline[gen]


def finalize_config(cfg: dict[str, Any]) -> dict[str, Any]:
    """
    Finalize configuration by enforcing invariants and computing derived parameters.

    Variables
    ----------
    population_count : int
        Must be >= 2.
    lambda_ : int
        Derived as round(population_count * offspring_multiplier).
    mission_schedule : list[dict]
        Determines the mission timeline and total generations.
    """
    cfg["population_count"] = max(2, int(cfg.get("population_count", 2)))
    cfg["offspring_multiplier"] = float(cfg.get("offspring_multiplier", 2.0))
    cfg["lambda_"] = int(round(cfg["population_count"] * cfg["offspring_multiplier"]))

    # Normalize schedule and compute missions_by_gen
    schedule = _normalize_mission_schedule(cfg)
    missions_by_gen = _build_mission_timeline(schedule)
    cfg["mission_schedule"] = schedule
    cfg["missions_by_gen"] = missions_by_gen

    # Make total generations match the schedule (authoritative)
    cfg["generations"] = len(missions_by_gen)

    # Keep cfg["mission"] consistent for readability (first phase)
    cfg["mission"] = missions_by_gen[0] if missions_by_gen else cfg.get("mission")

    return cfg
