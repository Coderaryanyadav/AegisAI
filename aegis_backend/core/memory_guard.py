import os
import logging
import platform
import subprocess
from typing import Dict, Tuple

logger = logging.getLogger("aegis_ai.memory_guard")

MIN_AVAILABLE_RAM_MB = int(os.environ.get("AEGIS_MIN_RAM_MB", "512"))
MIN_AVAILABLE_RAM_RATIO = float(os.environ.get("AEGIS_MIN_RAM_RATIO", "0.10"))


class MemoryGuard:
    """Queries available system RAM/VRAM before local LLM inference to prevent OS freezes."""

    @staticmethod
    def _read_meminfo_linux() -> Dict[str, int]:
        stats: Dict[str, int] = {}
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value_kb = int(parts[1].strip().split()[0])
                        stats[key] = value_kb * 1024
        except Exception:
            pass
        return stats

    @staticmethod
    def _read_meminfo_darwin() -> Dict[str, int]:
        try:
            result = subprocess.run(
                ["vm_stat"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            page_size = 4096
            pages: Dict[str, int] = {}
            for line in result.stdout.splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    num = val.strip().rstrip(".").strip()
                    if num.isdigit():
                        pages[key.strip()] = int(num)
            free = pages.get("Pages free", 0) * page_size
            inactive = pages.get("Pages inactive", 0) * page_size
            available = free + inactive
            total_result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            total = int(total_result.stdout.strip()) if total_result.stdout.strip().isdigit() else 0
            return {"MemTotal": total, "MemAvailable": available}
        except Exception:
            return {}

    @staticmethod
    def _collect_memory_bytes() -> tuple[float, float]:
        total_bytes = 0.0
        available_bytes = 0.0

        try:
            import psutil
            vm = psutil.virtual_memory()
            total_bytes = float(vm.total)
            available_bytes = float(vm.available)
        except ImportError:
            system = platform.system()
            if system == "Linux":
                info = MemoryGuard._read_meminfo_linux()
                total_bytes = float(info.get("MemTotal", 0))
                available_bytes = float(info.get("MemAvailable", info.get("MemFree", 0)))
            elif system == "Darwin":
                info = MemoryGuard._read_meminfo_darwin()
                total_bytes = float(info.get("MemTotal", 0))
                available_bytes = float(info.get("MemAvailable", 0))
            else:
                available_bytes = float(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_AVPHYS_PAGES"))
                total_bytes = float(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"))

        return total_bytes, available_bytes

    @staticmethod
    def get_memory_stats() -> Dict[str, object]:
        total_bytes, available_bytes = MemoryGuard._collect_memory_bytes()
        gpu_vram_mb = None

        available_mb = round(available_bytes / (1024 * 1024), 1)
        total_mb = round(total_bytes / (1024 * 1024), 1) if total_bytes else 0
        used_mb = round(total_mb - available_mb, 1) if total_mb else 0
        usage_pct = round((used_mb / total_mb) * 100, 1) if total_mb else 0
        allowed, _ = MemoryGuard.check_inference_allowed(
            required_mb=MIN_AVAILABLE_RAM_MB,
            available_mb=available_mb,
            total_mb=total_mb,
        )

        return {
            "total_mb": total_mb,
            "available_mb": available_mb,
            "used_mb": used_mb,
            "usage_percent": usage_pct,
            "gpu_vram_mb": gpu_vram_mb,
            "platform": platform.system(),
            "min_required_mb": MIN_AVAILABLE_RAM_MB,
            "inference_allowed": allowed,
        }

    @staticmethod
    def check_inference_allowed(
        required_mb: int = None,
        available_mb: float = None,
        total_mb: float = None,
    ) -> Tuple[bool, str]:
        threshold = required_mb if required_mb is not None else MIN_AVAILABLE_RAM_MB

        if available_mb is None or total_mb is None:
            total_bytes, avail_bytes = MemoryGuard._collect_memory_bytes()
            available_mb = round(avail_bytes / (1024 * 1024), 1)
            total_mb = round(total_bytes / (1024 * 1024), 1) if total_bytes else 0

        if available_mb < threshold:
            return False, (
                f"Insufficient system memory: {available_mb}MB available, "
                f"{threshold}MB required for safe local AI inference."
            )

        if total_mb:
            ratio = available_mb / total_mb
            if ratio < MIN_AVAILABLE_RAM_RATIO:
                return False, (
                    f"System memory critically low ({round(ratio * 100, 1)}% free). "
                    "Local AI inference throttled to protect system stability."
                )

        return True, "OK"
