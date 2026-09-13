import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from swarmcraft import BlockTypes


# =============================================================================
# CLI argument parsing (preset + resume flags + positional overrides)
# =============================================================================

def parse_run_args(args: str) -> tuple[str | None, Path | None, bool, list[str]]:
    """
    Parse the raw CLI argument string for `run`.

    Supported flags
    ---------------
    --preset <id>
        Loads a preset configuration.
    --resume
        Interactive resume selection (lists available runs and checkpoints).
    --resume-from <path>  (alias: --resume_from)
        Non-interactive resume selection using an explicit checkpoint file path.

    Positional arguments
    --------------------
    Remaining tokens (after consuming supported flags) are treated as backward-compatible
    positional overrides.

    Returns
    -------
    tuple[str | None, Path | None, bool, list[str]]
        (preset_id, resume_from_path, resume_interactive, argv)
    """
    tokens = args.split()
    preset_id: str | None = None
    resume_from_path: Path | None = None
    resume_interactive = False
    argv: list[str] = []

    i = 0
    while i < len(tokens):
        t = tokens[i]

        if t == "--preset" and i + 1 < len(tokens):
            preset_id = tokens[i + 1]
            i += 2
            continue

        if t == "--resume":
            resume_interactive = True
            i += 1
            continue

        if t in ("--resume-from", "--resume_from") and i + 1 < len(tokens):
            resume_from_path = Path(tokens[i + 1])
            i += 2
            continue

        argv.append(t)
        i += 1

    return preset_id, resume_from_path, resume_interactive, argv


def resolve_run_config(args: str) -> dict[str, Any]:
    """
    Resolve the effective run configuration using the precedence:

    1) default_run_config()
    2) optional preset config from experiment_setups.json via `--preset <id>`
    3) optional resume selection via:
       - `--resume-from <path>` (non-interactive), OR
       - `--resume` (interactive: user selects run_id and generation/latest)
       In both cases, if a previous run configuration can be found, the user is shown
       the previous settings and is asked whether to reuse them; if not, the user is
       prompted per setting to override (blank keeps the previous value).
    4) optional positional overrides (backward compatible)
    5) finalize_config() to enforce invariants and compute derived values

    Returns
    -------
    dict[str, Any]
        Fully resolved run configuration dict including derived key "lambda_" and
        (optionally) "resume_from" as a string path, suitable to pass as Path(...) later.
        Note: does not create run directories; do_run remains responsible for logging folders.
    """
    preset_id, resume_from_path, resume_interactive, argv = parse_run_args(args)

    cfg = default_run_config()

    if preset_id is not None:
        preset_cfg = load_preset_config(preset_id)
        for k, v in preset_cfg.items():
            cfg[k] = v

    # Resume selection: explicit path wins over interactive.
    checkpoint: Path | None = None
    if resume_from_path is not None:
        checkpoint = resume_from_path
    elif resume_interactive:
        checkpoint = prompt_resume_checkpoint()
    else:
        print("No checkpoint")

    if checkpoint is not None:

        prev_cfg = load_previous_run_config_for_checkpoint(checkpoint)
        if prev_cfg:
            prev_cfg = strip_logging_keys(prev_cfg)
            print_previous_settings(prev_cfg)

            reuse = prompt_yes_no(
                "Reuse the previous settings shown above? [Y/n]: ",
                default_yes=True,
            )
            cfg.update(prev_cfg)

            if not reuse:
                cfg = prompt_overrides_for_settings(cfg)
            cfg["resume_from"] = str(checkpoint)
            print("Checkpoint is: ", cfg["resume_from"])

        else:
            print(
                "Warning: previous run settings could not be loaded (experiment_setup.txt not found or invalid JSON); "
                "the resumed run will use the currently resolved settings."
            )

    cfg = apply_positional_overrides(cfg, argv)
    cfg = finalize_config(cfg)

    cfg["preset_id"] = preset_id
    print("cfg in run config: ", cfg)
    return cfg


# =============================================================================
# Run directory management (new runs)
# =============================================================================

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
    """
    preset_id = cfg.get("preset_id", None)
    run_dir = cfg.get("run_dir", None)
    resume_from = cfg.get("resume_from", None)

    print("=== RUN CONFIG ===")
    if preset_id is not None:
        print(f"Preset id: {preset_id}")
    if run_dir is not None:
        print(f"Logging directory: {run_dir}")
    if resume_from:
        print(f"Resume from: {resume_from}")

    print(f"arena_origin={cfg['arena_origin']} arena_size={cfg['arena_size']}")
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
    print(f"blocks={cfg['blocks']}")


# =============================================================================
# Resume helpers (interactive selection of run + checkpoint, then reuse/edit settings)
# =============================================================================

_RUN_DIR_RE = re.compile(r"^run_(\d+)$")
_GEN_FILE_RE = re.compile(r"^gen_(\d+)\.pkl$")


def _default_logging_base_dir() -> Path:
    return Path(os.getcwd()) / "logging"


def _read_run_setup(run_dir: Path) -> dict[str, Any]:
    """
    Read experiment_setup.txt (JSON) if present; returns {} on absence or parse failure.
    """
    setup_path = run_dir / "experiment_setup.txt"
    if not setup_path.exists():
        return {}
    try:
        return json.loads(setup_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def list_existing_runs(base_logging_dir: Path | None = None) -> list[dict[str, Any]]:
    """
    List run_N directories under the logging base directory.
    """
    base = base_logging_dir or _default_logging_base_dir()
    if not base.exists():
        return []

    runs: list[dict[str, Any]] = []
    for p in base.iterdir():
        if not p.is_dir():
            continue
        m = _RUN_DIR_RE.match(p.name)
        if not m:
            continue

        run_id = int(m.group(1))
        setup = _read_run_setup(p)

        ts = setup.get("timestamp")
        if not isinstance(ts, str) or not ts:
            ts = datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds")

        runs.append(
            {
                "run_id": run_id,
                "run_dir": p,
                "timestamp": ts,
                "exp_name": setup.get("exp_name"),
                "generations": setup.get("generations"),
                "population_count": setup.get("population_count"),
                "lambda_": setup.get("lambda_"),
            }
        )

    runs.sort(key=lambda r: r["run_id"])
    return runs


def list_population_checkpoints(run_dir: Path) -> dict[str, Path]:
    """
    List population checkpoints for a given run directory.

    Returns mapping:
      - "latest" -> populations/latest.pkl (if present)
      - "<g>" -> populations/gen_<g>.pkl
    """
    pop_dir = run_dir / "populations"
    if not pop_dir.exists():
        return {}

    ckpts: dict[str, Path] = {}
    latest = pop_dir / "latest.pkl"
    if latest.exists():
        ckpts["latest"] = latest

    for p in pop_dir.iterdir():
        if not p.is_file():
            continue
        m = _GEN_FILE_RE.match(p.name)
        if not m:
            continue
        g = m.group(1)
        ckpts[g] = p

    ordered: dict[str, Path] = {}
    if "latest" in ckpts:
        ordered["latest"] = ckpts["latest"]
    for g in sorted((k for k in ckpts.keys() if k.isdigit()), key=lambda x: int(x)):
        ordered[g] = ckpts[g]

    return ordered


def prompt_resume_checkpoint(base_logging_dir: Path | None = None) -> Path | None:
    """
    Interactive prompt:
      1) list available runs under ./logging/run_N/
      2) prompt run_id
      3) list available checkpoints (latest + gen files)
      4) prompt checkpoint selection
      5) return selected checkpoint path
    """
    base = base_logging_dir or _default_logging_base_dir()
    runs = list_existing_runs(base)

    if not runs:
        print(f"No runs found under: {base}")
        return None

    print("\n=== Available runs ===")
    for r in runs:
        rid = r["run_id"]
        ts = r.get("timestamp") or "?"
        exp = r.get("exp_name") or "?"
        gens = r.get("generations")
        mu = r.get("population_count")
        lam = r.get("lambda_")
        print(f"  [{rid}] {ts} | exp={exp} gens={gens} mu={mu} lambda={lam}")

    s = input("Select run id to resume (blank to cancel): ").strip()
    if s == "":
        return None
    if not s.isdigit():
        print("Invalid run id selection (must be an integer).")
        return None
    chosen_id = int(s)

    chosen_run = next((r for r in runs if r["run_id"] == chosen_id), None)
    if chosen_run is None:
        print("Selected run id does not exist.")
        return None

    ckpts = list_population_checkpoints(chosen_run["run_dir"])
    if not ckpts:
        print(f"No checkpoints found in: {chosen_run['run_dir'] / 'populations'}")
        return None

    print("\n=== Available checkpoints ===")
    if "latest" in ckpts:
        print("  latest  (populations/latest.pkl)")
    gens = [k for k in ckpts.keys() if k.isdigit()]
    if gens:
        print("  generations:", ", ".join(sorted(gens, key=lambda x: int(x))))

    g = input(
        "Select checkpoint: enter 'latest' or a generation number g (resumes at g+1), blank to cancel: "
    ).strip()

    if g == "":
        return None
    if g in ckpts:
        return ckpts[g]

    print("Invalid checkpoint selection.")
    return None


def derive_run_dir_from_checkpoint(checkpoint_path: Path) -> Path | None:
    """
    If checkpoint_path matches .../logging/run_N/populations/(latest.pkl|gen_X.pkl),
    return the run_N directory; otherwise return None.
    """
    try:
        pop_dir = checkpoint_path.parent
        run_dir = pop_dir.parent
    except Exception:
        return None

    if pop_dir.name != "populations":
        return None
    if not _RUN_DIR_RE.match(run_dir.name):
        return None
    return run_dir


def load_previous_run_config_for_checkpoint(checkpoint_path: Path) -> dict[str, Any]:
    """
    Load the previous run configuration from experiment_setup.txt for the run that produced
    checkpoint_path, if that structure can be inferred; otherwise return {}.
    """
    run_dir = derive_run_dir_from_checkpoint(checkpoint_path)
    if run_dir is None:
        return {}
    return _read_run_setup(run_dir)


def strip_logging_keys(cfg: dict[str, Any]) -> dict[str, Any]:
    """
    Remove keys that must not be imported from the previous run because they refer to
    logging metadata or derived arrays that will be recomputed.
    """
    drop = {
        "run_id",
        "run_dir",
        "pop_dir",
        "timestamp",
        "preset_id",
    }
    return {k: v for k, v in cfg.items() if k not in drop}


def print_previous_settings(prev_cfg: dict[str, Any]) -> None:
    """
    Display the key settings that affect EA meta and evaluation behaviour.
    """
    def g(key: str, default: Any = None) -> Any:
        return prev_cfg.get(key, default)

    print("\n=== Previous settings (from selected run) ===")
    print(f"exp_name={g('exp_name')}")
    print(f"arena_origin={g('arena_origin')} arena_size={g('arena_size')}")
    print(
        f"swarm_size={g('swarm_size')} "
        f"generations={g('generations')} "
        f"arena_count={g('arena_count')} "
        f"run_duration={g('run_duration')} "
        f"reps={g('number_repetitions')}"
    )

    mu = g("population_count")
    lam = g("lambda_")
    off = g("offspring_multiplier")
    print(
        f"EA: mu={mu} lambda={lam} offspring_multiplier={off} "
        f"cx={g('crossover_rate')} mut={g('mutation_prob')} "
        f"depth={g('min_depth')}-{g('max_depth')} "
        f"tourn={g('tournsize')} elites={g('n_elites')}"
    )
    print(f"blocks={g('blocks')}")


def prompt_yes_no(prompt: str, *, default_yes: bool) -> bool:
    """
    Returns True for yes, False for no; blank returns the default.
    """
    s = input(prompt).strip().lower()
    if s == "":
        return default_yes
    if s in ("y", "yes"):
        return True
    if s in ("n", "no"):
        return False
    return default_yes


def prompt_overrides_for_settings(cfg: dict[str, Any]) -> dict[str, Any]:
    """
    Prompt for per-setting overrides; blank input keeps the current value.

    The baseline at this point is expected to be the previous run config, and the
    caller is expected to have already populated cfg with the previous values.
    """
    print("\nEnter a new value to override, or press Enter to keep the previous value.")

    # Strings
    cfg["exp_name"] = prompt_optional_str("exp_name", cfg.get("exp_name"))

    # Vec3
    cfg["arena_origin"] = prompt_optional_vec3("arena_origin", cfg.get("arena_origin"))
    cfg["arena_size"] = prompt_optional_vec3("arena_size", cfg.get("arena_size"))

    # Core integers
    cfg["swarm_size"] = prompt_optional_int("swarm_size", cfg.get("swarm_size"))
    cfg["generations"] = prompt_optional_int("generations", cfg.get("generations"))
    cfg["arena_count"] = prompt_optional_int("arena_count", cfg.get("arena_count"))
    cfg["run_duration"] = prompt_optional_int("run_duration", cfg.get("run_duration"))
    cfg["number_repetitions"] = prompt_optional_int("number_repetitions", cfg.get("number_repetitions"))

    # EA parameters (these drive the EA meta saved by ea_mu_plus_lambda)
    cfg["population_count"] = prompt_optional_int("population_count (mu)", cfg.get("population_count"))

    # Allow user to set either offspring_multiplier or lambda explicitly; if lambda is set, it overwrites offspring_multiplier.
    cfg["offspring_multiplier"] = prompt_optional_float("offspring_multiplier", cfg.get("offspring_multiplier"))

    lam_in = input(f"lambda_ (offspring count) [{cfg.get('lambda_', None)}] (blank keeps derived from offspring_multiplier): ").strip()
    if lam_in != "":
        try:
            lam_val = int(lam_in)
            mu_val = int(cfg["population_count"])
            if mu_val <= 0:
                raise ValueError("population_count must be > 0 to derive offspring_multiplier from lambda_.")
            cfg["offspring_multiplier"] = float(lam_val) / float(mu_val)
        except Exception as e:
            print(f"Invalid lambda_ input; keeping offspring_multiplier unchanged. Reason: {e}")

    cfg["crossover_rate"] = prompt_optional_float("crossover_rate (cxpb)", cfg.get("crossover_rate"))
    cfg["mutation_prob"] = prompt_optional_float("mutation_prob (mutpb)", cfg.get("mutation_prob"))
    cfg["min_depth"] = prompt_optional_int("min_depth", cfg.get("min_depth"))
    cfg["max_depth"] = prompt_optional_int("max_depth", cfg.get("max_depth"))
    cfg["tournsize"] = prompt_optional_int("tournsize", cfg.get("tournsize"))
    cfg["n_elites"] = prompt_optional_int("n_elites", cfg.get("n_elites"))

    # JSON-editable settings
    cfg["blocks"] = prompt_optional_json("blocks (JSON object)", cfg.get("blocks"))

    return cfg


def prompt_optional_str(name: str, current: Any) -> Any:
    s = input(f"{name} [{current}]: ").strip()
    return current if s == "" else s


def prompt_optional_int(name: str, current: Any) -> Any:
    s = input(f"{name} [{current}]: ").strip()
    if s == "":
        return current
    try:
        return int(s)
    except Exception:
        print(f"Invalid integer for {name}; keeping previous value.")
        return current


def prompt_optional_float(name: str, current: Any) -> Any:
    s = input(f"{name} [{current}]: ").strip()
    if s == "":
        return current
    try:
        return float(s)
    except Exception:
        print(f"Invalid float for {name}; keeping previous value.")
        return current


def prompt_optional_vec3(name: str, current: Any) -> Any:
    """
    Accepts either comma-separated 'x,y,z' or JSON list '[x,y,z]'; blank keeps current.
    """
    s = input(f"{name} [{current}]: ").strip()
    if s == "":
        return current
    try:
        if s.startswith("["):
            v = json.loads(s)
            if not isinstance(v, list) or len(v) != 3:
                raise ValueError("Expected JSON list of length 3.")
            return (int(v[0]), int(v[1]), int(v[2]))
        parts = [p.strip() for p in s.split(",")]
        if len(parts) != 3:
            raise ValueError("Expected three comma-separated values.")
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except Exception as e:
        print(f"Invalid vec3 for {name}; keeping previous value. Reason: {e}")
        return current


def prompt_optional_json(name: str, current: Any) -> Any:
    """
    Prompts for JSON input; blank keeps current; invalid JSON keeps current.
    """
    current_str = json.dumps(current, indent=2, sort_keys=True) if current is not None else "null"
    print(f"\n{name} current value:\n{current_str}")
    s = input(f"New {name} (enter JSON, blank keeps current): ").strip()
    if s == "":
        return current
    try:
        return json.loads(s)
    except Exception as e:
        print(f"Invalid JSON for {name}; keeping previous value. Reason: {e}")
        return current


# =============================================================================
# Preset management
# =============================================================================

def _preset_file_path() -> Path:
    """
    Return the filesystem path to the JSON file that contains multiple experiment configs.
    """
    return Path(__file__).resolve().parent / "experiment_setups.json"


def load_all_presets(preset_path: Path | None = None) -> dict[str, Any]:
    """
    Load the full presets dictionary from a JSON file.
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
    """
    presets = load_all_presets(preset_path)
    key = str(preset_id)
    if key not in presets:
        raise KeyError(f"Preset id '{key}' not found in {preset_path or _preset_file_path()}")
    cfg = presets[key]
    if not isinstance(cfg, dict):
        raise ValueError(f"Preset id '{key}' must map to an object/dict in JSON.")
    return cfg


# =============================================================================
# Default config + normalization + positional overrides
# =============================================================================

def default_run_config() -> dict[str, Any]:
    """
    Construct the default run configuration used when neither preset nor CLI overrides are provided.
    """
    return {
        "exp_name": "ConstructionExperiment",

        "arena_origin": (10, -60, 10),
        "arena_size": (20, 10, 20),

        "swarm_size": 2,
        "generations": 100,

        "population_count": 10,
        "offspring_multiplier": 2.0,

        "arena_count": 1,
        "run_duration": 30,

        "crossover_rate": 0.2,
        "mutation_prob": 0.4,

        "min_depth": 1,
        "max_depth": 2,

        "number_repetitions": 1,

        "tournsize": 3,
        "n_elites": 1,

        "fitness_function": "S1",
        "construction": False,

        "blocks": {
            BlockTypes.BLUE_WOOL.value: 9,
            BlockTypes.ORANGE_WOOL.value: 0,
            BlockTypes.BROWN_WOOL.value: 0,
            BlockTypes.GREEN_WOOL.value: 0,
        },

        "resume_from": None,

        "skill_library": [],
        "skill_injection_prob": 0.0,
        "save_skill": False,
        "skill_name": None,
    }


def _normalize_vec3(value: Any, *, name: str, default: tuple[int, int, int]) -> tuple[int, int, int]:
    """
    Normalize a 3D vector coming from config.

    Accepts tuples/lists of length 3 (JSON will typically provide lists), converts to tuple[int,int,int],
    and raises ValueError for invalid shapes or types.
    """
    if value is None:
        return default

    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"'{name}' must be a list/tuple of length 3, got: {value!r}")

    try:
        x = int(value[0])
        y = int(value[1])
        z = int(value[2])
    except (TypeError, ValueError) as e:
        raise ValueError(f"'{name}' entries must be integers, got: {value!r}") from e

    return (x, y, z)


def _normalize_arena_geometry(cfg: dict[str, Any]) -> None:
    """
    Ensure cfg contains normalized arena_origin and arena_size as tuple[int,int,int].
    """
    cfg["arena_origin"] = _normalize_vec3(
        cfg.get("arena_origin"),
        name="arena_origin",
        default=(10, -60, 10),
    )
    cfg["arena_size"] = _normalize_vec3(
        cfg.get("arena_size"),
        name="arena_size",
        default=(20, 10, 20),
    )


def apply_positional_overrides(cfg: dict[str, Any], argv: list[str]) -> dict[str, Any]:
    """
    Apply backward-compatible positional CLI overrides onto cfg.

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


def finalize_config(cfg: dict[str, Any]) -> dict[str, Any]:
    """
    Finalize configuration by enforcing invariants and computing derived parameters.

    Note
    ----
    lambda_ is always derived from population_count and offspring_multiplier; this ensures
    that the EA meta passed to ea_mu_plus_lambda is consistent with the resolved config.
    generations is taken directly from cfg (as set by the default config, a preset, a
    resumed run's settings, or a positional override) rather than derived from a mission
    schedule.
    """
    _normalize_arena_geometry(cfg)

    cfg["population_count"] = max(2, int(cfg.get("population_count", 2)))
    cfg["offspring_multiplier"] = float(cfg.get("offspring_multiplier", 2.0))
    cfg["lambda_"] = int(round(cfg["population_count"] * cfg["offspring_multiplier"]))

    cfg["generations"] = int(cfg.get("generations", 1))

    return cfg