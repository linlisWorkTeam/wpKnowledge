import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';

const siteRoot = 'endlessWpKnowledgeRunner/site';
const htmlPath = `${siteRoot}/index.html`;
const html = readFileSync(htmlPath, 'utf8');
const css = readFileSync(`${siteRoot}/styles.css`, 'utf8');
const script = readFileSync(`${siteRoot}/app.js`, 'utf8');

test('GitHub Pages site is self-contained and project-path safe', () => {
  for (const path of [
    'index.html', 'styles.css', 'app.js', 'mark.svg', 'social-card.svg', '.nojekyll', 'README.md',
  ]) {
    assert.equal(existsSync(`${siteRoot}/${path}`), true, `missing site asset: ${path}`);
  }
  assert.doesNotMatch(html, /(?:src|href)="\/(?!\/)/, 'local assets must not assume a domain root');
  assert.doesNotMatch(html, /(?:unpkg|jsdelivr|fonts\.googleapis|googletagmanager)/i);
  assert.match(html, /connect-src 'none'/);

  for (const match of html.matchAll(/(?:src|href)="(\.\/[^"#?]+)"/g)) {
    assert.equal(
      existsSync(resolve(dirname(htmlPath), match[1])),
      true,
      `missing local asset: ${match[1]}`,
    );
  }
});

test('project site exposes human and Agent onboarding without weakening trust gates', () => {
  assert.match(html, /data-onboarding-tab="human"/);
  assert.match(html, /data-onboarding-tab="agent"/);
  assert.match(html, /id="agent-setup-prompt"/);
  assert.match(html, /npm run validate:specs/);
  assert.match(html, /不得跳过测试、降低阈值或伪造通过结果/);
  assert.match(html, /不得把 CANDIDATE 手工改成 VERIFIED/);
  assert.match(script, /data-onboarding-panel/);
  assert.match(script, /navigator\.clipboard/);
});

test('project site and Console implement separate light and dark themes', () => {
  const consoleHtml = readFileSync('endlessWpKnowledgeRunner/web/index.html', 'utf8');
  const consoleCss = readFileSync('endlessWpKnowledgeRunner/web/styles.css', 'utf8');
  const consoleScript = readFileSync('endlessWpKnowledgeRunner/web/app.js', 'utf8');
  const frontendSpec = readFileSync('endlessWpKnowledgeRunner/specs/04-product/frontend-product-design.md', 'utf8');

  assert.match(css, /:root\[data-theme="light"\]/);
  assert.match(script, /prefers-color-scheme: light/);
  assert.match(script, /wpknowledge-site-theme/);
  assert.match(script, /setTheme\(root\.dataset\.theme === 'light' \? 'dark' : 'light', true\)/);
  assert.match(consoleHtml, /id="theme-button"/);
  assert.match(consoleCss, /:root\[data-theme="light"\]/);
  assert.match(consoleScript, /wp-knowledge-theme/);
  assert.match(consoleScript, /applyTheme\(document\.documentElement\.dataset\.theme === 'light' \? 'dark' : 'light', true\)/);
  assert.match(frontendSpec, /KF-UI-013/);
  assert.match(frontendSpec, /AC-UI-013/);
});

test('Pages workflow deploys only the static site directory', () => {
  const workflow = readFileSync('.github/workflows/pages.yml', 'utf8');
  assert.match(workflow, /path: endlessWpKnowledgeRunner\/site/);
  assert.match(workflow, /actions\/configure-pages@v6/);
  assert.match(workflow, /actions\/upload-pages-artifact@v5/);
  assert.match(workflow, /actions\/deploy-pages@v5/);
  assert.equal(existsSync('LICENSE'), true);
});
