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
      this.operationInProgress = false; // Stress test protection
      this.operationQueue = []; // Operation queue for rapid calls
      this.telemetryEnabled = false; // Disable telemetry by default to avoid errors
      this.modalStartTime = null; // Track modal timing
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

    // Telemetry collection methods
    sendTelemetry(eventType, modalName, data = {}) {
      if (!this.telemetryEnabled) return;
      
      try {
        const payload = {
          event_type: eventType,
          modal_name: modalName,
          data: data
        };
        
        fetch('/api/telemetry/modal', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.getCSRFToken()
          },
          body: JSON.stringify(payload)
        }).catch(err => {
          if (this.debug) {
            console.warn('[CrystalBudget Modal] Telemetry failed:', err);
          }
        });
      } catch (error) {
        if (this.debug) {
          console.warn('[CrystalBudget Modal] Telemetry error:', error);
        }
      }
    }

    recordModalOpen(modalName) {
      this.modalStartTime = Date.now();
      this.sendTelemetry('open', modalName);
    }

    recordModalClose(modalName) {
      const duration = this.modalStartTime ? Date.now() - this.modalStartTime : 0;
      this.sendTelemetry('close', modalName, { duration_ms: duration });
      this.modalStartTime = null;
    }

    recordModalSubmit(modalName, success = true) {
      const duration = this.modalStartTime ? Date.now() - this.modalStartTime : 0;
      this.sendTelemetry('submit', modalName, { success, duration_ms: duration });
    }

    recordModalError(modalName, errorType, errorMessage = null) {
      this.sendTelemetry('error', modalName, { 
        error_type: errorType, 
        error_message: errorMessage 
      });
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
      // Stress test protection: prevent rapid operations
      if (this.operationInProgress) {
        this.log('warn', `Modal operation already in progress, queuing: ${modalId}`);
        this.operationQueue.push({ type: 'show', modalId, options });
        return false;
      }

      this.operationInProgress = true;
      this.log('debug', `Opening modal: ${modalId}`, options);
      
      const modal = document.getElementById(modalId);
      if (!modal) {
        this.operationInProgress = false;
        this.processQueue(); // Process next in queue
        this.log('error', `Modal with id "${modalId}" not found`);
        console.error(`Modal with id "${modalId}" not found`);
        return false;
      }

      // Hide any existing modal first
      if (this.activeModal) {
        this.log('debug', `Hiding existing modal: ${this.activeModal.id}`);
        this.hide();
      }

      // Close drawer if open (mutual exclusion for stable UX)
      if (document.body.classList.contains('drawer-open')) {
        this.log('debug', 'Closing drawer before opening modal');
        const closeDrawerEvent = new CustomEvent('modal:closeDrawer');
        document.dispatchEvent(closeDrawerEvent);
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
        // Insert backdrop as first child so it's behind content
        modal.insertBefore(backdrop, modal.firstChild);

        // Animate backdrop
        requestAnimationFrame(() => {
          backdrop.classList.add('cb-modal__backdrop--show');
        });
      }

      this.activeModal = modal;

      // Record telemetry
      this.recordModalOpen(modalId);

      // Focus management
      this.focusModal(modal);

      // Initialize modal behaviors (multi-source toggle, etc.)
      this.initModalBehaviors(modal);

      // Emit custom event
      this.emit('Modal:opened', { modal, modalId, options });

      // Operation completed - process queue
      setTimeout(() => {
        this.operationInProgress = false;
        this.processQueue();
      }, 100); // Small delay for smooth UX

      return true;
    }

    hide(modalIdParam = null) {
      const modal = modalIdParam ? document.getElementById(modalIdParam) : this.activeModal;
      if (!modal || !modal.classList.contains('cb-modal--show')) {
        this.log('debug', `Attempted to hide modal but it's not open: ${modalIdParam || 'current'}`);
        return false;
      }

      const modalId = modal.id;
      this.log('debug', `Hiding modal: ${modalId}`);

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

      // Record telemetry
      this.recordModalClose(modalId);

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
        // Initialize modal behaviors after content is loaded
        this.initModalBehaviors(modal);
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
      // Support both old format (message, onConfirm, options) and new format (single options object)
      if (typeof message === 'object' && message !== null) {
        // New format: confirm({ message: '...', title: '...', ... })
        options = message;
        message = options.message || 'Вы уверены?';
        onConfirm = options.onConfirm || options.then;
      }

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

      // Return a Promise for new-style usage
      const promise = new Promise((resolve, reject) => {
        // Handle confirm action
        const confirmBtn = modal.querySelector('[data-confirm-action]');
        if (confirmBtn) {
          confirmBtn.addEventListener('click', () => {
            this.hide();
            if (typeof onConfirm === 'function') {
              onConfirm();
            }
            resolve();
          }, { once: true });
        }

        // Handle cancel action
        const cancelBtns = modal.querySelectorAll('[data-modal-close]');
        cancelBtns.forEach(btn => {
          btn.addEventListener('click', () => {
            reject();
          }, { once: true });
        });
      });

      this.show(modalId);
      return promise;
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
      modal.setAttribute('aria-labelledby', modalId + '-title');
      
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
    // Modal Behaviors (Category Multi-Source Toggle, etc.)
    // ==========================================================================

    initModalBehaviors(modal) {
      console.log('[ModalManager] initModalBehaviors called');

      // Initialize category add form
      this.initCategoryAddForm(modal);

      // Initialize income forms
      this.initIncomeAddForm(modal);
      this.initIncomeEditForm(modal);
    }

    initCategoryAddForm(modal) {
      const form = modal.querySelector('form[data-form="category-add"]');
      if (!form) {
        console.log('[CategoryAdd] Form not found in modal');
        return;
      }

      console.log('[CategoryAdd] Initializing form');

      // Elements
      const multiSourceSwitch = form.querySelector('#multiSourceSwitchAdd');
      const singleSourceSection = form.querySelector('#singleSourceSection');
      const multiSourceSection = form.querySelector('#multiSourceSection');

      if (!multiSourceSwitch || !singleSourceSection || !multiSourceSection) {
        console.log('[CategoryAdd] Required elements not found:', {
          multiSourceSwitch,
          singleSourceSection,
          multiSourceSection
        });
        return;
      }

      console.log('[CategoryAdd] All elements found, setting up...');

      // Single source elements
      const singleLimitTypeInputs = form.querySelectorAll('input[name="limit_type"]');
      const singleValueInput = form.querySelector('#singleValueInput');
      const singleValueSuffix = form.querySelector('#singleValueSuffix');
      const singleSourceHint = form.querySelector('#singleSourceHint');

      // Multi source elements
      const newSourceSelect = form.querySelector('#newSourceSelect');
      const newSourceTypeInputs = form.querySelectorAll('input[name="new_source_type"]');
      const newSourceValue = form.querySelector('#newSourceValue');
      const newSourceSuffix = form.querySelector('#newSourceSuffix');
      const addSourceBtn = form.querySelector('#addSourceBtn');
      const sourcesList = form.querySelector('#sourcesList');
      const sourcesTotal = form.querySelector('#sourcesTotal');
      const totalPercent = form.querySelector('#totalPercent');
      const totalStatus = form.querySelector('#totalStatus');
      const sourcesDataInput = form.querySelector('#sourcesDataInput');

      let sources = [];

      // Toggle mode
      const toggleMode = () => {
        const isMulti = multiSourceSwitch.checked;
        console.log('[CategoryAdd] toggleMode, isMulti:', isMulti);

        if (isMulti) {
          singleSourceSection.style.display = 'none';
          multiSourceSection.style.display = 'block';
          singleValueInput.removeAttribute('required');
          singleValueInput.disabled = true;
        } else {
          singleSourceSection.style.display = 'block';
          multiSourceSection.style.display = 'none';
          singleValueInput.setAttribute('required', 'required');
          singleValueInput.disabled = false;
        }
      };

      // Update single suffix
      const updateSingleSuffix = () => {
        const selected = Array.from(singleLimitTypeInputs).find(i => i.checked);
        if (!selected) return;

        if (selected.value === 'percent') {
          singleValueSuffix.textContent = '%';
          singleValueInput.placeholder = '15';
          singleValueInput.max = '100';
          singleValueInput.step = '0.1';
          if (singleSourceHint) singleSourceHint.style.display = 'block';
        } else {
          singleValueSuffix.textContent = '₽';
          singleValueInput.placeholder = '15000';
          singleValueInput.max = '';
          singleValueInput.step = '0.01';
          if (singleSourceHint) singleSourceHint.style.display = 'none';
        }
      };

      // Update new source suffix
      const updateNewSourceSuffix = () => {
        const selected = Array.from(newSourceTypeInputs).find(i => i.checked);
        if (!selected) return;

        if (selected.value === 'percent') {
          newSourceSuffix.textContent = '%';
          newSourceValue.placeholder = '0';
          newSourceValue.max = '100';
          newSourceValue.step = '0.1';
        } else {
          newSourceSuffix.textContent = '₽';
          newSourceValue.placeholder = '0';
          newSourceValue.max = '';
          newSourceValue.step = '0.01';
        }
      };

      // Add source
      const addSource = () => {
        const sourceId = newSourceSelect.value;
        const sourceName = newSourceSelect.options[newSourceSelect.selectedIndex]?.text;
        const type = Array.from(newSourceTypeInputs).find(i => i.checked)?.value || 'percent';
        const value = parseFloat(newSourceValue.value);

        if (!sourceId) {
          alert('Выберите источник дохода');
          return;
        }

        if (!value || value <= 0) {
          alert('Укажите значение больше 0');
          return;
        }

        if (type === 'percent' && value > 100) {
          alert('Процент не может быть больше 100%');
          return;
        }

        if (sources.find(s => s.id === sourceId)) {
          alert('Этот источник уже добавлен');
          return;
        }

        sources.push({ id: sourceId, name: sourceName, type, value });
        renderSources();
        updateTotal();
        updateSourcesData();

        newSourceSelect.value = '';
        newSourceValue.value = '';
        form.querySelector('#newSourcePercent').checked = true;
        updateNewSourceSuffix();
      };

      // Remove source
      const removeSource = (sourceId) => {
        sources = sources.filter(s => s.id !== sourceId);
        renderSources();
        updateTotal();
        updateSourcesData();
      };

      // Render sources
      const renderSources = () => {
        if (sources.length === 0) {
          sourcesList.innerHTML = '<p class="text-muted small mb-0">Добавьте источники</p>';
          return;
        }

        const escapeHtml = (text) => {
          const div = document.createElement('div');
          div.textContent = text;
          return div.innerHTML;
        };

        sourcesList.innerHTML = sources.map(source => `
          <div class="card border mb-2">
            <div class="card-body py-2 px-3">
              <div class="d-flex justify-content-between align-items-center">
                <div>
                  <strong>${escapeHtml(source.name)}</strong>
                  <span class="text-muted ms-2">${source.value}${source.type === 'percent' ? '%' : '₽'}</span>
                </div>
                <button type="button" class="btn btn-sm btn-outline-danger" data-remove-source="${source.id}">
                  <i class="bi bi-trash"></i>
                </button>
              </div>
            </div>
          </div>
        `).join('');

        // Attach remove handlers
        sourcesList.querySelectorAll('[data-remove-source]').forEach(btn => {
          btn.addEventListener('click', () => {
            removeSource(btn.getAttribute('data-remove-source'));
          });
        });
      };

      // Update total
      const updateTotal = () => {
        const percentSources = sources.filter(s => s.type === 'percent');
        if (percentSources.length === 0) {
          sourcesTotal.style.display = 'none';
          return;
        }

        const total = percentSources.reduce((sum, s) => sum + s.value, 0);
        totalPercent.textContent = total.toFixed(1);
        sourcesTotal.style.display = 'block';

        if (total === 0) {
          totalStatus.innerHTML = '<i class="bi bi-exclamation-circle text-secondary"></i> добавьте источники';
        } else if (total > 0 && total <= 100) {
          totalStatus.innerHTML = '<i class="bi bi-check-circle text-success"></i> корректно';
        } else {
          totalStatus.innerHTML = '<i class="bi bi-exclamation-triangle text-warning"></i> превышен лимит';
        }
      };

      // Update hidden field
      const updateSourcesData = () => {
        sourcesDataInput.value = JSON.stringify(sources);
      };

      // Event listeners
      multiSourceSwitch.addEventListener('change', toggleMode);

      singleLimitTypeInputs.forEach(input => {
        input.addEventListener('change', updateSingleSuffix);
      });

      newSourceTypeInputs.forEach(input => {
        input.addEventListener('change', updateNewSourceSuffix);
      });

      if (addSourceBtn) {
        addSourceBtn.addEventListener('click', addSource);
      }

      // Form validation
      form.addEventListener('submit', (e) => {
        if (multiSourceSwitch.checked) {
          if (sources.length === 0) {
            e.preventDefault();
            alert('Добавьте хотя бы один источник');
            return;
          }

          const percentTotal = sources.filter(s => s.type === 'percent').reduce((sum, s) => sum + s.value, 0);
          if (percentTotal > 100) {
            e.preventDefault();
            alert('Сумма процентов не может превышать 100%');
            return;
          }
        }

        if (!form.checkValidity()) {
          e.preventDefault();
          e.stopPropagation();
          form.classList.add('was-validated');
        }
      });

      // Initialize
      updateSingleSuffix();
      updateNewSourceSuffix();
      console.log('[CategoryAdd] Form initialized successfully');
    }

    initIncomeAddForm(modal) {
      const form = modal.querySelector('form[data-form="income"]');
      if (!form) return;

      console.log('[IncomeAdd] Initializing income add form');

      const amount = form.querySelector('input[name="amount"]');
      const sourceInput = form.querySelector('#source_name');
      const errBox = form.querySelector('#form-errors');
      const loading = form.querySelector('#form-loading');

      // Mark fields as "dirty" after first input/blur
      form.querySelectorAll('input, select, textarea').forEach(el => {
        el.addEventListener('input', () => el.classList.add('dirty'));
        el.addEventListener('blur', () => el.classList.add('dirty'));
      });

      // Auto-focus amount input after source name entry
      if (sourceInput && amount) {
        sourceInput.addEventListener('blur', function() {
          if (this.value.trim()) {
            setTimeout(() => {
              amount.focus();
              amount.select();
            }, 100);
          }
        });
      }

      // Quick shortcuts for popular income amounts
      if (amount) {
        amount.addEventListener('keydown', function(e) {
          if (e.ctrlKey && e.key >= '1' && e.key <= '5') {
            e.preventDefault();
            const quickAmounts = ['30000', '50000', '75000', '100000', '150000'];
            this.value = quickAmounts[parseInt(e.key) - 1];
            this.focus();
          }
        });

        // Auto-add .00 on blur
        amount.addEventListener('blur', function() {
          if (this.value && /^\d+$/.test(this.value)) {
            this.value = this.value + '.00';
          }
        });
      }

      // Form submission
      form.addEventListener('submit', (e) => {
        // Normalize amount
        if (amount && amount.value) {
          const v = amount.value.replace(',', '.').trim();
          if (/^\d+(\.\d{1,2})?$/.test(v)) {
            amount.value = (Math.round(parseFloat(v) * 100) / 100).toFixed(2);
          }
        }

        if (!form.checkValidity()) {
          e.preventDefault();
          e.stopPropagation();
          form.classList.add('was-validated');
          return;
        }

        loading?.classList.remove('d-none');
        errBox?.classList.add('d-none');
      });

      console.log('[IncomeAdd] Form initialized successfully');
    }

    initIncomeEditForm(modal) {
      const form = modal.querySelector('form[data-form="income-edit"]');
      if (!form) return;

      console.log('[IncomeEdit] Initializing income edit form');

      const amount = form.querySelector('input[name="amount"]');
      const sourceInput = form.querySelector('#source_name');
      const errBox = form.querySelector('#form-errors');
      const loading = form.querySelector('#form-loading');

      // Mark fields as "dirty" after first input/blur
      form.querySelectorAll('input, select, textarea').forEach(el => {
        el.addEventListener('input', () => el.classList.add('dirty'));
        el.addEventListener('blur', () => el.classList.add('dirty'));
      });

      // Auto-focus amount input after source name change (only if amount is empty)
      if (sourceInput && amount) {
        sourceInput.addEventListener('change', function() {
          if (this.value && !amount.value.trim()) {
            setTimeout(() => amount.focus(), 100);
          }
        });
      }

      // Form submission
      form.addEventListener('submit', (e) => {
        // Normalize amount
        if (amount && amount.value) {
          const v = amount.value.replace(',', '.').trim();
          if (/^\d+(\.\d{1,2})?$/.test(v)) {
            amount.value = (Math.round(parseFloat(v) * 100) / 100).toFixed(2);
          }
        }

        if (!form.checkValidity()) {
          e.preventDefault();
          e.stopPropagation();
          form.classList.add('was-validated');
          return;
        }

        loading?.classList.remove('d-none');
        errBox?.classList.add('d-none');
      });

      console.log('[IncomeEdit] Form initialized successfully');
    }

    initMultiSourceToggle(modal) {
      const toggle = modal.querySelector('[data-role="multi-source-toggle"]');
      console.log('[ModalManager] initMultiSourceToggle - toggle:', toggle);

      if (!toggle) {
        console.log('[ModalManager] No multi-source toggle found');
        return;
      }

      const singleSourceSection = modal.querySelector('[data-role="single-source-section"]');
      const multiSourceSection = modal.querySelector('[data-role="multi-source-section"]');
      const limitTypeSection = modal.querySelector('[data-role="limit-type-section"]');
      const valueSection = modal.querySelector('[data-role="value-section"]');

      console.log('[ModalManager] Sections:', {
        single: singleSourceSection,
        multi: multiSourceSection,
        limitType: limitTypeSection,
        value: valueSection
      });

      if (!singleSourceSection || !multiSourceSection) {
        console.log('[ModalManager] Missing required sections');
        return;
      }

      // Remove old event listeners by cloning
      const newToggle = toggle.cloneNode(true);
      toggle.parentNode.replaceChild(newToggle, toggle);
      console.log('[ModalManager] Toggle event listener attached');

      newToggle.addEventListener('change', () => {
        console.log('[ModalManager] Toggle changed to:', newToggle.checked);
        this.toggleMultiSourceMode(
          newToggle.checked,
          singleSourceSection,
          multiSourceSection,
          limitTypeSection,
          valueSection
        );
      });
    }

    toggleMultiSourceMode(isMulti, singleSection, multiSection, limitTypeSection, valueSection) {
      if (isMulti) {
        // Show multi-source, hide single-source
        this.hideSection(singleSection);
        if (limitTypeSection) this.hideSection(limitTypeSection);
        if (valueSection) this.hideSection(valueSection);
        this.showSection(multiSection);
      } else {
        // Show single-source, hide multi-source
        this.hideSection(multiSection);
        this.showSection(singleSection);
        if (limitTypeSection) this.showSection(limitTypeSection);
        if (valueSection) this.showSection(valueSection);
      }
    }

    hideSection(section) {
      if (!section) return;

      // Disable and remove required from all inputs
      section.querySelectorAll('input, select, textarea').forEach(input => {
        input.disabled = true;
        input.removeAttribute('required');
      });

      // Animate hide
      section.style.opacity = '0';
      section.style.maxHeight = '0';
      section.style.overflow = 'hidden';
      setTimeout(() => {
        section.style.display = 'none';
      }, 300);
    }

    showSection(section) {
      if (!section) return;

      // Show and animate
      section.style.display = 'block';
      section.style.overflow = 'hidden';
      setTimeout(() => {
        section.style.opacity = '1';
        section.style.maxHeight = '1000px';

        // Enable inputs and restore required
        section.querySelectorAll('input, select, textarea').forEach(input => {
          input.disabled = false;
          if (input.dataset.required === 'true') {
            input.setAttribute('required', 'required');
          }
        });
      }, 10);
    }

    initLimitTypeToggle(modal) {
      const limitTypeInputs = modal.querySelectorAll('[data-role="limit-type"]');
      const valueSuffix = modal.querySelector('[data-role="value-suffix"]');
      const valueInput = modal.querySelector('[data-role="value-input"]');

      if (!limitTypeInputs.length || !valueSuffix || !valueInput) return;

      limitTypeInputs.forEach(input => {
        input.addEventListener('change', () => {
          if (input.value === 'percent') {
            valueSuffix.textContent = '%';
            valueInput.placeholder = '15';
            valueInput.max = '100';
            valueInput.step = '0.1';
          } else {
            valueSuffix.textContent = '₽';
            valueInput.placeholder = '15000';
            valueInput.max = '';
            valueInput.step = '0.01';
          }
        });
      });
    }

    syncModalState(modal) {
      // Sync multi-source toggle state on modal open
      const toggle = modal.querySelector('[data-role="multi-source-toggle"]');
      if (!toggle) return;

      const singleSourceSection = modal.querySelector('[data-role="single-source-section"]');
      const multiSourceSection = modal.querySelector('[data-role="multi-source-section"]');
      const limitTypeSection = modal.querySelector('[data-role="limit-type-section"]');
      const valueSection = modal.querySelector('[data-role="value-section"]');

      if (singleSourceSection && multiSourceSection) {
        // Set initial state without animation
        if (toggle.checked) {
          singleSourceSection.style.display = 'none';
          if (limitTypeSection) limitTypeSection.style.display = 'none';
          if (valueSection) valueSection.style.display = 'none';
          multiSourceSection.style.display = 'block';
          multiSourceSection.style.opacity = '1';
          multiSourceSection.style.maxHeight = '1000px';
        } else {
          multiSourceSection.style.display = 'none';
          singleSourceSection.style.display = 'block';
          singleSourceSection.style.opacity = '1';
          singleSourceSection.style.maxHeight = '1000px';
          if (limitTypeSection) {
            limitTypeSection.style.display = 'block';
            limitTypeSection.style.opacity = '1';
          }
          if (valueSection) {
            valueSection.style.display = 'block';
            valueSection.style.opacity = '1';
          }
        }
      }
    }

    initMultiSourceManagement(modal) {
      const newSourceSelect = modal.querySelector('#newSourceSelect');
      const newSourceType = modal.querySelector('#newSourceType');
      const newSourceValue = modal.querySelector('#newSourceValue');
      const newSourceSuffix = modal.querySelector('#newSourceSuffix');
      const addSourceBtn = modal.querySelector('#addSourceBtn');
      const sourcesList = modal.querySelector('#sourcesList');
      const sourcesDataInput = modal.querySelector('#sourcesDataInput');

      if (!newSourceSelect || !addSourceBtn || !sourcesList) return;

      // Load income sources
      this.loadIncomeSources(newSourceSelect);

      // Array to store sources
      let sources = [];

      // Update suffix when type changes
      if (newSourceType && newSourceSuffix) {
        newSourceType.addEventListener('change', () => {
          if (newSourceType.value === 'percent') {
            newSourceSuffix.textContent = '%';
            newSourceValue.placeholder = '0';
            newSourceValue.max = '100';
          } else {
            newSourceSuffix.textContent = '₽';
            newSourceValue.placeholder = '0';
            newSourceValue.max = '';
          }
        });
      }

      // Add source button
      addSourceBtn.addEventListener('click', () => {
        const sourceId = newSourceSelect.value;
        const sourceName = newSourceSelect.options[newSourceSelect.selectedIndex]?.text;
        const type = newSourceType.value;
        const value = parseFloat(newSourceValue.value);

        if (!sourceId || !value || value <= 0) {
          alert('Пожалуйста, выберите источник и укажите значение');
          return;
        }

        // Check if source already added
        if (sources.find(s => s.id === sourceId)) {
          alert('Этот источник уже добавлен');
          return;
        }

        // Add source
        sources.push({
          id: sourceId,
          name: sourceName,
          type: type,
          value: value
        });

        // Update UI
        this.renderSources(sourcesList, sources, () => {
          // Remove callback
          sources = sources.filter(s => s.id !== sourceId);
          this.renderSources(sourcesList, sources, arguments.callee);
          this.updateSourcesData(sourcesDataInput, sources);
        });

        // Update hidden input
        this.updateSourcesData(sourcesDataInput, sources);

        // Reset form
        newSourceSelect.value = '';
        newSourceValue.value = '';
      });
    }

    loadIncomeSources(selectElement) {
      // Load income sources from API
      fetch('/api/v1/income-sources')
        .then(response => response.json())
        .then(data => {
          selectElement.innerHTML = '<option value="">Выберите источник...</option>';
          (data.sources || []).forEach(source => {
            const option = document.createElement('option');
            option.value = source.id;
            option.textContent = source.name;
            selectElement.appendChild(option);
          });
        })
        .catch(error => {
          console.error('Error loading income sources:', error);
        });
    }

    renderSources(container, sources, removeCallback) {
      container.innerHTML = '';

      if (sources.length === 0) {
        container.innerHTML = '<p class="text-muted small mb-0">Источники не добавлены</p>';
        return;
      }

      const escapeHtml = (text) => {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
      };

      sources.forEach(source => {
        const sourceCard = document.createElement('div');
        sourceCard.className = 'card border mb-2';
        sourceCard.innerHTML = `
          <div class="card-body py-2 px-3">
            <div class="d-flex justify-content-between align-items-center">
              <div>
                <strong>${escapeHtml(source.name)}</strong>
                <span class="text-muted ms-2">${source.value}${source.type === 'percent' ? '%' : '₽'}</span>
              </div>
              <button type="button" class="btn btn-sm btn-outline-danger" data-source-id="${source.id}">
                <i class="bi bi-trash"></i>
              </button>
            </div>
          </div>
        `;

        // Add remove handler
        const removeBtn = sourceCard.querySelector('[data-source-id]');
        removeBtn.addEventListener('click', () => removeCallback(source.id));

        container.appendChild(sourceCard);
      });
    }

    updateSourcesData(input, sources) {
      if (!input) return;
      input.value = JSON.stringify(sources);
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

    // Process queued operations (stress test protection)
    processQueue() {
      if (this.operationQueue.length === 0 || this.operationInProgress) {
        return;
      }

      const nextOperation = this.operationQueue.shift();
      this.log('debug', `Processing queued operation: ${nextOperation.type}`, nextOperation);
      
      // Execute the queued operation
      if (nextOperation.type === 'show') {
        this.show(nextOperation.modalId, nextOperation.options);
      } else if (nextOperation.type === 'hide') {
        this.hide(nextOperation.modalId);
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

  // Also expose ModalManager for backward compatibility
  window.ModalManager = window.Modal;

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