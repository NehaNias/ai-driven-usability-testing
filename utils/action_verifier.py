import base64
import hashlib
import json
import re
import time
import io
from playwright.sync_api import Page
from google.genai import types as gtypes


class ActionVerifier:
    def __init__(self, client, model: str):
        self.client = client
        self.model = model

    def _call_llm(self, prompt: str, images: list[bytes] = None) -> str:
        max_retries = 10
        for attempt in range(max_retries):
            try:
                contents = [prompt]
                if images:
                    for img_bytes in images:
                        contents.append(gtypes.Part.from_bytes(data=img_bytes, mime_type="image/png"))

                response = self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=gtypes.GenerateContentConfig(
                        temperature=0.2,
                        response_mime_type="application/json"
                    )
                )
                return response.text or ""
            except Exception as e:
                error_msg = str(e).lower()
                if "503" in error_msg or "unavailable" in error_msg:
                    wait_time = (2 ** attempt) + 1
                    print(f"Gemini 503 - Retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                print(f"LLM error: {e}")
                return ""
        return ""

    def _parse_json_response(self, text: str) -> dict:
        try:
            s, e = text.find("{"), text.rfind("}") + 1
            if s != -1 and e > s:
                return json.loads(text[s:e])
        except Exception:
            pass
        return {}

    @staticmethod
    def get_screenshot_hash(page: Page) -> str:
        return hashlib.md5(page.screenshot()).hexdigest()

    def get_screenshot_text(self, page: Page) -> str:
        try:
            screenshot = page.screenshot()
            response = self._call_llm(
                prompt=(
                    "List all visible UI text on this screenshot as a flat lowercase string. "
                    "Include button labels, headings, notifications, links, and any visible text. "
                    "Return ONLY a JSON object like: {\"text\": \"all visible text here\"}"
                ),
                images=[screenshot]
            )
            data = self._parse_json_response(response)
            return data.get("text", "").lower()
        except Exception as e:
            print(f"WARNING: Screenshot text extraction failed — {e}")
            return ""

    @staticmethod
    def looks_like_search_results(url: str) -> bool:
        u = url.lower()
        return "/s?" in u or "/search" in u or "/results" in u or "k=" in u or "q=" in u

    def _extract_verification_keywords(self, reasoning: str) -> dict[str, list[str]]:
        #Ask LLM to extract should_disappear / should_appear keywords from reasoning.
        prompt = f"""Given this browser action reasoning, extract keywords to verify the action succeeded.

REASONING: "{reasoning}"

STRICT RULES:
- should_disappear: ONLY if action explicitly CLOSES/DISMISSES/REMOVES a visible element (popup, modal, notification, banner)
  * Use UNIQUE phrases specific to that element, not generic words that appear elsewhere on the page
  * The words/phrases must uniquely identify the dismissed element
  * Extract EXACT words or short phrases that appear verbatim in the visible UI text of that element
- should_appear: ONLY if action explicitly NAVIGATES to a new page or REVEALS entirely new content not yet visible
- Return EMPTY lists for ANY of these cases:
    * Clicking a search bar, input field, or any field to focus it
    * Clicking a button to prepare for typing
    * Submitting a form or pressing enter (URL change handles this)
    * Scrolling, hovering
    * When unsure
- Max 4 words/phrases per list
- Only include text that appears verbatim as UI text on screen

Return ONLY this JSON:
{{
    "should_disappear": [],
    "should_appear": []
}}"""
        response = self._call_llm(prompt)
        data = self._parse_json_response(response)
        return {
            "should_disappear": data.get("should_disappear", []),
            "should_appear":    data.get("should_appear", [])
        }

    
    @staticmethod
    def _fuzzy_match(keyword: str, text: str, threshold: float = 0.8) -> bool:
        from difflib import SequenceMatcher
        keyword = keyword.lower()
        text = text.lower()
        
        # Direct substring check
        if re.search(r'\b' + re.escape(keyword) + r'\b', text):
            return True
        
        # Fuzzy word-by-word check only
        for word in text.split():
            ratio = SequenceMatcher(None, keyword, word).ratio()
            if ratio >= threshold:
                return True
        
        return False  

    def _check_keywords(
        self,
        keywords: dict[str, list[str]],
        before_ocr: str,
        after_ocr: str,
    ) -> tuple[bool | None, str]:
        """
        Check OCR before/after against keywords.
        Returns (True/False, reason) if conclusive, (None, reason) if inconclusive.
        """
        should_disappear = [w.lower() for w in keywords.get("should_disappear", [])]
        should_appear    = [w.lower() for w in keywords.get("should_appear", [])]

        # Prevents hallucinated keywords from causing false negatives
        should_disappear = [w for w in should_disappear if self._fuzzy_match(w, before_ocr)]

        # Discard should_appear keywords already present in before_ocr
        should_appear = [w for w in should_appear if not self._fuzzy_match(w, before_ocr)]

        # If both lists are empty after validation, then its inconclusive
        if not should_disappear and not should_appear:
            return None, "No valid keywords after validation — skipping to visual LLM"

        vanished    = [w for w in should_disappear if self._fuzzy_match(w, before_ocr) and not self._fuzzy_match(w, after_ocr)]
        still_there = [w for w in should_disappear if self._fuzzy_match(w, before_ocr) and self._fuzzy_match(w, after_ocr)]
        appeared    = [w for w in should_appear    if not self._fuzzy_match(w, before_ocr) and self._fuzzy_match(w, after_ocr)]
        missing     = [w for w in should_appear    if not self._fuzzy_match(w, after_ocr)]

        # Success
        if vanished and not still_there:
            return True, f"Confirmed — disappeared from screen: {vanished}"
        if appeared:
            return True, f"Confirmed — appeared on screen: {appeared}"

        # Failure, no positive signal at all
        if still_there and not vanished and not appeared:
            return False, f"Failed — should have disappeared but still visible: {still_there}"
        if missing and not appeared and not vanished and not still_there:
            return False, f"Failed — expected to appear but not found: {missing}"

        return None, "Inconclusive — no OCR signal for extracted keywords"


    def _verify_semantic(self, before_screenshot: bytes, after_screenshot: bytes, action: dict) -> tuple[bool, str]:
        """Ask Gemini to compare before/after screenshots and verify intended effect."""
        prompt = f"""You are verifying whether a browser action had the intended effect.

ACTION: {action.get('action')}
INTENDED EFFECT: {action.get('reasoning', '')}

You are given two screenshots: BEFORE and AFTER the action.
Note: the screenshots may look identical if the action was a focus/input click.

Rules:
- If the intended effect was to focus/activate an input or search bar → success is true even if screenshots are identical
- If the intended effect was to close/dismiss something still visible → success is false
- If the intended effect was to navigate somewhere but URL did not change → success is false

Reply ONLY with this JSON:
{{"success": true/false, "reason": "brief explanation"}}"""

        response = self._call_llm(prompt, images=[before_screenshot, after_screenshot])
        data = self._parse_json_response(response)
        return data.get("success", False), f"LLM: {data.get('reason', 'no reason given')}"


    @staticmethod
    def _verify_type(typed_text: str, after_ocr: str) -> tuple[bool, str]:
        if not typed_text:
            return False, "No typed text specified"
        ocr_clean = re.sub(r'[^a-z0-9\s]', '', after_ocr.lower())
        raw_words = typed_text.lower().split()
        words = [re.sub(r'[^a-z0-9]', '', w) for w in raw_words]
        words = [w for w in words if len(w) > 2]
        #words = [w for w in typed_text.lower().split() if len(w) > 2]
        if not words:
            return True, "No meaningful words to verify"
        matched = [w for w in words if re.search(r'\b' + re.escape(w) + r'\b', ocr_clean)]
        confidence = len(matched) / len(words)
        if confidence >= 0.75:
            return True, f"OCR matched {len(matched)}/{len(words)} words: {matched}"
        return False, f"OCR only matched {len(matched)}/{len(words)} words: {matched}"


    def verify_action_success(self, page: Page, action: dict, before_state: dict) -> tuple[bool, str]:
        act = (action.get("action") or "").upper()
        reasoning = action.get("reasoning", "")

        try:
            page.wait_for_load_state("domcontentloaded", timeout=3000)
        except Exception:
            pass

        try:
            after_url   = page.url
            after_title = page.title()
        except Exception:
            return True, "Page navigated (execution context destroyed)"

        try:
            after_hash       = self.get_screenshot_hash(page)
            after_ocr        = self.get_screenshot_text(page)
            after_screenshot = page.screenshot()
        except Exception:
            after_hash       = before_state["hash"]
            after_ocr        = ""
            after_screenshot = before_state["raw_screenshot"]

        if act == "CLICK":
            if after_url != before_state["url"] and after_url != "about:blank":
                if self.looks_like_search_results(after_url):
                    return True, "Search results URL detected"
                return True, "URL changed after click"

            if after_hash != before_state["hash"]:
                # Step 1: keyword extraction + OCR check
                if reasoning:
                    keywords = self._extract_verification_keywords(reasoning)
                    if keywords["should_disappear"] or keywords["should_appear"]:
                        success, reason = self._check_keywords(
                            keywords,
                            before_state["ocr_text"],
                            after_ocr
                        )
                        if success is True:        
                            return True, reason
                        if success is False:       
                            return False, reason
                    
                    return self._verify_semantic(
                        before_state["raw_screenshot"],
                        after_screenshot,
                        action
                    )
                return True, "Visual change detected — no reasoning to verify against"

            if reasoning:
                success, reason = self._verify_semantic(
                    before_state["raw_screenshot"],
                    after_screenshot,
                    action
                )
                return success, reason
            return True, "Click accepted optimistically — no reasoning to verify against"

        if act == "TYPE":
            return self._verify_type(action.get("text", ""), after_ocr)

        if act == "PRESS_ENTER":
            if after_url != before_state["url"]:
                return True, "Enter triggered navigation"
            if self.looks_like_search_results(after_url):
                return True, "Search results URL detected"
            if after_hash != before_state["hash"]:
                return True, "Visual change after Enter"
            return False, "Enter had no effect — CLICK or TYPE may have failed upstream"

        if act == "SCROLL":
            changed = after_hash != before_state["hash"]
            return changed, "Scroll caused visual change" if changed else "Scroll had no effect"

        if act == "DRAG":
            changed = after_hash != before_state["hash"]
            return changed, "Drag caused visual change" if changed else "Drag had no visual effect"

        changed = after_hash != before_state["hash"]
        return changed, "Visual change detected" if changed else "No visual change detected"

    
    @staticmethod
    def get_verification_feedback(action: dict, success: bool, reason: str) -> str | None:
        if success:
            return None
        return (
            f"PREVIOUS_ACTION_FAILED: {action.get('action', 'UNKNOWN')} — {reason}. "
            f"Please retry with better precision."
        )
