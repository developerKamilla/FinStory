function renderLibrary(){
 const cards=[['🐷','Накопления','4 из 5 карточек'],['🪙','Вклады','1 из 6 карточек'],['🛡️','Страхование','Завершён'],['🔒','Кредиты','Откроется позже']];
 app.innerHTML=chrome(`<div class="content"><h1 class="section-title">Энциклопедия</h1><p class="section-sub">Все темы в одном месте</p><div class="ency-list">${cards.map(c=>`<div class="ency-card"><div class="round-icon">${c[0]}</div><div><strong>${c[1]}</strong><span>${c[2]}</span></div></div>`).join('')}</div></div>`,null,true,'library');
}
function renderQuests(){
 app.innerHTML=chrome(`<div class="content"><h1 class="section-title">Квесты на этот месяц</h1><p class="lead">Заработай 25 баллов!</p><div class="quick"><div class="qblock"><strong>Пройди 5 уроков <span class="pill-note">+20 XP</span></strong><div class="track"><div class="fill" style="width:60%;background:#55df00"></div></div></div><div class="qblock"><strong>Занимайся 3 дня подряд <span class="pill-note">+50 XP</span></strong><div class="track"><div class="fill" style="width:40%"></div></div></div><div class="qblock"><strong>Пройди раздел «Накопления» <span class="pill-note">+50 XP</span></strong><div class="track"><div class="fill" style="width:15%;background:#cf83e8"></div></div></div></div></div>`,null,true,'quests');
}
function renderProfile(){
 const p=state.profile; const inter=(p?.interests||[]).map(x=>`${interestEmoji[x.name]||'⭐'} ${boot.interests.find(i=>i.id===x.name)?.name||x.name}`).join('<br>');
 app.innerHTML=chrome(`<div class="content"><h1 class="section-title">Профиль</h1><div class="lesson-hero" style="margin-top:20px"><div><small>Уровень знаний</small><h2>${p?levelRU[p.knowledge_level]:'—'}</h2><p>${p?`${p.knowledge_score}/6 по базовому тесту`:'Квиз ещё не пройден'}</p></div><div class="character-badge">🙂</div></div><div class="quick"><h3>Главные интересы</h3><p class="lead">${inter||'Нет данных'}</p><button class="secondary" onclick="startQuiz()">Пройти квиз заново</button></div></div>`,null,true,'profile');
}

(async()=>{ try{ boot=await api('/api/bootstrap'); renderWelcome(); }catch(e){ app.innerHTML=`<div style="padding:40px;color:white">Не удалось запустить MVP: ${e.message}</div>`; } })();
