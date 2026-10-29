(function(){
  const video = document.getElementById('video');
  const canvas = document.getElementById('canvas');
  const judgeBtn = document.getElementById('judge');
  const resultDiv = document.getElementById('result');
  const fileInput = document.getElementById('file-input');
  const counter = document.getElementById('hit-counter');

  const EVENT_CODE_KEY = 'costumeJudgeEventCode';
  const MAX_IMAGE_DIMENSION = 1024;

  let hits = Number(localStorage.getItem('costumeJudgeHits') || 666);
  let audioElem = null;
  let muteBtn = null;
  let replayBtn = null;
  let lastRoast = null;
  let lastMP3 = null;
  let usedBrowserSpeak = false;
  let eventCodeRequired = false;

  function renderCounter(){
    if(counter) counter.textContent = String(hits).padStart(7, '0');
  }

  async function startCamera(){
    if(!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia){
      resultDiv.innerHTML = '<p class="error-message">Camera access is unavailable here. You can upload a photo below.</p>';
      return;
    }
    try{
      const stream = await navigator.mediaDevices.getUserMedia({video:{facingMode:'user'}, audio:false});
      video.srcObject = stream;
      await video.play();
    }catch(_e){
      resultDiv.innerHTML = '<p class="error-message">Camera access is required to judge your costume. You can also upload a photo below.</p>';
    }
  }

  function getEventCode(){
    return localStorage.getItem(EVENT_CODE_KEY) || '';
  }

  async function fetchEventCodeRequirement(){
    try {
      const resp = await fetch('/api/config');
      if(!resp.ok) return;
      const data = await resp.json();
      eventCodeRequired = !!data.event_code_required;
    } catch(_e){
      eventCodeRequired = false;
    }
  }

  async function ensureEventCode(){
    if(!eventCodeRequired) return true;
    if(getEventCode()) return true;
    const entered = window.prompt('Enter event passcode to continue:');
    if(!entered || !entered.trim()) return false;
    localStorage.setItem(EVENT_CODE_KEY, entered.trim());
    return true;
  }

  function apiHeaders(base){
    const headers = base || {};
    const code = getEventCode();
    if(code) headers['x-event-code'] = code;
    return headers;
  }

  function clearEventCode(){
    localStorage.removeItem(EVENT_CODE_KEY);
  }

  function showResult(json){
    resultDiv.innerHTML = '';
    const card = document.createElement('section');
    card.className = 'scorecard';
    card.innerHTML = `
      <h2>Scorecard</h2>
      <p class="costume">${escapeHtml(json.costume || 'Unknown costume')}</p>
      <table class="scores">
        <thead><tr><th scope="col">Dark Arts Category</th><th scope="col">Score</th></tr></thead>
        <tbody>
          <tr><th scope="row">Spookiness</th><td>${json.spookiness}/10</td></tr>
          <tr><th scope="row">Creativity</th><td>${json.creativity}/10</td></tr>
          <tr><th scope="row">Effort</th><td>${json.effort}/10</td></tr>
          <tr><th scope="row">Overall</th><td>${json.overall}/10</td></tr>
        </tbody>
      </table>
      <p class="roast">${escapeHtml(json.roast || '')}</p>
    `;
    resultDiv.appendChild(card);
    playRoast(json.roast);
    insertReplayButton();
  }

  function escapeHtml(s){
    if(!s) return '';
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  async function playRoast(text, isReplay = false){
    lastRoast = text;
    usedBrowserSpeak = false;
    if(audioElem) { audioElem.pause(); audioElem.remove(); audioElem = null; }
    if(muteBtn) { muteBtn.remove(); muteBtn = null; }
    if(!text || typeof text !== 'string') return;
    if(lastMP3 && isReplay) {
      audioElem = document.createElement('audio');
      audioElem.src = URL.createObjectURL(lastMP3);
      audioElem.autoplay = true;
      audioElem.controls = false;
      audioElem.style.display = 'none';
      document.body.appendChild(audioElem);
      attachMuteBtn();
      return;
    }

    if(!(await ensureEventCode())) return;

    lastMP3 = null;
    try {
      const resp = await fetch('/api/speak', {
        method: 'POST',
        headers: apiHeaders({'Content-Type': 'application/json'}),
        body: JSON.stringify({text})
      });
      if(resp.status === 401 || resp.status === 403){
        clearEventCode();
        if(await ensureEventCode()) return playRoast(text, isReplay);
        return;
      }
      if(resp.ok && (resp.headers.get('Content-Type') || '').includes('audio/mpeg')){
        const blob = await resp.blob();
        lastMP3 = blob;
        audioElem = document.createElement('audio');
        audioElem.src = URL.createObjectURL(blob);
        audioElem.autoplay = true;
        audioElem.controls = false;
        audioElem.style.display = 'none';
        document.body.appendChild(audioElem);
        attachMuteBtn();
      } else {
        usedBrowserSpeak = true;
        browserSpeak(text);
      }
    }catch(_e){
      usedBrowserSpeak = true;
      browserSpeak(text);
    }
  }

  function attachMuteBtn() {
    muteBtn = document.createElement('button');
    muteBtn.className = 'mute-btn';
    muteBtn.textContent = '🔊';
    muteBtn.setAttribute('aria-label','Mute/unmute roast audio');
    muteBtn.onclick = ()=>{
      if(audioElem.muted) { audioElem.muted = false; muteBtn.textContent = '🔊'; }
      else { audioElem.muted = true; muteBtn.textContent = '🔇'; }
    };
    resultDiv.appendChild(muteBtn);
    audioElem.addEventListener('ended',()=>{ if(muteBtn) muteBtn.remove(); });
  }

  function insertReplayButton() {
    if(replayBtn) replayBtn.remove();
    replayBtn = document.createElement('button');
    replayBtn.className = 'replay-btn';
    replayBtn.textContent = 'Replay roast';
    replayBtn.setAttribute('aria-label', 'Replay the roast aloud');
    replayBtn.onclick = () => {
      if(lastMP3) {
        playRoast(lastRoast, true);
      } else if (lastRoast && usedBrowserSpeak) {
        browserSpeak(lastRoast);
      }
    };
    resultDiv.appendChild(replayBtn);
  }

  function browserSpeak(text){
    if(typeof window.speechSynthesis !== 'undefined'){
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.rate = 1.05;
      u.pitch = 1.0;
      u.volume = 1;
      const voices = window.speechSynthesis.getVoices();
      for(const v of voices){
        if(/fem|dramatic|emma|google|voice|en/i.test(v.name)) { u.voice = v; break; }
      }
      window.speechSynthesis.speak(u);
    }
  }

  function resizedJpegBlobFromSource(sourceCanvas, quality){
    return new Promise((resolve) => {
      const width = sourceCanvas.width;
      const height = sourceCanvas.height;
      const longest = Math.max(width, height);
      const scale = longest > MAX_IMAGE_DIMENSION ? (MAX_IMAGE_DIMENSION / longest) : 1;
      const out = document.createElement('canvas');
      out.width = Math.max(1, Math.round(width * scale));
      out.height = Math.max(1, Math.round(height * scale));
      const outCtx = out.getContext('2d');
      outCtx.drawImage(sourceCanvas, 0, 0, out.width, out.height);
      out.toBlob((blob) => resolve(blob), 'image/jpeg', quality);
    });
  }

  async function uploadBlob(blob){
    if(!(await ensureEventCode())){
      resultDiv.innerHTML = '<p class="error-message">Passcode required.</p>';
      return;
    }

    const fd = new FormData();
    fd.append('photo', blob, 'photo.jpg');
    const waitingText = 'Consulting the haunted fashion oracle...';
    resultDiv.innerHTML = `
      <section class="loading-card" aria-live="polite">
        <div class="loading-spinner" aria-hidden="true"></div>
        <p class="loading-text">${escapeHtml(waitingText)}</p>
      </section>
    `;
    try{
      const resp = await fetch('/api/judge', {method:'POST', headers: apiHeaders(), body:fd});
      if(resp.status === 401 || resp.status === 403){
        clearEventCode();
        if(await ensureEventCode()) return uploadBlob(blob);
        throw new Error('Passcode required');
      }
      if(!resp.ok) throw new Error('Upload failed');
      const j = await resp.json();
      if(j.message) throw new Error(j.message);
      showResult(j);
      hits += 1;
      localStorage.setItem('costumeJudgeHits', String(hits));
      renderCounter();
    }catch(_e){
      resultDiv.innerHTML = '<p class="error-message">The spirits are busy, try again in a moment</p>';
    }
  }

  judgeBtn.addEventListener('click', async ()=>{
    if(!video.videoWidth || !video.videoHeight){
      resultDiv.innerHTML = '<p class="error-message">The camera is not ready. Allow camera access or upload a photo below.</p>';
      return;
    }
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video,0,0);
    const blob = await resizedJpegBlobFromSource(canvas, 0.86);
    if(!blob){
      resultDiv.innerHTML = '<p class="error-message">Could not capture the costume photo. Try again.</p>';
      return;
    }
    await uploadBlob(blob);
  });

  if(fileInput){
    fileInput.addEventListener('change', ()=>{
      const f = fileInput.files && fileInput.files[0];
      if(!f) return;
      const reader = new FileReader();
      reader.onload = function(){
        const img = new Image();
        img.onload = async function(){
          canvas.width = img.naturalWidth;
          canvas.height = img.naturalHeight;
          const ctx = canvas.getContext('2d');
          ctx.drawImage(img,0,0);
          const blob = await resizedJpegBlobFromSource(canvas, 0.86);
          if(!blob){
            resultDiv.innerHTML = '<p class="error-message">Could not read the image. Try another file.</p>';
            return;
          }
          await uploadBlob(blob);
        };
        img.src = reader.result;
      };
      reader.readAsDataURL(f);
    });
  }

  (async ()=>{
    renderCounter();
    await fetchEventCodeRequirement();
    await ensureEventCode();
    startCamera();
  })();
})();
