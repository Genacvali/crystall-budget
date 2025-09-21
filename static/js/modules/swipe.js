// Swipe functionality for mobile cards
export function initSwipeCards() {
  const swipeCards = document.querySelectorAll('.swipe-card');
  
  swipeCards.forEach(card => {
    let startX = 0;
    let currentX = 0;
    let isDragging = false;
    const swipeContent = card.querySelector('.swipe-content');
    const threshold = 50; // Minimum swipe distance
    
    // Touch events
    card.addEventListener('touchstart', handleStart, { passive: true });
    card.addEventListener('touchmove', handleMove, { passive: false });
    card.addEventListener('touchend', handleEnd, { passive: true });
    
    // Mouse events for desktop testing
    card.addEventListener('mousedown', handleStart);
    card.addEventListener('mousemove', handleMove);
    card.addEventListener('mouseup', handleEnd);
    card.addEventListener('mouseleave', handleEnd);
    
    function handleStart(e) {
      isDragging = true;
      startX = e.type === 'touchstart' ? e.touches[0].clientX : e.clientX;
      card.classList.add('swiping');
      swipeContent.style.transition = 'none';
    }
    
    function handleMove(e) {
      if (!isDragging) return;
      
      e.preventDefault();
      currentX = (e.type === 'touchmove' ? e.touches[0].clientX : e.clientX) - startX;
      
      // Limit swipe distance
      const maxSwipe = 100;
      currentX = Math.max(-maxSwipe, Math.min(maxSwipe, currentX));
      
      swipeContent.style.transform = `translateX(${currentX}px)`;
      
      // Visual feedback
      if (currentX > threshold) {
        card.classList.add('swipe-left-feedback');
        card.classList.remove('swipe-right-feedback');
      } else if (currentX < -threshold) {
        card.classList.add('swipe-right-feedback');
        card.classList.remove('swipe-left-feedback');
      } else {
        card.classList.remove('swipe-left-feedback', 'swipe-right-feedback');
      }
    }
    
    function handleEnd(e) {
      if (!isDragging) return;
      
      isDragging = false;
      card.classList.remove('swiping', 'swipe-left-feedback', 'swipe-right-feedback');
      swipeContent.style.transition = 'transform 0.3s ease';
      
      if (currentX > threshold) {
        // Swipe right - edit
        const editBtn = card.querySelector('.swipe-action.edit');
        if (editBtn) {
          const editUrl = editBtn.dataset.url;
          window.location.href = editUrl;
        }
      } else if (currentX < -threshold) {
        // Swipe left - delete
        const deleteBtn = card.querySelector('.swipe-action.delete');
        if (deleteBtn) {
          const confirmText = deleteBtn.dataset.confirmText;
          if (confirm(confirmText)) {
            const expenseId = deleteBtn.dataset.expenseId;
            // Create and submit delete form
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = `/expenses/delete/${expenseId}`;
            document.body.appendChild(form);
            form.submit();
          }
        }
      }
      
      // Reset position
      swipeContent.style.transform = 'translateX(0)';
      currentX = 0;
    }
  });
  
  // Click handlers for swipe actions
  document.querySelectorAll('.swipe-action.edit').forEach(btn => {
    btn.addEventListener('click', function() {
      const url = this.dataset.url;
      if (url) {
        window.location.href = url;
      }
    });
  });
  
  document.querySelectorAll('.swipe-action.delete').forEach(btn => {
    btn.addEventListener('click', function() {
      const confirmText = this.dataset.confirmText;
      if (confirm(confirmText)) {
        const expenseId = this.dataset.expenseId;
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/expenses/delete/${expenseId}`;
        document.body.appendChild(form);
        form.submit();
      }
    });
  });
}