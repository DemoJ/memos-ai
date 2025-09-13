// ==UserScript==
// @name         Memos AI Assistant Floater
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  Adds a floating AI assistant window to Memos.
// @author       Roo
// @match        http://10.8.8.14:5230/*
// @grant        GM_addStyle
// ==/UserScript==

(function() {
    'use strict';

    // Stop the script from running in iframes
    if (window.self !== window.top) {
        return;
    }

    // --- Configuration ---
    const assistantUrl = "http://10.8.8.14:9877"; // Your AI Assistant URL
    const iconUrl = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxZW0iIGhlaWdodD0iMWVtIiB2aWV3Qm94PSIwIDAgMjQgMjQiPjxwYXRoIGZpbGw9Im5vbmUiIHN0cm9rZT0iIzg4OCIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIiBzdHJva2Utd2lkdGg9IjIiIGQ9Ik0xMiAzTDkuNSA4LjVMNCAxMWw1LjUgMi41TDEyIDE5bDIuNS01LjVMMjAgMTFsLTUuNS0yLjV6Ii8+PC9zdmc+"; // A simple AI icon

    // --- Create Floating Icon ---
    const floatIcon = document.createElement('div');
    floatIcon.id = 'ai-assistant-icon';
    floatIcon.innerHTML = `<img src="${iconUrl}" style="width: 28px; height: 28px;">`;
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
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 50%;
            display: flex;
            justify-content: center;
            align-items: center;
            cursor: pointer;
            z-index: 9998;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1);
            transition: background-color 0.3s, box-shadow 0.3s;
        }
        #ai-assistant-icon:hover {
            background-color: #f5f5f5;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        #ai-assistant-window {
            position: fixed;
            bottom: 90px;
            right: 30px;
            width: 600px;
            height: 700px;
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