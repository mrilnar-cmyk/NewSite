import time
from groq import Groq
from django.conf import settings
from .models import Formula, Category, ChatMessage


def test_ai():
    """Простая проверка что API работает"""
    client = Groq(api_key=settings.GROQ_API_KEY)
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": "Скажи 'Привет! Я работаю!'"}],
        temperature=0.3,
        max_tokens=100,
    )
    return response.choices[0].message.content


def build_system_prompt(user):
    """Строит КОМПАКТНЫЙ системный промпт"""
    
    formulas = Formula.objects.filter(user=user).select_related('category').order_by('symbol')
    
    parts = []
    parts.append("Ты AI-ассистент Formula. Отвечай на русском. Помогай с формулами, расчётами, объяснениями.")
    parts.append("")
    
    if formulas.exists():
        inputs = formulas.filter(is_input=True)
        if inputs.exists():
            parts.append("ВХОДНЫЕ:")
            for f in inputs[:30]:
                unit = f" [{f.unit}]" if f.unit else ""
                val = f"={f.default_value}" if f.default_value is not None else ""
                parts.append(f"  {f.symbol}: {f.name}{unit}{val}")
            parts.append("")
        
        calcs = formulas.filter(is_input=False)
        if calcs.exists():
            parts.append("ФОРМУЛЫ:")
            for f in calcs[:30]:
                unit = f" [{f.unit}]" if f.unit else ""
                expr = f.expression if f.expression else "?"
                parts.append(f"  {f.symbol} = {expr} ({f.name}{unit})")
            parts.append("")
        
        parts.append(f"Итого: {formulas.count()} формул")
    else:
        parts.append("Формул пока нет.")
    
    return "\n".join(parts)


def get_chat_history(user, limit=10):
    """Последние сообщения (компактно)"""
    messages = ChatMessage.objects.filter(user=user).order_by('-created_at')[:limit]
    return list(reversed(messages))


def chat_with_ai(user, user_message):
    """Отправляет сообщение AI с контекстом формул"""
    client = Groq(api_key=settings.GROQ_API_KEY)
    
    # Сохраняем сообщение пользователя
    ChatMessage.objects.create(user=user, role='user', content=user_message)
    
    system_prompt = build_system_prompt(user)
    history = get_chat_history(user, limit=10)
    
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        # Обрезаем длинные сообщения в истории
        content = msg.content[:500] if len(msg.content) > 500 else msg.content
        messages.append({"role": msg.role, "content": content})
    
    try:
        time.sleep(1)  # Задержка для защиты от rate limit
        
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.4,
            max_tokens=1000,
        )
        
        ai_response = response.choices[0].message.content
        
        ChatMessage.objects.create(user=user, role='assistant', content=ai_response)
        
        return {'success': True, 'message': ai_response}
        
    except Exception as e:
        error_msg = str(e)
        print("=" * 50)
        print("GROQ ERROR:", error_msg)
        print("=" * 50)
        
        # Удаляем сообщение пользователя чтобы не дублировалось
        last_msg = ChatMessage.objects.filter(
            user=user, role='user', content=user_message
        ).last()
        if last_msg:
            last_msg.delete()
        
        if 'rate_limit' in error_msg.lower() or 'tokens' in error_msg.lower():
            return {
                'success': False,
                'message': 'Слишком много запросов. Подождите 30 секунд.'
            }
        
        return {'success': False, 'message': f'Ошибка: {error_msg}'}


def clear_chat_history(user):
    """Очищает историю чата"""
    count = ChatMessage.objects.filter(user=user).count()
    ChatMessage.objects.filter(user=user).delete()
    return count