import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import YAML from 'yaml';

const siteRoot = 'endlessWpKnowledgeRunner/site';
const htmlPath = `${siteRoot}/index.html`;
const html = readFileSync(htmlPath, 'utf8');
const css = readFileSync(`${siteRoot}/styles.css`, 'utf8');
const script = readFileSync(`${siteRoot}/app.js`, 'utf8');

function themeTokens(source: string, selector: string): Record<string, string> {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const block = source.match(new RegExp(`${escaped}\\s*\\{([^}]+)\\}`));
  assert.ok(block, `missing theme block: ${selector}`);
  return Object.fromEntries(
    [...block[1].matchAll(/--([\w-]+):\s*(#[\da-f]{6})\s*;/gi)]
      .map((match) => [match[1], match[2].toLowerCase()]),
  );
}

function relativeLuminance(hex: string): number {
  const channels = hex.slice(1).match(/../g)?.map((channel) => Number.parseInt(channel, 16) / 255);
  assert.ok(channels && channels.length === 3, `invalid color: ${hex}`);
  const [red, green, blue] = channels.map((channel) => (
    channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4
  ));
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
}

function contrastRatio(foreground: string, background: string): number {
  const values = [relativeLuminance(foreground), relativeLuminance(background)]
    .sort((left, right) => right - left);
  return (values[0] + 0.05) / (values[1] + 0.05);
}

function assertReadablePalette(
  tokens: Record<string, string>,
  foregrounds: string[],
  label: string,
): void {
  for (const foreground of foregrounds) {
    assert.ok(tokens[foreground], `${label} misses --${foreground}`);
    assert.ok(tokens.bg, `${label} misses --bg`);
    assert.ok(
      contrastRatio(tokens[foreground], tokens.bg) >= 4.5,
      `${label} --${foreground} does not reach WCAG AA against --bg`,
    );
  }
}

test('GitHub Pages site is self-contained and project-path safe', () => {
  for (const path of [
    'index.html', 'styles.css', 'app.js', 'mark.svg', 'social-card.svg', '.nojekyll', 'README.md',
  ]) {
    assert.equal(existsSync(`${siteRoot}/${path}`), true, `missing site asset: ${path}`);
  }
  assert.doesNotMatch(html, /(?:src|href)="\/(?!\/)/, 'local assets must not assume a domain root');
  assert.doesNotMatch(html, /(?:unpkg|jsdelivr|fonts\.googleapis|googletagmanager)/i);
  assert.match(html, /connect-src 'none'/);

  const ids = new Set([...html.matchAll(/\sid="([^"]+)"/g)].map((match) => match[1]));
  for (const match of html.matchAll(/href="#([^"]+)"/g)) {
    assert.ok(ids.has(match[1]), `broken site anchor: #${match[1]}`);
  }

  for (const match of html.matchAll(/(?:src|href)="(\.\/[^"#?]+)"/g)) {
    assert.equal(
      existsSync(resolve(dirname(htmlPath), match[1])),
      true,
      `missing local asset: ${match[1]}`,
    );
  }
});

test('project site exposes human and Agent onboarding without weakening trust gates', () => {
  const gettingStarted = readFileSync('endlessWpKnowledgeRunner/docs/GETTING_STARTED.md', 'utf8');
  assert.match(html, /data-onboarding-tab="human"/);
  assert.match(html, /data-onboarding-tab="agent"/);
  assert.match(html, /id="agent-setup-prompt"/);
  assert.match(html, /npm run validate:specs/);
  assert.match(html, /不得跳过测试、降低阈值或伪造通过结果/);
  assert.match(html, /不得把 CANDIDATE 手工改成 VERIFIED/);
  assert.match(script, /data-onboarding-panel/);
  assert.match(script, /navigator\.clipboard/);
  for (const command of [
    'npm ci', 'npm run typecheck', 'npm run validate:specs', 'npm test',
    'WP_FLYWHEEL_HOME=.workpanel npm run knowledge -- init',
    'WP_FLYWHEEL_HOME=.workpanel npm run knowledge:serve',
  ]) {
    assert.ok(html.includes(command), `site misses onboarding command: ${command}`);
    assert.ok(gettingStarted.includes(command), `guide misses onboarding command: ${command}`);
  }
  for (const boundary of [
    '不得跳过测试、降低阈值或伪造通过结果',
    '不得把 CANDIDATE 手工改成 VERIFIED',
  ]) {
    assert.ok(html.includes(boundary), `site misses Agent boundary: ${boundary}`);
    assert.ok(gettingStarted.includes(boundary), `guide misses Agent boundary: ${boundary}`);
  }
});

test('project site and Console implement separate light and dark themes', () => {
  const consoleHtml = readFileSync('endlessWpKnowledgeRunner/web/index.html', 'utf8');
  const consoleCss = readFileSync('endlessWpKnowledgeRunner/web/styles.css', 'utf8');
  const consoleScript = readFileSync('endlessWpKnowledgeRunner/web/app.js', 'utf8');
  const frontendSpec = readFileSync('endlessWpKnowledgeRunner/specs/04-product/frontend-product-design.md', 'utf8');
  const siteDark = themeTokens(css, ':root');
  const siteLight = themeTokens(css, ':root[data-theme="light"]');
  const consoleDark = themeTokens(consoleCss, ':root');
  const consoleLight = themeTokens(consoleCss, ':root[data-theme="light"]');

  assert.match(css, /:root\[data-theme="light"\]/);
  assert.match(script, /prefers-color-scheme: light/);
  assert.match(script, /wpknowledge-site-theme/);
  assert.match(script, /function setTheme\(theme, persist = false\)/);
  assert.match(script, /setTheme\(root\.dataset\.theme === 'light' \? 'dark' : 'light', true\)/);
  assert.match(consoleHtml, /id="theme-button"/);
  assert.match(consoleCss, /:root\[data-theme="light"\]/);
  assert.match(consoleScript, /wp-knowledge-theme/);
  assert.match(consoleScript, /function applyTheme\(theme, persist = false\)/);
  assert.match(consoleScript, /applyTheme\(document\.documentElement\.dataset\.theme === 'light' \? 'dark' : 'light', true\)/);
  assert.doesNotMatch(script, /WP_KNOWLEDGE_WRITE_TOKEN/);
  assert.doesNotMatch(consoleScript, /localStorage\.setItem\([^\n]+token/i);
  assert.match(frontendSpec, /KF-UI-013/);
  assert.match(frontendSpec, /AC-UI-013/);

  const sharedPalette = {
    bg: ['#080b10', '#f4f7f9'],
    surface: ['#10151d', '#ffffff'],
    text: ['#eef2f7', '#17212b'],
    muted: ['#9aa8ba', '#586b7d'],
    accent: ['#71d4ff', '#07769f'],
    success: ['#76efbd', '#087c58'],
    warning: ['#ffd27d', '#92610f'],
    danger: ['#ff7d8e', '#b62f48'],
    governance: ['#c7a6ff', '#7250a8'],
  } as const;
  const siteNames = { accent: 'cyan', success: 'green', warning: 'amber', governance: 'violet' };
  for (const [name, [dark, light]] of Object.entries(sharedPalette)) {
    const siteName = siteNames[name as keyof typeof siteNames] ?? name;
    assert.equal(siteDark[siteName], dark, `site dark --${siteName}`);
    assert.equal(siteLight[siteName], light, `site light --${siteName}`);
    assert.equal(consoleDark[name], dark, `Console dark --${name}`);
    assert.equal(consoleLight[name], light, `Console light --${name}`);
    assert.ok(frontendSpec.toLowerCase().includes(dark), `Spec misses dark ${name} token ${dark}`);
    assert.ok(frontendSpec.toLowerCase().includes(light), `Spec misses light ${name} token ${light}`);
  }
  assertReadablePalette(siteDark, ['text', 'muted', 'cyan', 'green', 'amber', 'violet', 'danger'], 'site dark');
  assertReadablePalette(siteLight, ['text', 'muted', 'cyan', 'green', 'amber', 'violet', 'danger'], 'site light');
  assertReadablePalette(consoleDark, ['text', 'muted', 'accent', 'success', 'warning', 'governance', 'danger'], 'Console dark');
  assertReadablePalette(consoleLight, ['text', 'muted', 'accent', 'success', 'warning', 'governance', 'danger'], 'Console light');
});

test('Pages workflow deploys only the static site directory', () => {
  const workflow = readFileSync('.github/workflows/pages.yml', 'utf8');
  const config = YAML.parse(workflow);
  const steps = config.jobs.deploy.steps as Array<{ uses?: string; with?: { path?: string } }>;
  assert.deepEqual(config.on.push.branches, ['main']);
  assert.deepEqual(config.permissions, { contents: 'read', pages: 'write', 'id-token': 'write' });
  assert.equal(steps.find((step) => step.uses === 'actions/configure-pages@v6')?.uses, 'actions/configure-pages@v6');
  assert.equal(
    steps.find((step) => step.uses === 'actions/upload-pages-artifact@v5')?.with?.path,
    'endlessWpKnowledgeRunner/site',
  );
  assert.equal(steps.find((step) => step.uses === 'actions/deploy-pages@v5')?.uses, 'actions/deploy-pages@v5');
  assert.equal(existsSync('LICENSE'), true);
  assert.match(readFileSync('LICENSE', 'utf8'), /MIT License/);
});
