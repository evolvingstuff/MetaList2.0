'use strict';

class SuggestionsList extends HTMLElement {

    constructor() {
        super();
        this.myId = null;
    }

    render() {
        let html = '';
        html += '    <div class="suggestion">Lorem ipsum dolor sit amet</div>';
        html += '    <div class="suggestion">Consectetur adipiscing elit</div>';
        html += '    <div class="suggestion">Sed do eiusmod tempor incididunt</div>';
        this.innerHTML = html;

        const suggestions = document.getElementById(this.myId);
        const attached_to = this.getAttribute('data-attached-to');
        const webComponent = document.getElementById(attached_to);
        const inputBox = webComponent.querySelector('input');
        const orientation = this.getAttribute('data-orientation');

        //position suggestions
        //TODO: move into suggestions web component
        //TODO: recalculate on window resize

        let gap = 3;
        let rect = inputBox.getBoundingClientRect();
        suggestions.style.left = rect.left + 'px';
            suggestions.style.width = rect.width + 'px';
        if (orientation === 'below') {
            suggestions.style.top = (rect.bottom + window.scrollY + gap) + 'px';
        }
        else if (orientation === 'above') {
            console.log('DEBUG above');
            //suggestions.style.top = (rect.top + window.scrollY - suggestions.offsetHeight - gap) + 'px';
            suggestions.style.top = (rect.top + window.scrollY - suggestions.offsetHeight - gap) + 'px';
        }
        else {
            throw Error(`unknown (or missing) orientation attribute: ${orientation}`);
        }
        console.log('cp1');
    }

    attachEventHandlers() {

        const attached_to = this.getAttribute('data-attached-to');
        const webComponent = document.getElementById(attached_to);
        const inputBox = webComponent.querySelector('input');
        const suggestionsDiv = document.getElementById(this.myId);

        inputBox.addEventListener('focus', () => {
            console.log(inputBox);
            suggestionsDiv.style.display = 'block'; //make it visible BEFORE render
            this.render();
        });

        inputBox.addEventListener('blur', () => {
            console.log(inputBox);
            suggestionsDiv.style.display = 'none';
        });
    }

    connectedCallback() {
        this.myId = this.getAttribute('id');
        console.log(this.myId);
        this.render();
        this.attachEventHandlers();
    }

    disconnectedCallback() {
        //TODO remove event listeners
    }
}

customElements.define('suggestions-list', SuggestionsList);