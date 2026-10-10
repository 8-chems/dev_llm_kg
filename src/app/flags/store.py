import json
import os
from typing import Any
from src.app.config import Settings
from src.app.flags.models import FlagConfig


class FlagStore:

    def __init__(self, settings: Settings):
        self._settings = settings
        self._flags: dict[str, FlagConfig] = {}
        self.load_base_thresholds()

    def load_base_thresholds(self) -> None:
        path = self._settings.thresholds_path
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for k, v in data.items():
                    if isinstance(v, (int, float)):
                        self._flags[k] = FlagConfig(
                            decision=k,
                            mode=self._settings.pipeline_mode,
                            tau=float(v),
                        )
            except Exception:
                pass

        # Defaults if missing
        for d in ["resolve", "hop", "goal", "ground", "dedupe"]:
            if d not in self._flags:
                self._flags[d] = FlagConfig(
                    decision=d,
                    mode=self._settings.pipeline_mode,
                    tau=0.85 if d == "resolve" else 0.80,
                )

    def get_flag(self, decision: str) -> FlagConfig:
        return self._flags.get(
            decision,
            FlagConfig(
                decision=decision, mode=self._settings.pipeline_mode, tau=0.80
            ),
        )

    def get_taus(self) -> dict[str, float]:
        return {k: v.tau for k, v in self._flags.items()}

    def set_flag(self, decision: str, mode: str, tau: float) -> FlagConfig:
        flag = FlagConfig(decision=decision, mode=mode, tau=tau)
        self._flags[decision] = flag
        return flag

    def get_all_flags(self) -> dict[str, Any]:
        return {k: v.model_dump() for k, v in self._flags.items()}
