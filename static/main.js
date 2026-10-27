(function(){
  const video = document.getElementById('video');
  const canvas = document.getElementById('canvas');
  const judgeBtn = document.getElementById('judge');
  const resultDiv = document.getElementById('result');
  const counter = document.getElementById('hit-counter');
  let hits = Number(localStorage.getItem('costumeJudgeHits') || 666);

  function renderCounter(){
    counter.textContent = String(hits).padStart(7, '0');
  }

  async function startCamera(){
    try{
      const stream = await navigator.mediaDevices.getUserMedia({video:true});
      video.srcObject = stream;
    }catch(e){
      resultDiv.innerHTML = '<p class="error-message">Camera access is required to judge your costume.</p>';
    }
  }

  function showResult(json){
    resultDiv.innerHTML = '';
    const card = document.createElement('section');
    card.className = 'scorecard';
    card.innerHTML = `
      <h2>✦ The Judgment ✦</h2>
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
  }

  function escapeHtml(s){
    if(!s) return '';
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  judgeBtn.addEventListener('click', async ()=>{
    if(!video.videoWidth || !video.videoHeight){
      resultDiv.innerHTML = '<p class="error-message">The crystal ball is still warming up. Please try again.</p>';
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
        resultDiv.innerHTML = `<p class="error-message">${escapeHtml(e.message)}</p>`;
      }
    }, 'image/png');
  });

  renderCounter();
  startCamera();
})();
