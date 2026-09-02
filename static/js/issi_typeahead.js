function initISSITypeahead(input) {
  const targetId = input.dataset.suggestionsTarget;
  const suggestions = targetId ? document.getElementById(targetId) : input.parentElement.querySelector(".issi-suggestions");
  const suggestionsUrl = input.dataset.suggestionsUrl;
  if (!suggestions || !suggestionsUrl) return;

  let suggestionController = null;

  function hideSuggestions() {
    suggestions.classList.add("d-none");
    suggestions.innerHTML = "";
  }

  function renderSuggestions(items) {
    suggestions.innerHTML = "";
    if (!items.length) {
      hideSuggestions();
      return;
    }

    items.forEach(item => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "list-group-item list-group-item-action d-flex justify-content-between align-items-start gap-3";
      button.dataset.issiNumber = item.number;

      const text = document.createElement("span");
      text.className = "text-start";
      text.textContent = item.alias ? `${item.number} - ${item.alias}` : item.number;
      button.appendChild(text);

      if (item.is_active) {
        const badge = document.createElement("span");
        badge.className = "badge bg-secondary";
        badge.textContent = input.dataset.activeLabel || "Actief";
        button.appendChild(badge);
      }

      button.addEventListener("click", () => {
        input.value = item.number;
        hideSuggestions();
        input.focus();
      });

      suggestions.appendChild(button);
    });

    suggestions.classList.remove("d-none");
  }

  input.addEventListener("input", () => {
    const query = input.value.trim();
    if (suggestionController) suggestionController.abort();
    if (query.length < 2) {
      hideSuggestions();
      return;
    }

    suggestionController = new AbortController();
    const url = `${suggestionsUrl}?q=${encodeURIComponent(query)}`;
    fetch(url, { signal: suggestionController.signal })
      .then(response => response.json())
      .then(data => renderSuggestions(data.results || []))
      .catch(error => {
        if (error.name !== "AbortError") hideSuggestions();
      });
  });

  document.addEventListener("click", event => {
    if (!input.contains(event.target) && !suggestions.contains(event.target)) {
      hideSuggestions();
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-issi-typeahead]").forEach(initISSITypeahead);
});
