import httpx
import asyncio
import os


class GenieClient:

    @property
    def base_url(self):
        host = os.getenv("DATABRICKS_HOST")
        space_id = os.getenv("GENIE_SPACE_ID")
        return f"https://{host}/api/2.0/genie/spaces/{space_id}"

    @property
    def headers(self):
        token = os.getenv("DATABRICKS_TOKEN")
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def start_conversation(self, question: str) -> dict:
        """
        새 대화를 시작하고 답변 반환.
        Returns: {"conversation_id": str, "text": ..., "query": ..., "query_result": ...,
                  "suggested_questions": [...], "error": str | None}
        """
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/start-conversation",
                headers=self.headers,
                json={"content": question},
            )
            if response.status_code == 429:
                return _rate_limit_error()
            response.raise_for_status()
            data = response.json()

            conversation_id = data["conversation_id"]
            message_id = data["message_id"]
            result = await self._poll_message(client, conversation_id, message_id)
            result["conversation_id"] = conversation_id
            return result

    async def continue_conversation(self, conversation_id: str, question: str) -> dict:
        """기존 대화에 메시지 추가"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/conversations/{conversation_id}/messages",
                headers=self.headers,
                json={"content": question},
            )
            if response.status_code == 429:
                return _rate_limit_error()
            response.raise_for_status()
            data = response.json()

            message_id = data["message_id"]
            result = await self._poll_message(client, conversation_id, message_id)
            result["conversation_id"] = conversation_id
            return result

    async def _poll_message(
        self, client: httpx.AsyncClient, conversation_id: str, message_id: str
    ) -> dict:
        max_attempts = 30
        for _ in range(max_attempts):
            response = await client.get(
                f"{self.base_url}/conversations/{conversation_id}/messages/{message_id}",
                headers=self.headers,
            )
            response.raise_for_status()
            data = response.json()
            status = data.get("status")

            if status == "COMPLETED":
                return await self._parse_response(client, conversation_id, message_id, data)
            elif status in ("FAILED", "CANCELLED"):
                return {
                    "error": data.get("error", "알 수 없는 오류"),
                    "text": None,
                    "query": None,
                    "query_result": None,
                    "suggested_questions": [],
                }
            await asyncio.sleep(2)

        return _timeout_error()

    async def _parse_response(
        self,
        client: httpx.AsyncClient,
        conversation_id: str,
        message_id: str,
        data: dict,
    ) -> dict:
        result = {
            "text": None,
            "query": None,
            "query_result": None,
            "suggested_questions": [],
            "error": None,
        }

        for attachment in data.get("attachments", []):
            attachment_id = attachment.get("attachment_id", "")

            if "text" in attachment:
                result["text"] = attachment["text"].get("content", "")

            elif "query" in attachment:
                query = attachment["query"]
                result["query"] = {
                    "sql": query.get("query", ""),
                    "description": query.get("description", ""),
                    "title": query.get("title", ""),
                }
                result["query_result"] = await self._fetch_query_result(
                    client, conversation_id, message_id, attachment_id
                )

            elif "suggested_questions" in attachment:
                result["suggested_questions"] = attachment["suggested_questions"].get(
                    "questions", []
                )

        return result

    async def _fetch_query_result(
        self,
        client: httpx.AsyncClient,
        conversation_id: str,
        message_id: str,
        attachment_id: str,
    ) -> list:
        try:
            url = (
                f"{self.base_url}/conversations/{conversation_id}/messages/"
                f"{message_id}/attachments/{attachment_id}/query-result"
            )
            response = await client.get(url, headers=self.headers)
            if response.status_code != 200:
                return []

            data = response.json()
            statement_response = data.get("statement_response", {})
            columns = [
                col["name"]
                for col in statement_response.get("manifest", {})
                .get("schema", {})
                .get("columns", [])
            ]
            rows_raw = statement_response.get("result", {}).get("data_array", [])
            return [dict(zip(columns, row)) for row in rows_raw]

        except Exception:
            return []


def _rate_limit_error() -> dict:
    return {
        "error": "rate_limit",
        "text": None,
        "query": None,
        "query_result": None,
        "suggested_questions": [],
        "conversation_id": None,
    }


def _timeout_error() -> dict:
    return {
        "error": "timeout",
        "text": None,
        "query": None,
        "query_result": None,
        "suggested_questions": [],
        "conversation_id": None,
    }
