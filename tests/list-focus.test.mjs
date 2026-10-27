import test from 'node:test';
import assert from 'node:assert/strict';
import {beginListRedraw, finishListRedraw, revealSelectedRecord} from '../docs/list-focus.mjs';

class FakeElement {
  constructor(className = '', id = null) {
    this.className = className;
    this.dataset = id === null ? {} : {id};
    this.children = [];
    this.parent = null;
    this.focusCalls = [];
    this.scrollCalls = [];
    this.classList = {contains: name => this.className.split(/\s+/).includes(name)};
  }
  append(...elements) {
    for (const element of elements) {
      element.parent = this;
      this.children.push(element);
    }
  }
  replaceChildren(...elements) {
    this.children = [];
    this.append(...elements);
  }
  contains(element) {
    return this === element || this.children.some(child => child.contains(element));
  }
  querySelectorAll(selector) {
    const className = selector.slice(1);
    return this.children.flatMap(child => [
      ...(child.classList.contains(className) ? [child] : []),
      ...child.querySelectorAll(selector),
    ]);
  }
  querySelector(selector) {
    return this.querySelectorAll(selector)[0] || null;
  }
  focus(options) {
    this.focusCalls.push(options);
  }
  scrollIntoView(options) {
    this.scrollCalls.push(options);
  }
}

function listWith({recordIds = [], sourceIds = [], hasMore = false} = {}) {
  const list = new FakeElement('record-list');
  for (const id of recordIds) {
    const card = new FakeElement('record-card', id);
    card.append(new FakeElement('record-item', id));
    if (sourceIds.includes(id)) card.append(new FakeElement('record-source-link', id));
    list.append(card);
  }
  if (hasMore) list.append(new FakeElement('more-results'));
  return list;
}

test('paging keeps keyboard focus on the next pager, then moves to the final record', () => {
  const before = listWith({recordIds:['record-1','record-2'], hasMore:true});
  const priorPager = before.querySelector('.more-results');
  const focus = beginListRedraw(before, priorPager,{focusMore:true});
  const afterFirstPage = listWith({recordIds:['record-1','record-2','record-3'], hasMore:true});
  assert.equal(finishListRedraw(afterFirstPage, focus), afterFirstPage.querySelector('.more-results'));

  const afterLastPage = listWith({recordIds:['record-1','record-2','record-3']});
  assert.equal(finishListRedraw(afterLastPage, focus), afterLastPage.querySelectorAll('.record-item').at(-1));
});

test('selecting a record restores focus to its replacement button after list redraw', () => {
  const before = listWith({recordIds:['record-1','record-2']});
  const focus = beginListRedraw(before, before.querySelectorAll('.record-item')[1]);
  const afterSelection = listWith({recordIds:['record-1','record-2']});
  const replacement = afterSelection.querySelectorAll('.record-item')[1];

  assert.equal(finishListRedraw(afterSelection, focus), replacement);
  assert.deepEqual(replacement.focusCalls, [{preventScroll:true}]);
});

test('map-driven redraw preserves focus on the selected record source link', () => {
  const before = listWith({recordIds:['record-9'], sourceIds:['record-9']});
  const focus = beginListRedraw(before, before.querySelector('.record-source-link'));
  const afterMapMove = listWith({recordIds:['record-9'], sourceIds:['record-9']});

  assert.equal(finishListRedraw(afterMapMove, focus), afterMapMove.querySelector('.record-source-link'));
});

test('map selection scrolls an off-page selected card into view without focusing it', () => {
  const listBeforeSelection = listWith({recordIds:['record-1','record-2']});
  const outsideListControl = new FakeElement('map-canvas');
  const focus = beginListRedraw(listBeforeSelection, outsideListControl);

  assert.equal(focus, null);
  const listAfterSelection = listWith({recordIds:['record-1','record-2','map-selected']});
  const selectedCard = listAfterSelection.querySelectorAll('.record-card').find(card => card.dataset.id === 'map-selected');
  assert.equal(revealSelectedRecord(listAfterSelection, 'map-selected'), selectedCard);
  assert.deepEqual(selectedCard.scrollCalls, [{block:'nearest'}]);
  assert.equal(selectedCard.querySelectorAll('.record-item')[0].focusCalls.length, 0);
});

test('a removed focused record moves focus to the first remaining result', () => {
  const before = listWith({recordIds:['outside-view']});
  const focus = beginListRedraw(before, before.querySelector('.record-item'));
  const afterMapMove = listWith({recordIds:['inside-view']});

  assert.equal(finishListRedraw(afterMapMove, focus), afterMapMove.querySelector('.record-item'));
});
