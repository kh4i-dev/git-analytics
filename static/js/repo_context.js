// Global repository and branch state variables
let activeRepoId = null;
let activeBranch = null;

async function clearBackendContextCache(repoId, branchName) {
  try {
    await postAI('/api/v1/ai/clear-context', { repo_id: repoId, branch: branchName });
  } catch (e) {
    console.error('Failed to clear backend context cache', e);
  }
}

// Client-side Custom Dropdown Controls
function toggleDropdown(menuId) {
  const menus = ['repo-menu', 'branch-menu'];
  menus.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      if (id === menuId) {
        el.classList.toggle('is-active');
      } else {
        el.classList.remove('is-active');
      }
    }
  });
}

function filterRepositories(event) {
  const query = event.target.value.toLowerCase();
  const items = document.querySelectorAll('#repo-list .dropdown-item');
  items.forEach(item => {
    const text = item.getAttribute('data-repo-fullname').toLowerCase();
    if (text.includes(query)) {
      item.style.display = 'flex';
    } else {
      item.style.display = 'none';
    }
  });
}

function selectRepository(repoId, savedBranch = null) {
  const reposList = window.userRepositories || [];
  const repo = reposList.find(r => r.id === repoId);
  if (!repo) return;

  activeRepoId = repoId;
  localStorage.setItem('git_analytics_ai_active_repo', repoId);

  // Update selected repo styling
  document.querySelectorAll('#repo-list .dropdown-item').forEach(item => {
    if (parseInt(item.getAttribute('data-repo-id')) === repoId) {
      item.classList.add('is-selected');
    } else {
      item.classList.remove('is-selected');
    }
  });

  // Update repo trigger text label
  const repoLabel = document.getElementById('selected-repo-label');
  if (repoLabel) repoLabel.textContent = repo.full_name;

  // Build branch options contextual list
  const branchList = document.getElementById('branch-list');
  if (branchList) {
    branchList.innerHTML = '';
    
    // Add default branch
    if (repo.default_branch) {
      const defaultDiv = document.createElement('div');
      defaultDiv.className = 'dropdown-item mono-font';
      defaultDiv.setAttribute('data-branch-name', repo.default_branch);
      defaultDiv.innerHTML = `<i data-lucide="git-commit" class="item-icon"></i> <span>${escapeHtml(repo.default_branch)} <small style="opacity:0.65">(default)</small></span>`;
      defaultDiv.onclick = (e) => { selectBranch(repo.default_branch); e.stopPropagation(); };
      branchList.appendChild(defaultDiv);
    }

    // Add other synced branches
    (repo.branches || []).forEach(bName => {
      if (bName !== repo.default_branch) {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'dropdown-item mono-font';
        itemDiv.setAttribute('data-branch-name', bName);
        itemDiv.innerHTML = `<i data-lucide="git-branch" class="item-icon"></i> <span>${escapeHtml(bName)}</span>`;
        itemDiv.onclick = (e) => { selectBranch(bName); e.stopPropagation(); };
        branchList.appendChild(itemDiv);
      }
    });

    if (window.lucide) window.lucide.createIcons();
  }

  // Pick branch
  let targetBranch = savedBranch || repo.default_branch || 'main';
  // Ensure the picked branch actually exists in repo's list, fallback to default branch if not
  const allRepoBranches = [...(repo.branches || [])];
  if (repo.default_branch && !allRepoBranches.includes(repo.default_branch)) {
    allRepoBranches.push(repo.default_branch);
  }
  if (!allRepoBranches.includes(targetBranch)) {
    targetBranch = repo.default_branch || allRepoBranches[0] || 'main';
  }
  selectBranch(targetBranch);

  // Update context info row details
  document.getElementById('info-repo-name').textContent = repo.full_name;
  document.getElementById('info-commits-count').textContent = repo.commit_count;
  document.getElementById('info-contributors-count').textContent = repo.contributor_count;

  // Toggle layout sections visibility
  document.getElementById('ai-scope-badge').style.display = 'inline-flex';
  document.getElementById('active-context-info').style.display = 'flex';
  document.getElementById('chat-onboarding-state').style.display = 'none';
  document.getElementById('chat-messages').style.display = 'flex';
  
  // Enable interactive input textareas
  const chatInput = document.getElementById('assistant-question');
  const chatSend = document.getElementById('send-question-btn');
  if (chatInput) {
    chatInput.removeAttribute('disabled');
    chatInput.placeholder = `Ask about auth flow, sync pipeline, architecture or modules in ${repo.full_name}`;
  }
  if (chatSend) chatSend.removeAttribute('disabled');

  // Close dropdown menu
  toggleDropdown(null);
}

function selectBranch(branchName) {
  activeBranch = branchName;
  localStorage.setItem('git_analytics_ai_active_branch', branchName);

  // Update trigger branch text label
  const branchLabel = document.getElementById('selected-branch-label');
  if (branchLabel) branchLabel.textContent = branchName;

  // Update selected branch list class
  document.querySelectorAll('#branch-list .dropdown-item').forEach(item => {
    if (item.getAttribute('data-branch-name') === branchName) {
      item.classList.add('is-selected');
    } else {
      item.classList.remove('is-selected');
    }
  });

  // Update info bar detail
  document.getElementById('info-branch-name').textContent = branchName;

  // Invalidate cache and load scoped history
  if (activeRepoId) {
    clearBackendContextCache(activeRepoId, branchName);
    const reposList = window.userRepositories || [];
    const repo = reposList.find(r => r.id === activeRepoId);
    const repoName = repo ? repo.name : 'Repository';
    loadScopedChatHistory(activeRepoId, branchName, repoName);
    updateIndexStatusUI(activeRepoId);
  }

  // Close dropdown menu
  toggleDropdown(null);
}

function updateWelcomeAndSuggestions(repoName) {
  // Update welcome header
  const title = document.getElementById('assistant-welcome-title');
  if (title) title.innerHTML = `Engineering AI Copilot <span style="color:var(--purple); font-size:12px; font-weight:700; margin-left:6px; font-family:monospace; background:rgba(188,140,255,0.08); padding:2px 6px; border-radius:4px; border:1px solid rgba(188,140,255,0.15)">${escapeHtml(repoName)}</span>`;

  const desc = document.getElementById('assistant-welcome-desc');
  if (desc) desc.textContent = `Hỏi bất kỳ điều gì về codebase của ${repoName}. Tôi có thể phân tích kiến trúc sync service, giải thích quy trình auth flow, đề xuất test cases, hoặc rà soát cấu trúc thư mục.`;

  // Update quick chips
  const chipsGrid = document.getElementById('welcome-suggestions-chips');
  if (chipsGrid) {
    chipsGrid.innerHTML = `
      <div class="suggestion-chip" onclick="useSuggestion('Giải thích kiến trúc đồng bộ repository (Sync Service) của ${escapeHtml(repoName)}')">
        <i data-lucide="git-compare"></i> Explain ${escapeHtml(repoName)} sync
      </div>
      <div class="suggestion-chip" onclick="useSuggestion('Quy trình auth và đăng nhập bằng GitHub được thiết kế ra sao trong ${escapeHtml(repoName)}?')">
        <i data-lucide="shield-check"></i> Review auth flow
      </div>
      <div class="suggestion-chip" onclick="useSuggestion('Đề xuất bộ test case cho chức năng chuyển đổi cấu hình BYOK trong ${escapeHtml(repoName)}.')">
        <i data-lucide="terminal"></i> Suggest test cases
      </div>
      <div class="suggestion-chip" onclick="useSuggestion('Phân tích cấu trúc thư mục và các module chính của ${escapeHtml(repoName)}.')">
        <i data-lucide="brain-circuit"></i> Analyze repository structure
      </div>
    `;
  }

  // Update mini chips
  const miniChips = document.getElementById('mini-suggestions-chips');
  if (miniChips) {
    miniChips.innerHTML = `
      <div class="suggestion-chip-mini" onclick="useSuggestion('Đề xuất cải tiến cấu trúc dự án ${escapeHtml(repoName)}')">
        Suggest improvements
      </div>
      <div class="suggestion-chip-mini" onclick="useSuggestion('Tạo tóm tắt release notes từ commit gần đây trong ${escapeHtml(repoName)}')">
        Generate release summary
      </div>
    `;
  }

  if (window.lucide) window.lucide.createIcons();
}

// Global click-away handler to auto-close custom dropdowns
document.addEventListener('click', () => {
  toggleDropdown(null);
});

async function updateIndexStatusUI(repoId) {
  if (!repoId) return;
  
  setBadgingState("loading");

  try {
    const response = await fetch(`/api/v1/ai/repository/${repoId}/index-status`);
    if (!response.ok) throw new Error("Failed to fetch index status");
    const json = await response.json();
    const data = json.data || {};
    
    if (data.has_context) {
      setBadgingState("active", data);
    } else {
      setBadgingState("inactive", data);
    }
  } catch (e) {
    console.error("Failed to update index status UI:", e);
    setBadgingState("inactive", { chunk_count: 0, file_count: 0 });
  }
}

function setBadgingState(state, data = {}) {
  const indexBadge = document.getElementById('indexed-context-badge');
  const scopeBadge = document.getElementById('ai-scope-badge');
  
  if (!indexBadge || !scopeBadge) return;

  const indexBadgeDot = indexBadge.querySelector('.badge-dot');
  const indexBadgeText = indexBadge.querySelector('.badge-text');
  
  const scopeBadgeDot = scopeBadge.querySelector('.badge-dot');
  const scopeBadgeText = scopeBadge.querySelector('.badge-text');

  if (state === "active") {
    // Header Badge: Green Active
    indexBadge.style.color = '#4ade80';
    indexBadge.style.borderColor = 'rgba(74, 222, 128, 0.25)';
    indexBadge.style.background = 'rgba(74, 222, 128, 0.05)';
    if (indexBadgeText) indexBadgeText.textContent = 'INDEXED CONTEXT ACTIVE';
    if (indexBadgeDot) {
      indexBadgeDot.style.backgroundColor = '#4ade80';
      indexBadgeDot.style.animation = 'badge-pulse 2s infinite ease-in-out';
    }

    // Scope Badge: Green Active
    scopeBadge.style.color = '#4ade80';
    scopeBadge.style.borderColor = 'rgba(74, 222, 128, 0.16)';
    scopeBadge.style.background = 'rgba(74, 222, 128, 0.04)';
    scopeBadge.style.boxShadow = '0 0 10px rgba(74, 222, 128, 0.05)';
    if (scopeBadgeText) scopeBadgeText.textContent = 'Repository Context Active';
    if (scopeBadgeDot) {
      scopeBadgeDot.style.backgroundColor = '#4ade80';
      scopeBadgeDot.style.animation = 'badge-pulse 2s infinite ease-in-out';
    }
  } else if (state === "loading") {
    // Header Badge: Neutral / Loading
    indexBadge.style.color = '#94a3b8';
    indexBadge.style.borderColor = 'rgba(148, 163, 184, 0.25)';
    indexBadge.style.background = 'rgba(148, 163, 184, 0.05)';
    if (indexBadgeText) indexBadgeText.textContent = 'CHECKING INDEX STATUS...';
    if (indexBadgeDot) {
      indexBadgeDot.style.backgroundColor = '#94a3b8';
      indexBadgeDot.style.animation = 'none';
    }

    // Scope Badge: Neutral / Loading
    scopeBadge.style.color = '#94a3b8';
    scopeBadge.style.borderColor = 'rgba(148, 163, 184, 0.16)';
    scopeBadge.style.background = 'rgba(148, 163, 184, 0.04)';
    scopeBadge.style.boxShadow = 'none';
    if (scopeBadgeText) scopeBadgeText.textContent = 'Checking Context...';
    if (scopeBadgeDot) {
      scopeBadgeDot.style.backgroundColor = '#94a3b8';
      scopeBadgeDot.style.animation = 'none';
    }
  } else {
    // Inactive/Empty State: Soft Red / Muted
    indexBadge.style.color = '#f87171';
    indexBadge.style.borderColor = 'rgba(248, 113, 113, 0.25)';
    indexBadge.style.background = 'rgba(248, 113, 113, 0.05)';
    if (indexBadgeText) indexBadgeText.textContent = 'NO INDEXED CONTEXT';
    if (indexBadgeDot) {
      indexBadgeDot.style.backgroundColor = '#f87171';
      indexBadgeDot.style.animation = 'none';
    }

    // Scope Badge: Soft Red / Muted
    scopeBadge.style.color = '#f87171';
    scopeBadge.style.borderColor = 'rgba(248, 113, 113, 0.16)';
    scopeBadge.style.background = 'rgba(248, 113, 113, 0.04)';
    scopeBadge.style.boxShadow = 'none';
    if (scopeBadgeText) scopeBadgeText.textContent = 'No Indexed Context';
    if (scopeBadgeDot) {
      scopeBadgeDot.style.backgroundColor = '#f87171';
      scopeBadgeDot.style.animation = 'none';
    }
  }
}
