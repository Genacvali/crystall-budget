// DOM utility functions

export function qs(selector, parent = document) {
  return parent.querySelector(selector);
}

export function qsa(selector, parent = document) {
  return Array.from(parent.querySelectorAll(selector));
}

export function on(element, event, handler, options) {
  if (typeof element === 'string') {
    element = qs(element);
  }
  if (element) {
    element.addEventListener(event, handler, options);
  }
}

export function off(element, event, handler, options) {
  if (typeof element === 'string') {
    element = qs(element);
  }
  if (element) {
    element.removeEventListener(event, handler, options);
  }
}

export function createElement(tag, attributes = {}, children = []) {
  const element = document.createElement(tag);

  Object.entries(attributes).forEach(([key, value]) => {
    if (key === 'className') {
      element.className = value;
    } else if (key === 'dataset') {
      Object.entries(value).forEach(([dataKey, dataValue]) => {
        element.dataset[dataKey] = dataValue;
      });
    } else {
      element.setAttribute(key, value);
    }
  });

  children.forEach(child => {
    if (typeof child === 'string') {
      element.appendChild(document.createTextNode(child));
    } else {
      element.appendChild(child);
    }
  });

  return element;
}
