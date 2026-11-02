# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/scripts/run_ghl_reconciliation.py
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def main() -> None:
    endpoint = os.environ.get("GHL_SYNC_API_URL", "").strip()
    token = os.environ.get("GHL_SYNC_CRON_TOKEN", "").strip()
    if not endpoint or not token:
        raise RuntimeError("GHL_SYNC_API_URL and GHL_SYNC_CRON_TOKEN are required for reconciliation")

    request = Request(
        endpoint,
        method="POST",
        headers={"X-GHL-Sync-Token": token, "Content-Type": "application/json"},
        data=b"{}",
    )
    try:
        with urlopen(request, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
            print(json.dumps(payload, separators=(",", ":")))
    except HTTPError as error:
        response_body = error.read().decode("utf-8", errors="replace")
        print(f"GHL reconciliation request failed with HTTP {error.code}: {response_body}", file=sys.stderr)
        raise
    except URLError as error:
        print(f"GHL reconciliation request could not reach the backend: {error.reason}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
