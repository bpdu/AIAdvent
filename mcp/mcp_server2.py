"""
MCP Server с LibreTranslate API для перевода на эсперанто
День 14: Композиция MCP-инструментов

WebSocket сервер для перевода текста на эсперанто через LibreTranslate API.
"""

import asyncio
import json
import logging
import requests

from mcp.server import Server
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.routing import Route, WebSocketRoute
from starlette.requests import Request
from starlette.responses import Response
from starlette.websockets import WebSocket
import uvicorn

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LibreTranslate API configuration
LIBRETRANSLATE_API_URL = "https://libretranslate.com/translate"
LIBRETRANSLATE_LANGUAGES_URL = "https://libretranslate.com/languages"

# Создаём MCP сервер
mcp_server = Server("translation-mcp-server")


def check_esperanto_available():
    """Проверить, доступен ли эсперанто на LibreTranslate сервере."""
    try:
        logger.info("Checking if Esperanto is available on LibreTranslate...")
        response = requests.get(LIBRETRANSLATE_LANGUAGES_URL, timeout=5)
        response.raise_for_status()
        languages = response.json()

        # Проверяем наличие кода "eo" (Esperanto)
        eo_available = any(lang.get("code") == "eo" for lang in languages)

        if eo_available:
            logger.info("✓ Esperanto (eo) is available on LibreTranslate")
        else:
            logger.warning("✗ Esperanto (eo) is NOT available on this LibreTranslate instance")
            logger.info(f"Available languages: {[lang.get('code') for lang in languages[:10]]}")

        return eo_available

    except Exception as e:
        logger.error(f"Error checking language support: {e}")
        return False


def translate_to_esperanto(text: str) -> str:
    """
    Перевести русский текст на эсперанто через LibreTranslate API.

    Args:
        text: Текст на русском языке для перевода

    Returns:
        Переведенный текст на эсперанто или сообщение об ошибке
    """
    if not text or not text.strip():
        return json.dumps({"error": "Empty text provided"})

    try:
        logger.info(f"Translating text to Esperanto ({len(text)} chars)...")

        # Подготовка запроса к LibreTranslate API
        payload = {
            "q": text,
            "source": "ru",  # Russian
            "target": "eo",  # Esperanto
            "format": "text",
            "api_key": ""  # Публичный API, ключ не требуется
        }

        # Отправка POST запроса
        response = requests.post(
            LIBRETRANSLATE_API_URL,
            json=payload,
            timeout=30  # Более длинный timeout для больших текстов
        )

        logger.info(f"LibreTranslate response status: {response.status_code}")

        if response.status_code != 200:
            logger.error(f"LibreTranslate API error: {response.text}")
            return json.dumps({
                "error": f"LibreTranslate API returned status {response.status_code}",
                "original_text": text
            })

        response.raise_for_status()
        result = response.json()

        # Извлекаем переведенный текст
        translated_text = result.get("translatedText", "")

        if not translated_text:
            logger.error("Empty translation received from LibreTranslate")
            return json.dumps({
                "error": "Empty translation received",
                "original_text": text
            })

        logger.info(f"Translation successful ({len(translated_text)} chars)")
        return translated_text

    except requests.exceptions.Timeout:
        logger.error("LibreTranslate API timeout")
        return json.dumps({
            "error": "Translation service timeout",
            "original_text": text
        })
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling LibreTranslate API: {e}")
        return json.dumps({
            "error": f"Translation service error: {str(e)}",
            "original_text": text
        })
    except Exception as e:
        logger.error(f"Unexpected error during translation: {e}", exc_info=True)
        return json.dumps({
            "error": f"Unexpected error: {str(e)}",
            "original_text": text
        })


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """Возвращает список доступных инструментов."""
    return [
        Tool(
            name="translate-to-esperanto",
            description="Translate Russian text to Esperanto using LibreTranslate API",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Russian text to translate to Esperanto"
                    }
                },
                "required": ["text"]
            }
        )
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Вызов инструмента."""
    if name == "translate-to-esperanto":
        text = arguments.get("text", "")
        translated_text = translate_to_esperanto(text)
        return [TextContent(
            type="text",
            text=translated_text
        )]
    else:
        return [TextContent(
            type="text",
            text=f"Инструмент не найден: {name}"
        )]


async def root(request: Request):
    """Корневой endpoint."""
    return Response(
        content=json.dumps({
            "name": "Translation MCP Server",
            "version": "1.0.0",
            "protocol": "MCP",
            "endpoint": "/mcp",
            "tools": 1,
            "description": "Translate text to Esperanto via LibreTranslate API"
        }),
        media_type="application/json"
    )


async def handle_websocket(websocket: WebSocket):
    """Обработчик WebSocket endpoint для MCP протокола."""
    # Принимаем WebSocket с subprotocol "mcp"
    subprotocol = None
    if "mcp" in websocket.headers.get("sec-websocket-protocol", "").split(", "):
        subprotocol = "mcp"

    await websocket.accept(subprotocol=subprotocol)
    logger.info(f"Новое WebSocket подключение от {websocket.client}, subprotocol={subprotocol}")

    try:
        while True:
            # Получаем сообщение от клиента
            data = await websocket.receive_text()
            logger.info(f"Received message: {data[:200]}")

            try:
                request = json.loads(data)
                method = request.get("method")
                request_id = request.get("id")
                params = request.get("params", {})

                logger.info(f"JSON-RPC request: method={method}, id={request_id}")

                # Обработка initialize
                if method == "initialize":
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {
                                "tools": {}
                            },
                            "serverInfo": {
                                "name": "translation-mcp-server",
                                "version": "1.0.0"
                            }
                        }
                    }
                    await websocket.send_text(json.dumps(response))
                    logger.info("Sent initialize response")

                # Обработка tools/list
                elif method == "tools/list":
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "tools": [
                                {
                                    "name": "translate-to-esperanto",
                                    "description": "Translate Russian text to Esperanto using LibreTranslate API",
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {
                                            "text": {
                                                "type": "string",
                                                "description": "Russian text to translate to Esperanto"
                                            }
                                        },
                                        "required": ["text"]
                                    }
                                }
                            ]
                        }
                    }
                    await websocket.send_text(json.dumps(response))
                    logger.info("Sent tools/list response")

                # Обработка tools/call
                elif method == "tools/call":
                    tool_name = params.get("name")
                    tool_arguments = params.get("arguments", {})
                    logger.info(f"Calling tool: {tool_name}")

                    if tool_name == "translate-to-esperanto":
                        # Переводим текст на эсперанто
                        text = tool_arguments.get("text", "")
                        translated_text = translate_to_esperanto(text)

                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": {
                                "content": [
                                    {
                                        "type": "text",
                                        "text": translated_text
                                    }
                                ]
                            }
                        }
                        await websocket.send_text(json.dumps(response))
                        logger.info(f"Sent tool response: {len(translated_text)} chars")
                    else:
                        # Неизвестный tool
                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": -32601,
                                "message": f"Tool not found: {tool_name}"
                            }
                        }
                        await websocket.send_text(json.dumps(response))

                # Обработка notifications/initialized
                elif method == "notifications/initialized":
                    # Это notification, не требует ответа
                    logger.info("Received initialized notification")

                else:
                    # Неизвестный метод
                    logger.warning(f"Unknown method: {method}")
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}"
                        }
                    }
                    await websocket.send_text(json.dumps(response))

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": "Parse error"
                    }
                }
                await websocket.send_text(json.dumps(error_response))
            except Exception as e:
                logger.error(f"Error processing request: {e}", exc_info=True)
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id") if 'request' in locals() else None,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }
                await websocket.send_text(json.dumps(error_response))

    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        logger.info("WebSocket connection closed")


# Создаём приложение
app = Starlette(
    routes=[
        Route("/", root),
        WebSocketRoute("/mcp", handle_websocket),
    ]
)


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Translation MCP Server запущен (WebSocket)")
    logger.info("День 14: Композиция MCP-инструментов")
    logger.info("=" * 60)

    # Проверяем доступность эсперанто
    esperanto_available = check_esperanto_available()

    logger.info(f"LibreTranslate API: {LIBRETRANSLATE_API_URL}")
    logger.info(f"Esperanto support: {'✓ available' if esperanto_available else '✗ unavailable'}")
    logger.info("Доступные инструменты: 1")
    logger.info("  - translate-to-esperanto: Translate Russian text to Esperanto")
    logger.info("=" * 60)
    logger.info("WebSocket endpoint: ws://localhost:8081/mcp")
    logger.info("=" * 60)

    if not esperanto_available:
        logger.warning("⚠️  Esperanto may not be available - translations might fail")

    uvicorn.run(app, host="0.0.0.0", port=8081)
