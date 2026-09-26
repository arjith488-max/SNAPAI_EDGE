"""
SnapAI Edge - Privacy Guard
Scans input text for sensitive data (API keys, passwords, emails, phone numbers, credentials, financial data).
Never claims 100% detection. Provides mask and routing guidance.
"""

import re
from typing import List, Dict, Any
from pydantic import BaseModel, Field


class SensitiveItem(BaseModel):
    category: str
    match_preview: str  # masked preview, e.g. "sk-***"
    start: int
    end: int


class PrivacyScanResult(BaseModel):
    has_sensitive_data: bool = False
    detected_categories: List[str] = Field(default_factory=list)
    items: List[SensitiveItem] = Field(default_factory=list)
    risk_level: str = "none"  # "none" | "low" | "medium" | "high"
    warning: str = ""


class PrivacyGuard:
    """
    Pattern-matching privacy analyzer for user inputs and documents before cloud transmission.
    """

    PATTERNS = {
        "api_key": [
            r"\bsk-[a-zA-Z0-9]{20,}\b",                # OpenAI style
            r"\bAIza[0-9A-Za-z-_]{35}\b",              # Google AI / Maps
            r"\bAKIA[0-9A-Z]{16}\b",                    # AWS Access Key
            r"\bghp_[a-zA-Z0-9]{36}\b",                # GitHub Personal Token
            r"\bglpat-[a-zA-Z0-9\-]{20}\b",            # GitLab Token
            r"(?i)\b(?:api[_-]?key|secret[_-]?key|access[_-]?token)[\s:=]+['\"]?([a-zA-Z0-9_\-]{16,})['\"]?",
        ],
        "password": [
            r"(?i)\b(?:password|passwd|pwd)[\s:=]+['\"]?([^\s'\"]{6,})['\"]?",
            r"(?i)\b(?:client[_-]?secret)[\s:=]+['\"]?([^\s'\"]{8,})['\"]?",
        ],
        "email": [
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b",
        ],
        "phone_number": [
            r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        ],
        "financial": [
            # Credit card (Visa, MasterCard, Amex, Discover - 13 to 16 digits)
            r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
            r"\b3[47]\d{2}[-\s]?\d{6}[-\s]?\d{5}\b",
            # IBAN
            r"\b[A-Z]{2}\d{2}[A-Z0-9]{12,30}\b",
        ],
        "identifier": [
            # SSN format: 000-00-0000
            r"\b\d{3}-\d{2}-\d{4}\b",
        ],
    }

    @classmethod
    def scan(cls, text: str) -> PrivacyScanResult:
        """Scan text and return detailed findings."""
        if not text:
            return PrivacyScanResult()

        found_items: List[SensitiveItem] = []
        categories: set = set()

        for category, regex_list in cls.PATTERNS.items():
            for pat in regex_list:
                for match in re.finditer(pat, text):
                    categories.add(category)
                    matched_str = match.group(0)
                    # Mask preview for safe reporting (never expose full secrets in logs/response)
                    if len(matched_str) > 6:
                        preview = matched_str[:2] + "****" + matched_str[-2:]
                    else:
                        preview = "****"
                    found_items.append(
                        SensitiveItem(
                            category=category,
                            match_preview=preview,
                            start=match.start(),
                            end=match.end(),
                        )
                    )

        if not found_items:
            return PrivacyScanResult(
                has_sensitive_data=False,
                risk_level="none",
                warning="No sensitive patterns detected.",
            )

        cat_list = sorted(list(categories))
        risk = "high" if any(c in ("api_key", "password", "financial", "identifier") for c in cat_list) else "medium"
        warning = f"Sensitive data detected ({', '.join(cat_list)}). Processing locally is recommended to safeguard privacy."

        return PrivacyScanResult(
            has_sensitive_data=True,
            detected_categories=cat_list,
            items=found_items,
            risk_level=risk,
            warning=warning,
        )

    @classmethod
    def mask(cls, text: str) -> str:
        """Replace detected sensitive items with safe tokens like [MASKED_EMAIL]."""
        if not text:
            return text

        masked_text = text
        for category, regex_list in cls.PATTERNS.items():
            token = f"[MASKED_{category.upper()}]"
            for pat in regex_list:
                masked_text = re.sub(pat, token, masked_text)

        return masked_text


# Singleton
privacy_guard = PrivacyGuard()
