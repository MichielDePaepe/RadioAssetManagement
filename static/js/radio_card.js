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
        el.outerHTML = html;
        if (callback) callback(el); // callback na elke fetch, met element
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
            }
            node.querySelectorAll?.('.card').forEach(inner => {
              renderRadioCards([inner]);
            });
          }
        });
      }
    });

    observer.observe(document.body, { childList: true, subtree: true });
  });