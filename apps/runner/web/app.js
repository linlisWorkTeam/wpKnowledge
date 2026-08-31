const metrics = document.querySelector('#metrics')
const health = document.querySelector('#health')
const list = document.querySelector('#knowledge-list')
const detail = document.querySelector('#detail')
const search = document.querySelector('#search')
const status = document.querySelector('#status')

const escapeHtml = (value) => String(value ?? '')
  .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;').replaceAll("'", '&#039;')

async function request(path) {
  const response = await fetch(path)
  if (!response.ok) throw new Error(`${response.status} ${path}`)
  return response.json()
}

async function loadStatus() {
  const data = await request('/api/v1/status')
  health.textContent = '运行正常'
  health.classList.add('healthy')
  const entries = [
    ['知识版本', data.knowledgeTotal],
    ['已验证', data.verified],
    ['候选', data.candidates],
    ['发布记录', data.publications],
  ]
  metrics.innerHTML = entries.map(([label, value]) => `
    <div class="metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>
  `).join('')
}

function card(item) {
  return `
    <button class="knowledge-card" data-version="${escapeHtml(item.versionId)}">
      <span class="card-top"><b>${escapeHtml(item.title || item.moduleId)}</b><em class="badge ${item.status.toLowerCase()}">${escapeHtml(item.status)}</em></span>
      <span>${escapeHtml(item.description || '暂无描述')}</span>
      <small>质量 ${escapeHtml(item.qualityScore)} · ${escapeHtml(item.versionId)}</small>
    </button>
  `
}

async function loadList() {
  const query = search.value.trim()
  const selectedStatus = status.value
  if (query) {
    const result = await request(`/api/v1/query?q=${encodeURIComponent(query)}&status=${encodeURIComponent(selectedStatus)}`)
    list.innerHTML = result.hits.map(card).join('') || '<p class="muted">没有命中。</p>'
  } else {
    const result = await request(`/api/v1/knowledge?status=${encodeURIComponent(selectedStatus)}`)
    list.innerHTML = result.knowledge.map(card).join('') || '<p class="muted">暂无知识版本。</p>'
  }
}

async function openVersion(versionId) {
  const item = await request(`/api/v1/knowledge/${encodeURIComponent(versionId)}`)
  detail.classList.remove('empty')
  detail.innerHTML = `
    <div class="detail-head">
      <div><p class="eyebrow">${escapeHtml(item.moduleId)}</p><h2>${escapeHtml(item.title || item.moduleId)}</h2></div>
      <em class="badge ${item.status.toLowerCase()}">${escapeHtml(item.status)}</em>
    </div>
    <p>${escapeHtml(item.description)}</p>
    <dl>
      <div><dt>质量门禁</dt><dd>${escapeHtml(item.qualityOutcome)} · ${escapeHtml(item.qualityScore)}</dd></div>
      <div><dt>行为门禁</dt><dd>${item.gateDecisionId ? escapeHtml(item.gateDecisionId) : '尚未通过，不可发布'}</dd></div>
      <div><dt>内容摘要</dt><dd>${escapeHtml(item.bodyRef.sha256)}</dd></div>
    </dl>
    <h3>溯源</h3>
    <ul>${item.provenance.map((source) => `<li><code>${escapeHtml(source.path)}</code>${source.commit ? ` @ ${escapeHtml(source.commit)}` : ''}</li>`).join('')}</ul>
    <h3>正文</h3>
    <pre>${escapeHtml(item.body)}</pre>
  `
}

list.addEventListener('click', (event) => {
  const button = event.target.closest('[data-version]')
  if (button) openVersion(button.dataset.version).catch(showError)
})
search.addEventListener('input', () => loadList().catch(showError))
status.addEventListener('change', () => loadList().catch(showError))

function showError(error) {
  health.textContent = '连接失败'
  health.classList.remove('healthy')
  detail.textContent = error.message
}

Promise.all([loadStatus(), loadList()]).catch(showError)
