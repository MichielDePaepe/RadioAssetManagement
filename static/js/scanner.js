class Scanner {
  constructor({ inputId, onScan }) {
    this.input = document.getElementById(inputId);
    this.scanUrl = "/en/radio/scan/";   // hardcoded
    this.onScan = onScan;

    if (!this.input) {
      throw new Error(`Input element with id "${inputId}" not found.`);
    }

    this._init();
  }

  _init() {
    this.input.style.position = 'absolute';
    this.input.style.left = '-9999px';

    this.input.setAttribute('autocomplete', 'off');
    this.input.setAttribute('autocorrect', 'off');
    this.input.setAttribute('autocapitalize', 'off');

    // bind handlers zodat we ze later kunnen verwijderen
    this._focusInput = () => this.input.focus();
    this._blurHandler = () => setTimeout(this._focusInput, 100);
    this._keyHandler = (e) => this._onKeyPress(e);

    this.is_scanning = false;
  }

  start() {
    if (! this.is_scanning) {
      document.addEventListener('click', this._focusInput);
      document.addEventListener('keydown', this._focusInput);
      window.addEventListener('blur', this._blurHandler);
      
      this.input.addEventListener('keypress', this._keyHandler);

      this._focusInput();

      this.is_scanning = true;
    }
  }

  stop() {
    if (this.is_scanning) {
      document.removeEventListener('click', this._focusInput);
      document.removeEventListener('keydown', this._focusInput);
      window.removeEventListener('blur', this._blurHandler);
      
      this.input.removeEventListener('keypress', this._keyHandler);

      this.is_scanning = false;
    }
  }

  _onKeyPress(e) {
    if (e.key !== 'Enter') return;

    e.preventDefault();
    e.stopPropagation();

    const scanned_line = this.input.value.trim();
    this.input.value = '';
    if (scanned_line === '') return;

    fetch(this.scanUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scanned_line }),
    })
    .then(res => res.json())
    .then(data => this.onScan(data))
    .catch(err => console.error("Scan error:", err));
  }

  destroy() {
    this.stop()

    if (document.activeElement === this.input) {
      document.activeElement.blur();
    }
  }

}
