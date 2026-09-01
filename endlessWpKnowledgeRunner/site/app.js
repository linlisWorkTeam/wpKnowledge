const stages = {
  ingest: {
    kicker: 'INPUT · PROVENANCE',
    title: '先保存来源，再讨论答案',
    description: 'Markdown、固定 Git commit 或项目经验进入 CAS，系统创建 CANDIDATE，并保留来源、版本与完整性信息。',
    actor: 'Engineer · Registry · CAS',
    guard: 'Provenance + content digest',
    output: 'KnowledgeVersion:CANDIDATE',
  },
  generate: {
    kicker: 'AGENT · CHECKPOINT',
    title: '生成可以重试，副作用不能失控',
    description: 'DocGen 与 CodeGen Agent 按 Schema 交接不可变 Artifact。GenerationKey 保证同一次节点重放返回已提交结果，而不是重复执行。',
    actor: 'Orchestrator · DocGen · CodeGen',
    guard: 'JSON Schema + GenerationKey',
    output: 'DocArtifact + CodeArtifact',
  },
  evaluate: {
    kicker: 'EVIDENCE · INDEPENDENCE',
    title: '让独立执行结果说话',
    description: 'EvalRunner 在受控临时工作区执行允许的工具，记录测试总数、关键失败、工具链指纹和不可变证据，而不是接受 Agent 自评分。',
    actor: 'EvalRunner · Registry · CAS',
    guard: 'Independent evidence binding',
    output: 'EvaluationReport',
  },
  correct: {
    kicker: 'FAILURE · LEARNING',
    title: '把失败定位为可执行修订',
    description: 'Gate 返回 ITERATE 后，Review Agent 把失败转成结构化 Correction，定位知识路径、判据与风险；Orchestrator 只修订相关知识并 fresh generate。',
    actor: 'Gate · Review Agent · Orchestrator',
    guard: 'Correction Schema + iteration budget',
    output: 'Revised KnowledgeVersion',
  },
  publish: {
    kicker: 'GATE · ATOMIC COMMIT',
    title: '只有完整证据才能成为正式知识',
    description: '确定性 Gate 校验来源、证据归属、测试、稳定性和工件完整性。PASS 后，Run、事件、版本状态与 publication receipt 在一个事务中提交。',
    actor: 'Publication Gate · Registry',
    guard: 'PASS + artifact integrity',
    output: 'VERIFIED + PublicationReceipt',
  },
};

const root = document.documentElement;
const header = document.querySelector('[data-header]');
const menuButton = document.querySelector('[data-menu-toggle]');
const mobileMenu = document.querySelector('[data-mobile-menu]');
const themeButton = document.querySelector('[data-theme-toggle]');
const toast = document.querySelector('[data-toast]');

function setTheme(theme, persist = false) {
  root.dataset.theme = theme;
  themeButton?.setAttribute('aria-label', theme === 'dark' ? '切换到浅色主题' : '切换到深色主题');
  if (persist) {
    try {
      localStorage.setItem('wpknowledge-site-theme', theme);
    } catch {
      // Storage can be unavailable in hardened browsers; the visual toggle still works.
    }
  }
}

try {
  const savedTheme = localStorage.getItem('wpknowledge-site-theme');
  const preferredTheme = matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  setTheme(savedTheme === 'light' || savedTheme === 'dark' ? savedTheme : preferredTheme);
} catch {
  setTheme('dark');
}

themeButton?.addEventListener('click', () => {
  setTheme(root.dataset.theme === 'light' ? 'dark' : 'light', true);
});

function closeMenu() {
  if (!menuButton || !mobileMenu) return;
  menuButton.setAttribute('aria-expanded', 'false');
  mobileMenu.hidden = true;
}

menuButton?.addEventListener('click', () => {
  if (!mobileMenu) return;
  const expanded = menuButton.getAttribute('aria-expanded') === 'true';
  menuButton.setAttribute('aria-expanded', String(!expanded));
  mobileMenu.hidden = expanded;
});

mobileMenu?.querySelectorAll('a').forEach((link) => link.addEventListener('click', closeMenu));

function updateHeader() {
  header?.classList.toggle('scrolled', window.scrollY > 12);
}

updateHeader();
window.addEventListener('scroll', updateHeader, { passive: true });

const stageButtons = [...document.querySelectorAll('[data-stage]')];
const stageFields = {
  kicker: document.querySelector('[data-stage-kicker]'),
  title: document.querySelector('[data-stage-title]'),
  description: document.querySelector('[data-stage-description]'),
  actor: document.querySelector('[data-stage-actor]'),
  guard: document.querySelector('[data-stage-guard]'),
  output: document.querySelector('[data-stage-output]'),
};

function selectStage(button) {
  const stage = stages[button.dataset.stage];
  if (!stage) return;
  stageButtons.forEach((item) => {
    const active = item === button;
    item.classList.toggle('active', active);
    item.setAttribute('aria-selected', String(active));
    item.tabIndex = active ? 0 : -1;
  });
  Object.entries(stageFields).forEach(([key, element]) => {
    if (element) element.textContent = stage[key];
  });
}

stageButtons.forEach((button, index) => {
  button.addEventListener('click', () => selectStage(button));
  button.addEventListener('keydown', (event) => {
    if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    let nextIndex = index;
    if (event.key === 'Home') nextIndex = 0;
    else if (event.key === 'End') nextIndex = stageButtons.length - 1;
    else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') nextIndex = (index - 1 + stageButtons.length) % stageButtons.length;
    else nextIndex = (index + 1) % stageButtons.length;
    stageButtons[nextIndex].focus();
    selectStage(stageButtons[nextIndex]);
  });
});

const onboardingButtons = [...document.querySelectorAll('[data-onboarding-tab]')];
const onboardingPanels = [...document.querySelectorAll('[data-onboarding-panel]')];

function selectOnboarding(button) {
  const target = button.dataset.onboardingTab;
  onboardingButtons.forEach((item) => {
    const active = item === button;
    item.classList.toggle('active', active);
    item.setAttribute('aria-selected', String(active));
    item.tabIndex = active ? 0 : -1;
  });
  onboardingPanels.forEach((panel) => {
    const active = panel.dataset.onboardingPanel === target;
    panel.hidden = !active;
  });
}

onboardingButtons.forEach((button, index) => {
  button.addEventListener('click', () => selectOnboarding(button));
  button.addEventListener('keydown', (event) => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    let nextIndex = index;
    if (event.key === 'Home') nextIndex = 0;
    else if (event.key === 'End') nextIndex = onboardingButtons.length - 1;
    else if (event.key === 'ArrowLeft') nextIndex = (index - 1 + onboardingButtons.length) % onboardingButtons.length;
    else nextIndex = (index + 1) % onboardingButtons.length;
    onboardingButtons[nextIndex].focus();
    selectOnboarding(onboardingButtons[nextIndex]);
  });
});

let toastTimer;
function showToast(message) {
  if (!toast) return;
  toast.textContent = message;
  toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toast.hidden = true;
  }, 1800);
}

async function copyText(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const area = document.createElement('textarea');
  area.value = text;
  area.style.position = 'fixed';
  area.style.opacity = '0';
  document.body.append(area);
  area.select();
  document.execCommand('copy');
  area.remove();
}

document.querySelectorAll('[data-copy-target]').forEach((button) => {
  button.addEventListener('click', async () => {
    const selector = button.dataset.copyTarget;
    const source = selector ? document.querySelector(selector) : null;
    if (!source) return;
    try {
      await copyText(source.textContent.trim());
      showToast(button.dataset.copyLabel || '内容已复制');
    } catch {
      showToast('复制失败，请手动选择');
    }
  });
});

const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
const revealItems = document.querySelectorAll('.reveal');
if (reducedMotion || !('IntersectionObserver' in window)) {
  revealItems.forEach((item) => item.classList.add('visible'));
} else {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('visible');
      observer.unobserve(entry.target);
    });
  }, { threshold: .12 });
  revealItems.forEach((item) => observer.observe(item));
}

document.querySelectorAll('[data-year]').forEach((element) => {
  element.textContent = String(new Date().getFullYear());
});
