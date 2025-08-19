from __future__ import annotations
from typing import Any, Dict, Optional
import os, json, time
import pandas as pd

def _ensure_dir(p: str) -> None:
    if p:
        os.makedirs(p, exist_ok=True)

def _has_pyarrow() -> bool:
    try:
        import pyarrow  # noqa: F401
        return True
    except Exception:
        return False

def save_df_smart(df: pd.DataFrame, path_no_ext: str) -> str:
    """Save DataFrame to parquet if pyarrow is present, else CSV. Returns final path."""
    base, _ = os.path.splitext(path_no_ext)
    _ensure_dir(os.path.dirname(base))
    if _has_pyarrow():
        path = base + ".parquet"
        df.to_parquet(path, index=False)
    else:
        path = base + ".csv"
        df.to_csv(path, index=False)
    return path

def load_df_smart(path_no_ext: str) -> pd.DataFrame:
    """Load DataFrame saved by save_df_smart."""
    base, ext = os.path.splitext(path_no_ext)
    pq = base + ".parquet" if ext == "" else path_no_ext
    cs = base + ".csv" if ext == "" else path_no_ext
    if os.path.exists(pq):
        return pd.read_parquet(pq)
    if os.path.exists(cs):
        return pd.read_csv(cs)
    raise FileNotFoundError(f"Artifact not found: {path_no_ext}(.parquet|.csv)")

class ArtifactStore:
    """
    Minimal, generic artifact store with a small manifest.
    - Namespaces (e.g., 'runs/2025-08-18/gameA')
    - Types: 'df', 'json', 'bytes'
    - Optional metadata per artifact
    """
    def __init__(self, root: str) -> None:
        self.root = os.path.abspath(root)
        _ensure_dir(self.root)
        self._manifest_path = os.path.join(self.root, "_manifest.json")
        if not os.path.exists(self._manifest_path):
            with open(self._manifest_path, "w") as f:
                json.dump({"artifacts": []}, f)

    def _ns_path(self, namespace: str, name: str, suffix: str = "") -> str:
        p = os.path.join(self.root, namespace, name + suffix)
        _ensure_dir(os.path.dirname(p))
        return p

    def _add_manifest(self, rec: Dict[str, Any]) -> None:
        with open(self._manifest_path, "r") as f:
            man = json.load(f)
        man.setdefault("artifacts", []).append(rec)
        with open(self._manifest_path, "w") as f:
            json.dump(man, f, indent=2)

    # DataFrame ----------------------------------------
    def put_df(self, df: pd.DataFrame, namespace: str, name: str, meta: Optional[Dict[str, Any]] = None) -> str:
        path = self._ns_path(namespace, name)
        final = save_df_smart(df, path)
        self._add_manifest({
            "ts": time.time(), "namespace": namespace, "name": name, "type": "df", "path": final, "meta": meta or {}
        })
        return final

    def get_df(self, namespace: str, name: str) -> pd.DataFrame:
        return load_df_smart(self._ns_path(namespace, name))

    # JSON ---------------------------------------------
    def put_json(self, obj: Any, namespace: str, name: str, meta: Optional[Dict[str, Any]] = None) -> str:
        path = self._ns_path(namespace, name + ".json")
        with open(path, "w") as f:
            json.dump(obj, f, indent=2)
        self._add_manifest({
            "ts": time.time(), "namespace": namespace, "name": name, "type": "json", "path": path, "meta": meta or {}
        })
        return path

    def get_json(self, namespace: str, name: str) -> Any:
        path = self._ns_path(namespace, name + ".json")
        with open(path, "r") as f:
            return json.load(f)

    # Bytes --------------------------------------------
    def put_bytes(self, data: bytes, namespace: str, name: str, ext: str = ".bin", meta: Optional[Dict[str, Any]] = None) -> str:
        path = self._ns_path(namespace, name + ext)
        with open(path, "wb") as f:
            f.write(data)
        self._add_manifest({
            "ts": time.time(), "namespace": namespace, "name": name, "type": "bytes", "path": path, "meta": meta or {}
        })
        return path