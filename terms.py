import json
import os
import re
import threading
from pathlib import Path

from baseline_terms import TermModel as Baseline

ROOT = Path(__file__).resolve().parent
DICTIONARY = json.loads((ROOT / 'dictionary.json').read_text(encoding='utf-8'))
LABELS = {'art':'рисование', 'architecture':'архитектура', 'anime':'аниме',
          'movies':'кино', 'sport':'спорт', 'cars':'автомобили', 'music':'музыка',
          'travel':'путешествия', 'books':'чтение', 'gaming':'игры',
          'cooking':'кулинария', 'crafts':'рукоделие', 'other':'другие интересы'}


def make_prompt(term, definition, story, weights):
    labels = {}
    for key, value in weights.items():
        key = LABELS.get(key, key)
        labels[key] = labels.get(key, 0) + value
    total = sum(labels.values()) or 1
    text = ', '.join(f'{k}: {v/total:.2f}' for k,v in sorted(labels.items(), key=lambda x:(-x[1],x[0])))
    return (f'Объясни термин простыми словами и приведи пример только из истории. '
            f'Сохрани финансовый смысл и факты. Термин: {term}. '
            f'Значение: {definition} Интересы: {text}. История: {story} Объяснение:')


class TermService:
    def __init__(self):
        self.lock = threading.Lock()
        self.model = None
        self.tokenizer = None
        self.backend = 'not_loaded'

    def load(self):
        if self.model is not None:
            return
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        except ImportError as e:
            raise RuntimeError('Установи зависимости тем же Python: python -m pip install -r requirements.txt') from e
        torch.set_num_threads(min(4, os.cpu_count() or 1))
        path = ROOT / 'models' / 'terms'
        if (path / 'config.json').is_file():
            print('Загружаем локальные веса терминов...', flush=True)
            tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
            model = AutoModelForSeq2SeqLM.from_pretrained(path, local_files_only=True)
            backend = 'local_merged'
        else:
            from peft import PeftModel
            adapter = ROOT / 'models' / 'adapter'
            config = json.loads((adapter / 'adapter_config.json').read_text())
            print('Полных весов нет. Загружаем базовую модель из Hugging Face и локальный адаптер...', flush=True)
            tokenizer = AutoTokenizer.from_pretrained(adapter, local_files_only=True)
            base = AutoModelForSeq2SeqLM.from_pretrained(config['base_model_name_or_path'])
            model = PeftModel.from_pretrained(base, adapter, local_files_only=True).merge_and_unload()
            backend = 'trained_adapter'
        model.eval()
        self.torch = torch
        self.tokenizer = tokenizer
        self.model = model
        self.backend = backend
        print('Модель терминов готова.', flush=True)

    def explain(self, term, definition, story, hints, weights, demo=False):
        if demo or term not in DICTIONARY:
            example = Baseline().example(story, hints, term=term)
            return {'term':term, 'definition':definition.rstrip('.') + '.', 'example':example,
                    'text':definition.rstrip('.') + '. ' + example,
                    'source':'demo_dictionary' if demo else 'dictionary', 'raw':''}
        with self.lock:
            self.load()
            prompt = make_prompt(term, DICTIONARY[term], story, weights)
            x = self.tokenizer(prompt, return_tensors='pt')
            if x['input_ids'].shape[1] > 384:
                raise ValueError('Текст слишком длинный для модели терминов; сократи историю до 500 знаков')
            with self.torch.inference_mode():
                y = self.model.generate(**x, max_new_tokens=192, num_beams=3,
                        do_sample=False, no_repeat_ngram_size=3,
                        length_penalty=1.0, early_stopping=True)
            answer = self.tokenizer.decode(y[0], skip_special_tokens=True).strip()
            if not answer:
                raise RuntimeError('Модель терминов вернула пустой ответ')
            return {'term':term, 'text':answer, 'definition':'', 'example':'',
                    'source':self.backend, 'raw':answer}


TERMS_MODEL = TermService()
