const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
test('no scanning until context menu click; all three explicit contexts registered', async () => {
  let installed, clicked, fetchCount = 0;
  const menus = [], messages = [];
  const chrome = {
    runtime: {onInstalled: {addListener(fn) {installed = fn;}}},
    contextMenus: {removeAll(fn) {fn();}, create(menu) {menus.push(menu);}, onClicked: {addListener(fn) {clicked = fn;}}},
    scripting: {async executeScript() {return []; }},
    tabs: {async sendMessage(id, message) {messages.push(message);}},
    action: {async setBadgeText() {}}
  };
  vm.runInNewContext(fs.readFileSync('extension/background.js', 'utf8'), {
    chrome, crypto: {randomUUID: () => 'one'}, AbortSignal,
    fetch: async (url, options) => {
      fetchCount++;
      if (options.body) {
        assert.equal(JSON.parse(options.body).text, 'fomo');
        return {ok: true, json: async () => ({id: 'job'})};
      }
      return {ok: true, json: async () => ({status: 'done', result: {label: 'Belum terverifikasi'}})};
    }
  });
  installed();
  assert.equal(fetchCount, 0);
  assert.deepEqual(menus.map(m => m.contexts[0]), ['selection', 'image', 'video']);
  await clicked({menuItemId: 'text', selectionText: 'fomo'}, {id: 5});
  assert.equal(fetchCount, 2);
  assert.deepEqual(messages.map(m => m.type), ['scan-start', 'scan-result']);
});
