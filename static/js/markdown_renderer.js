// Initialize custom marked renderer for premium terminal code blocks
function setupMarkedRenderer() {
  if (typeof marked !== 'undefined') {
    const renderer = new marked.Renderer();
    renderer.code = function(code, language) {
      const cleanLang = language || 'code';
      const blockId = 'code-' + Math.random().toString(36).substring(2, 9);
      return `
        <div class="terminal-code-block">
          <div class="terminal-header">
            <div class="terminal-dots">
              <span class="terminal-dot red"></span>
              <span class="terminal-dot yellow"></span>
              <span class="terminal-dot green"></span>
            </div>
            <span class="terminal-lang">${cleanLang}</span>
            <button class="copy-code-btn" onclick="copyCodeBlock('${blockId}', this)">
              <i data-lucide="copy" class="copy-icon"></i>
              <span>Copy</span>
            </button>
          </div>
          <pre><code id="${blockId}" class="language-${cleanLang}">${escapeHtml(code)}</code></pre>
        </div>
      `;
    };
    marked.setOptions({ renderer: renderer });
  }
}
