// MutationObserver om nieuwe timeago elementen te detecteren
  const observer = new MutationObserver(mutations => {
    for (const mutation of mutations) {
      for (const node of mutation.addedNodes) {
        if (node.nodeType === 1) { // element node
          if (node.classList.contains('timeago')) {
            timeago.render(node, 'nl');
          }
          // check ook kinderen van het toegevoegde element
          node.querySelectorAll?.('.timeago').forEach(el => {
            timeago.render(el, 'nl');
          });
        }
      }
    }
  });

  observer.observe(document.body, { childList: true, subtree: true });

  


function renderRadioCards(elements, callback) {
  elements.forEach(el => {
    const tei = el.dataset.tei;
    if (!tei) return;

    fetch(`/radio/${tei}/card/`)
      .then(r => r.text())
      .then(html => {
        const wrapper = document.createElement('div');
        wrapper.innerHTML = html.trim();
        const newEl = wrapper.firstChild;

        if (el.parentNode) {
          el.replaceWith(newEl);
        } else {
          console.warn('Element heeft geen parent, kan niet vervangen worden:', el);
        }

        if (callback) callback(newEl);
      });
  });
}





document.addEventListener("DOMContentLoaded", () => {
  // initial load
  renderRadioCards(document.querySelectorAll('.radio-card'), () => {
    document.querySelectorAll('.card').forEach(el => {
      if(window.radio_cards_gray_on_load){
        el.style.filter = 'grayscale(100%)';
      }        
    });
  });

  // observer voor dynamisch toegevoegde elementen
  const observer = new MutationObserver(mutations => {
    for (const mutation of mutations) {
      mutation.addedNodes.forEach(node => {
        if (node.nodeType === 1) {
          if (node.classList.contains('radio-card')) {
            renderRadioCards([node]);
            // observeer data-tei veranderingen op nieuwe card
            teiObserver.observe(node, { attributes: true, attributeFilter: ['data-tei'] });
          }
          node.querySelectorAll?.('.card').forEach(inner => {
            renderRadioCards([inner]);
          });
        }
      });
    }
  });

  observer.observe(document.body, { childList: true, subtree: true });

  // observer voor data-tei wijzigingen
  const teiObserver = new MutationObserver(mutations => {
    for (const mutation of mutations) {
      if (mutation.type === 'attributes' && mutation.attributeName === 'data-tei') {
        renderRadioCards([mutation.target]);
      }
    }
  });

  // observeer bestaande radio-cards
  document.querySelectorAll('.radio-card').forEach(el => {
    teiObserver.observe(el, { attributes: true, attributeFilter: ['data-tei'] });
  });
});
