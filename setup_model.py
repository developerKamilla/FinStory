import argparse
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALLOWED = {'config.json','generation_config.json','tokenizer_config.json','tokenizer.json',
           'special_tokens_map.json','spiece.model','model.safetensors','model.safetensors.index.json'}


def install(archive):
    target = ROOT / 'models' / 'terms'
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        config = next((n for n in names if n.endswith('output/model/config.json')), None)
        if config is None:
            raise ValueError('Нужен тот самый зип с папкой output/model')
        prefix = config[:-len('config.json')]
        settings = json.loads(z.read(config))
        if settings.get('model_type') != 't5':
            raise ValueError('В архиве другая модель')
        files = [n for n in names if n.startswith(prefix) and
                 (Path(n).name in ALLOWED or (Path(n).name.startswith('model-') and n.endswith('.safetensors')))
                 and '/' not in n[len(prefix):]]
        if not any(n.endswith('.safetensors') for n in files):
            raise ValueError('Нет файла весов')
        target.mkdir(parents=True,exist_ok=True)
        for n in files:
            print('Копируем:',Path(n).name,flush=True)
            tmp = target / (Path(n).name + '.part')
            with z.open(n) as source, tmp.open('wb') as dest:
                shutil.copyfileobj(source,dest,length=1024*1024)
            tmp.replace(target/Path(n).name)
    print('Готово.',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('archive',nargs='?')
    a=p.parse_args()
    archive=Path(a.archive) if a.archive else ROOT/'FinStory_trained_model.zip'
    if not archive.is_file() and not a.archive:
        candidates=list((Path.home()/'Downloads').glob('FinStory_trained_model*.zip'))
        if len(candidates)==1:archive=candidates[0]
    if not archive.is_file():
        raise SystemExit(1)
    try:install(archive)
    except (ValueError,zipfile.BadZipFile,OSError) as e:
        print('Не удалось установить модель:',e)
        raise SystemExit(1)
