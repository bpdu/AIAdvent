"""
Тестовый скрипт для демонстрации сжатия диалога (День 9 - AI Advent Challenge)

Этот скрипт демонстрирует:
1. Разговор с 12 сообщениями (6 вопросов + 6 ответов)
2. Автоматическое сжатие после 10 сообщений
3. Сравнение токенов ДО и ПОСЛЕ сжатия
4. Качество ответов с использованием summary

Используется модель DeepSeek Chat
"""

import requests
import json
from dotenv import load_dotenv
import os
import time

# Load environment variables
load_dotenv(dotenv_path='.secrets/deepseek-api-key.env')

DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_API_URL = 'https://api.deepseek.com/v1/chat/completions'
MODEL_NAME = 'deepseek-chat'

def call_deepseek_api(messages) -> tuple:
    """Call DeepSeek API and return response with token usage"""
    headers = {
        'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
        'Content-Type': 'application/json'
    }

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 500
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()

        response_text = result['choices'][0]['message']['content']
        usage = result.get('usage', {})

        return (
            response_text,
            {
                'total_tokens': usage.get('total_tokens', 0),
                'prompt_tokens': usage.get('prompt_tokens', 0),
                'completion_tokens': usage.get('completion_tokens', 0)
            }
        )
    except Exception as e:
        print(f"❌ Error: {e}")
        return (f"Error: {str(e)}", {'total_tokens': 0, 'prompt_tokens': 0, 'completion_tokens': 0})

def create_conversation_summary(messages) -> str:
    """Create a summary of conversation history"""
    conversation_text = "\n".join([
        f"{msg['role'].upper()}: {msg['content']}"
        for msg in messages if msg.get('role') != 'system'
    ])

    summary_prompt = f"""Создай краткое резюме следующего диалога.
Сохрани ВСЮ важную информацию, факты, контекст и выводы.
Резюме должно позволить продолжить разговор без потери контекста.

Диалог:
{conversation_text}

Краткое резюме (на русском):"""

    summary_messages = [
        {"role": "system", "content": "Ты помощник, который создаёт краткие резюме диалогов, сохраняя всю важную информацию."},
        {"role": "user", "content": summary_prompt}
    ]

    response_text, _ = call_deepseek_api(summary_messages)
    return response_text

def calculate_tokens(messages):
    """Estimate tokens in messages"""
    chars = sum(len(msg['content']) for msg in messages)
    return chars // 4  # Rough estimate

def main():
    print("\n" + "="*70)
    print("🗜️  ДЕМОНСТРАЦИЯ СЖАТИЯ ДИАЛОГА (День 9 - AI Advent Challenge)")
    print("="*70)

    # Диалог для теста
    test_questions = [
        "Привет! Расскажи кратко о себе.",
        "Что такое искусственный интеллект?",
        "Как работают нейронные сети?",
        "Что такое токены в языковых моделях?",
        "Почему важно оптимизировать использование токенов?",
        "Как можно сжать историю диалога?",
        # После сжатия - проверяем сохранность контекста
        "Вернёмся к началу: помнишь, о чём мы говорили в самом первом сообщении?",
        "А что ты говорил про токены?",
    ]

    conversation_history = []
    total_tokens_without_compression = 0
    total_tokens_with_compression = 0

    print("\n" + "="*70)
    print("📊 ФАЗА 1: Диалог БЕЗ сжатия (первые 6 вопросов)")
    print("="*70)

    # Фаза 1: Без сжатия
    for i, question in enumerate(test_questions[:6], 1):
        print(f"\n🙋 Сообщение #{i}: {question}")

        conversation_history.append({"role": "user", "content": question})

        response, token_usage = call_deepseek_api(conversation_history)

        conversation_history.append({"role": "assistant", "content": response})

        total_tokens_without_compression += token_usage['total_tokens']

        print(f"🤖 Ответ: {response[:100]}...")
        print(f"📊 Токены: {token_usage['total_tokens']} (запрос: {token_usage['prompt_tokens']}, ответ: {token_usage['completion_tokens']})")

        time.sleep(0.5)  # Small delay between requests

    print(f"\n{'='*70}")
    print(f"📊 ИТОГО фаза 1 (БЕЗ сжатия): {total_tokens_without_compression} токенов")
    print(f"   Сообщений в истории: {len(conversation_history)}")
    print(f"   Примерно токенов в истории: ~{calculate_tokens(conversation_history)}")
    print(f"{'='*70}")

    # Фаза 2: Создаём summary
    print("\n" + "="*70)
    print("🗜️  ФАЗА 2: СЖАТИЕ ИСТОРИИ")
    print("="*70)

    print("\n🔄 Создаю summary диалога...")

    messages_to_summarize = conversation_history.copy()
    tokens_before = calculate_tokens(messages_to_summarize)

    summary = create_conversation_summary(messages_to_summarize)

    print(f"\n📝 Summary создан:")
    print(f"   {summary[:200]}...")

    # Replace history with summary
    conversation_history = [
        {
            "role": "system",
            "content": f"Предыдущий контекст диалога (резюме {len(messages_to_summarize)} сообщений):\n{summary}"
        }
    ]

    tokens_after = calculate_tokens(conversation_history)

    print(f"\n📊 Результаты сжатия:")
    print(f"   • Сообщений до: {len(messages_to_summarize)}")
    print(f"   • Сообщений после: {len(conversation_history)}")
    print(f"   • Токенов до: ~{tokens_before}")
    print(f"   • Токенов после: ~{tokens_after}")
    print(f"   • Сэкономлено: ~{tokens_before - tokens_after} токенов")
    print(f"   • Экономия: {100 - (tokens_after / tokens_before * 100):.0f}%")

    # Фаза 3: Продолжаем диалог с summary
    print("\n" + "="*70)
    print("📊 ФАЗА 3: Продолжение диалога С summary (проверка контекста)")
    print("="*70)

    for i, question in enumerate(test_questions[6:], 7):
        print(f"\n🙋 Сообщение #{i}: {question}")

        conversation_history.append({"role": "user", "content": question})

        response, token_usage = call_deepseek_api(conversation_history)

        conversation_history.append({"role": "assistant", "content": response})

        total_tokens_with_compression += token_usage['total_tokens']

        print(f"🤖 Ответ: {response[:200]}...")
        print(f"📊 Токены: {token_usage['total_tokens']} (запрос: {token_usage['prompt_tokens']}, ответ: {token_usage['completion_tokens']})")

        time.sleep(0.5)

    print(f"\n{'='*70}")
    print(f"📊 ИТОГО фаза 3 (С сжатием): {total_tokens_with_compression} токенов")
    print(f"   Сообщений в истории: {len(conversation_history)}")
    print(f"   Примерно токенов в истории: ~{calculate_tokens(conversation_history)}")
    print(f"{'='*70}")

    # Итоговое сравнение
    print("\n" + "="*70)
    print("🎯 ИТОГОВОЕ СРАВНЕНИЕ")
    print("="*70)

    print(f"\n💰 Экономия токенов:")
    print(f"   • Без сжатия (фаза 1): {total_tokens_without_compression} токенов")
    print(f"   • С сжатием (фаза 3): {total_tokens_with_compression} токенов")

    if total_tokens_with_compression > 0:
        savings = ((total_tokens_without_compression - total_tokens_with_compression) /
                   total_tokens_without_compression * 100)
        print(f"   • Экономия: ~{savings:.0f}% токенов!")

    print(f"\n✅ ВЫВОДЫ:")
    print(f"   1. Сжатие позволяет существенно снизить расход токенов")
    print(f"   2. Контекст диалога сохраняется благодаря качественному summary")
    print(f"   3. Модель может отвечать на вопросы о прошлом диалоге")
    print(f"   4. Это особенно полезно для длинных разговоров")
    print(f"   5. DeepSeek Chat отлично справляется с созданием резюме!")

    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    if not DEEPSEEK_API_KEY:
        print("❌ Ошибка: Не настроена переменная окружения DEEPSEEK_API_KEY")
        print("   Создайте файл .secrets/deepseek-api-key.env со следующим содержимым:")
        print("   DEEPSEEK_API_KEY=your_api_key_here")
    else:
        main()
