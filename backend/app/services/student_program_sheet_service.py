# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/student_program_sheet_service.py
import json
import re
import time
from typing import Any
from urllib.parse import quote

import httpx
from fastapi import HTTPException
from jose import jwt

from app.core.config import settings


class StudentProgramSheetService:
    """Read approved lifecycle fields from Google Sheets without persisting student data."""

    token_url = "https://oauth2.googleapis.com/token"
    api_base_url = "https://sheets.googleapis.com/v4/spreadsheets"
    sheets_scope = "https://www.googleapis.com/auth/spreadsheets.readonly"
    field_aliases = {
        "email": {"email", "studentemail", "emailaddress"},
        "program": {"program", "programname", "course", "coursename"},
        "cohort": {"cohort", "cohortname", "class"},
        "attendance": {"attendance", "attendancestatus", "attendancerate", "attendancepercentage", "classesattended", "absences"},
        "assignment_status": {"assignmentstatus", "assignmentsubmitted", "assignmentcompletion", "assignments"},
        "capstone_status": {"capstonestatus", "capstoneprogress", "capstone"},
    }

    def __init__(self) -> None:
        self._access_token: str | None = None
        self._token_expires_at = 0.0

    @staticmethod
    def _configured() -> bool:
        return bool(
            settings.CUSTOMER_SUCCESS_SHEETS_SERVICE_ACCOUNT_JSON
            and settings.CUSTOMER_SUCCESS_PROGRAM_SHEET_ID
            and settings.CUSTOMER_SUCCESS_PROGRAM_SHEET_RANGE
        )

    @staticmethod
    def _normalize_header(value: Any) -> str:
        return re.sub(r"[^a-z0-9]", "", str(value or "").casefold())

    @staticmethod
    def _normalize_email(value: Any) -> str:
        return str(value or "").strip().casefold()

    @staticmethod
    def _cell_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _field_indexes(self, headers: list[Any]) -> dict[str, int]:
        normalized = [self._normalize_header(header) for header in headers]
        indexes: dict[str, int] = {}
        for field, aliases in self.field_aliases.items():
            matches = [index for index, header in enumerate(normalized) if header in aliases]
            if len(matches) > 1:
                raise HTTPException(
                    status_code=503,
                    detail={"code": "source_schema_ambiguous", "source": "student_program_sheet", "field": field},
                )
            if matches:
                indexes[field] = matches[0]
        if "email" not in indexes:
            raise HTTPException(
                status_code=503,
                detail={"code": "source_schema_invalid", "source": "student_program_sheet", "required_field": "email"},
            )
        return indexes

    @classmethod
    def _parse_values(
        cls,
        values: list[list[Any]],
        max_rows: int,
    ) -> dict[str, list[dict[str, str | None]]]:
        if not values:
            return {}
        if len(values) - 1 > max_rows:
            raise HTTPException(
                status_code=503,
                detail={"code": "source_limit_exceeded", "source": "student_program_sheet"},
            )
        field_indexes = cls()._field_indexes(values[0])
        records: dict[str, list[dict[str, str | None]]] = {}
        for row in values[1:]:
            email_index = field_indexes["email"]
            email = cls._normalize_email(row[email_index] if email_index < len(row) else None)
            if not email:
                continue
            record = {
                field: cls._cell_text(row[index] if index < len(row) else None)
                for field, index in field_indexes.items()
                if field != "email"
            }
            records.setdefault(email, []).append(record)
        return records

    @staticmethod
    def _load_credentials() -> dict[str, Any]:
        try:
            credentials = json.loads(settings.CUSTOMER_SUCCESS_SHEETS_SERVICE_ACCOUNT_JSON)
        except (TypeError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=503,
                detail={"code": "source_not_configured", "source": "student_program_sheet"},
            ) from exc
        if not credentials.get("client_email") or not credentials.get("private_key"):
            raise HTTPException(
                status_code=503,
                detail={"code": "source_not_configured", "source": "student_program_sheet"},
            )
        return credentials

    async def _get_access_token(self) -> str:
        now = int(time.time())
        if self._access_token and now < self._token_expires_at:
            return self._access_token
        credentials = self._load_credentials()
        try:
            assertion = jwt.encode(
                {
                    "iss": credentials["client_email"],
                    "scope": self.sheets_scope,
                    "aud": self.token_url,
                    "iat": now,
                    "exp": now + 3600,
                },
                credentials["private_key"],
                algorithm="RS256",
            )
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail={"code": "source_credentials_invalid", "source": "student_program_sheet"},
            ) from exc
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    self.token_url,
                    data={
                        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                        "assertion": assertion,
                    },
                )
                response.raise_for_status()
            payload = response.json()
            token = payload.get("access_token")
            if not token:
                raise HTTPException(status_code=502, detail="Google did not return a Sheets access token")
            self._access_token = str(token)
            self._token_expires_at = now + max(int(payload.get("expires_in") or 3600) - 60, 30)
            return self._access_token
        except HTTPException:
            raise
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=502, detail="Google Sheets authentication failed") from exc
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise HTTPException(status_code=502, detail="Google Sheets authentication is unavailable") from exc

    async def records_by_email(self) -> dict[str, list[dict[str, str | None]]]:
        """Read the configured Program Sheet using a Sheets-readonly service-account token."""
        if not self._configured():
            raise HTTPException(
                status_code=503,
                detail={"code": "source_not_configured", "source": "student_program_sheet"},
            )
        access_token = await self._get_access_token()
        spreadsheet_id = quote(settings.CUSTOMER_SUCCESS_PROGRAM_SHEET_ID, safe="")
        value_range = quote(settings.CUSTOMER_SUCCESS_PROGRAM_SHEET_RANGE, safe="")
        url = f"{self.api_base_url}/{spreadsheet_id}/values/{value_range}"
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    url,
                    params={"majorDimension": "ROWS", "valueRenderOption": "FORMATTED_VALUE"},
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()
            values = response.json().get("values") or []
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                raise HTTPException(status_code=503, detail="Google Sheets rate limit reached; retry later") from exc
            raise HTTPException(status_code=502, detail="Student Program Sheet read failed") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(status_code=502, detail="Student Program Sheet is unavailable or invalid") from exc

        max_rows = settings.CUSTOMER_SUCCESS_PROGRAM_SHEET_MAX_ROWS
        return self._parse_values(values, max_rows)


student_program_sheet_service = StudentProgramSheetService()
