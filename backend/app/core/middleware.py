import re
import json
import hashlib
from typing import Dict, Tuple, Any
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

class PIIAnonymizer:
    def __init__(self):
        # Compiled patterns for Email, Phone Numbers, and US SSNs
        self.email_pattern = re.compile(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b')
        self.phone_pattern = re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
        self.ssn_pattern = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')

    def anonymize(self, text: str, mapping: Dict[str, str]) -> str:
        if not isinstance(text, str):
            return text

        # Anonymize SSNs
        def replace_ssn(match):
            val = match.group(0)
            token = f"[SSN-{hashlib.md5(val.encode()).hexdigest()[:8].upper()}]"
            mapping[token] = val
            return token
        text = self.ssn_pattern.sub(replace_ssn, text)

        # Anonymize Emails
        def replace_email(match):
            val = match.group(0)
            token = f"[EMAIL-{hashlib.md5(val.encode()).hexdigest()[:8].upper()}]"
            mapping[token] = val
            return token
        text = self.email_pattern.sub(replace_email, text)

        # Anonymize Phones
        def replace_phone(match):
            val = match.group(0)
            token = f"[PHONE-{hashlib.md5(val.encode()).hexdigest()[:8].upper()}]"
            mapping[token] = val
            return token
        text = self.phone_pattern.sub(replace_phone, text)

        return text

    def de_anonymize(self, text: str, mapping: Dict[str, str]) -> str:
        if not isinstance(text, str):
            return text
        for token, original in mapping.items():
            text = text.replace(token, original)
        return text


class PIISanitizationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.anonymizer = PIIAnonymizer()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # We only sanitize JSON requests
        content_type = request.headers.get("content-type", "")
        if "application/json" not in content_type:
            return await call_next(request)

        # Buffer the request body
        body = await request.body()
        if not body:
            return await call_next(request)

        try:
            body_str = body.decode("utf-8")
            body_json = json.loads(body_str)
        except Exception:
            # Fall back if JSON parsing fails
            return await call_next(request)

        # Walk JSON and replace PII
        pii_map: Dict[str, str] = {}
        
        def sanitize_value(val: Any) -> Any:
            if isinstance(val, str):
                return self.anonymizer.anonymize(val, pii_map)
            elif isinstance(val, dict):
                return {k: sanitize_value(v) for k, v in val.items()}
            elif isinstance(val, list):
                return [sanitize_value(v) for v in val]
            return val

        sanitized_json = sanitize_value(body_json)
        new_body = json.dumps(sanitized_json).encode("utf-8")

        # Set custom state to carry the map to response phase
        request.state.pii_map = pii_map

        # Create a new receive channel containing the sanitized request body
        async def receive():
            return {"type": "http.request", "body": new_body, "more_body": False}

        # Override request receive method
        request._receive = receive

        # Execute downstream endpoints
        response = await call_next(request)

        # De-anonymize response if there are mapped elements
        if hasattr(request.state, "pii_map") and request.state.pii_map:
            # Check response headers
            res_content_type = response.headers.get("content-type", "")
            if "application/json" in res_content_type and not isinstance(response, StreamingResponse):
                # Read response body
                response_body = [section async for section in response.body_iterator]
                response_content = b"".join(response_body).decode("utf-8")
                
                # Rehydrate PII
                rehydrated_content = self.anonymizer.de_anonymize(response_content, request.state.pii_map)
                new_response_body = rehydrated_content.encode("utf-8")
                
                # Rebuild response with correct headers
                headers = dict(response.headers)
                headers["content-length"] = str(len(new_response_body))
                return Response(
                    content=new_response_body,
                    status_code=response.status_code,
                    headers=headers,
                    media_type=response.media_type
                )

        return response
