from pathlib import Path

from .characters import choose_character, load_characters
from .classifier import InterestClassifier
from .course import get_lesson, load_lessons, load_terms
from .generator import PersonalizedGenerator
from .profile import build_user_profile


class FinStoryEngine:
    def __init__(self, project_root):
        root = Path(project_root)
        self.classifier = InterestClassifier(root / 'models' / 'interest_classifier.joblib')
        self.generator = PersonalizedGenerator(root)
        self.characters = load_characters(root / 'data' / 'characters.json')
        self.lessons = load_lessons(root / 'data' / 'lessons.json')
        self.terms = load_terms(root / 'data' / 'finance_terms.csv')

    def profile(self, selected_interests, free_text_answers, knowledge_answers):
        return build_user_profile(self.classifier, selected_interests, free_text_answers, knowledge_answers)

    def lesson(self, profile, lesson_id, previous_story=''):
        lesson = get_lesson(self.lessons, lesson_id)
        interests = [item['name'] for item in profile.get('interests', []) if item.get('name')]
        interests = interests or ['tech']
        character = choose_character(self.characters, interests[0], 1)
        story, takeaway, cards, plan, source = self.generator.create(
            lesson, character, interests, profile.get('knowledge_level', 'beginner'),
            self.terms, previous_story
        )
        return {
            'lesson': lesson, 'character': character, 'main_interest': interests[0],
            'interests_used': interests[:3], 'story': story, 'takeaway': takeaway,
            'terms': cards, 'questions': lesson['questions'],
            'plan': {key: value for key, value in plan.items() if key != 'character'},
            'generation': {'mode': source},
        }
