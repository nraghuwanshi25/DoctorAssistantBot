# completion_service.py
"""Completion API service layer."""

import json
import os
import time as time_module
import asyncio
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from InMemoryChatStoreNew import InMemoryChatStoreNew
from DoctorDetailService import DoctorDetailService
from Database import get_async_session

load_dotenv()

load_dotenv()  # loads .env from current working directory
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set in .env or environment")

print("Loaded OPENAI_API_KEY (length):", len(OPENAI_API_KEY))

class ChatRequest(BaseModel):
    userid: str = Field(..., alias="userid")
    userMessage: str = Field(..., alias="userMessage")


# ---------------------------
# Async runner wrapper
# ---------------------------
async def _run_async_db_call(fn, *args, **kwargs):
    try:
        async with get_async_session() as session:  # <-- unwrap the async generator
            service = DoctorDetailService(session)
            return await fn(service, *args, **kwargs)
    except Exception as exc:
        # Log the exception for debugging
        print(f"[ERROR] Exception during DB/service call: {exc}")
        return {
            "status": "error",
            "message": "Something went wrong while processing your request. Please try again later."
        }


def async_run(fn, *args, **kwargs):
    """
    Run an async service function from sync code.
    Uses asyncio.run() (safe if no event loop is running).
    If an event loop is already running, falls back to
    creating a new loop and running there (thread-based fallback).
    """
    try:
        return asyncio.run(_run_async_db_call(fn, *args, **kwargs))
    except RuntimeError:
        # event loop already running (e.g. uvicorn). Create a new loop in a thread.
        loop = asyncio.new_event_loop()
        result = None

        def _target():
            nonlocal result
            result = loop.run_until_complete(_run_async_db_call(fn, *args, **kwargs))
            loop.close()

        import threading
        t = threading.Thread(target=_target)
        t.start()
        t.join()
        return result


# ---------------------------
# Service wrapper functions
# ---------------------------
async def _f_get_doctors(service: DoctorDetailService):
    return await service.get_doctors()


async def _f_filter_doctors(service: DoctorDetailService, specialty: str):
    return await service.filter_doctors(specialty)


async def _f_get_doctor_availability(
        service: DoctorDetailService,
        doctor_name: str,
        date: Optional[str] = None,
        include_booked: bool = False
):
    return await service.get_doctor_availability(
        doctor_name=doctor_name,
        date=date,
        include_booked=include_booked
    )


async def _f_book_appointment(
        service: DoctorDetailService,
        user_id: str,
        doctor_name: str,
        date: str,
        time_range: str,
        patient_name: str,
        email: str,
        phone: str
):
    return await service.book_appointment(
        user_id=user_id,
        doctor_name=doctor_name,
        date=date,
        time_range=time_range,
        patient_name=patient_name,
        email=email,
        phone=phone
    )


async def _f_recommend_alternatives(
        service: DoctorDetailService,
        doctor_name: str,
        date: str,
        start_time: str,
        end_time: str
):
    # convert start_time/end_time strings "HH:MM" or "HH:MM:SS" to time objects
    from datetime import time as dt_time
    def _parse(t: str) -> dt_time:
        if len(t.split(":")) == 2:
            return dt_time.fromisoformat(t + ":00")
        return dt_time.fromisoformat(t)
    st = _parse(start_time)
    et = _parse(end_time)
    return await service.recommend_alternatives(doctor_name, date, st, et)


# ---------------------------
# FUNCTION_MAP (maps tool calls to run-time wrappers)
# ---------------------------
def _get_arg(d: Dict[str, Any], *keys, default=None):
    for k in keys:
        if k in d:
            return d[k]
    return default


def _to_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return bool(value)


FUNCTION_MAP = {
    "get_doctors": lambda **a: async_run(_f_get_doctors),
    "filter_doctors": lambda **a: async_run(_f_filter_doctors, _get_arg(a, "specialty", "speciality")),
    "get_doctor_availability": lambda **a: async_run(
        _f_get_doctor_availability,
        a.get("doctor_name"),
        a.get("date", None),
        _to_bool(a.get("include_booked", False))
    ),
    "book_appointment": lambda **a: async_run(
        _f_book_appointment,
        _get_arg(a, "user_id", "user_id", default="anonymous"),
        a.get("doctor_name"),
        a.get("date"),
        _get_arg(a, "time", "time_range", default=a.get("time_range")),
        a.get("patient_name"),
        a.get("email"),
        a.get("phone")
    ),
    "recommend_alternatives": lambda **a: async_run(
        _f_recommend_alternatives,
        a.get("doctor_name"),
        a.get("date"),
        a.get("start_time"),
        a.get("end_time")
    ),
}


# ---------------------------
# Rate-limit helper (kept)
# ---------------------------
def _maybe_wait_and_retry(response: requests.Response, attempt: int, max_attempts: int, base_delay: int) -> bool:
    if response.status_code != 429:
        return False
    if attempt >= max_attempts:
        raise requests.exceptions.HTTPError("429 Too Many Requests", response=response)

    delay = base_delay * (2**attempt)
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            delay = int(retry_after)
        except ValueError:
            pass
    print(f"⚠️ Rate limit hit (429). Retrying in {delay}s (attempt {attempt + 1}/{max_attempts})")
    time_module.sleep(delay)
    return True


# ---------------------------
# OpenAI call & function-calling loop
# ---------------------------
# ---------------------------
# OpenAI call & function-calling loop with error handling
# ---------------------------
def _call_openai(messages: List[Dict[str, Any]], user_id: str) -> str:
    if not OPENAI_API_KEY:
        return "(fallback) Assistant is offline."

    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}


    while True:
        payload = {
            "model": "gpt-4o-mini",
            "messages": messages,
            "functions": InMemoryChatStoreNew.FUNCTIONS,
            "function_call": "auto",
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()

            data = response.json()
            assistant_message = data["choices"][0]["message"]

            # -------------------------------------------------------------------
            # 1. Modern multi-tool format (tool_calls)
            # -------------------------------------------------------------------
            if "tool_calls" in assistant_message:
                messages.append(assistant_message)

                for tool_call in assistant_message["tool_calls"]:
                    fn_info = tool_call.get("function") or tool_call.get("function_call")
                    if not fn_info:
                        continue

                    fn_name = fn_info.get("name")
                    args = json.loads(fn_info.get("arguments", "{}"))

                    function = FUNCTION_MAP.get(fn_name)
                    if function:
                        if fn_name == 'book_appointment':
                            args["user_id"] = args.get("user_id", user_id)

                        result = function(**args)

                        func_message: Dict[str, Any] = {
                            "role": "function",
                            "name": fn_name,
                            "content": json.dumps(result),
                        }

                        call_id = tool_call.get("id")
                        if call_id:
                            func_message["tool_call_id"] = call_id

                        messages.append(func_message)

                InMemoryChatStoreNew.set_messages(user_id, messages)
                continue  # <--- IMPORTANT (NO RECURSION)

            # -------------------------------------------------------------------
            # 2. Legacy single function_call
            # -------------------------------------------------------------------
            if "function_call" in assistant_message:
                fn_name = assistant_message["function_call"]["name"]
                args = json.loads(assistant_message["function_call"].get("arguments", "{}"))

                function = FUNCTION_MAP.get(fn_name)
                if function:
                    if fn_name == 'book_appointment':
                        args["user_id"] = args.get("user_id", user_id)

                    result = function(**args)

                    messages.append(assistant_message)
                    messages.append({
                        "role": "function",
                        "name": fn_name,
                        "content": json.dumps(result)
                    })

                    InMemoryChatStoreNew.set_messages(user_id, messages)
                    continue  # <--- LOOP AGAIN

            # -------------------------------------------------------------------
            # 3. No more function calls → final assistant message
            # -------------------------------------------------------------------
            assistant_text = assistant_message.get("content", "") or ""
            messages.append({"role": "assistant", "content": assistant_text})
            InMemoryChatStoreNew.set_messages(user_id, messages)
            InMemoryChatStoreNew.print_user_history(user_id)

            return assistant_text

        except Exception as exc:
            print(f"[ERROR] Exception during _call_openai: {exc}")
        return {
            "status": "error",
            "message": "Unable to contact the assistant at the moment. Please try again later."
        }

def process_chat(request: ChatRequest) -> str:
    user_id = request.userid
    user_message = request.userMessage

    InMemoryChatStoreNew.add_message(user_id, {"role": "user", "content": user_message})

    try:
        return _call_openai(InMemoryChatStoreNew.get_messages(user_id), user_id)
    except Exception as exc:
        return f"Error contacting assistant: {exc}"
