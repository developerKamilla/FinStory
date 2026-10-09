const app = document.querySelector('#app');
let boot = null;
let state = {
  onboard: 0,
  quizIndex: 0,
  selectedInterests: [],
  freeText: ['', '', ''],
  knowledge: [null, null, null, null, null, null],
  profile: JSON.parse(localStorage.getItem('finstory_profile') || 'null'),
  activeLesson: null,
  stories: {},
  quizScore: 0,
};

const interestEmoji = {gaming:'🎮',sport:'⚽',music:'🎵',movies:'🎬',tech:'💻',science:'🔬',business:'💼',books:'📚',travel:'✈️',art:'🎨',cars:'🏎️'};
const lessonEmoji = ['💰','💳','🐷','％','🧾','📈','✨','📊','📜','⚖️','🧩','💼'];
const levelRU = {beginner:'Новичок',basic:'Базовый',intermediate:'Уверенный'};

function chrome(inner, progress=null, nav=false, activeNav='home'){
  return `<section class="screen">
    <div class="status"><span>9:45</span><span>▮▮ ◉ ▰</span></div>
    <div class="webbar"><span>‹</span><span>finstory.local</span><span></span></div>
    ${progress===null?'':`<div class="top-progress"><div class="track"><div class="fill" style="width:${progress}%"></div></div></div>`}
    ${inner}
    ${nav?bottomNav(activeNav):''}
  </section>`;
}
function bottomNav(active='home'){
  return `<nav class="bottom-nav">
    <button class="navitem ${active==='home'?'active':''}" onclick="renderHome()"><span class="ico">⌂</span>Главная</button>
    <button class="navitem ${active==='library'?'active':''}" onclick="renderLibrary()"><span class="ico">▤</span>Энциклопедия</button>
    <button class="navitem ${active==='quests'?'active':''}" onclick="renderQuests()"><span class="ico">♜</span>Задания</button>
    <button class="navitem ${active==='profile'?'active':''}" onclick="renderProfile()"><span class="ico">●</span>Профиль</button>
  </nav>`;
}
function toast(msg){ const t=document.createElement('div');t.className='toast';t.textContent=msg;document.body.appendChild(t);setTimeout(()=>t.remove(),1800); }

async function api(path, body){
  const r = await fetch(path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});
  const data=await r.json(); if(!r.ok||data.ok===false) throw new Error(data.error||'API error'); return data;
}


function escapeText(value){ return String(value).replace(/[&<>"']/g, ch=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[ch])); }
