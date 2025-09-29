/*!
 * CrystalBudget Modal System
 * Unified modal management for consistent UX across the application
 */

(function(window, document) {
  'use strict';

  // ==========================================================================
  // Modal Manager Class
  // ==========================================================================

  class ModalManager {
    constructor() {
      this.activeModal = null;
      this.focusBeforeModal = null;
      this.scrollPosition = 0;
      this.debug = false; // Set to true for debugging
      this.init();
    }

    init() {
      this.bindEvents();
      this.createModalContainer();
      this.handleEscapeKey();
      this.preventHiddenRequiredValidation();
    }

    // Create modal container if it doesn't exist
    createModalContainer() {
      if (!document.getElementById('cb-modal-container')) {
        const container = document.createElement('div');
        container.id = 'cb-modal-container';
        container.setAttribute('aria-hidden', 'true');
        document.body.appendChild(container);
      }
    }

    // Bind global event listeners
    bindEvents() {
      // Handle modal triggers
      document.addEventListener('click', (e) => {
        const trigger = e.target.closest('[data-modal-open]');
        if (trigger) {
          e.preventDefault();
          const modalId = trigger.getAttribute('data-modal-open');
          this.show(modalId);
          return;
        }

        const urlTrigger = e.target.closest('[data-modal-url]');
        if (urlTrigger) {
          e.preventDefault();
          const url = urlTrigger.getAttribute('data-modal-url');
          const modalId = urlTrigger.getAttribute('data-modal-target') || 'modal-main';
          this.loadAndShow(modalId, url);
          return;
        }

        const confirmTrigger = e.target.closest('[data-confirm]');
        if (confirmTrigger) {
          e.preventDefault();
          const message = confirmTrigger.getAttribute('data-confirm');
          const actionAttribute = confirmTrigger.getAttribute('data-confirm-action');
          
          let action;
          if (actionAttribute) {
            // Execute function from data-confirm-action
            action = () => {
              try {
                // Support both function calls and direct function names
                if (actionAttribute.includes('(')) {
                  eval(actionAttribute);
                } else {
                  window[actionAttribute]();
                }
              } catch (error) {
                console.error('Error executing confirm action:', error);
                this.showError('Произошла ошибка при выполнении действия');
              }
            };
          } else {
            // Default action: submit closest form or follow href
            action = () => {
              const form = confirmTrigger.closest('form');
              const href = confirmTrigger.getAttribute('href');
              
              if (form) {
                form.submit();
              } else if (href) {
                window.location.href = href;
              }
            };
          }
          
          this.confirm(message, action);
          return;
        }

        // Handle close buttons
        const closeBtn = e.target.closest('[data-modal-close]');
        if (closeBtn) {
          e.preventDefault();
          this.hide();
          return;
        }

        // Handle backdrop clicks
        if (e.target.classList.contains('cb-modal__backdrop')) {
          this.hide();
        }
      });

      // Handle form submissions in modals
      document.addEventListener('submit', (e) => {
        const form = e.target;
        if (form.closest('.cb-modal')) {
          this.handleFormSubmit(form, e);
        }
      });
    }

    // Handle escape key
    handleEscapeKey() {
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && this.activeModal) {
          this.hide();
        }
      });
    }

    // Prevent validation errors on hidden required fields
    preventHiddenRequiredValidation() {
      document.addEventListener('submit', (e) => {
        const form = e.target;
        if (!(form && form.tagName === 'FORM')) return;

        // Find required elements that are hidden
        const requiredElements = Array.from(form.querySelectorAll('[required]'));
        requiredElements.forEach(el => {
          let currentEl = el;
          let isHidden = false;
          
          // Check if element or parent is hidden
          while (currentEl && currentEl !== document.body) {
            const style = window.getComputedStyle(currentEl);
            if (style.display === 'none' || style.visibility === 'hidden') {
              isHidden = true;
              break;
            }
            currentEl = currentEl.parentElement;
          }
          
          if (isHidden || el.disabled) {
            el.removeAttribute('required');
            el.disabled = true;
          }
        });
      }, true);
    }

    // ==========================================================================
    // Modal Display Methods
    // ==========================================================================

    log(level, message, data = {}) {
      if (this.debug) {
        console[level](`[CrystalBudget Modal] ${message}`, data);
      }
    }

    showError(message) {
      // Show user-friendly error message
      const errorModal = this.createDynamicModal('modal-error');
      const html = `
        <div class="cb-modal__header">
          <h5 class="cb-modal__title">
            <i class="bi bi-exclamation-triangle text-warning me-2"></i>Ошибка
          </h5>
          <button type="button" class="cb-modal__close" data-modal-close></button>
        </div>
        <div class="cb-modal__body">
          <p>${this.escapeHtml(message)}</p>
        </div>
        <div class="cb-modal__footer">
          <button type="button" class="cb-modal__btn cb-modal__btn--primary" data-modal-close>
            ОК
          </button>
        </div>
      `;
      errorModal.className = 'cb-modal cb-modal--confirm';
      this.setModalContent(errorModal, html);
      this.show('modal-error');
    }

    show(modalId, options = {}) {
      this.log('debug', `Opening modal: ${modalId}`, options);
      
      const modal = document.getElementById(modalId);
      if (!modal) {
        this.log('error', `Modal with id "${modalId}" not found`);
        console.error(`Modal with id "${modalId}" not found`);
        return false;
      }

      // Hide any existing modal first
      if (this.activeModal) {
        this.log('debug', `Hiding existing modal: ${this.activeModal.id}`);
        this.hide();
      }

      // Store focus
      this.focusBeforeModal = document.activeElement;
      
      // Store scroll position and prevent body scroll
      this.scrollPosition = window.pageYOffset;
      document.body.style.overflow = 'hidden';
      document.body.style.paddingRight = this.getScrollbarWidth() + 'px';

      // Show modal
      modal.setAttribute('aria-hidden', 'false');
      modal.classList.add('cb-modal--show');
      
      // Add backdrop if not exists
      if (!modal.querySelector('.cb-modal__backdrop')) {
        const backdrop = document.createElement('div');
        backdrop.className = 'cb-modal__backdrop';
        modal.appendChild(backdrop);
        
        // Animate backdrop
        requestAnimationFrame(() => {
          backdrop.classList.add('cb-modal__backdrop--show');
        });
      }

      this.activeModal = modal;

      // Focus management
      this.focusModal(modal);

      // Emit custom event
      this.emit('Modal:opened', { modal, modalId, options });

      return true;
    }

    hide(modalId = null) {
      const modal = modalId ? document.getElementById(modalId) : this.activeModal;
      if (!modal || !modal.classList.contains('cb-modal--show')) {
        this.log('debug', `Attempted to hide modal but it's not open: ${modalId || 'current'}`);
        return false;
      }

      this.log('debug', `Hiding modal: ${modal.id}`);

      // Remove focus trap
      this.removeFocusTrap(modal);

      // Hide modal
      modal.classList.remove('cb-modal--show');
      modal.setAttribute('aria-hidden', 'true');

      // Hide backdrop
      const backdrop = modal.querySelector('.cb-modal__backdrop');
      if (backdrop) {
        backdrop.classList.remove('cb-modal__backdrop--show');
        setTimeout(() => {
          if (backdrop.parentNode) {
            backdrop.remove();
          }
        }, 150);
      }

      // Restore body scroll
      document.body.style.overflow = '';
      document.body.style.paddingRight = '';

      // Restore focus safely
      if (this.focusBeforeModal) {
        try {
          // Check if the element is still in the DOM and can receive focus
          if (document.body.contains(this.focusBeforeModal) && 
              typeof this.focusBeforeModal.focus === 'function') {
            this.focusBeforeModal.focus();
          }
        } catch (error) {
          this.log('debug', 'Could not restore focus to original element', error);
          // Fallback: focus on body or first focusable element
          const fallbackFocusable = document.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
          if (fallbackFocusable) {
            fallbackFocusable.focus();
          }
        }
      }

      const modalId = modal.id;
      this.activeModal = null;
      this.focusBeforeModal = null;

      // Emit custom event
      this.emit('Modal:closed', { modal, modalId });

      return true;
    }

    loadAndShow(modalId, url, options = {}) {
      this.log('debug', `Loading modal: ${modalId} from ${url}`, options);
      
      let modal = document.getElementById(modalId);
      
      // Create modal if it doesn't exist
      if (!modal) {
        modal = this.createDynamicModal(modalId);
        this.log('debug', `Created dynamic modal: ${modalId}`);
      }

      // Show loading state
      this.setModalContent(modal, this.getLoadingHTML());
      this.show(modalId, options);

      const startTime = performance.now();

      // Load content with timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => {
        controller.abort();
      }, 10000); // 10 second timeout

      fetch(url, {
        method: 'GET',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'Accept': 'text/html, application/json',
          'X-CSRF-Token': this.getCSRFToken()
        },
        signal: controller.signal
      })
      .then(response => {
        clearTimeout(timeoutId);
        const loadTime = performance.now() - startTime;
        this.log('debug', `Modal content loaded in ${loadTime.toFixed(2)}ms`, { url, status: response.status });
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.text();
      })
      .then(html => {
        this.setModalContent(modal, html);
        this.emit('Modal:loaded', { modal, modalId, url });
        this.log('debug', `Modal content set for ${modalId}`);
      })
      .catch(error => {
        clearTimeout(timeoutId);
        this.log('error', `Failed to load modal content: ${error.message}`, { url, modalId });
        console.error('Failed to load modal content:', error);
        
        let errorMessage = 'Не удалось загрузить содержимое';
        if (error.name === 'AbortError') {
          errorMessage = 'Время ожидания истекло. Попробуйте еще раз.';
        } else if (error.message.includes('HTTP 404')) {
          errorMessage = 'Страница не найдена';
        } else if (error.message.includes('HTTP 500')) {
          errorMessage = 'Ошибка сервера. Попробуйте позже.';
        }
        
        this.setModalContent(modal, this.getErrorHTML(errorMessage, url));
        this.emit('Modal:loadError', { modal, modalId, url, error });
      });

      return true;
    }

    // ==========================================================================
    // Confirm Dialog
    // ==========================================================================

    confirm(message, onConfirm, options = {}) {
      const {
        title = 'Подтверждение',
        confirmText = 'Да',
        cancelText = 'Отмена',
        type = 'warning',
        icon = this.getConfirmIcon(type)
      } = options;

      const modalId = 'modal-confirm';
      let modal = document.getElementById(modalId);
      
      if (!modal) {
        modal = this.createDynamicModal(modalId);
      }

      const html = `
        <div class="cb-modal__header">
          <h5 class="cb-modal__title">${this.escapeHtml(title)}</h5>
          <button type="button" class="cb-modal__close" data-modal-close></button>
        </div>
        <div class="cb-modal__body">
          <div class="cb-modal__icon cb-modal__icon--${type}">
            ${icon}
          </div>
          <p class="cb-modal__message">${this.escapeHtml(message)}</p>
        </div>
        <div class="cb-modal__footer">
          <div class="cb-modal__actions">
            <button type="button" class="cb-modal__btn cb-modal__btn--outline" data-modal-close>
              ${this.escapeHtml(cancelText)}
            </button>
            <button type="button" class="cb-modal__btn cb-modal__btn--${type === 'danger' ? 'danger' : 'primary'}" data-confirm-action>
              ${this.escapeHtml(confirmText)}
            </button>
          </div>
        </div>
      `;

      modal.className = 'cb-modal cb-modal--confirm';
      this.setModalContent(modal, html);

      // Handle confirm action
      const confirmBtn = modal.querySelector('[data-confirm-action]');
      if (confirmBtn) {
        confirmBtn.addEventListener('click', () => {
          this.hide();
          if (typeof onConfirm === 'function') {
            onConfirm();
          }
        }, { once: true });
      }

      this.show(modalId);
      return true;
    }

    // ==========================================================================
    // Helper Methods
    // ==========================================================================

    createDynamicModal(modalId) {
      const modal = document.createElement('div');
      modal.id = modalId;
      modal.className = 'cb-modal';
      modal.setAttribute('aria-hidden', 'true');
      modal.setAttribute('role', 'dialog');
      modal.setAttribute('aria-modal', 'true');
      
      modal.innerHTML = `
        <div class="cb-modal__dialog">
          <div class="cb-modal__content" tabindex="-1">
            <!-- Content will be loaded here -->
          </div>
        </div>
      `;

      const container = document.getElementById('cb-modal-container') || document.body;
      container.appendChild(modal);
      
      return modal;
    }

    setModalContent(modal, html) {
      const content = modal.querySelector('.cb-modal__content');
      if (content) {
        content.innerHTML = html;
      }
    }

    focusModal(modal) {
      // Focus first focusable element or modal content
      const focusableElements = modal.querySelectorAll(
        'button:not([disabled]), [href]:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"]):not([disabled])'
      );
      
      if (focusableElements.length > 0) {
        focusableElements[0].focus();
      } else {
        const content = modal.querySelector('.cb-modal__content');
        if (content) {
          content.focus();
        }
      }

      // Set up focus trap
      this.setupFocusTrap(modal);
    }

    setupFocusTrap(modal) {
      const focusableElements = modal.querySelectorAll(
        'button:not([disabled]), [href]:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"]):not([disabled])'
      );
      
      if (focusableElements.length === 0) return;

      const firstFocusable = focusableElements[0];
      const lastFocusable = focusableElements[focusableElements.length - 1];

      const trapFocus = (e) => {
        if (e.key !== 'Tab') return;

        if (e.shiftKey) {
          // Shift + Tab
          if (document.activeElement === firstFocusable) {
            e.preventDefault();
            lastFocusable.focus();
          }
        } else {
          // Tab
          if (document.activeElement === lastFocusable) {
            e.preventDefault();
            firstFocusable.focus();
          }
        }
      };

      modal.addEventListener('keydown', trapFocus);
      
      // Clean up when modal is hidden
      modal.setAttribute('data-focus-trap', 'true');
      modal._focusTrapHandler = trapFocus;
    }

    removeFocusTrap(modal) {
      if (modal._focusTrapHandler) {
        modal.removeEventListener('keydown', modal._focusTrapHandler);
        delete modal._focusTrapHandler;
        modal.removeAttribute('data-focus-trap');
      }
    }

    handleFormSubmit(form, event) {
      const submitBtn = form.querySelector('button[type="submit"]');
      
      if (submitBtn && !submitBtn.disabled) {
        // Prevent double submission
        submitBtn.disabled = true;
        
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<i class="cb-modal__spinner"></i> Обработка...';
        
        // Re-enable after timeout as fallback
        setTimeout(() => {
          submitBtn.disabled = false;
          submitBtn.innerHTML = originalText;
        }, 5000);
      }

      this.emit('Modal:formSubmit', { form, modal: this.activeModal });
    }

    getScrollbarWidth() {
      const scrollDiv = document.createElement('div');
      scrollDiv.style.cssText = 'width: 100px; height: 100px; overflow: scroll; position: absolute; top: -9999px;';
      document.body.appendChild(scrollDiv);
      const scrollbarWidth = scrollDiv.offsetWidth - scrollDiv.clientWidth;
      document.body.removeChild(scrollDiv);
      return scrollbarWidth;
    }

    getLoadingHTML() {
      return `
        <div class="cb-modal__body cb-modal__body--loading">
          <div class="cb-modal__loading">
            <div class="cb-modal__spinner"></div>
            <span>Загрузка...</span>
          </div>
        </div>
      `;
    }

    getCSRFToken() {
      const meta = document.querySelector('meta[name="csrf-token"]');
      return meta ? meta.getAttribute('content') : '';
    }

    getErrorHTML(message, url = null) {
      return `
        <div class="cb-modal__header">
          <h5 class="cb-modal__title">
            <i class="bi bi-exclamation-triangle text-warning me-2"></i>Ошибка
          </h5>
          <button type="button" class="cb-modal__close" data-modal-close></button>
        </div>
        <div class="cb-modal__body">
          <div class="cb-modal__icon cb-modal__icon--danger">
            <i class="bi bi-exclamation-octagon"></i>
          </div>
          <p class="cb-modal__message">${this.escapeHtml(message)}</p>
          ${url ? `
            <div class="mt-3">
              <button type="button" class="cb-modal__btn cb-modal__btn--outline" onclick="Modal.load('${this.activeModal?.id || 'modal-main'}', '${url}')">
                <i class="bi bi-arrow-clockwise me-1"></i>Попробовать снова
              </button>
            </div>
          ` : ''}
        </div>
        <div class="cb-modal__footer">
          <button type="button" class="cb-modal__btn cb-modal__btn--primary" data-modal-close>
            Закрыть
          </button>
        </div>
      `;
    }

    getConfirmIcon(type) {
      const icons = {
        warning: '<i class="bi bi-exclamation-triangle"></i>',
        danger: '<i class="bi bi-exclamation-octagon"></i>',
        info: '<i class="bi bi-info-circle"></i>',
        success: '<i class="bi bi-check-circle"></i>'
      };
      return icons[type] || icons.warning;
    }

    escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }

    emit(eventName, detail = {}) {
      const event = new CustomEvent(eventName, { detail });
      document.dispatchEvent(event);
    }

    // ==========================================================================
    // Public API
    // ==========================================================================

    isOpen(modalId = null) {
      if (modalId) {
        const modal = document.getElementById(modalId);
        return modal && modal.classList.contains('cb-modal--show');
      }
      return this.activeModal !== null;
    }

    getActiveModal() {
      return this.activeModal;
    }

    closeAll() {
      if (this.activeModal) {
        this.hide();
      }
    }
  }

  // ==========================================================================
  // Global API and Initialization
  // ==========================================================================

  // Create global instance
  const Modal = new ModalManager();

  // Expose public API
  window.Modal = {
    show: (modalId, options) => Modal.show(modalId, options),
    hide: (modalId) => Modal.hide(modalId),
    load: (modalId, url, options) => Modal.loadAndShow(modalId, url, options),
    confirm: (message, onConfirm, options) => Modal.confirm(message, onConfirm, options),
    isOpen: (modalId) => Modal.isOpen(modalId),
    closeAll: () => Modal.closeAll(),
    getActive: () => Modal.getActiveModal(),
    debug: (enabled = true) => { Modal.debug = enabled; }
  };

  // Backward compatibility with common modal patterns
  window.openModal = window.Modal.show;
  window.closeModal = window.Modal.hide;
  window.confirmAction = window.Modal.confirm;

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      console.log('CrystalBudget Modal System initialized');
    });
  } else {
    console.log('CrystalBudget Modal System initialized');
  }

})(window, document);

// ==========================================================================
// Additional Utilities for Legacy Support
// ==========================================================================

// Support for Bootstrap-style modal triggers
document.addEventListener('click', function(e) {
  const trigger = e.target.closest('[data-bs-toggle="modal"]');
  if (trigger) {
    e.preventDefault();
    const target = trigger.getAttribute('data-bs-target');
    if (target) {
      const modalId = target.startsWith('#') ? target.slice(1) : target;
      window.Modal.show(modalId);
    }
  }
});

// Support for Bootstrap-style modal dismissal
document.addEventListener('click', function(e) {
  const dismiss = e.target.closest('[data-bs-dismiss="modal"]');
  if (dismiss) {
    e.preventDefault();
    window.Modal.hide();
  }
});

// Enhanced form handling for AJAX forms
document.addEventListener('submit', function(e) {
  const form = e.target;
  
  // Handle AJAX forms
  if (form.classList.contains('ajax-form') || form.hasAttribute('data-ajax')) {
    e.preventDefault();
    
    const formData = new FormData(form);
    const submitBtn = form.querySelector('button[type="submit"]');
    
    // Show loading state
    if (submitBtn) {
      submitBtn.disabled = true;
      const originalText = submitBtn.innerHTML;
      submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Обработка...';
      
      fetch(form.action || window.location.href, {
        method: form.method || 'POST',
        body: formData,
        headers: {
          'X-Requested-With': 'XMLHttpRequest'
        }
      })
      .then(response => {
        if (response.ok) {
          // Handle success
          const redirectHeader = response.headers.get('X-Redirect');
          if (redirectHeader) {
            window.location.href = redirectHeader;
          } else {
            window.location.reload();
          }
        } else {
          throw new Error(`HTTP ${response.status}`);
        }
      })
      .catch(error => {
        console.error('Form submission error:', error);
        alert('Произошла ошибка при отправке формы');
      })
      .finally(() => {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = originalText;
        }
      });
    }
  }
});