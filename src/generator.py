from .language_model import LanguageModel
from .plan_model import PlotPlanner
from .scenes import scene_for
from .short_chapters import render
from .term_model import TermSelector
from .validation import valid_chapter


class PersonalizedGenerator:
    def __init__(self, root):
        self.language_model = LanguageModel(root)
        self.planner = PlotPlanner(root / 'models' / 'plot_ranker.joblib')
        self.term_selector = TermSelector(root / 'models' / 'term_ranker.joblib')

    def create(self, lesson, character, interests, level, term_bank, previous_story=''):
        main = interests[0]
        plan = self.planner.choose(lesson, character, main)
        story, takeaway = render(int(lesson['lesson_id']), character, scene_for(main))
        cards = []
        for index, term_name in enumerate(lesson['terms']):
            term = term_bank[term_name.lower()]
            interest = interests[index % len(interests)]
            cards.append({'term': term['term'], 'personalized': self.term_selector.select(term, interest),
                          'interest': interest})
        generated = self.language_model.write(lesson, character, interests, plan, previous_story, cards)
        source = 'подготовленная глава'
        if valid_chapter(generated, lesson, character, story):
            story, takeaway = generated['story'], generated['takeaway']
            source = 'генерация по плану'
        return story, takeaway, cards, plan, source
