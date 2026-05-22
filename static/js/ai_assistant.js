function recreateWelcomeCard(repoName) {
  const messagesContainer = document.getElementById('chat-messages');
  if (!messagesContainer) return;
  
  const existing = document.getElementById('assistant-welcome');
  if (existing) existing.remove();
  
  const welcomeCard = document.createElement('div');
  welcomeCard.className = 'assistant-welcome-card';
  welcomeCard.id = 'assistant-welcome';
  welcomeCard.innerHTML = `
    <div class="welcome-header">
      <div class="welcome-avatar">
        <i data-lucide="sparkles"></i>
      </div>
      <h3 id="assistant-welcome-title">Engineering AI Copilot</h3>
    </div>
    <p class="welcome-desc" id="assistant-welcome-desc">
      Hỏi bất kỳ điều gì về repository đã đồng bộ của bạn. Tôi có thể giải thích kiến trúc, rà soát quy trình auth flow, phân tích pipeline sync, hoặc đề xuất test cases.
    </p>
    <div class="welcome-suggestions-label">Gợi ý câu hỏi nhanh:</div>
    <div class="suggestion-chips-grid" id="welcome-suggestions-chips">
      <!-- suggestions chips grid gets loaded dynamically -->
    </div>
  `;
  messagesContainer.appendChild(welcomeCard);
  updateWelcomeAndSuggestions(repoName);
}

function loadScopedChatHistory(repoId, branchName, repoName) {
  const messagesContainer = document.getElementById('chat-messages');
  if (!messagesContainer) return;
  
  messagesContainer.innerHTML = '';
  
  const cacheKey = `git_analytics_chat_history:${repoId}:${branchName}`;
  const raw = localStorage.getItem(cacheKey);
  let messages = [];
  try {
    if (raw) {
      messages = JSON.parse(raw);
    }
  } catch (e) {
    console.error('Failed to parse chat history', e);
  }
  
  if (!Array.isArray(messages) || messages.length === 0) {
    recreateWelcomeCard(repoName);
    return;
  }
  
  messages.forEach(msg => {
    if (msg.role === 'user') {
      const userRow = document.createElement('div');
      userRow.className = 'chat-bubble-row user';
      userRow.innerHTML = `<div class="message-bubble user-bubble">${escapeHtml(msg.content)}</div>`;
      messagesContainer.appendChild(userRow);
    } else if (msg.role === 'assistant') {
      const assistantRow = document.createElement('div');
      assistantRow.className = 'chat-bubble-row assistant';
      
      const parsedHtml = typeof marked !== 'undefined' ? marked.parse(msg.answer) : escapeHtml(msg.answer);
      const answerBubbleId = 'answer-' + Math.random().toString(36).substring(2, 9);
      
      let contextBannerHtml = '';
      if (msg.context_metadata && msg.context_metadata.retrieved_files && msg.context_metadata.retrieved_files.length > 0) {
        const filteredFiles = msg.context_metadata.retrieved_files.filter(filePath => !filePath.includes('grapuco'));
        if (filteredFiles.length > 0) {
          const fileTags = filteredFiles.map(filePath => {
            const isMd = filePath.endsWith('.md');
            const icon = isMd ? 'file-text' : 'file-code';
            const parts = filePath.split('/');
            const simpleName = parts[parts.length - 1];
            return `<span class="source-tag" title="${escapeHtml(filePath)}"><i data-lucide="${icon}"></i> ${escapeHtml(simpleName)}</span>`;
          }).join('');
          
          contextBannerHtml = `
            <div class="context-sources-strip">
              <span class="sources-title"><i data-lucide="database"></i> Indexed Context:</span>
              <div class="sources-tags-wrapper">${fileTags}</div>
            </div>
          `;
        }
      }
      
      let devDebugHtml = '';
      if (msg.context_metadata) {
        const source = msg.context_metadata.repository_source || 'Unknown';
        const count = msg.context_metadata.retrieved_chunk_count || 0;
        const filesCount = (msg.context_metadata.retrieved_files || []).length;
        const repoId = msg.context_metadata.repository_id || 'N/A';
        const branchVal = msg.context_metadata.branch || 'N/A';
        const lastIndexed = msg.context_metadata.last_indexed_at || 'Never';
        const idxStatus = msg.context_metadata.indexing_status || 'unknown';
        const badgeColor = source === 'Local Workspace' ? '#10B981' : '#F59E0B';
        devDebugHtml = `
          <div class="dev-debug-badge" style="display: inline-flex; flex-wrap: wrap; align-items: center; gap: 6px; padding: 4px 8px; border-radius: 6px; font-size: 11px; font-family: SFMono-Regular, Consolas, monospace; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); margin-top: 8px; color: var(--text-muted); width: fit-content; line-height: 1.5;">
            <span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: ${badgeColor}; box-shadow: 0 0 8px ${badgeColor};"></span>
            <span style="font-weight: 600; color: var(--purple);">[Dev Debug]</span> 
            <span>Source: <strong>${escapeHtml(source)}</strong></span>
            <span style="opacity: 0.35;">|</span>
            <span>Chunks: <strong>${count}</strong></span>
            <span style="opacity: 0.35;">|</span>
            <span>Files: <strong>${filesCount}</strong></span>
            <span style="opacity: 0.35;">|</span>
            <span>Repo ID: <strong>${escapeHtml(String(repoId))}</strong></span>
            <span style="opacity: 0.35;">|</span>
            <span>Branch: <strong>${escapeHtml(branchVal)}</strong></span>
            <span style="opacity: 0.35;">|</span>
            <span>Status: <strong>${escapeHtml(idxStatus)}</strong></span>
            <span style="opacity: 0.35;">|</span>
            <span>Indexed At: <strong>${escapeHtml(lastIndexed)}</strong></span>
          </div>
        `;
      }
      
      assistantRow.innerHTML = `
        <div class="chat-avatar-mini"><i data-lucide="bot"></i></div>
        <div style="display: flex; flex-direction: column; gap: 6px; width: 100%; max-width: 820px;">
          <div id="${answerBubbleId}" class="message-bubble assistant-bubble">
            ${contextBannerHtml}
            ${parsedHtml}
            ${devDebugHtml}
          </div>
          <div class="feedback-chips-row">
            <button class="feedback-chip" onclick="copyFullAnswer('${answerBubbleId}', this)"><i data-lucide="copy"></i> <span>Copy Answer</span></button>
            <button class="feedback-chip" onclick="askFollowUp('Suggest improvements to this solution.')"><i data-lucide="sparkles"></i> Suggest Improvements</button>
            <button class="feedback-chip" onclick="askFollowUp('Explain this part further.')"><i data-lucide="code-2"></i> Explain Further</button>
          </div>
        </div>
      `;
      messagesContainer.appendChild(assistantRow);
    }
  });
  
  if (window.lucide) window.lucide.createIcons();
  const viewport = document.getElementById('chat-viewport');
  if (viewport) viewport.scrollTop = viewport.scrollHeight;
}

async function askAssistant() {
  const messagesContainer = document.getElementById('chat-messages');
  const viewport = document.getElementById('chat-viewport');
  const input = document.getElementById('assistant-question');
  if (!input) return;
  const question = input.value.trim();
  
  if (!question) return;
  
  // Hide welcome card on first interaction
  const welcome = document.getElementById('assistant-welcome');
  if (welcome) {
    welcome.remove();
  }
  
  // Append User message bubble
  const userRow = document.createElement('div');
  userRow.className = 'chat-bubble-row user';
  userRow.innerHTML = `<div class="message-bubble user-bubble">${escapeHtml(question)}</div>`;
  messagesContainer.appendChild(userRow);
  
  // Save user message to history
  const cacheKey = `git_analytics_chat_history:${activeRepoId}:${activeBranch || 'main'}`;
  let messages = [];
  try {
    const raw = localStorage.getItem(cacheKey);
    if (raw) messages = JSON.parse(raw);
  } catch (e) {}
  messages.push({ role: 'user', content: question });
  try {
    localStorage.setItem(cacheKey, JSON.stringify(messages));
  } catch (e) {}
  
  // Clear input and scroll
  input.value = '';
  viewport.scrollTop = viewport.scrollHeight;
  
  // Append Assistant elegant loading shimmer
  const indicatorRow = document.createElement('div');
  indicatorRow.className = 'chat-bubble-row assistant';
  indicatorRow.id = 'assistant-typing';
  indicatorRow.innerHTML = `
    <div class="chat-avatar-mini"><i data-lucide="bot"></i></div>
    <div class="message-bubble assistant-bubble shimmer-bubble" style="width: 100%; max-width: 540px;">
      <div class="shimmer-line long"></div>
      <div class="shimmer-line medium"></div>
      <div class="shimmer-line short"></div>
    </div>
  `;
  messagesContainer.appendChild(indicatorRow);
  if (window.lucide) window.lucide.createIcons();
  viewport.scrollTop = viewport.scrollHeight;
  
  try {
    // Append repository context metadata securely to the question payload
    let contextualQuestion = question;
    if (activeRepoId) {
      const reposList = window.userRepositories || [];
      const repo = reposList.find(r => r.id === activeRepoId);
      if (repo) {
        contextualQuestion += `\n\n[Context - Repository: ${repo.full_name}, Branch: ${activeBranch || 'N/A'}]`;
      }
    }
    
    // Call setup for robust marked formatting
    setupMarkedRenderer();
    
    const payload = {
      question: contextualQuestion,
      repo_id: activeRepoId,
      branch: activeBranch
    };
    
    const data = await postAI('/api/v1/ai/assistant', payload);
    
    // Remove typing indicator
    const typingIndicator = document.getElementById('assistant-typing');
    if (typingIndicator) typingIndicator.remove();
    
    // Append Assistant response bubble with sources strip and quick feedback chips
    const assistantRow = document.createElement('div');
    assistantRow.className = 'chat-bubble-row assistant';
    
    let contextBannerHtml = '';
    if (data.context_metadata && data.context_metadata.retrieved_files && data.context_metadata.retrieved_files.length > 0) {
      const filteredFiles = data.context_metadata.retrieved_files.filter(filePath => !filePath.includes('grapuco'));
      if (filteredFiles.length > 0) {
        const fileTags = filteredFiles.map(filePath => {
          const isMd = filePath.endsWith('.md');
          const icon = isMd ? 'file-text' : 'file-code';
          const parts = filePath.split('/');
          const simpleName = parts[parts.length - 1];
          return `<span class="source-tag" title="${escapeHtml(filePath)}"><i data-lucide="${icon}"></i> ${escapeHtml(simpleName)}</span>`;
        }).join('');
        
        contextBannerHtml = `
          <div class="context-sources-strip">
            <span class="sources-title"><i data-lucide="database"></i> Indexed Context:</span>
            <div class="sources-tags-wrapper">${fileTags}</div>
          </div>
        `;
      }
    }
    
    // Build beautiful [Dev Debug] section
    let devDebugHtml = '';
    if (data.context_metadata) {
      const source = data.context_metadata.repository_source || 'Unknown';
      const count = data.context_metadata.retrieved_chunk_count || 0;
      const filesCount = (data.context_metadata.retrieved_files || []).length;
      const repoId = data.context_metadata.repository_id || 'N/A';
      const branchVal = data.context_metadata.branch || 'N/A';
      const lastIndexed = data.context_metadata.last_indexed_at || 'Never';
      const idxStatus = data.context_metadata.indexing_status || 'unknown';
      const badgeColor = source === 'Local Workspace' ? '#10B981' : '#F59E0B';
      devDebugHtml = `
        <div class="dev-debug-badge" style="display: inline-flex; flex-wrap: wrap; align-items: center; gap: 6px; padding: 4px 8px; border-radius: 6px; font-size: 11px; font-family: SFMono-Regular, Consolas, monospace; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); margin-top: 8px; color: var(--text-muted); width: fit-content; line-height: 1.5;">
          <span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: ${badgeColor}; box-shadow: 0 0 8px ${badgeColor};"></span>
          <span style="font-weight: 600; color: var(--purple);">[Dev Debug]</span> 
          <span>Source: <strong>${escapeHtml(source)}</strong></span>
          <span style="opacity: 0.35;">|</span>
          <span>Chunks: <strong>${count}</strong></span>
          <span style="opacity: 0.35;">|</span>
          <span>Files: <strong>${filesCount}</strong></span>
          <span style="opacity: 0.35;">|</span>
          <span>Repo ID: <strong>${escapeHtml(String(repoId))}</strong></span>
          <span style="opacity: 0.35;">|</span>
          <span>Branch: <strong>${escapeHtml(branchVal)}</strong></span>
          <span style="opacity: 0.35;">|</span>
          <span>Status: <strong>${escapeHtml(idxStatus)}</strong></span>
          <span style="opacity: 0.35;">|</span>
          <span>Indexed At: <strong>${escapeHtml(lastIndexed)}</strong></span>
        </div>
      `;
    }
    
    const answerBubbleId = 'answer-' + Math.random().toString(36).substring(2, 9);
    const parsedHtml = typeof marked !== 'undefined' ? marked.parse(data.answer) : escapeHtml(data.answer);
    
    assistantRow.innerHTML = `
      <div class="chat-avatar-mini"><i data-lucide="bot"></i></div>
      <div style="display: flex; flex-direction: column; gap: 6px; width: 100%; max-width: 820px;">
        <div id="${answerBubbleId}" class="message-bubble assistant-bubble">
          ${contextBannerHtml}
          ${parsedHtml}
          ${devDebugHtml}
        </div>
        <div class="feedback-chips-row">
          <button class="feedback-chip" onclick="copyFullAnswer('${answerBubbleId}', this)"><i data-lucide="copy"></i> <span>Copy Answer</span></button>
          <button class="feedback-chip" onclick="askFollowUp('Suggest improvements to this solution.')"><i data-lucide="sparkles"></i> Suggest Improvements</button>
          <button class="feedback-chip" onclick="askFollowUp('Explain this part further.')"><i data-lucide="code-2"></i> Explain Further</button>
        </div>
      </div>
    `;
    
    messagesContainer.appendChild(assistantRow);
    updateActiveProviderBadge(data.metadata);
    
    // Save assistant response to history
    try {
      const raw = localStorage.getItem(cacheKey);
      if (raw) messages = JSON.parse(raw);
    } catch (e) {}
    messages.push({
      role: 'assistant',
      answer: data.answer,
      context_metadata: data.context_metadata,
      metadata: data.metadata
    });
    try {
      localStorage.setItem(cacheKey, JSON.stringify(messages));
    } catch (e) {}
    
  } catch (err) {
    // Remove typing indicator
    const typingIndicator = document.getElementById('assistant-typing');
    if (typingIndicator) typingIndicator.remove();
    
    // Append Assistant error bubble
    const assistantRow = document.createElement('div');
    assistantRow.className = 'chat-bubble-row assistant';
    assistantRow.innerHTML = `
      <div class="chat-avatar-mini"><i data-lucide="alert-circle" style="color:var(--danger-text)"></i></div>
      <div class="message-bubble assistant-bubble" style="color:var(--danger-text)">Chưa có câu trả lời: ${escapeHtml(err.message)}</div>
    `;
    messagesContainer.appendChild(assistantRow);
  }
  
  if (window.lucide) window.lucide.createIcons();
  viewport.scrollTop = viewport.scrollHeight;
}
