"""
MCP Server с MyMemory API для перевода на эсперанто
День 14: Композиция MCP-инструментов

WebSocket сервер для перевода текста на эсперанто через MyMemory Translation API.
Бесплатный API без регистрации, лимит: 10000 слов/день.
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

# MyMemory Translation API configuration (free, no registration required)
MYMEMORY_API_URL = "https://api.mymemory.translated.net/get"

# Создаём MCP сервер
mcp_server = Server("translation-mcp-server")


def check_esperanto_available():
    """Проверить, доступен ли эсперанто на MyMemory API."""
    try:
        logger.info("Checking if MyMemory API is available...")
        # Пробный запрос для проверки работы API
        test_params = {
            "q": "test",
            "langpair": "ru|eo"
        }
        response = requests.get(MYMEMORY_API_URL, params=test_params, timeout=5)
        response.raise_for_status()

        result = response.json()
        if result.get("responseStatus") == 200:
            logger.info("✓ MyMemory API is working, Esperanto supported")
            return True
        else:
            logger.warning(f"✗ MyMemory API returned status: {result.get('responseStatus')}")
            return False

    except Exception as e:
        logger.error(f"Error checking MyMemory API: {e}")
        return False


def translate_to_esperanto(text: str) -> str:
    """
    Перевести русский текст на эсперанто через MyMemory Translation API.

    Args:
        text: Текст на русском языке для перевода

    Returns:
        Переведенный текст на эсперанто или сообщение об ошибке
    """
    if not text or not text.strip():
        return json.dumps({"error": "Empty text provided"})

    try:
        logger.info(f"Translating text to Esperanto ({len(text)} chars)...")

        # MyMemory API имеет лимит на длину текста (~500 символов за раз)
        # Если текст длинный, разбиваем на части
        max_chunk_size = 500

        if len(text) > max_chunk_size:
            logger.info(f"Text is long ({len(text)} chars), splitting into chunks...")
            # Разбиваем по параграфам
            paragraphs = text.split('\n\n')
            translated_parts = []

            for para in paragraphs:
                if not para.strip():
                    translated_parts.append('')
                    continue

                # Если параграф все еще слишком длинный, разбиваем по предложениям
                if len(para) > max_chunk_size:
                    sentences = para.split('. ')
                    chunk = ''
                    para_translation = []

                    for sentence in sentences:
                        if len(chunk) + len(sentence) < max_chunk_size:
                            chunk += sentence + '. '
                        else:
                            if chunk:
                                trans = _translate_chunk(chunk.strip())
                                if trans:
                                    para_translation.append(trans)
                            chunk = sentence + '. '

                    if chunk:
                        trans = _translate_chunk(chunk.strip())
                        if trans:
                            para_translation.append(trans)

                    translated_parts.append(' '.join(para_translation))
                else:
                    trans = _translate_chunk(para)
                    if trans:
                        translated_parts.append(trans)

            final_translation = '\n\n'.join(translated_parts)
            logger.info(f"Translation successful ({len(final_translation)} chars)")
            return final_translation
        else:
            # Короткий текст, переводим целиком
            return _translate_chunk(text)

    except requests.exceptions.Timeout:
        logger.error("MyMemory API timeout")
        return json.dumps({
            "error": "Translation service timeout",
            "original_text": text
        })
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling MyMemory API: {e}")
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


def _translate_chunk(text: str) -> str:
    """
    Перевести небольшой фрагмент текста через MyMemory API.

    Args:
        text: Текст для перевода (должен быть < 500 символов)

    Returns:
        Переведенный текст
    """
    params = {
        "q": text,
        "langpair": "ru|eo"  # Russian to Esperanto
    }

    response = requests.get(
        MYMEMORY_API_URL,
        params=params,
        timeout=30
    )

    logger.info(f"MyMemory API response status: {response.status_code}")

    if response.status_code != 200:
        logger.error(f"MyMemory API error: {response.text}")
        raise Exception(f"MyMemory API returned status {response.status_code}")

    response.raise_for_status()
    result = response.json()

    # Проверяем статус ответа
    if result.get("responseStatus") != 200:
        logger.error(f"MyMemory API error: {result}")
        raise Exception(f"MyMemory API error: {result.get('responseDetails', 'Unknown error')}")

    # Извлекаем переведенный текст
    translated_text = result.get("responseData", {}).get("translatedText", "")

    if not translated_text:
        logger.error("Empty translation received from MyMemory")
        raise Exception("Empty translation received")

    return translated_text


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """Возвращает список доступных инструментов."""
    return [
        Tool(
            name="translate-to-esperanto",
            description="Translate Russian text to Esperanto using MyMemory Translation API",
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
            "description": "Translate text to Esperanto via MyMemory Translation API"
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
                                    "description": "Translate Russian text to Esperanto using MyMemory Translation API",
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

    # Проверяем доступность MyMemory API
    esperanto_available = check_esperanto_available()

    logger.info(f"MyMemory API: {MYMEMORY_API_URL}")
    logger.info(f"API Status: {'✓ available' if esperanto_available else '✗ unavailable'}")
    logger.info("Доступные инструменты: 1")
    logger.info("  - translate-to-esperanto: Translate Russian text to Esperanto")
    logger.info("Лимит: 10000 слов/день (бесплатный API)")
    logger.info("=" * 60)
    logger.info("WebSocket endpoint: ws://localhost:8081/mcp")
    logger.info("=" * 60)

    if not esperanto_available:
        logger.warning("⚠️  MyMemory API may not be available - translations might fail")

    uvicorn.run(app, host="0.0.0.0", port=8081)
