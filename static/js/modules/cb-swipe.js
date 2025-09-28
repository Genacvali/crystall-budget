/**
 * CrystalBudget Swipe Actions
 * Свайп-действия для мобильных карточек
 */

class SwipeActions {
  constructor() {
    this.activeSwipe = null;
    this.swipeThreshold = 40; // px
    this.velocityThreshold = 0.3; // px/ms
    this.actionsPanelWidth = 120; // px
    
    this.init();
  }

  init() {
    // Инициализация только на мобильных устройствах
    if (window.innerWidth >= 992) {
      return;
    }

    this.bindEvents();
    this.setupKeyboardNavigation();
  }

  bindEvents() {
    // Делегированные события на документе
    document.addEventListener('pointerdown', this.handlePointerDown.bind(this), { passive: false });
    document.addEventListener('pointermove', this.handlePointerMove.bind(this), { passive: false });
    document.addEventListener('pointerup', this.handlePointerEnd.bind(this));
    document.addEventListener('click', this.handleClick.bind(this));
    
    // Fallback для touch events
    document.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: false });
    document.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: false });
    document.addEventListener('touchend', this.handleTouchEnd.bind(this));

    // Закрытие по Escape
    document.addEventListener('keydown', this.handleKeyDown.bind(this));
    
    // Закрытие при изменении размера окна
    window.addEventListener('resize', this.handleResize.bind(this));
  }

  handlePointerDown(e) {
    const track = e.target.closest('.cb-swipe-track');
    if (!track) return;

    const swipe = track.closest('.cb-swipe');
    if (!swipe) return;

    this.startSwipe(e, swipe, track);
  }

  handleTouchStart(e) {
    // Fallback для старых браузеров
    if (!window.PointerEvent) {
      const track = e.target.closest('.cb-swipe-track');
      if (!track) return;
      
      const swipe = track.closest('.cb-swipe');
      if (!swipe) return;

      this.startSwipe(e.touches[0], swipe, track);
    }
  }

  startSwipe(pointer, swipe, track) {
    // Предотвращаем свайп если уже есть открытая карточка (кроме текущей)
    if (this.activeSwipe && this.activeSwipe !== swipe) {
      this.closeSwipe(this.activeSwipe);
    }

    this.swipeData = {
      swipe,
      track,
      startX: pointer.clientX,
      startY: pointer.clientY,
      startTime: Date.now(),
      currentX: pointer.clientX,
      isActive: false,
      initialOffset: swipe.dataset.open === 'true' ? -this.actionsPanelWidth : 0
    };

    track.classList.add('is-swiping');
  }

  handlePointerMove(e) {
    if (!this.swipeData) return;
    
    this.updateSwipe(e);
    e.preventDefault();
  }

  handleTouchMove(e) {
    if (!window.PointerEvent && this.swipeData) {
      this.updateSwipe(e.touches[0]);
      e.preventDefault();
    }
  }

  updateSwipe(pointer) {
    const { startX, startY, track, initialOffset } = this.swipeData;
    const deltaX = pointer.clientX - startX;
    const deltaY = pointer.clientY - startY;

    // Определяем направление жеста
    if (!this.swipeData.isActive) {
      if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 10) {
        this.swipeData.isActive = true;
      } else if (Math.abs(deltaY) > 10) {
        // Вертикальный жест - отменяем
        this.cancelSwipe();
        return;
      }
    }

    if (this.swipeData.isActive) {
      this.swipeData.currentX = pointer.clientX;
      
      // Ограничиваем движение
      let newOffset = initialOffset + deltaX;
      newOffset = Math.max(-this.actionsPanelWidth, Math.min(0, newOffset));
      
      track.style.transform = `translateX(${newOffset}px)`;
    }
  }

  handlePointerEnd(e) {
    if (!this.swipeData) return;
    
    this.endSwipe();
  }

  handleTouchEnd(e) {
    if (!window.PointerEvent && this.swipeData) {
      this.endSwipe();
    }
  }

  endSwipe() {
    if (!this.swipeData) return;

    const { swipe, track, startX, currentX, startTime, isActive, initialOffset } = this.swipeData;
    
    track.classList.remove('is-swiping');

    if (!isActive) {
      this.swipeData = null;
      return;
    }

    const deltaX = currentX - startX;
    const deltaTime = Date.now() - startTime;
    const velocity = Math.abs(deltaX) / deltaTime;

    // Определяем должны ли мы открыть/закрыть
    const shouldOpen = deltaX < -this.swipeThreshold || velocity > this.velocityThreshold;
    
    if (initialOffset === 0) {
      // Была закрыта
      if (shouldOpen) {
        this.openSwipe(swipe);
      } else {
        this.closeSwipe(swipe);
      }
    } else {
      // Была открыта
      if (deltaX > this.swipeThreshold || velocity > this.velocityThreshold) {
        this.closeSwipe(swipe);
      } else {
        this.openSwipe(swipe);
      }
    }

    this.swipeData = null;
  }

  cancelSwipe() {
    if (!this.swipeData) return;
    
    const { swipe, track } = this.swipeData;
    track.classList.remove('is-swiping');
    
    // Возвращаем в исходное положение
    const isOpen = swipe.dataset.open === 'true';
    track.style.transform = `translateX(${isOpen ? -this.actionsPanelWidth : 0}px)`;
    
    this.swipeData = null;
  }

  handleClick(e) {
    // Клик по кнопке меню (⋮)
    if (e.target.closest('.cb-swipe-menu')) {
      e.preventDefault();
      const swipe = e.target.closest('.cb-swipe');
      this.toggleSwipe(swipe);
      return;
    }

    // Клик по действию
    if (e.target.closest('.cb-swipe-btn')) {
      const swipe = e.target.closest('.cb-swipe');
      const btn = e.target.closest('.cb-swipe-btn');
      
      if (btn.classList.contains('cb-swipe-btn-delete')) {
        this.handleDelete(btn, swipe);
      } else if (btn.classList.contains('cb-swipe-btn-edit')) {
        this.handleEdit(btn, swipe);
      }
      return;
    }

    // Клик вне карточки - закрываем
    if (!e.target.closest('.cb-swipe')) {
      this.closeAllSwipes();
    }
  }

  handleDelete(btn, swipe) {
    const itemId = swipe.dataset.itemId;
    const itemType = swipe.dataset.itemType || 'expense';
    
    if (!confirm(`Удалить ${itemType === 'expense' ? 'расход' : 'доход'}?`)) {
      return;
    }

    // Показываем состояние загрузки
    swipe.classList.add('is-loading');
    
    // Отправляем запрос на удаление
    this.deleteItem(itemId, itemType)
      .then(() => {
        // Анимация удаления
        swipe.style.transition = 'all 300ms ease';
        swipe.style.transform = 'translateX(-100%)';
        swipe.style.opacity = '0';
        
        setTimeout(() => {
          swipe.remove();
        }, 300);
      })
      .catch((error) => {
        console.error('Delete failed:', error);
        swipe.classList.remove('is-loading');
        swipe.classList.add('has-error');
        
        setTimeout(() => {
          swipe.classList.remove('has-error');
        }, 2000);
      });
  }

  handleEdit(btn, swipe) {
    const itemId = swipe.dataset.itemId;
    const itemType = swipe.dataset.itemType || 'expense';
    
    // Переход на страницу редактирования или открытие модалки
    window.location.href = `/budget/${itemType}s/${itemId}/edit`;
  }

  async deleteItem(itemId, itemType) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    
    const response = await fetch(`/budget/${itemType}s/${itemId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      }
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    return response.json();
  }

  openSwipe(swipe) {
    // Закрываем другие открытые
    this.closeAllSwipes();
    
    this.activeSwipe = swipe;
    swipe.dataset.open = 'true';
    swipe.setAttribute('aria-expanded', 'true');
    
    const actions = swipe.querySelector('.cb-swipe-actions');
    actions.setAttribute('aria-hidden', 'false');
    
    // Фокус на первую кнопку
    const firstBtn = actions.querySelector('.cb-swipe-btn');
    if (firstBtn) {
      firstBtn.focus();
    }
  }

  closeSwipe(swipe) {
    if (!swipe) return;
    
    swipe.dataset.open = 'false';
    swipe.setAttribute('aria-expanded', 'false');
    
    const track = swipe.querySelector('.cb-swipe-track');
    const actions = swipe.querySelector('.cb-swipe-actions');
    
    track.style.transform = 'translateX(0)';
    actions.setAttribute('aria-hidden', 'true');
    
    if (this.activeSwipe === swipe) {
      this.activeSwipe = null;
    }
  }

  closeAllSwipes() {
    const openSwipes = document.querySelectorAll('.cb-swipe[data-open="true"]');
    openSwipes.forEach(swipe => this.closeSwipe(swipe));
  }

  toggleSwipe(swipe) {
    if (swipe.dataset.open === 'true') {
      this.closeSwipe(swipe);
    } else {
      this.openSwipe(swipe);
    }
  }

  handleKeyDown(e) {
    if (e.key === 'Escape') {
      this.closeAllSwipes();
    }
  }

  handleResize() {
    // При изменении размера окна закрываем все
    this.closeAllSwipes();
    
    // Переинициализация при переходе на/с мобильной версии
    if (window.innerWidth >= 992) {
      this.destroy();
    }
  }

  setupKeyboardNavigation() {
    // Навигация по кнопкам внутри панели действий
    document.addEventListener('keydown', (e) => {
      if (!this.activeSwipe) return;
      
      const actions = this.activeSwipe.querySelector('.cb-swipe-actions');
      const buttons = actions.querySelectorAll('.cb-swipe-btn');
      const focused = document.activeElement;
      
      if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        const currentIndex = Array.from(buttons).indexOf(focused);
        if (currentIndex !== -1) {
          e.preventDefault();
          const nextIndex = e.key === 'ArrowRight' 
            ? (currentIndex + 1) % buttons.length
            : (currentIndex - 1 + buttons.length) % buttons.length;
          buttons[nextIndex].focus();
        }
      }
    });
  }

  destroy() {
    this.closeAllSwipes();
    this.swipeData = null;
    this.activeSwipe = null;
  }
}

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
  if (window.innerWidth < 992) {
    window.swipeActions = new SwipeActions();
  }
});

// Переинициализация при изменении размера
window.addEventListener('resize', () => {
  if (window.innerWidth < 992 && !window.swipeActions) {
    window.swipeActions = new SwipeActions();
  }
});

export { SwipeActions };