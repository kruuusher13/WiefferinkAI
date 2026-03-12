"""
Gemini Text LLM Client
=======================

Wraps Gemini 2.5 Flash as a streaming text LLM with tool calling.
Replaces the Gemini Live API for reasoning — no audio generation overhead.
"""

import os
import json
import asyncio
import logging
from typing import Callable, Awaitable, Optional
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("gemini-llm")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"


def _build_tools(tools_schema: list) -> list[types.Tool]:
    """Convert Live API tool schema format to google-genai Tool format."""
    declarations = []
    for tool_group in tools_schema:
        for decl in tool_group.get("function_declarations", []):
            declarations.append(types.FunctionDeclaration(
                name=decl["name"],
                description=decl["description"],
                parameters=decl.get("parameters"),
            ))
    return [types.Tool(function_declarations=declarations)]


class GeminiLLM:
    """
    Streaming text LLM with tool calling via Gemini 2.5 Flash.

    Manages conversation history and supports tool call loops
    (model calls tool → result fed back → model continues).
    """

    def __init__(self, system_instruction: str, tools_schema: list):
        self._client = genai.Client(api_key=GOOGLE_API_KEY)
        self._model = GEMINI_MODEL
        self._system_instruction = system_instruction
        self._tools = _build_tools(tools_schema)
        self._history: list[types.Content] = []
        self._cancelled = False
        logger.info(f"GeminiLLM initialized (model={self._model})")

    async def generate_response(
        self,
        user_text: str,
        on_text_chunk: Callable[[str], Awaitable[None]],
        on_tool_call: Callable[[str, dict], Awaitable[str]],
    ) -> str:
        """
        Generate a streaming response for user_text.

        Calls on_text_chunk(chunk) for each streamed text token.
        Calls on_tool_call(name, args) -> result for tool calls.
        Returns the full response text.
        """
        self._cancelled = False

        # Add user message to history
        self._history.append(types.Content(
            role="user",
            parts=[types.Part(text=user_text)],
        ))

        full_response = await self._generate_with_tools(on_text_chunk, on_tool_call)
        return full_response

    async def _generate_with_tools(
        self,
        on_text_chunk: Callable[[str], Awaitable[None]],
        on_tool_call: Callable[[str, dict], Awaitable[str]],
    ) -> str:
        """Generate response, handling tool call loops."""
        full_text = ""

        while True:
            if self._cancelled:
                break

            text_parts = []
            tool_calls = []

            try:
                response = await self._client.aio.models.generate_content_stream(
                    model=self._model,
                    contents=self._history,
                    config=types.GenerateContentConfig(
                        system_instruction=self._system_instruction,
                        tools=self._tools,
                        temperature=0.7,
                    ),
                )

                async for chunk in response:
                    if self._cancelled:
                        break

                    if not chunk.candidates:
                        continue

                    candidate = chunk.candidates[0]
                    if not candidate.content or not candidate.content.parts:
                        continue

                    for part in candidate.content.parts:
                        if part.text:
                            text_parts.append(part.text)
                            full_text += part.text
                            await on_text_chunk(part.text)
                        elif part.function_call:
                            tool_calls.append(part.function_call)

            except Exception as e:
                logger.error(f"Gemini generate error: {e}")
                break

            # Add model response to history
            model_parts = []
            if text_parts:
                model_parts.append(types.Part(text="".join(text_parts)))
            for tc in tool_calls:
                model_parts.append(types.Part(function_call=tc))
            if model_parts:
                self._history.append(types.Content(role="model", parts=model_parts))

            # If no tool calls, we're done
            if not tool_calls:
                break

            # Execute tool calls and feed results back
            tool_response_parts = []
            for tc in tool_calls:
                name = tc.name
                args = dict(tc.args) if tc.args else {}
                logger.info(f"Tool call: {name}({args})")
                result = await on_tool_call(name, args)
                tool_response_parts.append(types.Part(
                    function_response=types.FunctionResponse(
                        name=name,
                        response={"result": str(result)},
                    )
                ))

            self._history.append(types.Content(
                role="user",
                parts=tool_response_parts,
            ))
            # Loop continues — Gemini will generate text based on tool results

        return full_text

    def add_context(self, text: str):
        """Add a context message (for language switch, takeover, etc.)."""
        self._history.append(types.Content(
            role="user",
            parts=[types.Part(text=text)],
        ))

    def cancel(self):
        """Cancel current generation (for interruption)."""
        self._cancelled = True

    def trim_history(self, max_turns: int = 40):
        """Keep history manageable for long calls."""
        if len(self._history) > max_turns:
            self._history = self._history[-max_turns:]

    def reset(self):
        """Clear conversation history."""
        self._history.clear()
