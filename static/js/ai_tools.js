async function postAI(path, payload) {
  if (!window.ai_enabled) {
    throw new Error(window.ai_message || "AI settings not configured.");
  }
  const res = await fetch(path, {
    method: 'POST',
    credentials: 'same-origin',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload)
  });
  const json = await res.json();
  if (!res.ok || json.error) throw new Error(json.error?.message || `HTTP ${res.status}`);
  return json.data;
}

function escapeHtml(value) {
  return String(value || '').replace(/[&<>"']/g, char => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  }[char]));
}

function updateActiveProviderBadge(metadata) {
  if (metadata && metadata.source) {
    const label = metadata.source;
    const icon = label.startsWith('Cloud') ? 'sparkles' : 'bot';
    
    const badge = document.getElementById('active-provider-badge');
    if (badge) {
      badge.innerHTML = `<code class="provider-mono"><i data-lucide="${icon}"></i> ${escapeHtml(label)}</code>`;
    }
    
    const chatBadge = document.getElementById('chat-provider-badge');
    if (chatBadge) {
      chatBadge.innerHTML = `<code class="provider-mono" style="font-size: 10px;"><i data-lucide="${icon}" style="width:11px; height:11px;"></i> ${escapeHtml(label)}</code>`;
    }
    
    if (window.lucide) window.lucide.createIcons();
  }
}

// Premium Code Block Copy Helper
function copyCodeBlock(codeId, btn) {
  const codeEl = document.getElementById(codeId);
  if (!codeEl) return;
  const text = codeEl.textContent;
  
  navigator.clipboard.writeText(text).then(() => {
    const textSpan = btn.querySelector('span');
    btn.style.borderColor = 'rgba(74, 222, 128, 0.4)';
    btn.style.background = 'rgba(74, 222, 128, 0.08)';
    btn.style.color = '#4ade80';
    if (textSpan) textSpan.textContent = 'Copied!';
    
    setTimeout(() => {
      btn.style.borderColor = '';
      btn.style.background = '';
      btn.style.color = '';
      if (textSpan) textSpan.textContent = 'Copy';
    }, 2000);
  }).catch(err => {
    console.error('Failed to copy: ', err);
  });
}

// Copy full response helper
function copyFullAnswer(bubbleId, btn) {
  const bubble = document.getElementById(bubbleId);
  if (!bubble) return;
  let cleanText = bubble.innerText;
  
  // Strip files context tag text if present to only copy assistant response
  const contextStrip = bubble.querySelector('.context-sources-strip');
  if (contextStrip) {
    cleanText = cleanText.replace(contextStrip.innerText, '').trim();
  }
  
  navigator.clipboard.writeText(cleanText).then(() => {
    const textSpan = btn.querySelector('span');
    btn.style.borderColor = 'rgba(74, 222, 128, 0.4)';
    btn.style.background = 'rgba(74, 222, 128, 0.08)';
    btn.style.color = '#4ade80';
    if (textSpan) textSpan.textContent = 'Copied!';
    
    setTimeout(() => {
      btn.style.borderColor = '';
      btn.style.background = '';
      btn.style.color = '';
      if (textSpan) textSpan.textContent = 'Copy Answer';
    }, 2000);
  }).catch(err => console.error(err));
}

// Click chips handler
function askFollowUp(text) {
  const input = document.getElementById('assistant-question');
  if (input) {
    input.value = text;
    askAssistant();
  }
}

async function generateCommit() {
  const output = document.getElementById('commit-output');
  if (!output) return;
  output.textContent = 'Đang phân tích diff...';
  try {
    const diffInput = document.getElementById('commit-diff');
    const diffValue = diffInput ? diffInput.value : '';
    const data = await postAI('/api/v1/ai/commit-message', {diff: diffValue});
    output.textContent = data.message;
    updateActiveProviderBadge(data.metadata);
  } catch (err) {
    output.textContent = 'Chưa tạo được commit message: ' + err.message;
  }
}

async function reviewDiff() {
  const output = document.getElementById('review-output');
  if (!output) return;
  output.textContent = 'Đang rà soát diff...';
  try {
    const diffInput = document.getElementById('review-diff');
    const diffValue = diffInput ? diffInput.value : '';
    const data = await postAI('/api/v1/ai/review', {diff: diffValue});
    output.innerHTML = data.findings.map(item => `<div class="review-item"><strong>${escapeHtml(item.title)}</strong><span>${escapeHtml(item.detail)}</span></div>`).join('');
    updateActiveProviderBadge(data.metadata);
  } catch (err) {
    output.textContent = 'Chưa review được diff: ' + err.message;
  }
}

function useSuggestion(text) {
  const input = document.getElementById('assistant-question');
  if (input) {
    input.value = text;
    askAssistant();
  }
}

function toggleGuide() {
  const content = document.getElementById('guide-content');
  const icon = document.getElementById('guide-toggle-icon');
  const badgeText = document.getElementById('guide-badge-text');
  
  if (!content) return;
  
  if (content.style.display === 'none' || content.style.display === '') {
    content.style.display = 'block';
    if (icon) icon.innerHTML = `<i data-lucide="chevron-up"></i> Ẩn cẩm nang`;
    if (badgeText) badgeText.textContent = 'Ẩn cẩm nang';
  } else {
    content.style.display = 'none';
    if (icon) icon.innerHTML = `<i data-lucide="chevron-down"></i> Xem cẩm nang`;
    if (badgeText) badgeText.textContent = 'Xem cẩm nang';
  }
  if (window.lucide) window.lucide.createIcons();
}

// Initial Bootstrap Icon Creation
if (window.lucide) {
  window.lucide.createIcons();
}
