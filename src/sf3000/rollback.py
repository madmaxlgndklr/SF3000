import json
import shutil
from datetime import datetime
from pathlib import Path


class Transaction:
    def __init__(self, command: str, point_dir: Path) -> None:
        self.command = command
        self.point_dir = point_dir
        self.point_dir.mkdir(parents=True, exist_ok=True)
        self._actions: list[dict] = []

    def backup_file(self, sd_root: Path, relative_path: str) -> None:
        """Copy file to rollback dir before any modification."""
        src = sd_root / relative_path
        backup_name = relative_path.replace("/", "_") + ".bak"
        shutil.copy2(src, self.point_dir / backup_name)
        self._actions.append({
            "type": "file_modified",
            "path": relative_path,
            "backup": backup_name,
        })

    def record_move(self, from_path: str, to_path: str) -> None:
        self._actions.append({
            "type": "file_moved",
            "from": from_path,
            "to": to_path,
        })

    def record_created(self, path: str) -> None:
        self._actions.append({"type": "file_created", "path": path})

    def commit(self) -> None:
        manifest = {
            "command": self.command,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "actions": self._actions,
        }
        (self.point_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )

    def abort(self) -> None:
        shutil.rmtree(self.point_dir, ignore_errors=True)


class RollbackManager:
    def __init__(self, sd_root: Path) -> None:
        self.sd_root = sd_root
        self._rollback_dir = sd_root / "cubegm" / ".sf3000_rollback"
        self._rollback_dir.mkdir(parents=True, exist_ok=True)

    def begin(self, command: str) -> Transaction:
        timestamp = datetime.now().strftime("%Y-%m-%dT%H%M%S")
        point_dir = self._rollback_dir / f"{timestamp}-{command}"
        return Transaction(command, point_dir)

    def list_points(self) -> list[dict]:
        points = []
        for d in sorted(self._rollback_dir.iterdir()):
            manifest_path = d / "manifest.json"
            if not manifest_path.exists():
                continue
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            points.append({
                "name": d.name,
                "command": manifest["command"],
                "timestamp": manifest["timestamp"],
                "action_count": len(manifest["actions"]),
            })
        return points

    def apply_rollback(self, point_name: str) -> None:
        point_dir = self._rollback_dir / point_name
        if not point_dir.exists():
            raise ValueError(f"Rollback point not found: {point_name}")

        manifest = json.loads((point_dir / "manifest.json").read_text(encoding="utf-8"))

        for action in reversed(manifest["actions"]):
            atype = action["type"]
            if atype == "file_modified":
                backup = point_dir / action["backup"]
                target = self.sd_root / action["path"]
                shutil.copy2(backup, target)
            elif atype == "file_moved":
                src = self.sd_root / action["to"]
                dst = self.sd_root / action["from"]
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
            elif atype == "file_created":
                target = self.sd_root / action["path"]
                if target.is_dir():
                    shutil.rmtree(target)
                elif target.exists():
                    target.unlink()

        shutil.rmtree(point_dir)
