import {
    EVT_DESELECT_ITEMSUBITEM,
    EVT_SELECT_ITEMSUBITEM,
    EVT_RESELECT_ITEMSUBITEM,
    EVT_TAGS_UPDATED
} from './items-list.js';

let _selectedItem = null;
let _selectedItemSubitemId = null;

import {
    EVT_TAGS_UPDATED
} from "../pub-sub-events.js";

class TagsBar extends HTMLElement {

    constructor()  {
        console.log('TagsBar.constructor()');
        super();
        this.myId = null;
    }

    render() {
        this.innerHTML = `<input class="tags-bar" id="my-tags-input" type="text" placeholder="" disabled spellcheck="false" size="64"/>`;
    }

    attachDOMEventHandlers() {
        //this.intervalID = setInterval(this.checkForUpdatedSearch.bind(this), this.INTERVAL);

        this.querySelector('input').addEventListener('keydown', (evt) => {
            if (evt.key === "Escape") {
                //don't try to handle this
                return;
            }
            evt.stopPropagation();
        });

        this.querySelector('input').addEventListener('input', (evt) => {
            this.actionTagsUpdated();
        });

        this.querySelector('input').addEventListener('mousedown', evt => {
            //override default behavior of body
            evt.stopPropagation();
        });

        this.querySelector('input').addEventListener('focus', () => {
            //PubSub.publish(EVT_SEARCH_FOCUS, {});
        });
    }

    subscribeToPubSubEvents() {
        PubSub.subscribe(EVT_DESELECT_ITEMSUBITEM, (msg, data) => {
            this.actionDeselect();
        });

        PubSub.subscribe(EVT_SELECT_ITEMSUBITEM, (msg, data) => {
            console.log('debug: EVT_SELECT_ITEMSUBITEM');
            this.actionSelectOrReselect(data);
        });

        PubSub.subscribe(EVT_RESELECT_ITEMSUBITEM, (msg, data) => {
            console.log('debug: EVT_RESELECT_ITEMSUBITEM');
            this.actionSelectOrReselect(data);
        });
    }

    actionTagsUpdated() {
        let updatedTags = this.querySelector('input').value;
        //TODO: parse for validity
        PubSub.publish(EVT_TAGS_UPDATED, updatedTags);
    }

    actionDeselect() {
        document.getElementById('my-tags-input').disabled = true;
        this.querySelector('input').value = '';
        _selectedItem = null;
        _selectedItemSubitemId = null;
    }

    actionSelectOrReselect(data) {
        if (_selectedItemSubitemId !== data['itemSubitemId']) {
            console.log('debug: actionSelectOrReselect');
            document.getElementById('my-tags-input').disabled = false;
            _selectedItem = data['item'];
            _selectedItemSubitemId = data['itemSubitemId'];
            let subitemIndex = parseInt(_selectedItemSubitemId.split(':')[1]);
            console.log(_selectedItem);
            this.querySelector('input').value = _selectedItem['subitems'][subitemIndex]['tags'];
        }
    }

    connectedCallback() {
        this.render();
        this.attachDOMEventHandlers();
        this.subscribeToPubSubEvents();
    }

    disconnectedCallback() {

    }

}

customElements.define('tags-bar', TagsBar);