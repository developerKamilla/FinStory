function renderHome(){
 if(!state.profile){startQuiz();return}
 const p=state.profile; const main=p.interests?.[0]?.name||'tech'; const mainName=boot.interests.find(x=>x.id===main)?.name||main;
 const rows=boot.lessons.map((l,idx)=>{ const current=idx===0; const cls=current?'current':''; return `<div class="lesson-row clickable" onclick="openLesson(${l.lesson_id})"><div class="node ${cls}">${lessonEmoji[idx]||'●'}</div><div class="lesson-info"><small>${current?'Начать':'Доступно'}</small><strong>${l.title}</strong></div></div>`;}).join('');
 app.innerHTML=chrome(`<div class="content"><div class="home-top"><div class="user-strip"><div class="avatar">🙂</div><div><small>Привет!</small><strong style="display:block">Твой курс</strong></div></div></div><div class="level-card"><div><span class="lvl">УРОВЕНЬ ${p.knowledge_score+1}</span><strong>${mainName}</strong></div><span style="font-size:28px">▤</span></div><div class="course-path"><div class="path-line"></div>${rows}</div></div>`,null,true);
}
async function openLesson(id){
 try{
  app.innerHTML=chrome(`<div class="content onboard-center"><div class="big-symbol">⏳</div><h2>Собираю урок</h2><p>Подбираю персонажа, историю и объяснения под твой профиль.</p></div>`,45);
  const data=await api('/api/lesson',{profile:state.profile,lesson_id:id,previous_story:state.stories[id-1]||''}); state.activeLesson=data.result; state.stories[id]=data.result.story; renderLesson();
 }catch(e){toast(e.message);renderHome()}
}
function renderLesson(){
 const r=state.activeLesson; if(!r)return renderHome(); const storyWords=r.story.trim().split(/\s+/).length;
 const terms=r.terms.map(t=>`<div class="term-card"><strong>${t.term}</strong><p>${escapeText(t.personalized)}</p></div>`).join('');
 app.innerHTML=chrome(`<div class="content"><button class="linkbtn" onclick="renderHome()">← Карта курса</button><div class="lesson-hero"><div><small>Микроистория · ${storyWords} слов</small><h2>${r.lesson.title}</h2><p>${r.character.name} · ${r.character.personality.split(',')[0]}</p><div class="mini-interest-row">${(r.interests_used||[]).map(i=>`<span>${interestEmoji[i]||'⭐'} ${boot.interests.find(x=>x.id===i)?.name||i}</span>`).join('')}</div></div><div class="character-badge">${interestEmoji[r.main_interest]||'🙂'}</div></div><div class="story-card">${escapeText(r.story)}</div><div class="quick"><strong>Микровывод</strong><p>${escapeText(r.takeaway)}</p></div><h3 style="margin:22px 0 8px">Новые понятия</h3><div class="terms">${terms}</div><div class="quick"><h3 style="margin-top:0">Быстрая проверка</h3><p class="lead">3 вопроса по только что прочитанному уроку.</p><button class="primary" onclick="renderLessonQuiz()">Начать →</button></div></div>`,75);
}
function renderLessonQuiz(){
 const r=state.activeLesson; state.lessonAnswers=Array(r.questions.length).fill(null); state.quizScore=0;
 const blocks=r.questions.map((q,qi)=>`<div class="qblock"><strong>${qi+1}. ${q.question}</strong><div class="qanswers">${q.answers.map((a,ai)=>`<button id="qa-${qi}-${ai}" onclick="answerLesson(${qi},${ai})">${a}</button>`).join('')}</div></div>`).join('');
 app.innerHTML=chrome(`<div class="content"><button class="linkbtn" onclick="renderLesson()">← К истории</button><h1 class="section-title">Проверим понимание</h1><p class="section-sub">3 коротких вопроса</p><div class="quick">${blocks}</div><div class="action-stack" style="margin-top:18px"><button class="primary" onclick="finishLessonQuiz()">Завершить урок →</button></div></div>`,90);
}
function answerLesson(qi,ai){
 if(state.lessonAnswers[qi]!==null)return; const q=state.activeLesson.questions[qi]; state.lessonAnswers[qi]=ai; if(ai===q.correct)state.quizScore++;
 q.answers.forEach((_,j)=>{ const b=document.querySelector(`#qa-${qi}-${j}`); if(j===q.correct)b.classList.add('good'); else if(j===ai)b.classList.add('bad'); b.disabled=true; });
}
function finishLessonQuiz(){ if(state.lessonAnswers.some(x=>x===null)){toast('Ответь на все 3 вопроса');return} app.innerHTML=chrome(`<div class="content onboard-center"><div class="big-symbol">🏆</div><h2>Урок завершён</h2><div class="result-score">${state.quizScore}/3</div><p>${state.quizScore===3?'Отлично — все ответы верные.':'Можно вернуться к истории и закрепить понятия.'}</p><div class="action-stack" style="width:100%;margin-top:25px"><button class="primary" onclick="renderHome()">На карту курса →</button><button class="secondary" onclick="renderLesson()">Прочитать ещё раз</button></div></div>`,100); }

