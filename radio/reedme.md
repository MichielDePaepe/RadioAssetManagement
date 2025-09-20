# Radio

## Radio Selector

Een herbruikbare modal en knopcomponent om radio’s te selecteren in een Django-app. 
Gebruikt Bootstrap voor modals en buttons, en ondersteunt een callbackfunctie voor verwerking van de selectie.

### Gebruik

1. Laad de template tags in je template:

```django
{% load radio_selector_tags %}
```

2. Voeg de modal toe in je pagina:

```django
{% radio_selector_modal %}
```

3. Voeg een knop toe:

```django
{% radio_selector_button %}
```

### Callbackfunctie

Definieer een globale callbackfunctie om de geselecteerde radio te verwerken:

```js
function radio_selector_callback(btn, data){
  ...
}
```

- De knop die de modal opent wordt automatisch doorgegeven (`btn`).
- `data` bevat `tei`, `issi`, `alias` en `radio` van de geselecteerde radio

### Template Tags

#### `radio_selector_modal`

```django
{% radio_selector_modal title="Radio zoeken" %}
```

- `title` (optioneel): titel van de modal.

#### `radio_selector_button`

```django
{% radio_selector_button btn_type="btn-primary" extra_class="me-2" callback="myCallback" %}
```

- `btn_type` (optioneel): Bootstrap button class.
- `extra_class` (optioneel): extra CSS-classes voor de knop.
- `callback` (optioneel): naam van de JS-functie die wordt aangeroepen bij selectie.
- Alle andere argumenten zullen als `data-<key>='<value>'` toegevoegd worden aan de knop. Deze kunnen later in de callback 

### Styling

- Gebruikt Bootstrap 5 voor modals en buttons.
- Dmv `extra_class` kan de button gestyled worden.
