/**
 * Category Edit Modal Handler
 * Handles multi-source toggle and form interactions
 */

(function() {
  'use strict';

  console.log('[CategoryEdit Module] Loaded');

  // Use event delegation on document level
  document.addEventListener('click', function(e) {
    // Handle multi-source switch toggle
    if (e.target && e.target.id === 'multiSourceSwitch') {
      console.log('[CategoryEdit] Switch clicked!', e.target.checked);
      handleMultiSourceToggle(e.target);
    }
  });

  document.addEventListener('change', function(e) {
    // Handle limit type change for single-source
    if (e.target && e.target.name === 'limit_type') {
      handleLimitTypeChange(e.target);
    }

    // Handle source type change in add source form
    if (e.target && e.target.id === 'sourceTypeSelectEdit') {
      handleSourceTypeChange(e.target);
    }
  });

  // Handle form submissions with event delegation
  // Use capture phase to intercept before other handlers
  document.addEventListener('submit', function(e) {
    // Handle add source form
    if (e.target && e.target.id === 'addSourceFormEdit') {
      e.preventDefault();
      e.stopImmediatePropagation(); // Prevent other handlers from running
      handleAddSourceSubmit(e.target);
      return;
    }

    // Handle delete source forms
    if (e.target && e.target.classList.contains('delete-rule-form')) {
      e.preventDefault();
      e.stopImmediatePropagation(); // Prevent other handlers from running
      handleDeleteSourceSubmit(e.target);
      return;
    }
  }, true); // Use capture phase

  function handleMultiSourceToggle(switchElement) {
    const isMulti = switchElement.checked;
    const modal = switchElement.closest('.cb-modal__content') || document;

    const singleSourceFields = modal.querySelector('#singleSourceFields');
    const multiSourceFields = modal.querySelector('#multiSourceFields');
    const isMultiSourceHidden = modal.querySelector('#isMultiSourceHidden');
    const valueInput = modal.querySelector('[id^="valueInputEdit"]');

    console.log('[CategoryEdit] Found elements:', {
      singleSourceFields,
      multiSourceFields,
      isMultiSourceHidden,
      valueInput
    });

    if (isMulti) {
      console.log('[CategoryEdit] Switching to multi-source mode');
      if (singleSourceFields) singleSourceFields.style.display = 'none';
      if (multiSourceFields) multiSourceFields.style.display = 'block';
      if (isMultiSourceHidden) isMultiSourceHidden.value = '1';
      if (valueInput) valueInput.removeAttribute('required');
    } else {
      console.log('[CategoryEdit] Switching to single-source mode');
      if (singleSourceFields) singleSourceFields.style.display = 'block';
      if (multiSourceFields) multiSourceFields.style.display = 'none';
      if (isMultiSourceHidden) isMultiSourceHidden.value = '0';
      if (valueInput) valueInput.setAttribute('required', 'required');
    }
  }

  function handleLimitTypeChange(input) {
    const modal = input.closest('.cb-modal__content') || document;
    const valueSuffix = modal.querySelector('[id^="valueSuffixEdit"]');

    if (valueSuffix) {
      valueSuffix.textContent = input.value === 'percent' ? '%' : '₽';
    }
  }

  function handleSourceTypeChange(select) {
    const modal = select.closest('.cb-modal__content') || document;
    const sourceValueSuffixEdit = modal.querySelector('#sourceValueSuffixEdit');

    if (sourceValueSuffixEdit) {
      sourceValueSuffixEdit.textContent = select.value === 'percent' ? '%' : '₽';
    }
  }

  function handleAddSourceSubmit(form) {
    console.log('[CategoryEdit] Add source form submitted');

    // Check if already submitting
    if (form.dataset.submitting === 'true') {
      console.log('[CategoryEdit] Already submitting, ignoring');
      return;
    }
    form.dataset.submitting = 'true';

    const submitBtn = form.querySelector('button[type="submit"]');
    const originalBtnText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Добавление...';

    const formData = new FormData(form);

    fetch(form.action, {
      method: 'POST',
      body: formData,
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/json'
      }
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        console.log('[CategoryEdit] Source added successfully, reloading modal');
        // Extract category ID from form action URL
        const categoryId = form.action.match(/\/category\/(\d+)\//)[1];
        // Clear form
        form.reset();
        // Reset button state
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnText;
        form.dataset.submitting = 'false';
        // Reload modal content to show updated list
        reloadModalContent(categoryId);
      } else {
        alert(data.error || 'Ошибка при добавлении источника');
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnText;
        form.dataset.submitting = 'false';
      }
    })
    .catch(error => {
      console.error('[CategoryEdit] Error adding source:', error);
      alert('Ошибка при добавлении источника');
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalBtnText;
      form.dataset.submitting = 'false';
    });
  }

  function handleDeleteSourceSubmit(form) {
    console.log('[CategoryEdit] Delete source form submitted');

    const btn = form.querySelector('button[type="submit"]');
    const originalHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

    const formData = new FormData(form);

    fetch(form.action, {
      method: 'POST',
      body: formData,
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/json'
      }
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        console.log('[CategoryEdit] Source deleted successfully, reloading modal');
        reloadModalContent(data.category_id);
      } else {
        alert(data.error || 'Ошибка при удалении источника');
        btn.disabled = false;
        btn.innerHTML = originalHtml;
      }
    })
    .catch(error => {
      console.error('[CategoryEdit] Error deleting source:', error);
      alert('Ошибка при удалении источника');
      btn.disabled = false;
      btn.innerHTML = originalHtml;
    });
  }

  function reloadModalContent(categoryId) {
    console.log('[CategoryEdit] Reloading modal content for category', categoryId);
    const modalUrl = `/budget/modals/category/${categoryId}/edit`;

    // Find the modal and prevent any close events during reload
    const modal = document.querySelector('.cb-modal--show');
    if (modal) {
      modal.dataset.reloading = 'true';
    }

    fetch(modalUrl, {
      headers: {
        'X-Requested-With': 'XMLHttpRequest'
      }
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      return response.text();
    })
    .then(html => {
      const modalContent = document.querySelector('.cb-modal--show .cb-modal__content');
      if (modalContent) {
        // Save scroll position
        const scrollPos = modalContent.scrollTop;

        modalContent.innerHTML = html;
        console.log('[CategoryEdit] Modal content reloaded');

        // Restore scroll position
        modalContent.scrollTop = scrollPos;

        // Re-run scripts in the new content
        const scripts = modalContent.querySelectorAll('script');
        scripts.forEach(oldScript => {
          const newScript = document.createElement('script');
          newScript.textContent = oldScript.textContent;
          oldScript.parentNode.replaceChild(newScript, oldScript);
        });
      }

      // Remove reloading flag
      if (modal) {
        modal.dataset.reloading = 'false';
      }
    })
    .catch(error => {
      console.error('[CategoryEdit] Error reloading modal:', error);
      alert('Ошибка при обновлении списка источников');

      // Remove reloading flag
      if (modal) {
        modal.dataset.reloading = 'false';
      }
    });
  }

  console.log('[CategoryEdit Module] Event handlers registered');
})();
