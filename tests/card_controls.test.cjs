const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM } = require('jsdom');

const source = fs.readFileSync(path.join(__dirname, '../javascript/civitai_helper.js'), 'utf8');

function setup({ lobe = true, hidden = [], placeholder = false } = {}) {
    const dom = new JSDOM('<body><div id="host"><div id="txt2img_lora_cards" class="extra-network-cards"></div></div></body>', { runScripts: 'outside-only', pretendToBeVisual: true });
    const win = dom.window;
    win.console = { log() {} };
    win.opts = { ch_hide_buttons: hidden, localization: 'zh_CN' };
    win.gradioApp = () => win.document;
    let loaded;
    win.onUiLoaded = callback => { loaded = callback; };
    if (lobe) win.document.querySelector('#host').id = 'txt2img-extra-network-sidebar';
    win.eval(source);
    const cards = win.document.querySelector('.extra-network-cards');
    const addCard = () => {
        const card = win.document.createElement('div');
        card.className = 'card';
        card.dataset.name = "example's model";
        card.innerHTML = '<div class="button-row"><div class="copy-path-button card-button" title="Copy path"></div><div class="metadata-button card-button" title="Metadata"></div><div class="edit-button card-button" title="Edit metadata"></div></div><div class="actions"><div class="additional"><span class="search_terms"></span><span class="search_terms">abc123</span></div><span class="name"></span></div>';
        card.querySelector('.search_terms').textContent = "Lora\\sub folder\\example's model.safetensors";
        card.querySelector('.name').textContent = card.dataset.name;
        if (placeholder) card.querySelector('.additional').insertAdjacentHTML('beforeend', '<ul></ul><a>🖼️</a>');
        cards.appendChild(card);
        return card;
    };
    return { dom, win, cards, addCard, loaded: () => loaded() };
}

test('browser download selects localized native tabs and accepts a Gradio 4 textarea', () => {
    const app = setup();
    try {
        app.win.document.body.insertAdjacentHTML('beforeend', `<div id="tabs">
          <div class="tab-nav"><button>模型浏览</button><button>模型助手</button></div>
          <div class="tabitem" id="tab_civitai_helper_browser"><article id="ch_123_card"></article></div>
          <div class="tabitem" id="tab_civitai_helper"><div><div class="tab-nav"><button>单个下载</button><button>批量下载</button></div>
          <div class="tabitem" id="ch_dl_single_tab"><div id="ch_dl_url"><textarea></textarea></div>
          <button id="ch_dl_get_info">获取信息</button><button id="ch_download_model_button">下载</button></div><div class="tabitem"></div></div></div></div>`);
        const doc = app.win.document;
        let selected = 0, requested = 0;
        doc.querySelectorAll('#tabs > .tab-nav button')[1].addEventListener('click', () => selected++);
        doc.getElementById('ch_dl_get_info').addEventListener('click', () => requested++);
        doc.getElementById('ch_download_model_button').scrollIntoView = () => {};
        app.win.ch_downloader(new app.win.MouseEvent('click'), 123);
        assert.equal(selected, 1);
        assert.equal(requested, 1);
        assert.equal(doc.querySelector('#ch_dl_url textarea').value, '123');
        assert.ok(doc.getElementById('ch_123_card').classList.contains('ch_active_card'));
    } finally { app.dom.window.close(); }
});

test('repairs an empty Lobe placeholder once, keeping all six Helper actions', () => {
    const app = setup({ placeholder: true });
    try {
        const card = app.addCard();
        app.win.ch_refresh_cards();
        app.win.ch_refresh_cards();
        assert.equal(card.querySelectorAll('ul').length, 1);
        assert.equal(card.querySelectorAll('ul[data-civitai-helper] a').length, 6);
        assert.equal(card.querySelectorAll('.ch-card-menu-toggle').length, 1);
        assert.equal(card.querySelectorAll('.additional > a').length, 0);
    } finally { app.dom.window.close(); }
});

test('new cards initialize after an already initialized card', () => {
    const app = setup();
    try {
        app.addCard();
        app.win.ch_refresh_cards();
        const later = app.addCard();
        app.win.ch_refresh_cards();
        assert.equal(later.querySelectorAll('ul a').length, 6);
    } finally { app.dom.window.close(); }
});

test('hides actions selected in settings and keeps classic card controls working', () => {
    const app = setup({ hidden: ['remove_model_button', 'rename_model_button'], lobe: false });
    try {
        const card = app.addCard();
        app.win.ch_refresh_cards();
        assert.equal(card.querySelectorAll('ul a').length, 4);
        assert.equal(card.querySelector('.ch-card-menu-toggle'), null);
    } finally { app.dom.window.close(); }
});

test('actions retain spaces, quotes and subfolder separators without inline JavaScript', () => {
    const app = setup();
    try {
        const card = app.addCard();
        app.win.ch_refresh_cards();
        let args;
        app.win.add_trigger_words = (event, ...values) => { event.stopPropagation(); args = values; };
        card.querySelector('.addtriggerwords').click();
        assert.deepEqual(args, ['lora', "sub folder\\example's model.safetensors abc123"]);
        assert.equal(card.querySelector('.addtriggerwords').hasAttribute('onclick'), false);
    } finally { app.dom.window.close(); }
});

test('menu escapes card clipping, forwards native actions and restores keyboard focus', () => {
    const app = setup();
    try {
        const card = app.addCard();
        let nativeCard;
        card.querySelector('.metadata-button').onclick = event => { nativeCard = event.target.closest('.card'); };
        app.win.ch_refresh_cards();
        const trigger = card.querySelector('.ch-card-menu-toggle');
        trigger.click();
        const menu = app.win.document.querySelector('[role="menu"]');
        assert.equal(menu.parentElement, app.win.document.body);
        assert.equal(menu.querySelectorAll('[role="menuitem"]').length, 9);
        assert.equal(menu.querySelectorAll('svg').length, 9);
        menu.querySelectorAll('[role="menuitem"]')[1].click();
        assert.equal(nativeCard, card);
        assert.equal(menu.hidden, true);
        trigger.click();
        menu.dispatchEvent(new app.win.KeyboardEvent('keydown', { key: 'End', bubbles: true }));
        assert.equal(app.win.document.activeElement.textContent, '删除模型及相关文件');
        menu.dispatchEvent(new app.win.KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
        assert.equal(menu.hidden, true);
        assert.equal(app.win.document.activeElement, trigger);
        assert.equal(trigger.getAttribute('aria-expanded'), 'false');
    } finally { app.dom.window.close(); }
});

test('observes card insertion and moving a gallery into the Lobe sidebar', async () => {
    const app = setup({ lobe: false });
    try {
        app.loaded();
        const card = app.addCard();
        const sidebar = app.win.document.createElement('div');
        sidebar.id = 'txt2img-extra-network-sidebar';
        app.win.document.body.appendChild(sidebar);
        sidebar.appendChild(app.cards);
        await new Promise(resolve => app.win.requestAnimationFrame(() => app.win.requestAnimationFrame(resolve)));
        assert.equal(card.querySelectorAll('ul a').length, 6);
        assert.ok(card.querySelector('.ch-card-menu-toggle'));
    } finally { app.dom.window.close(); }
});

test('replace preview opens the native editor using the correct card context', async () => {
    const app = setup();
    try {
        const card = app.addCard();
        const editor = app.win.document.createElement('div');
        editor.id = 'txt2img_lora_edit_user_metadata';
        editor.innerHTML = '<div class="extra-network-name"></div><div class="edit-user-metadata-buttons"><button>Cancel</button><button>Replace preview</button></div>';
        editor.querySelector('.extra-network-name').textContent = card.dataset.name;
        app.win.document.body.appendChild(editor);
        let editedCard;
        let previewReplaced = false;
        card.querySelector('.edit-button').onclick = event => {
            editedCard = event.target.parentElement.parentElement;
        };
        editor.querySelector('button:nth-child(2)').onclick = () => { previewReplaced = true; };
        app.win.ch_refresh_cards();
        card.querySelector('.replacepreview').click();
        await Promise.resolve();
        assert.equal(editedCard, card);
        assert.equal(previewReplaced, true);
    } finally { app.dom.window.close(); }
});
