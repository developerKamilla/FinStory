import re

REQUIRED = {
    3: ('20 000', '3 000', '12%'),
    4: ('10 000', '10%', '1 000'),
    6: ('10 000', '11 000', '10%'),
    7: ('10 000', '10%', '13 310'),
}


def valid_chapter(generated, lesson, character, fallback):
    if not isinstance(generated, dict):
        return False
    story, takeaway = generated.get('story'), generated.get('takeaway')
    if not isinstance(story, str) or not 120 <= len(story) <= 500:
        return False
    if not isinstance(takeaway, str) or not 25 <= len(takeaway) <= 180:
        return False
    lower = story.lower()
    if character['name'].lower() not in lower:
        return False
    if any(number not in story for number in REQUIRED.get(int(lesson['lesson_id']), ())):
        return False
    amounts = lambda value: set(re.findall(r'\d[\d ]*\s*(?:%|₽)', value))
    if not amounts(story).issubset(amounts(fallback)):
        return False
    if any(phrase in lower for phrase in ('гарантированная прибыль', 'без риска', 'как языковая модель')):
        return False
    return True
