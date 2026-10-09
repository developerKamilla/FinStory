function renderWelcome(){
  app.innerHTML = chrome(`<div class="content hero">
    <div class="brand-chip"><span class="brand-icon">F</span><span>Истории о финансах</span></div>
    <div class="hero-art"><div class="card-tilt">F</div><div class="coin">₽</div><div class="spark s1">✦</div><div class="spark s2">✦</div><div class="spark s3">✦</div></div>
    <h1>Читай.<br>Пробуй.<br><span class="red">Разбирайся.</span></h1>
    <p class="lead">Финансовая грамотность через короткие истории, связанные с твоими интересами.</p>
    <div class="metrics"><div class="metric"><strong>10</strong><span>вопросов квиза</span></div><div class="metric"><strong>12</strong><span>микроуроков</span></div><div class="metric"><strong>3</strong><span>вопроса после урока</span></div></div>
    <div class="action-stack"><button class="primary" onclick="renderOnboard(0)">Начать →</button>${state.profile?'<button class="secondary" onclick="renderHome()">Продолжить обучение</button>':''}</div>
  </div>`);
}

const onboard = [
 {sym:'🪙',title:'Двигайся по дорожке знаний',text:'Каждый урок — новый шаг. Истории и объяснения подстраиваются под твои интересы.'},
 {sym:'🔥',title:'Учись короткими подходами',text:'История занимает несколько минут, затем — новые понятия и три коротких вопроса.'},
 {sym:'🎯',title:'Персонализация без случайных фактов',text:'Факты и числа берутся из базы и Python-расчётов. Модель меняет форму объяснения, а не финансовый смысл.'},
 {sym:'😎',title:'Всё готово!',text:'Сначала пройди квиз из 10 вопросов — так система определит интересы и уровень.'},
];
function renderOnboard(i){ state.onboard=i; const x=onboard[i]; app.innerHTML=chrome(`<div class="content onboard-center"><div class="big-symbol">${x.sym}</div><h2>${x.title}</h2><p>${x.text}</p><div class="action-stack" style="width:100%;margin-top:40px"><button class="primary" onclick="${i<onboard.length-1?`renderOnboard(${i+1})`:'startQuiz()'}">${i<onboard.length-1?'Продолжить →':'Начать квиз →'}</button><button class="linkbtn" onclick="startQuiz()">Пропустить</button></div></div>`,((i+1)/onboard.length)*100);
}
function startQuiz(){ state.quizIndex=0; renderQuiz(); }

function renderQuiz(){
  const i=state.quizIndex; const progress=((i+1)/10)*100;
  let body='';
  if(i===0){
    body=`<h1 class="quiz-title">Что тебе интересно?</h1><div class="quiz-count">Вопрос 1 из 10 · можно выбрать несколько</div><p class="question">Выбери темы, которые тебе реально нравятся.</p><div class="choice-grid">${boot.interests.map(x=>`<button class="choice ${state.selectedInterests.includes(x.id)?'selected':''}" onclick="toggleInterest('${x.id}')"><span class="em">${interestEmoji[x.id]||'⭐'}</span>${x.name}</button>`).join('')}</div>`;
  } else if(i<=3){
    const qs=['Чем ты обычно занимаешься после школы?','Какие видео, каналы или темы ты чаще всего смотришь?','Как бы ты провёл свободные выходные?'];
    body=`<h1 class="quiz-title">Расскажи немного о себе</h1><div class="quiz-count">Вопрос ${i+1} из 10</div><p class="question">${qs[i-1]}</p><textarea id="free" placeholder="Например: играю в Minecraft, смотрю футбол и иногда программирую...">${state.freeText[i-1]}</textarea>`;
  } else {
    const q=boot.knowledge_questions[i-4]; const k=i-4;
    body=`<h1 class="quiz-title">Проверим базу</h1><div class="quiz-count">Вопрос ${i+1} из 10</div><p class="question">${q.text}</p><div class="mc">${q.options.map((o,idx)=>`<button class="${state.knowledge[k]===idx?'selected':''}" onclick="pickKnowledge(${k},${idx})">${String.fromCharCode(65+idx)}. ${o}</button>`).join('')}</div>`;
  }
  const canBack=i>0;
  app.innerHTML=chrome(`<div class="content"><div class="quiz-head"><button class="linkbtn" onclick="${canBack?'prevQuiz()':'renderWelcome()'}">← Назад</button><span class="pill-note">${i+1}/10</span></div>${body}<div class="action-stack" style="margin-top:34px"><button class="primary" onclick="nextQuiz()">${i===9?'Собрать профиль →':'Дальше →'}</button></div></div>`,progress);
}
function toggleInterest(id){ const a=state.selectedInterests; state.selectedInterests=a.includes(id)?a.filter(x=>x!==id):[...a,id]; renderQuiz(); }
function pickKnowledge(k,idx){ state.knowledge[k]=idx; renderQuiz(); }
function persistFree(){ if(state.quizIndex>=1&&state.quizIndex<=3){ const el=document.querySelector('#free'); if(el) state.freeText[state.quizIndex-1]=el.value.trim(); } }
function prevQuiz(){ persistFree(); state.quizIndex=Math.max(0,state.quizIndex-1);renderQuiz(); }
async function nextQuiz(){
  persistFree();
  if(state.quizIndex===0 && !state.selectedInterests.length){toast('Выбери хотя бы один интерес');return;}
  if(state.quizIndex<9){state.quizIndex++;renderQuiz();return;}
  try{
    const data=await api('/api/profile',{selected_interests:state.selectedInterests,free_text_answers:state.freeText,knowledge_answers:state.knowledge});
    state.profile=data.profile; localStorage.setItem('finstory_profile',JSON.stringify(state.profile)); renderProfileResult();
  }catch(e){toast(e.message)}
}
function renderProfileResult(){
  const p=state.profile; const tags=p.interests.slice(0,4).map(x=>`<span class="pill-note">${interestEmoji[x.name]||'⭐'} ${boot.interests.find(i=>i.id===x.name)?.name||x.name}</span>`).join(' ');
  app.innerHTML=chrome(`<div class="content onboard-center"><div class="big-symbol">🏁</div><h2>Твой маршрут готов</h2><p>Уровень: <strong>${levelRU[p.knowledge_level]||p.knowledge_level}</strong> · результат ${p.knowledge_score}/6</p><div style="display:flex;gap:7px;flex-wrap:wrap;justify-content:center;margin:14px 0">${tags}</div><div class="action-stack" style="width:100%;margin-top:35px"><button class="primary" onclick="renderHome()">Перейти к курсу →</button><button class="secondary" onclick="startQuiz()">Пройти квиз заново</button></div></div>`,100);
}

