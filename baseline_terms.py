import re


CUES = {
    'доход': ('доход', 'заработ', 'подработ', 'получ', 'гонорар'),
    'расход': ('расход', 'трат', 'заплат', 'оплат', 'покуп'),
    'бюджет': ('бюджет', 'состав', 'распредел', 'выдел', 'план', 'сравни'),
    'банковская карта': ('карт', 'терминал', 'оплат'),
    'остаток': ('остат', 'остал', 'счёт', 'счет'),
    'процентная ставка': ('ставк', 'процент'),
    'начисление процентов': ('начисл', 'процент'),
    'сбережения': ('сбереж', 'отклад', 'накоп', 'сохрани'),
    'кредит': ('кредит', 'заём', 'заем', 'долг', 'вернут'),
    'переплата': ('переплат', 'сверх', 'дорож'),
    'платёж': ('платёж', 'платеж', 'выплат', 'оплат'),
    'инфляция': ('инфляц', 'подорож', 'вырос', 'цен'),
    'покупательная способность': ('купить', 'меньше', 'больше', 'цен'),
    'цена': ('цен', 'стоим', 'подорож'),
    'сложный процент': ('процент', 'начисл', 'добав', 'увелич'),
    'капитализация': ('процент', 'добав', 'основн', 'сумм'),
    'дивиденд': ('дивиденд', 'прибыл', 'выплат'),
    'биржа': ('бирж', 'сделк', 'купил', 'продал'),
    'облигация': ('облигац', 'долг', 'эмитент'),
    'купон': ('купон', 'выплат', 'облигац'),
    'доходность': ('доходност', 'результат', 'вложенн', 'процент'),
    'риск': ('риск', 'потер', 'убыт', 'гарант'),
    'волатильность': ('волатильн', 'измен', 'колеб', 'цен'),
    'горизонт инвестирования': ('срок', 'лет', 'месяц', 'год'),
    'диверсификация': ('разн', 'распредел', 'одн', 'актив'),
    'актив': ('актив', 'акци', 'облигац', 'влож'),
    'инвестиционный портфель': ('портфел', 'набор', 'влож', 'состав'),
    'ликвидность': ('прод', 'быстр', 'рыночн', 'цен'),
}


def words(text):
    return set(re.findall(r'[a-zа-яё0-9]+', text.casefold()))


class TermModel:
    def example(self, story, keywords, term=''):
        if not isinstance(keywords, list):
            keywords = []
        parts = [s.strip() for s in re.split(r'(?<=[.!?])\s+', story) if s.strip()]
        if not parts:
            return ''
        hints = words(' '.join(s for s in keywords if isinstance(s,str))) - {'рублей','деньги','свои','счёт'}
        cues = CUES.get(term, ())
        ranked = []
        for i, sentence in enumerate(parts):
            low = sentence.casefold()
            relevance = sum(any(w.startswith(cue) for w in words(low)) for cue in cues)
            direct = bool(term and term in low)
            score = 25*direct + 4*relevance + min(3,len(words(sentence) & hints))
            ranked.append((score,-i,i,relevance or direct))
        best = max(ranked)
        if term and not best[3]:
            return ''
        i=best[2]
        scene=parts[i]
        if not term and i and re.match(r'^(он|она|они|его|её|это)\b',scene,re.I):
            scene=parts[i-1]+' '+scene
        return scene

    def explain(self, term, definition, story, keywords):
        meaning=definition.strip(' .')
        text=f'{term.capitalize()} — {meaning[:1].lower()+meaning[1:]}.'
        scene=self.example(story,keywords)
        return text+(f' Например: {scene}' if scene else '')
