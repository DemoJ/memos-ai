// ==UserScript==
// @name         Memos AI Assistant Floater
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  Adds a floating AI assistant window to Memos.
// @author       Roo
// @match        http://10.18.1.14:5230/*
// @grant        GM_addStyle
// ==/UserScript==

(function() {
    'use strict';

    // --- Configuration ---
    const assistantUrl = "http://10.18.1.14:9876"; // Your AI Assistant URL
    const iconUrl = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxZW0iIGhlaWdodD0iMWVtIiB2aWV3Qm94PSIwIDAgMjQgMjQiPjxwYXRoIGZpbGw9ImN1cnJlbnRDb2xvciIgZD0iTTEyIDJDNi40NzcgMiAyIDYuNDc3IDIgMTJzNC40NzcgMTAgMTAgMTBzMTAtNC40NzcgMTAtMTBTMTcuNTIzIDIgMTIgMm00LjQxNCAxMS40NzZhMSAxIDAgMCAxIC4wMDEgMS40MTVsLTIuMTIyIDIuMTIyYTEgMSAwIDAgMS0xLjQxNSAwTDEyIDUuNDE0bC0uODc5Ljg3OWExIDEgMCAwIDEtMS40MTUgMEw3LjU4NiA0LjE3MmExIDEgMCAwIDEgMC0xLjQxNWwyLjEyMS0yLjEyMmExIDEgMCAwIDEgMS40MTUgMGwxLjQxNCAxLjQxNGwxLjQxNC0xLjQxNGExIDEgMCAwIDEgMS40MTUgMGwyLjEyMiAyLjEyMmExIDEgMCAwIDEgMCAxLjQxNWwtMi4xMjIgMi4xMjFsLjg4Ljg3OW0tMS40MTUtNS42NTdsLS43MDcuNzA3bC43MDcuNzA3bDIuMTIyLTIuMTIybC0uNzA3LS43MDdtLTQuOTUgNC45NWwtMS40MTQtMS40MTRsLTEuNDEzIDEuNDE0bC43MDYuNzA3bDEuNDE1LTEuNDE0bDEuNDE0IDEuNDE0bC0uNzA3LjcwN20tMy41MzYtMy41MzZsLS43MDctLjcwN2wtMi4xMjIgMi4xMjJsLjcwNy43MDdaIj48L3BhdGg+PC9zdmc+"; // A simple robot icon

    // --- Create Floating Icon ---
    const floatIcon = document.createElement('div');
    floatIcon.id = 'ai-assistant-icon';
    floatIcon.innerHTML = `<img src="${iconUrl}" style="width: 32px; height: 32px;">`;
    document.body.appendChild(floatIcon);

    // --- Create Assistant Window ---
    const assistantWindow = document.createElement('div');
    assistantWindow.id = 'ai-assistant-window';
    assistantWindow.innerHTML = `
        <div id="ai-assistant-header">
            <span>AI Assistant</span>
            <button id="ai-assistant-close">X</button>
        </div>
        <iframe src="${assistantUrl}" id="ai-assistant-iframe"></iframe>
    `;
    document.body.appendChild(assistantWindow);

    // --- Add Styles ---
    GM_addStyle(`
        #ai-assistant-icon {
            position: fixed;
            bottom: 30px;
            right: 30px;
            width: 50px;
            height: 50px;
            background-color: #007bff;
            border-radius: 50%;
            display: flex;
            justify-content: center;
            align-items: center;
            cursor: pointer;
            z-index: 9998;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            transition: background-color 0.3s;
        }
        #ai-assistant-icon:hover {
            background-color: #0056b3;
        }
        #ai-assistant-window {
            position: fixed;
            bottom: 90px;
            right: 30px;
            width: 400px;
            height: 600px;
            background-color: white;
            border: 1px solid #ccc;
            border-radius: 8px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
            z-index: 9999;
            display: none;
            flex-direction: column;
            resize: both;
            overflow: hidden;
        }
        #ai-assistant-header {
            padding: 10px;
            cursor: move;
            background-color: #f1f1f1;
            border-bottom: 1px solid #ccc;
            display: flex;
            justify-content: space-between;
            align-items: center;
            height: 40px;
        }
        #ai-assistant-header span {
            font-weight: bold;
        }
        #ai-assistant-close {
            border: none;
            background: transparent;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
        }
        #ai-assistant-iframe {
            flex-grow: 1;
            border: none;
            width: 100%;
            height: calc(100% - 40px);
        }
    `);

    // --- Functionality ---
    const closeButton = document.getElementById('ai-assistant-close');

    let isWindowVisible = false;

    function toggleWindow() {
        isWindowVisible = !isWindowVisible;
        assistantWindow.style.display = isWindowVisible ? 'flex' : 'none';
    }

    floatIcon.addEventListener('click', toggleWindow);
    closeButton.addEventListener('click', toggleWindow);

    // --- Dragging Functionality ---
    const header = document.getElementById('ai-assistant-header');
    let isDragging = false;
    let offsetX, offsetY;

    header.addEventListener('mousedown', (e) => {
        isDragging = true;
        offsetX = e.clientX - assistantWindow.offsetLeft;
        offsetY = e.clientY - assistantWindow.offsetTop;
        assistantWindow.style.userSelect = 'none'; // Prevent text selection while dragging
    });

    document.addEventListener('mousemove', (e) => {
        if (isDragging) {
            assistantWindow.style.left = `${e.clientX - offsetX}px`;
            assistantWindow.style.top = `${e.clientY - offsetY}px`;
        }
    });

    document.addEventListener('mouseup', () => {
        isDragging = false;
        assistantWindow.style.userSelect = 'auto';
    });

})();