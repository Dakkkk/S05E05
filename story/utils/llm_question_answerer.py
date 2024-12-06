from openai import OpenAI
from config import OPENAI_API_KEY, QA_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)

def answer_question_in_polish(question: str, context: str) -> str:
    prompt = f"""
Jesteś ekspertem od tej historii i potrafisz odpowiadać na pytania na podstawie dostarczonego kontekstu.

Oto pytanie:
"{question}"

Oto kontekst (wycinki z dokumentów):
{context}

Odpowiedz po polsku, na podstawie podanego kontekstu. Jeżeli nie możesz znaleźć odpowiedzi w powyższym kontekście, powiedz wyraźnie, że brakuje informacji w dostarczonych dokumentach i określ, jakiego rodzaju informacji brakuje.
"""
    response = client.chat.completions.create(
        model=QA_MODEL,
        messages=[
            {"role": "system", "content": "Jesteś pomocnym asystentem."},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        max_tokens=1500
    )

    return response.choices[0].message.content.strip()
