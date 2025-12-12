"""
Тестовый скрипт для демонстрации внешней памяти (День 10 - AI Advent Challenge)

Этот скрипт демонстрирует:
1. Разговор с 12 сообщениями (6 вопросов + 6 ответов)
2. Автоматическое сжатие после 6 сообщений
3. Сохранение контекста в JSON-файл после сжатия
4. Загрузку контекста из JSON при следующем запуске
5. Долговременную память между запусками

Используется модель DeepSeek Chat
"""

import requests
import json
from dotenv import load_dotenv
import os
import time
from datetime import datetime

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

def save_context_to_json(conversation_history, filename=None):
    """Save conversation context to JSON file"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"context_{timestamp}.json"

    # Create memory directory if it doesn't exist
    memory_dir = "memory"
    if not os.path.exists(memory_dir):
        os.makedirs(memory_dir)

    filepath = os.path.join(memory_dir, filename)

    context_data = {
        "timestamp": datetime.now().isoformat(),
        "messages_count": len(conversation_history),
        "conversation_history": conversation_history
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(context_data, f, ensure_ascii=False, indent=2)

    return filepath

def load_context_from_json(filepath):
    """Load conversation context from JSON file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            context_data = json.load(f)

        return context_data.get('conversation_history', [])
    except FileNotFoundError:
        print(f"❌ Файл {filepath} не найден")
        return None
    except json.JSONDecodeError:
        print(f"❌ Ошибка чтения JSON из файла {filepath}")
        return None

def list_saved_contexts():
    """List all saved context files"""
    memory_dir = "memory"
    if not os.path.exists(memory_dir):
        return []

    files = [f for f in os.listdir(memory_dir) if f.endswith('.json')]
    files.sort(reverse=True)  # Most recent first
    return files

def main():
    print("\n" + "="*70)
    print("💾  ДЕМОНСТРАЦИЯ ВНЕШНЕЙ ПАМЯТИ (День 10 - AI Advent Challenge)")
    print("="*70)

    # Проверяем наличие сохраненных контекстов
    saved_contexts = list_saved_contexts()
    conversation_history = []

    if saved_contexts:
        print(f"\n📂 Найдено сохраненных контекстов: {len(saved_contexts)}")
        print("\nПоследние файлы:")
        for i, filename in enumerate(saved_contexts[:5], 1):
            print(f"   {i}. {filename}")

        print("\n❓ Хотите загрузить контекст из файла?")
        print("   Введите номер файла (1-5) или нажмите Enter для нового диалога")

        choice = input("Ваш выбор: ").strip()

        if choice.isdigit() and 1 <= int(choice) <= min(5, len(saved_contexts)):
            selected_file = saved_contexts[int(choice) - 1]
            filepath = os.path.join("memory", selected_file)

            loaded_context = load_context_from_json(filepath)

            if loaded_context:
                conversation_history = loaded_context
                print(f"\n✅ Контекст загружен из {selected_file}")
                print(f"   Загружено сообщений: {len(conversation_history)}")

                # Показываем краткое резюме загруженного контекста
                if conversation_history and conversation_history[0].get('role') == 'system':
                    summary_preview = conversation_history[0]['content'][:150]
                    print(f"\n📝 Краткое содержание контекста:")
                    print(f"   {summary_preview}...")
            else:
                print("\n⚠️  Не удалось загрузить контекст, начинаем новый диалог")
        else:
            print("\n▶️  Начинаем новый диалог")
    else:
        print("\n▶️  Сохраненных контекстов не найдено. Начинаем новый диалог")

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

    total_tokens_without_compression = 0
    total_tokens_with_compression = 0

    # Если контекст не был загружен, начинаем с пустой истории
    if not conversation_history:
        conversation_history = []

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

    # Сохраняем контекст в JSON
    print(f"\n💾 Сохраняю контекст в JSON...")
    saved_filepath = save_context_to_json(conversation_history)
    print(f"✅ Контекст сохранён в файл: {saved_filepath}")

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

    print(f"\n✅ ВЫВОДЫ (День 10 - Внешняя память):")
    print(f"   1. Сжатие позволяет существенно снизить расход токенов")
    print(f"   2. Контекст диалога сохраняется благодаря качественному summary")
    print(f"   3. Модель может отвечать на вопросы о прошлом диалоге")
    print(f"   4. Контекст автоматически сохраняется в JSON после сжатия")
    print(f"   5. При следующем запуске можно загрузить сохраненный контекст")
    print(f"   6. Это обеспечивает долговременную память между сеансами!")
    print(f"   7. DeepSeek Chat отлично справляется с созданием резюме!")

    print(f"\n💾 Файл с контекстом: {saved_filepath}")
    print(f"   При следующем запуске вы сможете загрузить этот контекст!")

    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    if not DEEPSEEK_API_KEY:
        print("❌ Ошибка: Не настроена переменная окружения DEEPSEEK_API_KEY")
        print("   Создайте файл .secrets/deepseek-api-key.env со следующим содержимым:")
        print("   DEEPSEEK_API_KEY=your_api_key_here")
    else:
        main()
