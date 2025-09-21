// DOM utilities
export const qs = (selector, root = document) => root.querySelector(selector);
export const qsa = (selector, root = document) => root.querySelectorAll(selector);
export const on = (element, event, handler) => element.addEventListener(event, handler);
export const delegate = (root, selector, event, handler) => {
  root.addEventListener(event, (e) => {
    if (e.target.matches(selector)) {
      handler(e);
    }
  });
};