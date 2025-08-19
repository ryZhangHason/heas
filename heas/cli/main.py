from __future__ import annotations
import argparse, json, importlib, importlib.util, os, sys, inspect
from typing import Any, Dict, Iterable, List, Optional

from ..config import Experiment, Algorithm, Evaluation
from ..api import simulate, optimize, evaluate

# ----------------------------- utils ---------------------------------

class _NumpyJSONEncoder(json.JSONEncoder):
    def default(self, o):  # type: ignore[override]
        try:
            import numpy as _np
            if isinstance(o, (_np.floating,)):
                return float(o)
            if isinstance(o, (_np.integer,)):
                return int(o)
            if isinstance(o, (_np.ndarray,)):
                return o.tolist()
        except Exception:
            pass
        try:
            import pandas as _pd
            if isinstance(o, (_pd.Timestamp,)):
                return o.isoformat()
            if hasattr(o, "to_dict") and callable(o.to_dict):
                return o.to_dict()
        except Exception:
            pass
        return super().default(o)

def _jprint(obj: Any) -> None:
    print(json.dumps(obj, indent=2, cls=_NumpyJSONEncoder))

def _import_object(path: str):
    """
    Accepts:
      - 'package.module:attr'
      - '/abs/or/rel/path/to/file.py:attr'
    """
    if ":" not in path:
        raise ValueError("Use 'module:object' or 'path/to/file.py:object'")
    mod_part, attr = path.split(":", 1)

    if mod_part.endswith(".py") or os.path.sep in mod_part or mod_part.startswith("."):
        file_path = os.path.abspath(mod_part)
        spec = importlib.util.spec_from_file_location("heas_user_module", file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module from {file_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules["heas_user_module"] = module
        spec.loader.exec_module(module)  # type: ignore[attr-defined]
        return getattr(module, attr)
    else:
        mod = importlib.import_module(mod_part)
        return getattr(mod, attr)

def _coerce_model_factory_from_obj(obj, default_seed):
    """Return a model_factory(kwargs) from many accepted inputs."""
    from ..hierarchy import CompositeHeasModel, Graph, make_model_from_spec

    # 1) Already a CompositeHeasModel instance
    if isinstance(obj, CompositeHeasModel):
        return lambda kw: obj

    # 2) A Graph instance -> wrap
    if isinstance(obj, Graph):
        return lambda kw: CompositeHeasModel(obj, seed=kw.get("seed", default_seed))

    # 3) A Spec (list[LayerSpec]) -> build via make_model_from_spec
    if isinstance(obj, list) and all(hasattr(x, "streams") for x in obj):
        def _mf(kw):
            return make_model_from_spec(obj, seed=kw.get("seed", default_seed))({})
        return _mf

    # 4) Callable cases:
    if callable(obj):
        try:
            sig = inspect.signature(obj)
            # 4a) Zero-arg callable -> call it, then recurse on the returned object
            if len(sig.parameters) == 0:
                returned = obj()
                return _coerce_model_factory_from_obj(returned, default_seed)
            # 4b) Callable expecting kwargs -> assume it's a HEAS model_factory(kwargs)
            else:
                return obj
        except Exception:
            # Be conservative: treat as model_factory
            return obj

    raise TypeError("Unsupported --graph object. Provide CompositeHeasModel, Graph, a list[LayerSpec], or a model_factory(kwargs).")

def _is_json_like(s: str) -> bool:
    s = s.strip()
    return (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]"))

def _load_json_any(path_or_json: str) -> Any:
    if os.path.exists(path_or_json):
        with open(path_or_json, "r") as f:
            return json.load(f)
    if _is_json_like(path_or_json):
        return json.loads(path_or_json)
    raise FileNotFoundError(f"Not a file and not JSON: {path_or_json}")

# ----------------------------- CLI -----------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(prog="heas", description="Hierarchical Evolutionary Agent Simulation")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # --- simulate (factory) ---
    p_sim = sub.add_parser("run", help="Run simulation episodes with a model factory")
    p_sim.add_argument("--factory", required=True, help="module:obj or path/to/file.py:obj")
    p_sim.add_argument("--steps", type=int, default=100)
    p_sim.add_argument("--episodes", type=int, default=10)
    p_sim.add_argument("--seed", type=int, default=42)

    # --- simulate (graph/spec/model) ---
    p_graph = sub.add_parser("run-graph", help="Run a hierarchical graph (spec or CompositeHeasModel)")
    p_graph.add_argument("--graph", required=True, help="module:obj or path/to/file.py:obj (Graph/Spec/CompositeHeasModel)")
    p_graph.add_argument("--steps", type=int, default=100)
    p_graph.add_argument("--episodes", type=int, default=10)
    p_graph.add_argument("--seed", type=int, default=42)

    # --- evolutionary tuning ---
    p_opt = sub.add_parser("tune", help="Run evolutionary optimization (DEAP)")
    p_opt.add_argument("--objective", required=True, help="module:obj or path/to/file.py:obj")
    p_opt.add_argument("--schema", required=True, help="module:obj or path/to/file.py:obj")
    p_opt.add_argument("--pop", type=int, default=50)
    p_opt.add_argument("--ngen", type=int, default=10)
    p_opt.add_argument("--strategy", default="nsga2", choices=["simple","nsga2","mu_plus_lambda"])
    p_opt.add_argument("--out", default="runs/heas")

    # --- evaluation of genotypes ---
    p_eval = sub.add_parser("eval", help="Evaluate saved genotypes with an objective")
    p_eval.add_argument("--objective", required=True, help="module:obj or path/to/file.py:obj")
    p_eval.add_argument("--genotypes", required=True, help="JSON path or inline JSON list of genotypes")

    # --- game: arena ---
    pg = sub.add_parser("arena", help="Arena: run scenarios × participants")
    pg_sub = pg.add_subparsers(dest="arena_cmd", required=True)
    pg_run = pg_sub.add_parser("run", help="Run arena and emit per-step/episode tables")
    pg_run.add_argument("--builder", required=True, help="module:obj (build_model(scenario, participant, ctx))")
    pg_run.add_argument("--scenarios", required=True,
                        help="module:obj returning ScenarioSet/list or path.json or inline JSON. "
                             "JSON can be {'grid':{...}} or a list of {'name', ...} dicts.")
    pg_run.add_argument("--participants", required=True,
                        help="Comma-separated participant names, or JSON list.")
    pg_run.add_argument("--steps", type=int, default=100)
    pg_run.add_argument("--episodes", type=int, default=10)
    pg_run.add_argument("--seed", type=int, default=42)
    pg_run.add_argument("--save-dir", default=None, help="Optional directory to save CSV/Parquet")

    # --- game: tournament ---
    pt = sub.add_parser("tournament", help="Tournament: arena + scoring + voting")
    pt_sub = pt.add_subparsers(dest="tournament_cmd", required=True)
    pt_play = pt_sub.add_parser("play", help="Play a tournament and compute votes")
    pt_play.add_argument("--builder", required=True, help="module:obj (build_model(scenario, participant, ctx))")
    pt_play.add_argument("--scenarios", required=True,
                         help="module:obj / path.json / inline JSON (grid or list).")
    pt_play.add_argument("--participants", required=True,
                         help="Comma-separated names or JSON list.")
    pt_play.add_argument("--score", required=True,
                         help="module:obj (score_fn(episode_record, participant)->float)")
    pt_play.add_argument("--voter", default="argmax",
                         help="'argmax'|'majority' or module:obj callable(scores_or_labels)->winner")
    pt_play.add_argument("--steps", type=int, default=100)
    pt_play.add_argument("--episodes", type=int, default=10)
    pt_play.add_argument("--seed", type=int, default=42)
    pt_play.add_argument("--save-dir", default=None, help="Optional directory to save tables")

    # --- visualization ---
    pv = sub.add_parser("viz", help="Quick visualizations")
    pv_sub = pv.add_subparsers(dest="viz_cmd", required=True)

    pv_steps = pv_sub.add_parser("steps", help="Per-step lines from DataFrame (csv/parquet)")
    pv_steps.add_argument("--file", required=True)
    pv_steps.add_argument("--x", default=None)
    pv_steps.add_argument("--y", default=None, help="Comma-separated y columns; default=auto numeric")
    pv_steps.add_argument("--facet", default="scenario")
    pv_steps.add_argument("--hue", default="participant")
    pv_steps.add_argument("--save", default=None)

    pv_votes = pv_sub.add_parser("votes", help="Votes matrix from DataFrame (csv/parquet)")
    pv_votes.add_argument("--file", required=True)
    pv_votes.add_argument("--save", default=None)

    pv_arch = pv_sub.add_parser("arch", help="Draw architecture from module path (spec or model)")
    pv_arch.add_argument("--graph", required=True, help="module:object (spec/list or CompositeHeasModel or Graph)")
    pv_arch.add_argument("--save", default=None)

    pv_log = pv_sub.add_parser("log", help="EA logbook curves from JSON (list of records)")
    pv_log.add_argument("--file", required=True)
    pv_log.add_argument("--save", default=None)

    pv_pareto = pv_sub.add_parser("pareto", help="Pareto scatter from JSON/CSV (Nx2)")
    pv_pareto.add_argument("--file", required=True)
    pv_pareto.add_argument("--save", default=None)
    pv_pareto.add_argument("--title", default="Pareto")

    args = parser.parse_args(argv)

    # ----------------- commands -----------------

    if args.cmd == "run":
        factory = _import_object(args.factory)
        exp = Experiment(model_factory=factory, steps=args.steps, episodes=args.episodes, seed=args.seed)
        res = simulate(exp)
        _jprint(res)
        return 0

    if args.cmd == "run-graph":
        obj = _import_object(args.graph)
        model_factory = _coerce_model_factory_from_obj(obj, args.seed)
        exp = Experiment(model_factory=model_factory, steps=args.steps, episodes=args.episodes, seed=args.seed)
        res = simulate(exp)
        _jprint(res)
        return 0

    if args.cmd == "tune":
        objective = _import_object(args.objective)
        schema = _import_object(args.schema)
        # dummy experiment; objective builds/uses its own model
        exp = Experiment(model_factory=lambda kw: None)
        algo = Algorithm(objective_fn=objective, genes_schema=schema,
                         pop_size=args.pop, ngen=args.ngen, out_dir=args.out, strategy=args.strategy)
        res = optimize(exp, algo)
        _jprint(res)
        return 0

    if args.cmd == "eval":
        objective = _import_object(args.objective)
        if os.path.exists(args.genotypes) or _is_json_like(args.genotypes):
            genos = _load_json_any(args.genotypes)
        else:
            raise FileNotFoundError(f"--genotypes not found or invalid JSON: {args.genotypes}")
        exp = Experiment(model_factory=lambda kw: None)
        eva = Evaluation(genotypes=genos, objective_fn=objective)
        res = evaluate(exp, eva)
        _jprint(res)
        return 0

    if args.cmd == "arena":
        if args.arena_cmd == "run":
            from ..game import Arena
            scenarios = _resolve_scenarios(args.scenarios)
            participants = _resolve_participants(args.participants)
            builder = _import_object(args.builder)
            arena = Arena(builder)
            per_step_df, per_episode_df = arena.run(
                scenarios=scenarios, participants=participants,
                steps=args.steps, episodes=args.episodes, seed=args.seed, ctx={"seed": args.seed}
            )
            out = {
                "shapes": {"per_step": list(per_step_df.shape), "per_episode": list(per_episode_df.shape)},
            }
            if args.save_dir:
                paths = _save_tables(args.save_dir, per_step_df, per_episode_df, None)
                out["saved"] = paths
            _jprint(out)
            return 0

    if args.cmd == "tournament":
        if args.tournament_cmd == "play":
            from ..game import Tournament
            scenarios = _resolve_scenarios(args.scenarios)
            participants = _resolve_participants(args.participants)
            builder = _import_object(args.builder)
            score_fn = _import_object(args.score)
            voter = _import_object(args.voter) if (":" in args.voter or args.voter in ("majority","argmax")) else args.voter
            t = Tournament(builder)
            res = t.play(
                scenarios=scenarios, participants=participants,
                steps=args.steps, episodes=args.episodes, seed=args.seed,
                score_fn=score_fn, voter=voter
            )
            out = {
                "shapes": {
                    "per_step": list(res.per_step.shape),
                    "per_episode": list(res.per_episode.shape),
                    "votes": list(res.votes.shape),
                }
            }
            if args.save_dir:
                paths = _save_tables(args.save_dir, res.per_step, res.per_episode, res.votes)
                out["saved"] = paths
            _jprint(out)
            return 0

    if args.cmd == "viz":
        # lazy-import to keep core light
        try:
            import pandas as pd
            import matplotlib
            matplotlib.use("Agg")  # headless safe
            import matplotlib.pyplot as plt
            from ..vis import plots as vplots
            from ..vis import hierarchy as varch
            from ..vis import evolution as vevo
        except Exception as e:
            raise RuntimeError("Visualization requires matplotlib and pandas installed.") from e

        if args.viz_cmd == "steps":
            df = _read_df(args.file)
            y = [c.strip() for c in args.y.split(",")] if args.y else None
            vplots.plot_steps(df, x=args.x, y_cols=y, facet_by=args.facet, hue=args.hue, title="per-step")
            if args.save: plt.savefig(args.save, dpi=200, bbox_inches="tight")
            else: plt.show()
            return 0

        if args.viz_cmd == "votes":
            df = _read_df(args.file)
            vplots.plot_votes_matrix(df, save=args.save)
            if not args.save:
                plt.show()
            return 0

        if args.viz_cmd == "arch":
            obj = _import_object(args.graph)
            varch.plot_architecture(obj, save=args.save)
            if not args.save:
                plt.show()
            return 0

        if args.viz_cmd == "log":
            data = _load_json_any(args.file)
            vevo.plot_logbook_curves(data, save=args.save)
            if not args.save:
                plt.show()
            return 0

        if args.viz_cmd == "pareto":
            pts = _load_points(args.file)
            vevo.plot_pareto_front(pts, save=args.save, title=args.title)
            if not args.save:
                plt.show()
            return 0

    parser.error("Unrecognized command")
    return 2

# ---------------- helpers for game/viz ----------------

def _resolve_scenarios(arg: str):
    """
    - 'module:obj' -> object (ScenarioSet or list of dicts) used directly.
    - JSON path or inline JSON:
        {"grid": {"region":["A","B"], "gov":["C","F"]}}
        or [{"name":"A|C", "region":"A", "gov":"C"}, ...]
    """
    from ..game.scenarios import make_grid, make_scenarios, ScenarioSet, Scenario  # lazy
    if ":" in arg or (arg.endswith(".py") or os.path.sep in arg):
        obj = _import_object(arg)
        if isinstance(obj, ScenarioSet):
            return obj.scenarios
        if isinstance(obj, list):
            # list[Scenario] or list[dict]
            if obj and hasattr(obj[0], "name") and hasattr(obj[0], "params"):
                return obj
            return make_scenarios(obj).scenarios
        # callable returning scenarios
        if callable(obj):
            got = obj()
            return _resolve_scenarios_input(got)
        return _resolve_scenarios_input(obj)

    data = _load_json_any(arg)
    return _resolve_scenarios_input(data)

def _resolve_scenarios_input(data):
    from ..game.scenarios import make_grid, make_scenarios, ScenarioSet
    if isinstance(data, ScenarioSet):
        return data.scenarios
    if isinstance(data, dict) and "grid" in data:
        return make_grid(data["grid"]).scenarios
    if isinstance(data, list):
        return make_scenarios(data).scenarios
    raise ValueError("Could not interpret scenarios input. Use module:obj, {'grid':{...}}, or list of dicts.")

def _resolve_participants(arg: str) -> List[str]:
    if _is_json_like(arg):
        data = json.loads(arg)
        if isinstance(data, list):
            return [str(x) for x in data]
        raise ValueError("--participants JSON must be a list")
    if os.path.exists(arg):
        with open(arg, "r") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [str(x) for x in data]
        raise ValueError("participants file must contain a JSON list")
    # comma-separated
    return [p.strip() for p in arg.split(",") if p.strip()]

def _save_tables(root: str, per_step_df, per_episode_df, votes_df=None):
    os.makedirs(root, exist_ok=True)
    try:
        import pandas as pd  # noqa
        # prefer parquet if pyarrow is present
        use_pq = _has_pyarrow()
        def _save(df, name):
            path = os.path.join(root, name + (".parquet" if use_pq else ".csv"))
            if use_pq:
                df.to_parquet(path, index=False)
            else:
                df.to_csv(path, index=False)
            return path
        out = {
            "per_step": _save(per_step_df, "per_step"),
            "per_episode": _save(per_episode_df, "per_episode"),
        }
        if votes_df is not None:
            out["votes"] = _save(votes_df, "votes")
        return out
    except Exception as e:
        raise RuntimeError("Failed to save tables; ensure pandas/pyarrow installed.") from e

def _has_pyarrow() -> bool:
    try:
        import pyarrow  # noqa: F401
        return True
    except Exception:
        return False

def _read_df(path: str):
    import pandas as pd
    if path.endswith(".parquet"):
        return pd.read_parquet(path)
    return pd.read_csv(path)

def _load_points(path: str):
    import numpy as np, pandas as pd
    if os.path.exists(path):
        if path.endswith(".csv"):
            df = pd.read_csv(path)
            # try common columns
            for cols in (("obj1","obj2"), ("x","y")):
                if all(c in df.columns for c in cols):
                    return df[list(cols)].to_numpy()
            # else take first two numeric columns
            num = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
            if len(num) >= 2:
                return df[num[:2]].to_numpy()
            raise ValueError("CSV must have at least two numeric columns.")
        else:
            with open(path, "r") as f:
                data = json.load(f)
            return _points_from_obj(data)
    else:
        # inline JSON
        data = json.loads(path)
        return _points_from_obj(data)

def _points_from_obj(obj):
    import numpy as np
    arr = np.array(obj, dtype=float)
    if arr.ndim != 2 or arr.shape[1] < 2:
        raise ValueError("Pareto points must be Nx2 array-like.")
    return arr

if __name__ == "__main__":
    sys.exit(main())