"use strict";

import {
    state
} from "../app-state.js";

const fifo = {};
const recent = {};
const locked = {};

const RequestBusyMode = Object.freeze({
  NOOP: Symbol("noop"),
  FIFO: Symbol("fifo"),
  RECENT: Symbol("recent")
});

const endpointBusyModes = {
    '/indent': RequestBusyMode.NOOP,
    '/outdent': RequestBusyMode.NOOP,
    '/add-item-sibling': RequestBusyMode.NOOP,
    '/add-subitem-sibling': RequestBusyMode.NOOP,
    '/add-subitem-child': RequestBusyMode.NOOP,
    '/add-item-top': RequestBusyMode.NOOP,
    '/paste-sibling': RequestBusyMode.NOOP,
    '/todo': RequestBusyMode.NOOP,
    '/done': RequestBusyMode.NOOP,
    '/expand': RequestBusyMode.NOOP,
    '/collapse': RequestBusyMode.NOOP,
    '/delete-subitem': RequestBusyMode.NOOP,
    '/move-item-up': RequestBusyMode.NOOP,
    '/move-item-down': RequestBusyMode.NOOP,
    '/move-subitem-up': RequestBusyMode.NOOP,
    '/move-subitem-down': RequestBusyMode.NOOP,
    '/paste-child': RequestBusyMode.NOOP,
    '/search': RequestBusyMode.RECENT,
    '/update-subitem-content': RequestBusyMode.RECENT,
    '/pagination-update': RequestBusyMode.RECENT,
    '/update-tags': RequestBusyMode.RECENT
}


window.onload = function(evt) {

    for (const [key, value] of Object.entries(endpointBusyModes)) {
        locked[key] = false;
        if (value === RequestBusyMode.NOOP) {
            //pass
        }
        else if (value === RequestBusyMode.FIFO) {
            fifo[key] = [];
        }
        else if (value === RequestBusyMode.RECENT) {
            recent[key] = null;
        }
        else {
            console.error('Unknown value ' + value);
        }
    }
}

export const genericRequestV2 = async function(evt, endpoint){
    console.log('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>');
    console.log(endpoint);
    console.log('locked:');
    console.log(locked);
    try {
        if (evt) {
            evt.preventDefault();
            evt.stopPropagation();
        }
        if (locked[endpoint]) {
            console.log(`endpoint ${endpoint} is locked`);
            if (endpointBusyModes[endpoint] === RequestBusyMode.NOOP) {
                console.log('NOOP');
                return;
            }
            else if (endpointBusyModes[endpoint] === RequestBusyMode.FIFO) {
                console.log('pushing state to fifo queue');
                fifo[endpoint].push(JSON.parse(JSON.stringify(state)));
                return;
            }
            else if (endpointBusyModes[endpoint] === RequestBusyMode.RECENT) {
                console.log('updating state to recent');
                recent[endpoint] = JSON.parse(JSON.stringify(state));
                return;
            }
            else {
                console.error('Unknown mode ' + endpointBusyModes[endpoint]);
                return;
            }
        }
        locked[endpoint] = true;
        console.log(`LOCKING ${endpoint}`);

        let request = {
            appState: state,
        }
        let response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(request)
        });
        let result = await response.json();
        /////////////////////////////////////////////////////////////
        console.log(`UNLOCKING ${endpoint}`);
        locked[endpoint] = false;

        console.log(`endpoint ${endpoint} is unlocked`);
        // if (endpointBusyModes[endpoint] === RequestBusyMode.NOOP) {
        //     //
        // }
        // else if (endpointBusyModes[endpoint] === RequestBusyMode.FIFO) {
        //     if (fifo[endpoint].length > 0) {
        //         console.log('requesting next state to fifo queue TODO');
        //         //localState = fifo[endpoint].pop();
        //         //TODO
        //     }
        // }
        // else if (endpointBusyModes[endpoint] === RequestBusyMode.RECENT) {
        //     if (recent[endpoint] !== null) {
        //         console.log('updating state to recent TODO');
        //         // console.log(state);
        //         // //recent[endpoint] = JSON.parse(JSON.stringify(itemsListState));
        //         // localState = recent[endpoint];
        //         // //recent[endpoint] = null;
        //         // //TODO
        //     }
        // }
        // else {
        //     console.error('Unknown mode ' + endpointBusyModes[endpoint]);
        //     return;
        // }
        /////////////////////////////////////////////////////////////
        return result;
    } catch (error) {
        console.log(error);
        //TODO publish the error
    }
}
