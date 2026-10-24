from __future__ import annotations

import threading
from collections import Counter, defaultdict


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests: Counter[tuple[str, str, int]] = Counter()
        self._duration_ms: defaultdict[tuple[str, str], float] = defaultdict(float)

    def observe(self, method: str, route: str, status_code: int, duration_ms: float) -> None:
        route = route if route.startswith("/api/") else "non_api"
        with self._lock:
            self._requests[(method, route, status_code)] += 1
            self._duration_ms[(method, route)] += duration_ms

    def prometheus(self) -> str:
        lines = [
            "# HELP vernis_http_requests_total HTTP requests processed by the API.",
            "# TYPE vernis_http_requests_total counter",
        ]
        with self._lock:
            for (method, route, status_code), count in sorted(self._requests.items()):
                safe_route = route.replace('"', '')
                lines.append(
                    f'vernis_http_requests_total{{method="{method}",route="{safe_route}",status="{status_code}"}} {count}'
                )
            lines.extend(
                [
                    "# HELP vernis_http_request_duration_milliseconds_sum Cumulative request duration.",
                    "# TYPE vernis_http_request_duration_milliseconds_sum counter",
                ]
            )
            for (method, route), duration in sorted(self._duration_ms.items()):
                safe_route = route.replace('"', '')
                lines.append(
                    f'vernis_http_request_duration_milliseconds_sum{{method="{method}",route="{safe_route}"}} {duration:.3f}'
                )
        return "\n".join(lines) + "\n"


metrics = MetricsRegistry()
