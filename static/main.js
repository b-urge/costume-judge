(function(){
  const video = document.getElementById('video');
  const canvas = document.getElementById('canvas');
  const judgeBtn = document.getElementById('judge');
  const resultDiv = document.getElementById('result');
  const fileInput = document.getElementById('file-input');
  const counter = document.getElementById('hit-counter');
  let hits = Number(localStorage.getItem('costumeJudgeHits') || 666);
  let audioElem = null;
  let muteBtn = null;
  let replayBtn = null;
  let lastRoast = null;
  let lastMP3 = null;
  let usedBrowserSpeak = false;

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
    }catch(e){
      resultDiv.innerHTML = '<p class="error-message">Camera access is required to judge your costume. You can also upload a photo below.</p>';
    }
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
      // Replay cached mp3
      audioElem = document.createElement('audio');
      audioElem.src = URL.createObjectURL(lastMP3);
      audioElem.autoplay = true;
      audioElem.controls = false;
      audioElem.style.display = 'none';
      document.body.appendChild(audioElem);
      attachMuteBtn();
      return;
    }
    lastMP3 = null;
    try {
      const resp = await fetch('/speak', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({text})});
      if(resp.ok && resp.headers.get('Content-Type') === 'audio/mpeg'){
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
    }catch(e){
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
    if(typeof window.speechSynthesis !== "undefined"){
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.rate = 1.05;
      u.pitch = 1.0;
      u.volume = 1;
      // Pick a more dramatic voice if available
      const voices = window.speechSynthesis.getVoices();
      for(const v of voices){
        if(/fem|dramatic|emma|google|voice|en/i.test(v.name)) { u.voice = v; break; }
      }
      window.speechSynthesis.speak(u);
    }
  }

  async function uploadBlob(blob){
    const fd = new FormData();
    fd.append('photo', blob, 'photo.png');
    resultDiv.textContent = 'Consulting the haunted fashion oracle...';
    try{
      const resp = await fetch('/upload',{method:'POST',body:fd});
      if(!resp.ok) throw new Error('Upload failed');
      const j = await resp.json();
      if(j.message) throw new Error(j.message);
      showResult(j);
      hits += 1;
      localStorage.setItem('costumeJudgeHits', String(hits));
      renderCounter();
    }catch(e){
      // Friendly fallback message
      resultDiv.innerHTML = `<p class="error-message">The spirits are busy, try again in a moment</p>`;
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
    canvas.toBlob(async (blob)=>{
      if(!blob){
        resultDiv.innerHTML = '<p class="error-message">Could not capture the costume photo. Try again.</p>';
        return;
      }
      await uploadBlob(blob);
    }, 'image/png');
  });

  // File input fallback
  if(fileInput){
    fileInput.addEventListener('change', ()=>{
      const f = fileInput.files && fileInput.files[0];
      if(!f) return;
      const reader = new FileReader();
      reader.onload = function(){
        const img = new Image();
        img.onload = function(){
          canvas.width = img.naturalWidth;
          canvas.height = img.naturalHeight;
          const ctx = canvas.getContext('2d');
          ctx.drawImage(img,0,0);
          canvas.toBlob(async (blob)=>{
            if(!blob){ resultDiv.innerHTML = '<p class="error-message">Could not read the image. Try another file.</p>'; return; }
            await uploadBlob(blob);
          }, 'image/png');
        };
        img.src = reader.result;
      };
      reader.readAsDataURL(f);
    });
  }

  renderCounter();
  startCamera();
})();
