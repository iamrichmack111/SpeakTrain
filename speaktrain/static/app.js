const state={catalog:null,language:0,course:'foundations',scenario:0,phrase:0,gender:'male',register:'informal',status:null,recorder:null,chunks:[],started:0,vocabQuestion:null,conjQuestion:null,conversationQuestion:null,today:null};
const $=id=>document.getElementById(id);
const escapeHtml=s=>String(s??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const current=()=>{const l=state.catalog.languages[state.language],s=l.scenarios[state.scenario];return {l,s,p:s.phrases[state.phrase]}};
const hasGender=p=>Boolean(p.variants||p.responseVariants||Object.values(p.registers||{}).some(form=>form.variants));
const currentForm=()=>{const {p}=current(),register=p.registers?.[state.register]||{},variant=register.variants?.[state.gender]||p.variants?.[state.gender]||{};return {...p,...register,...variant}};
const currentResponse=()=>{const {p}=current();return {...p,...(p.responseVariants?.[state.gender]||{})}};

async function boot(){
  const [catalog,status]=await Promise.all([fetch('/api/catalog').then(r=>r.json()),fetch('/api/status').then(r=>r.json())]);
  state.catalog=catalog;state.status=status;
  $('engineStatus').textContent=`Playback: ${status.piper?'Piper':'browser'} · Scoring: ${status.whisper?'Whisper':'manual fallback'}`;
  fillLanguages();renderCourses();renderWordLab();render();bind();loadToday();
}

function fillLanguages(){
  const options=state.catalog.languages.map((l,i)=>`<option value="${i}">${escapeHtml(l.name)}</option>`).join('');
  $('language').innerHTML=options;$('opiLanguage').innerHTML=options;$('vocabLanguage').innerHTML=options;fillCourses();
}
function fillCourses(){
  $('course').innerHTML=state.catalog.courses.map(c=>`<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('');$('course').value=state.course;fillScenarios();
}
function fillScenarios(){
  const l=state.catalog.languages[state.language];
  const available=l.scenarios.map((s,i)=>({s,i})).filter(item=>item.s.course===state.course);
  if(!available.length){state.course=state.catalog.courses[0].id;return fillCourses()}
  if(!available.some(item=>item.i===state.scenario))state.scenario=available[0].i;
  $('scenario').innerHTML=available.map(({s,i})=>`<option value="${i}">${escapeHtml(s.name)}</option>`).join('');$('scenario').value=state.scenario;
  fillPhrases();
}
function fillPhrases(){
  const {s}=current();
  $('phrase').innerHTML=s.phrases.map((p,i)=>`<option value="${i}">${i+1}. ${escapeHtml(p.english)}</option>`).join('');
}
function resetAttempt(){
  $('result').classList.add('hidden');$('result').innerHTML='';$('manualTranscript').value='';
  $('cipher').classList.add('hidden');speechSynthesis.cancel();
}
function render(){
  const {l,s,p}=current();if(!p.registers)state.register='informal';const form=currentForm();
  $('genderWrap').classList.toggle('hidden',!hasGender(p));$('gender').value=state.gender;
  $('registerWrap').classList.toggle('hidden',!p.registers);$('register').value=state.register;
  $('english').textContent=p.english;$('target').textContent=form.target;$('target').dir=l.direction;
  $('transliteration').textContent=form.transliteration;$('cipher').textContent=form.cipher||p.cipher;$('note').textContent=form.note||p.note;
  $('objective').textContent=s.objective||'';
  const reply=currentResponse();$('responseBlock').classList.toggle('hidden',!reply.response);$('response').textContent=reply.response||'';$('response').dir=l.direction;$('responseEnglish').textContent=reply.responseEnglish||'';$('responseTransliteration').textContent=reply.responseTransliteration||'';
  $('counter').textContent=`${s.name.toUpperCase()} · ${state.phrase+1} OF ${s.phrases.length}${p.registers?` · ${state.register.toUpperCase()}`:''}${hasGender(p)?` · TO A ${state.gender.toUpperCase()}`:''}`;
  $('phrase').value=state.phrase;renderOpi();
}
function renderCourses(){
  $('courseGrid').innerHTML=state.catalog.courses.map((course,index)=>{const modules=state.catalog.languages.flatMap(l=>l.scenarios.filter(s=>s.course===course.id));const phrases=modules.reduce((sum,s)=>sum+s.phrases.length,0);return `<button class="course-card" data-course="${course.id}"><span class="course-number">${index+1}</span><strong>${escapeHtml(course.name)}</strong><em>${escapeHtml(course.level)}</em><p>${escapeHtml(course.description)}</p><small>${modules.length} modules · ${phrases} phrases</small></button>`}).join('');
  $('courseGrid').querySelectorAll('button').forEach(button=>button.onclick=()=>{state.course=button.dataset.course;state.phrase=0;fillCourses();render();document.querySelector('[data-view="practice"]').click()});
}

function renderWordLab(){
  const words=state.catalog.lexicon.vocabulary,categories=[...new Set(words.map(word=>word.category))].sort();
  $('wordCategory').innerHTML='<option value="all">All categories</option>'+categories.map(category=>`<option value="${escapeHtml(category)}">${escapeHtml(category)}</option>`).join('');
  renderWordRows();fillBuilder();
}
function renderWordRows(){
  const query=$('wordSearch').value.trim().toLowerCase(),category=$('wordCategory').value,cognates=$('cognatesOnly').checked;
  const words=state.catalog.lexicon.vocabulary.filter(word=>{
    const haystack=[word.english,word.spanish,word.spanishPronunciation,word.arabic,word.arabicTransliteration,word.note].join(' ').toLowerCase();
    return (!query||haystack.includes(query))&&(category==='all'||word.category===category)&&(!cognates||word.cognate);
  });
  $('wordRows').innerHTML=words.map(word=>`<tr><td><strong>${escapeHtml(word.english)}</strong>${word.cognate?'<span class="cognate-badge">cognate</span>':''}</td><td>${escapeHtml(word.spanish)}</td><td class="sound">${escapeHtml(word.spanishPronunciation)}</td><td dir="rtl" class="arabic-cell">${escapeHtml(word.arabic)}</td><td class="sound">${escapeHtml(word.arabicTransliteration)}</td><td>${escapeHtml(word.partOfSpeech)}<small>${escapeHtml(word.category)}</small></td><td>${escapeHtml(word.note)}</td></tr>`).join('')||'<tr><td colspan="7">No words match these filters.</td></tr>';
}
function builderData(){return state.catalog.lexicon.builders[$('builderLanguage').value]}
function fillBuilder(){
  const data=builderData();
  const verbs=data.verbs.map((verb,index)=>`<option value="${index}">${escapeHtml(verb.infinitive)} · ${escapeHtml(verb.english)}</option>`).join('');
  $('conjugationVerb').innerHTML=verbs;$('builderVerb').innerHTML=verbs;
  $('builderSubject').innerHTML=data.subjects.map((subject,index)=>`<option value="${index}">${escapeHtml(subject.target)} · ${escapeHtml(subject.english)}</option>`).join('');
  $('builderTime').innerHTML=data.times.map((item,index)=>`<option value="${index}">${escapeHtml(item.target||'—')} ${item.english?'· '+escapeHtml(item.english):''}</option>`).join('');
  fillBuilderComplements();renderConjugation();
}
function fillBuilderComplements(){
  const data=builderData(),verb=data.verbs[Number($('builderVerb').value||0)];
  $('builderComplement').innerHTML=data.complements.map((item,index)=>({item,index})).filter(({item})=>!item.verbs||item.verbs.includes(verb.id)).map(({item,index})=>`<option value="${index}">${escapeHtml(item.target)} · ${escapeHtml(item.english)}</option>`).join('');buildSentence();
}
function conjugatedValue(verb,tense,person){
  const value=verb.conjugations[tense][person];return typeof value==='string'?{target:value,transliteration:value}:{target:value.target,transliteration:value.transliteration};
}
function renderConjugation(){
  const data=builderData(),verb=data.verbs[Number($('conjugationVerb').value||0)],tense=$('conjugationTense').value;
  $('conjugationTable').innerHTML=`<table><thead><tr><th>Person</th><th>${escapeHtml(data.name)} form</th><th>Pronunciation</th></tr></thead><tbody>${data.subjects.map(subject=>{const form=conjugatedValue(verb,tense,subject.person);return `<tr><td>${escapeHtml(subject.target)} · ${escapeHtml(subject.english)}</td><td dir="${data.direction}"><strong>${escapeHtml(form.target)}</strong></td><td class="sound">${escapeHtml(form.transliteration)}</td></tr>`}).join('')}</tbody></table>`;
  buildSentence();
}
function buildSentence(){
  if(!state.catalog?.lexicon)return;
  const data=builderData(),subject=data.subjects[Number($('builderSubject').value||0)],verb=data.verbs[Number($('builderVerb').value||0)],complement=data.complements[Number($('builderComplement').value||0)],time=data.times[Number($('builderTime').value||0)],tense=$('conjugationTense').value,form=conjugatedValue(verb,tense,subject.person),negative=$('builderNegative').checked,question=$('builderQuestion').checked;
  const targetParts=[subject.target,negative?(data.direction==='rtl'?'ما':'no'):null,form.target,complement.target,time.target].filter(Boolean);
  let target=targetParts.join(' ');if(question)target=data.direction==='rtl'?target+'؟':'¿'+target+'?';else target+='.';
  const transliterationParts=[subject.transliteration||subject.target,negative?(data.direction==='rtl'?'mā':'no'):null,form.transliteration,complement.transliteration||complement.target,time.transliteration||time.target].filter(Boolean);
  const english=[subject.english,negative?'do/did not':null,verb.english,complement.english,time.english].filter(Boolean).join(' ')+(question?'?':'.');
  $('builtEnglish').textContent=english;$('builtTarget').textContent=target;$('builtTarget').dir=data.direction;$('builtTransliteration').textContent=transliterationParts.join(' ')+(question?'?':'.');
}
function renderOpi(){
  const li=Number($('opiLanguage').value||0),difficulty=Number($('opiDifficulty').value||0),l=state.catalog.languages[li],s=l.scenarios[0];
  $('opiPrompt').textContent=s.opiPrompts[difficulty];$('opiPrompt').dir=l.direction;
}
function speak(text,lang,phraseId=null,variant='default',register='informal'){
  if(phraseId&&state.status.piper){
    const audio=new Audio(`/api/audio/${phraseId}?variant=${encodeURIComponent(variant)}&register=${encodeURIComponent(register)}`);
    audio.play().catch(()=>browserSpeak(text,lang));
  }else browserSpeak(text,lang);
}
function browserSpeak(text,lang){
  speechSynthesis.cancel();const utterance=new SpeechSynthesisUtterance(text);utterance.lang=lang;utterance.rate=.85;speechSynthesis.speak(utterance);
}

async function toggleRecording(kind){
  const button=$(kind==='opi'?'opiRecord':'record');
  if(state.recorder&&state.recorder.state==='recording'){
    state.recorder.stop();button.classList.remove('recording');button.textContent='● Record';return;
  }
  try{
    const stream=await navigator.mediaDevices.getUserMedia({audio:true});state.chunks=[];state.started=Date.now();state.recordKind=kind;
    state.recorder=new MediaRecorder(stream);state.recorder.ondataavailable=event=>state.chunks.push(event.data);state.recorder.onstop=()=>submitAudio(stream);state.recorder.start();
    button.classList.add('recording');button.textContent='■ Stop and score';
  }catch(error){alert('Microphone access failed. Use the manual transcript box instead.')}
}
async function submitAudio(stream){
  stream.getTracks().forEach(track=>track.stop());
  const blob=new Blob(state.chunks,{type:state.recorder.mimeType}),formData=new FormData();
  formData.append('audio',blob,'response.webm');formData.append('duration',String((Date.now()-state.started)/1000));
  let endpoint='/api/score',output='result';
  if(state.recordKind==='opi'){
    endpoint='/api/opi-score';output='opiResult';formData.append('language',state.catalog.languages[Number($('opiLanguage').value)].id);
  }else{
    formData.append('phrase_id',current().p.id);formData.append('variant',state.gender);formData.append('register',state.register);
  }
  const response=await fetch(endpoint,{method:'POST',body:formData});showResult(output,await response.json(),response.ok);
}
async function manualScore(opi=false){
  const formData=new FormData();let endpoint='/api/score',output='result';
  if(opi){
    endpoint='/api/opi-score';output='opiResult';formData.append('recognized',$('opiTranscript').value);formData.append('language',state.catalog.languages[Number($('opiLanguage').value)].id);
  }else{
    formData.append('recognized',$('manualTranscript').value);formData.append('phrase_id',current().p.id);formData.append('variant',state.gender);formData.append('register',state.register);
  }
  const response=await fetch(endpoint,{method:'POST',body:formData});showResult(output,await response.json(),response.ok);
}
function showResult(id,data,ok){
  const box=$(id);box.classList.remove('hidden');
  if(!ok){box.innerHTML=`<strong class="bad">${escapeHtml(data.error)}</strong><p>Install the optional speech package or type the response in the fallback box.</p>`;return}
  if(id==='opiResult'){
    const pace=data.timing?.wpm?` · ${data.timing.wpm} speech-active WPM`:' · Pace needs at least 10 words';
    box.innerHTML=`<div class="score">Practice ILR estimate: ${escapeHtml(data.practice_level)}</div><p>${data.word_count} words${pace}</p><p><strong>Transcript:</strong> ${escapeHtml(data.recognized)}</p><p>${escapeHtml(data.note)}</p>`;return;
  }
  const warning=data.short_phrase_warning?'<p class="note"><strong>Short-phrase caution:</strong> Whisper differed by a letter, so character-level partial credit was used. This is recognition feedback, not a definitive pronunciation judgment.</p>':'';
  const pace=data.wpm?`<p><strong>Speaking rate:</strong> ${data.wpm} speech-active WPM over ${data.speech_seconds} seconds of detected speech</p>`:`<p class="note"><strong>WPM withheld:</strong> ${data.spoken_words??0} recognized word(s). At least three words are required for a meaningful pace estimate.</p>`;
  const mastery=data.review?`<p class="mastery-message"><strong>${escapeHtml(data.review.mastery_label)}</strong> · scheduled ${escapeHtml(data.review.next_review)}</p>`:'';
  box.innerHTML=`<div class="score">${data.score}% recognition match</div>${pace}<p><strong>Expected (${escapeHtml(data.register)}${data.variant!=='default'?' · '+escapeHtml(data.variant):''}):</strong> ${escapeHtml(data.expected)}</p><p><strong>Recognized:</strong> ${escapeHtml(data.recognized||'—')}</p><p><strong>Missing:</strong> ${data.missing.map(escapeHtml).join(', ')||'None'}</p><p><strong>Extra/different:</strong> ${data.extra.map(escapeHtml).join(', ')||'None'}</p>${mastery}${warning}`;
  if(data.profile){updateProfile(data.profile);loadToday()}
}

function updateProfile(profile){$('headerLevel').textContent=`Level ${profile.level} · ${profile.title}`}

async function loadToday(){
  const data=await fetch('/api/today').then(response=>response.json());state.today=data;updateProfile(data.profile);
  $('dashLevel').textContent=data.profile.level;$('dashXp').textContent=`${data.profile.xp} XP · ${data.profile.level_progress}% to next level`;$('levelRing').style.setProperty('--progress',`${data.profile.level_progress*3.6}deg`);
  $('todayMessage').textContent=data.due_count?`${data.due_count} review${data.due_count===1?' is':'s are'} ready. Start with the weakest memory trace.`:'Your scheduled reviews are clear. Build new mastery today.';$('dueBadge').textContent=`${data.due_count} due`;
  const mastered=data.mastery['4']||0,learning=(data.mastery['1']||0)+(data.mastery['2']||0),strong=data.mastery['3']||0;
  $('todayStats').innerHTML=`<div class="stat glow"><strong>${data.due_count}</strong><span>Due now</span></div><div class="stat"><strong>${learning}</strong><span>Learning</span></div><div class="stat"><strong>${strong}</strong><span>Strong</span></div><div class="stat"><strong>${mastered}</strong><span>Mastered</span></div>`;
  $('todayQueue').innerHTML=data.items.map((item,index)=>`<button class="review-item" data-type="${item.type}" data-id="${item.id}"><span class="queue-number">${index+1}</span><span><strong>${escapeHtml(item.label)}</strong><small>${escapeHtml(item.detail)}</small></span><em class="mastery-${item.mastery}">${escapeHtml(item.mastery_label)}</em></button>`).join('');
  $('todayQueue').querySelectorAll('button').forEach(button=>button.onclick=()=>openReviewItem(button.dataset.type,button.dataset.id));
  $('courseProgress').innerHTML=data.courses.map(course=>`<div class="course-progress"><div><strong>${escapeHtml(course.name)}</strong><span>${course.strong} of ${course.total} strong</span></div><div class="progress-track"><i style="width:${course.percent}%"></i></div><b>${course.percent}%</b></div>`).join('');
}
function openReviewItem(type,id){
  if(type==='phrase')return openPhraseById(id);
  const view=type==='conjugation'?'conjugation':type==='conversation'?'conversation':'vocabulary';document.querySelector(`[data-view="${view}"]`).click();
}
function openPhraseById(id){
  for(let li=0;li<state.catalog.languages.length;li++)for(let si=0;si<state.catalog.languages[li].scenarios.length;si++){const pi=state.catalog.languages[li].scenarios[si].phrases.findIndex(item=>item.id===id);if(pi>=0){state.language=li;state.scenario=si;state.course=state.catalog.languages[li].scenarios[si].course;state.phrase=pi;$('language').value=li;fillCourses();render();document.querySelector('[data-view="practice"]').click();return}}
}

async function loadConjugation(){
  const language=$('conjLanguage').value,tense=$('conjTense').value;state.conjQuestion=await fetch(`/api/conjugation/question?language=${language}&tense=${tense}`).then(response=>response.json());const q=state.conjQuestion;
  $('conjContext').textContent=`${q.subject_english} · ${q.verb_english} · ${q.tense}`;$('conjPrompt').textContent=`${q.subject} + ${q.verb}`;$('conjPrompt').dir=q.direction;$('conjResult').classList.add('hidden');
  $('conjChoices').innerHTML=q.choices.map(choice=>`<button data-choice="${escapeHtml(choice)}">${escapeHtml(choice)}</button>`).join('');$('conjChoices').querySelectorAll('button').forEach(button=>button.onclick=()=>answerConjugation(button));
}
async function answerConjugation(button){
  const q=state.conjQuestion,response=await fetch('/api/conjugation/answer',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...q,selected:button.dataset.choice})}),data=await response.json();
  $('conjChoices').querySelectorAll('button').forEach(item=>{item.disabled=true;if(item.dataset.choice===data.correct_answer)item.classList.add('correct')});if(!data.correct)button.classList.add('incorrect');
  const result=$('conjResult');result.classList.remove('hidden');result.innerHTML=`<div class="score">${data.correct?'Correct +10 XP':'Review +2 XP'}</div><p><strong>${escapeHtml(data.correct_answer)}</strong></p><p class="transliteration">${escapeHtml(data.transliteration)}</p><p class="mastery-message">${escapeHtml(data.review.mastery_label)} · next review ${escapeHtml(data.review.next_review)}</p><button id="conjContinue">Continue</button>`;$('conjContinue').onclick=loadConjugation;updateProfile(data.profile);loadToday();
}

async function loadConversation(){
  const language=$('conversationLanguage').value;state.conversationQuestion=await fetch(`/api/conversation/question?language=${language}`).then(response=>response.json());const q=state.conversationQuestion;
  $('conversationScenario').textContent=q.scenario.toUpperCase();$('conversationEnglish').textContent=q.english;$('conversationPrompt').textContent=q.prompt;$('conversationPrompt').dir=q.direction;$('conversationTransliteration').textContent=q.transliteration;$('conversationResult').classList.add('hidden');
  $('conversationChoices').innerHTML=q.choices.map(choice=>`<button data-choice="${escapeHtml(choice)}">${escapeHtml(choice)}</button>`).join('');$('conversationChoices').querySelectorAll('button').forEach(button=>button.onclick=()=>answerConversation(button));
}
async function answerConversation(button){
  const q=state.conversationQuestion,response=await fetch('/api/conversation/answer',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({phrase_id:q.phrase_id,selected:button.dataset.choice})}),data=await response.json();
  $('conversationChoices').querySelectorAll('button').forEach(item=>{item.disabled=true;if(item.dataset.choice===data.correct_answer)item.classList.add('correct')});if(!data.correct)button.classList.add('incorrect');
  const result=$('conversationResult');result.classList.remove('hidden');result.innerHTML=`<div class="score">${data.correct?'Natural response':'Better response'}</div><p>${escapeHtml(data.correct_answer)}</p><div class="dialogue-bubble outgoing"><p class="response-target">${escapeHtml(data.response)}</p><p class="transliteration">${escapeHtml(data.transliteration)}</p></div><p class="mastery-message">${escapeHtml(data.review.mastery_label)} · next review ${escapeHtml(data.review.next_review)}</p><button id="conversationResponseHear">▶ Hear response</button> <button id="conversationContinue">Continue</button>`;$('conversationResponseHear').onclick=()=>speak(data.response,state.catalog.languages.find(item=>item.id===q.language).speechLang);$('conversationContinue').onclick=loadConversation;updateProfile(data.profile);loadToday();
}

async function loadVocabulary(){
  const language=state.catalog.languages[Number($('vocabLanguage').value||0)].id,mode=$('vocabMode').value;
  state.vocabQuestion=await fetch(`/api/vocabulary/question?language=${encodeURIComponent(language)}&mode=${encodeURIComponent(mode)}`).then(response=>response.json());
  const question=state.vocabQuestion;$('vocabPrompt').textContent=question.prompt;$('vocabPrompt').dir=question.direction;$('vocabResult').classList.add('hidden');
  $('vocabHint').textContent=question.quiz_type==='bridge'?'Answer first; Arabic transliteration appears during review.':'';
  $('vocabChoices').innerHTML=question.choices.map(choice=>`<button data-choice="${escapeHtml(choice)}">${escapeHtml(choice)}</button>`).join('');
  $('vocabChoices').querySelectorAll('button').forEach(button=>button.onclick=()=>answerVocabulary(button));
}
async function answerVocabulary(button){
  const question=state.vocabQuestion,selected=button.dataset.choice;
  const response=await fetch('/api/vocabulary/answer',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({phrase_id:question.phrase_id,mode:question.mode,quiz_type:question.quiz_type,selected})});
  const data=await response.json();
  $('vocabChoices').querySelectorAll('button').forEach(item=>{item.disabled=true;if(item.dataset.choice===data.correct_answer)item.classList.add('correct')});
  if(!data.correct)button.classList.add('incorrect');
  const result=$('vocabResult');result.classList.remove('hidden');result.innerHTML=`<div class="score">${data.correct?'Correct +10 XP':'Review +2 XP'}</div><p>Answer: <strong>${escapeHtml(data.correct_answer)}</strong></p>${data.transliteration?`<p class="transliteration">${escapeHtml(data.transliteration)}</p>`:''}${data.note?`<p class="note">${escapeHtml(data.note)}</p>`:''}${data.review?`<p class="mastery-message">${escapeHtml(data.review.mastery_label)} · next review ${escapeHtml(data.review.next_review)}</p>`:''}<button id="vocabContinue">Continue</button>`;
  $('vocabContinue').onclick=loadVocabulary;updateProfile(data.profile);loadToday();
}

async function loadProgress(){
  const data=await fetch('/api/progress').then(response=>response.json()),summary=data.summary;
  const hardest=data.hardest.length?`<h3>Priority phrases</h3><table><thead><tr><th>Phrase</th><th>Language</th><th>Attempts</th><th>Accuracy</th><th>WPM</th></tr></thead><tbody>${data.hardest.map(row=>`<tr><td>${escapeHtml(row.english)}</td><td>${escapeHtml(row.language)}</td><td>${row.attempts}</td><td>${row.average}%</td><td>${row.average_wpm??'—'}</td></tr>`).join('')}</tbody></table>`:'<p class="note">Complete a scored phrase to begin your history.</p>';
  const vocabAccuracy=data.vocabulary.attempts?Math.round(data.vocabulary.correct/data.vocabulary.attempts*100):null;
  const conjugationAccuracy=data.conjugation.attempts?Math.round(data.conjugation.correct/data.conjugation.attempts*100):null;
  $('progressTable').innerHTML=`
    <div class="stat-grid">
      <div class="stat"><strong>${data.profile.level}</strong><span>${escapeHtml(data.profile.title)}</span></div>
      <div class="stat"><strong>${data.profile.xp}</strong><span>XP</span></div>
      <div class="stat"><strong>${summary.attempts}</strong><span>Attempts</span></div>
      <div class="stat"><strong>${summary.average??'—'}${summary.average!==null?'%':''}</strong><span>Average match</span></div>
      <div class="stat"><strong>${summary.best??'—'}${summary.best!==null?'%':''}</strong><span>Best match</span></div>
      <div class="stat"><strong>${summary.average_wpm??'—'}</strong><span>Average WPM</span></div>
      <div class="stat"><strong>${summary.measured_pace_attempts}</strong><span>Valid pace samples</span></div>
      <div class="stat"><strong>${vocabAccuracy===null?'—':vocabAccuracy+'%'}</strong><span>Vocabulary</span></div>
      <div class="stat"><strong>${conjugationAccuracy===null?'—':conjugationAccuracy+'%'}</strong><span>Conjugation</span></div>
    </div>
    <h3>What to work on</h3><div class="advice">${data.recommendations.map(item=>`<div>${escapeHtml(item)}</div>`).join('')}</div>
    ${hardest}
    <h3>Memory techniques</h3><div class="techniques">${data.techniques.map(item=>`<div class="technique"><strong>${escapeHtml(item.name)}</strong>${escapeHtml(item.steps)}</div>`).join('')}</div>`;
}

function changePhrase(update){resetAttempt();update();render()}
function bind(){
  document.querySelectorAll('.tab').forEach(button=>button.onclick=()=>{
    document.querySelectorAll('.tab,.view').forEach(item=>item.classList.remove('active'));button.classList.add('active');$(button.dataset.view).classList.add('active');
    if(button.dataset.view==='today')loadToday();if(button.dataset.view==='progress')loadProgress();if(button.dataset.view==='vocabulary'&&!state.vocabQuestion)loadVocabulary();if(button.dataset.view==='conjugation'&&!state.conjQuestion)loadConjugation();if(button.dataset.view==='conversation'&&!state.conversationQuestion)loadConversation();
  });
  $('startSession').onclick=()=>{const first=$('todayQueue').querySelector('button');if(first)first.click()};
  $('language').onchange=event=>changePhrase(()=>{state.language=Number(event.target.value);state.scenario=state.phrase=0;fillScenarios()});
  $('course').onchange=event=>changePhrase(()=>{state.course=event.target.value;state.phrase=0;fillScenarios()});
  $('scenario').onchange=event=>changePhrase(()=>{state.scenario=Number(event.target.value);state.phrase=0;fillPhrases()});
  $('phrase').onchange=event=>changePhrase(()=>{state.phrase=Number(event.target.value)});
  $('gender').onchange=event=>changePhrase(()=>{state.gender=event.target.value});
  $('register').onchange=event=>changePhrase(()=>{state.register=event.target.value});
  $('next').onclick=()=>changePhrase(()=>{const {s}=current();state.phrase=(state.phrase+1)%s.phrases.length});
  $('cipherToggle').onclick=()=>$('cipher').classList.toggle('hidden');
  $('play').onclick=()=>{const {l,p}=current(),form=currentForm();if(p.id)speak(form.target,l.speechLang,p.id,state.gender,state.register)};
  $('responseHear').onclick=()=>{const {l}=current(),reply=currentResponse();if(reply.response)speak(reply.response,l.speechLang)};
  $('record').onclick=()=>toggleRecording('phrase');$('scoreManual').onclick=()=>manualScore(false);
  $('opiLanguage').onchange=renderOpi;$('opiDifficulty').onchange=renderOpi;$('opiNew').onclick=renderOpi;
  $('opiHear').onclick=()=>{const l=state.catalog.languages[Number($('opiLanguage').value)];speak($('opiPrompt').textContent,l.speechLang)};
  $('opiRecord').onclick=()=>toggleRecording('opi');$('opiManual').onclick=()=>manualScore(true);
  $('vocabNew').onclick=loadVocabulary;$('vocabLanguage').onchange=loadVocabulary;$('vocabMode').onchange=loadVocabulary;
  $('conjNew').onclick=loadConjugation;$('conjLanguage').onchange=loadConjugation;$('conjTense').onchange=loadConjugation;
  $('conversationNew').onclick=loadConversation;$('conversationLanguage').onchange=loadConversation;$('conversationHear').onclick=()=>{const q=state.conversationQuestion;if(q)speak(q.prompt,state.catalog.languages.find(item=>item.id===q.language).speechLang)};
  $('wordSearch').oninput=renderWordRows;$('wordCategory').onchange=renderWordRows;$('cognatesOnly').onchange=renderWordRows;
  $('builderLanguage').onchange=fillBuilder;$('conjugationVerb').onchange=renderConjugation;$('conjugationTense').onchange=renderConjugation;
  ['builderSubject','builderComplement','builderTime','builderNegative','builderQuestion'].forEach(id=>$(id).onchange=buildSentence);$('builderVerb').onchange=fillBuilderComplements;
  $('builtHear').onclick=()=>{const data=builderData();speak($('builtTarget').textContent,data.speechLang)};
  $('builtCopy').onclick=async()=>{await navigator.clipboard.writeText(`${$('builtTarget').textContent}\n${$('builtTransliteration').textContent}`);$('builtCopy').textContent='Copied';setTimeout(()=>$('builtCopy').textContent='Copy sentence',1000)};
}
boot().catch(error=>{$('engineStatus').textContent='Startup error';console.error(error)});
