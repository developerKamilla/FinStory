import contextlib
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import agent
import setup_model
from terms import TermService, make_prompt


class IntegrationTests(unittest.TestCase):
    def test_training_prompt_matches(self):
        text=make_prompt('акция','Смысл.','Лера купила акцию.',{'movies':0.8,'sport':0.2})
        self.assertIn('Интересы: кино: 0.80, спорт: 0.20.',text)
        self.assertIn('История: Лера купила акцию.',text)

    def test_model_answer_is_used_without_replacement(self):
        seen={}
        class Tokenizer:
            def __call__(self,text,**kwargs):
                seen['prompt']=text
                return {'input_ids':SimpleNamespace(shape=(1,20))}
            def decode(self,value,**kwargs):
                return 'Акция даёт долю в компании без гарантии дохода. Лера приобрела долю киностудии.'
        class Model:
            def generate(self,**kwargs):
                seen['generate']=kwargs
                return [[1,2]]
        m=TermService()
        m.model=Model();m.tokenizer=Tokenizer();m.backend='trained_adapter'
        m.torch=SimpleNamespace(inference_mode=contextlib.nullcontext)
        result=m.explain('акция','Смысл','Лера купила акцию киностудии.',[],{'movies':1})
        self.assertEqual(result['source'],'trained_adapter')
        self.assertEqual(result['text'],result['raw'])
        self.assertIn('долю киностудии',result['text'])
        self.assertIn('кино: 1.00',seen['prompt'])
        self.assertEqual(seen['generate']['num_beams'],3)

    def test_other_terms_use_dictionary(self):
        m=TermService()
        result=m.explain('бюджет','План доходов и расходов','Лера составила бюджет.', ['бюджет'],{'movies':1})
        self.assertEqual(result['source'],'dictionary')
        self.assertIsNone(m.model)

    def test_env_is_read_from_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp,'.env').write_text('\ufeffYANDEX_API_KEY="example"\nYANDEX_FOLDER_ID=folder\n',encoding='utf-8')
            with patch.object(agent,'ROOT',Path(tmp)),patch.dict(os.environ,{},clear=True):
                agent.load_env()
                self.assertEqual(os.getenv('YANDEX_API_KEY'),'example')
                self.assertEqual(os.getenv('YANDEX_FOLDER_ID'),'folder')

    def test_full_weights_archive_installation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            zpath=root/'weights.zip'
            with zipfile.ZipFile(zpath,'w') as z:
                z.writestr('output/model/config.json',json.dumps({'model_type':'t5'}))
                z.writestr('output/model/model.safetensors',b'test-weights')
                z.writestr('output/model/tokenizer.json','{}')
                z.writestr('output/model/../../escape','must-not-copy')
            with patch.object(setup_model,'ROOT',root):
                setup_model.install(zpath)
            self.assertEqual((root/'models/terms/model.safetensors').read_bytes(),b'test-weights')
            self.assertFalse((root/'escape').exists())


class FirstLessonTests(unittest.TestCase):
    def test_terms_get_different_relevant_sentences(self):
        from baseline_terms import TermModel
        story = ('Артём любил рисование. У него был небольшой доход от подработки по выходным. '
                 'Артём решил составить бюджет: сначала выделил деньги на регулярные траты, '
                 'а оставшуюся сумму решил откладывать на краски. '
                 'Он ограничил расходы на мелкие развлечения, чтобы быстрее накопить нужную сумму.')
        hints = ['бюджет', 'регулярные траты', 'краски']
        m = TermModel()
        results = [m.example(story,hints,t) for t in ['доход','расход','бюджет']]
        self.assertEqual(len(set(results)),3)
        self.assertIn('подработки',results[0])
        self.assertIn('ограничил расходы',results[1])
        self.assertIn('составить бюджет',results[2])
        self.assertTrue(all(r in story for r in results))

    def test_no_unrelated_example_when_evidence_is_missing(self):
        from baseline_terms import TermModel
        self.assertEqual(TermModel().example('Аня гуляла по музею.',['Аня','музею'],'доход'),'')
