#!/usr/bin/env python3
"""
Multi-Tab Claude Voice Assistant - Exact Replica
Built from scratch based on precise UI specifications
"""
from flask import Flask, render_template_string, request, jsonify, Response
from flask_socketio import SocketIO, emit
import ssl
import os
import threading
import time
import sys
from orchestrator_simple_v2 import orchestrator

# Force unbuffered output
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__

app = Flask(__name__)
app.config['SECRET_KEY'] = 'exact-replica-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Multi-Tab Claude Voice Assistant</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, "Segoe UI", Arial, sans-serif;
            background-color: rgb(0, 0, 0);
            color: rgb(0, 255, 0);
            font-size: 16px;
            font-weight: 400;
            text-align: start;
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        /* Tab Bar */
        #tabBar.tab-bar {
            display: flex;
            position: fixed;
            flex-direction: row;
            justify-content: normal;
            align-items: center;
            width: 100%;
            height: 45px;
            min-height: 45px;
            top: 0px;
            left: 0px;
            right: 0px;
            margin: 0px;
            padding: 0px 10px;
            border: none;
            border-radius: 0px;
            background-color: rgb(17, 17, 17);
            color: rgb(0, 255, 0);
            z-index: 1000;
            overflow-x: auto;
            overflow-y: auto;
            gap: normal;
        }
        
        /* Individual Tab */
        .tab {
            display: flex;
            position: relative;
            flex-direction: row;
            justify-content: normal;
            align-items: center;
            height: 35px;
            margin: 0px 5px 0px 0px;
            padding: 8px 16px;
            border: 1.25px solid rgb(0, 255, 0);
            border-radius: 0px;
            background-color: rgb(34, 34, 34);
            color: rgb(0, 255, 0);
            font-size: 14px;
            font-weight: 400;
            text-align: start;
            cursor: pointer;
            gap: 8px;
            transition-property: all;
            transition-duration: 0.3s;
            transition-timing-function: ease;
            transition-delay: 0s;
        }
        
        /* Active Tab */
        .tab.active {
            background-color: rgba(0, 255, 0, 0.2);
            color: rgb(0, 255, 0);
            font-weight: 700;
            border-color: rgb(0, 255, 0);
            box-shadow: 0 0 20px rgba(0, 255, 0, 0.5), inset 0 0 10px rgba(0, 255, 0, 0.2);
            position: relative;
        }
        
        .tab.active::after {
            content: '';
            position: absolute;
            bottom: -2px;
            left: 0;
            right: 0;
            height: 2px;
            background-color: rgb(17, 17, 17);
        }
        
        /* Unread message indicator - yellow highlight */
        .tab.has-unread {
            background-color: rgba(255, 255, 0, 0.2) !important;
            border-color: rgb(255, 255, 0) !important;
            animation: yellowPulse 1.5s ease-in-out infinite;
        }
        
        .tab.has-unread .tab-name {
            color: rgb(255, 255, 0);
        }
        
        @keyframes yellowPulse {
            0% { 
                box-shadow: 0 0 5px rgba(255, 255, 0, 0.5);
            }
            50% { 
                box-shadow: 0 0 20px rgba(255, 255, 0, 0.8), inset 0 0 10px rgba(255, 255, 0, 0.3);
            }
            100% { 
                box-shadow: 0 0 5px rgba(255, 255, 0, 0.5);
            }
        }
        
        /* Tab Name */
        .tab-name {
            display: block;
            position: static;
        }
        
        /* Tab Rename Input (Hidden) */
        .tab-rename-input {
            display: none;
            width: 100px;
            padding: 4px 8px;
            background-color: rgb(0, 0, 0);
            border: 1.25px solid rgb(0, 255, 0);
            color: rgb(0, 255, 0);
            font-size: 14px;
        }
        
        /* Add Tab Button (Hidden by default) */
        .add-tab {
            display: none;
            position: static;
            flex-direction: row;
            justify-content: center;
            align-items: center;
            min-width: 40px;
            margin: 0px;
            padding: 8px 16px;
            border: 1.25px dashed rgb(0, 255, 0);
            border-radius: 0px;
            background-color: rgba(0, 0, 0, 0);
            color: rgb(0, 255, 0);
            font-size: 20px;
            font-weight: 400;
            cursor: pointer;
        }
        
        /* Debug Box */
        #debugBox {
            display: block;
            position: fixed;
            width: 613.457px;
            height: 82.5px;
            bottom: 10px;
            left: 10px;
            margin: 0px;
            padding: 10px;
            border: 1.25px solid rgb(0, 255, 0);
            border-radius: 0px;
            background-color: rgb(17, 17, 17);
            color: rgb(0, 255, 0);
            font-size: 12px;
            font-weight: 400;
            z-index: 9999;
            overflow: visible;
        }
        
        /* Container */
        .container {
            display: flex;
            position: relative;
            flex-direction: row;
            justify-content: center;
            align-items: center;
            width: 100%;
            height: 100%;
            margin: 0px;
            padding: 65px 20px 20px;
            border: 0px none;
            border-radius: 0px;
            background-color: rgba(0, 0, 0, 0);
            color: rgb(0, 255, 0);
            overflow-x: hidden;
            overflow-y: hidden;
        }
        
        /* Main Card */
        .main-card {
            display: flex;
            position: relative;
            flex-direction: column;
            justify-content: normal;
            align-items: normal;
            width: 600px;
            height: 860.625px;
            max-width: 600px;
            max-height: 860.625px;
            margin: 0px;
            padding: 40px;
            border: 1.25px solid rgb(0, 255, 0);
            border-radius: 20px;
            background-color: rgba(0, 10, 0, 0.9);
            color: rgb(0, 255, 0);
            overflow-x: hidden;
            overflow-y: hidden;
        }
        
        /* Connection Indicator */
        .connection-indicator {
            display: flex;
            position: absolute;
            flex-direction: row;
            justify-content: normal;
            align-items: center;
            width: 81.8164px;
            height: 18.75px;
            top: 10px;
            right: 10px;
            margin: 0px;
            padding: 0px;
            border: 0px none;
            background-color: rgba(0, 0, 0, 0);
            color: rgb(0, 255, 0);
            font-size: 14px;
            gap: 5px;
        }
        
        /* Connection Dot */
        .connection-dot {
            display: block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background-color: rgb(255, 0, 0);
        }
        
        .connection-dot.connected {
            background-color: rgb(0, 255, 0);
        }
        
        /* Tab Count */
        #tabCount.tab-count {
            display: block;
            position: absolute;
            width: 77.0117px;
            height: 18.75px;
            top: 10px;
            left: 10px;
            margin: 0px;
            padding: 0px;
            border: 0px none;
            background-color: rgba(0, 0, 0, 0);
            color: rgb(0, 170, 0);
            font-size: 14px;
        }
        
        /* H1 Title */
        h1 {
            display: block;
            position: static;
            width: 517.5px;
            height: 47.5px;
            margin: 0px 0px 10px;
            padding: 0px;
            border: 0px none;
            background-color: rgba(0, 0, 0, 0);
            color: rgb(0, 255, 0);
            font-size: 36px;
            font-weight: 700;
            text-align: center;
        }
        
        /* Subtitle */
        #subtitle.subtitle {
            display: block;
            position: static;
            width: 517.5px;
            height: 25px;
            margin: 0px 0px 30px;
            padding: 0px;
            border: 0px none;
            background-color: rgba(0, 0, 0, 0);
            color: rgb(0, 170, 0);
            font-size: 18px;
            font-weight: 400;
            text-align: center;
        }
        
        /* Mic Container */
        .mic-container {
            display: flex;
            position: static;
            flex-direction: row;
            justify-content: center;
            align-items: normal;
            width: 517.5px;
            height: 120px;
            margin: 20px 0px;
            padding: 0px;
            border: 0px none;
            background-color: rgba(0, 0, 0, 0);
            color: rgb(0, 255, 0);
        }
        
        /* Mic Button */
        #micButton.mic-button {
            display: flex;
            position: relative;
            flex-direction: row;
            justify-content: center;
            align-items: center;
            width: 120px;
            height: 120px;
            margin: 0px;
            padding: 0px;
            border: 2.5px solid rgb(0, 255, 0);
            border-radius: 50%;
            background-color: rgba(0, 0, 0, 0);
            color: rgb(0, 0, 0);
            font-size: 50px;
            cursor: pointer;
            box-shadow: rgba(0, 255, 0, 0.5) 0px 0px 30px 0px;
            transition-property: all;
            transition-duration: 0.3s;
            transition-timing-function: ease;
        }
        
        /* Mic Button Recording State */
        #micButton.recording {
            background: #f00;
            border-color: #f00;
            box-shadow: 0 0 50px rgba(255, 0, 0, 0.8);
            animation: pulse 1s infinite;
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        
        /* Status */
        #status.status {
            display: block;
            position: static;
            width: 517.5px;
            height: 23.9844px;
            min-height: 24px;
            margin: 20px 0px;
            padding: 0px;
            border: 0px none;
            background-color: rgba(0, 0, 0, 0);
            color: rgb(0, 170, 0);
            font-size: 16px;
            text-align: center;
        }
        
        /* Text Input Container */
        .text-input-container {
            display: flex;
            gap: 10px;
            margin-top: 15px;
            width: 517.5px;
        }
        
        /* Text Input */
        .text-input {
            flex: 1;
            padding: 10px;
            background: #111;
            border: 2px solid #0f0;
            color: #0f0;
            border-radius: 5px;
            font-size: 14px;
            font-family: 'Courier New', monospace;
            outline: none;
            transition: all 0.3s;
        }
        
        .text-input:focus {
            box-shadow: 0 0 15px rgba(0, 255, 0, 0.5);
        }
        
        .text-input::placeholder {
            color: #666;
        }
        
        /* Send Button */
        .send-button {
            padding: 10px 20px;
            background: #0f0;
            color: #000;
            border: 2px solid #0f0;
            border-radius: 5px;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: bold;
        }
        
        .send-button:hover {
            background: #000;
            color: #0f0;
        }
        
        /* Controls Row */
        .controls-row {
            display: flex;
            position: static;
            flex-direction: row;
            justify-content: normal;
            align-items: center;
            width: 517.5px;
            height: 50px;
            margin: 20px 0px 0px;
            padding: 0px;
            border: 0px none;
            background-color: rgba(0, 0, 0, 0);
            color: rgb(0, 255, 0);
            gap: 10px;
        }
        
        /* Voice Select */
        #voiceSelect.voice-select {
            width: 387.5px;
            padding: 12px;
            background-color: rgb(17, 17, 17);
            border: 1.25px solid rgb(0, 255, 0);
            border-radius: 10px;
            color: rgb(0, 255, 0);
            font-size: 16px;
            cursor: pointer;
        }
        
        /* Mute Button */
        #muteButton.mute-button {
            display: flex;
            position: static;
            flex-direction: row;
            justify-content: center;
            align-items: center;
            width: 50px;
            height: 50px;
            margin: 0px;
            padding: 0px;
            border: 1.25px solid rgb(0, 255, 0);
            border-radius: 50%;
            background-color: rgb(17, 17, 17);
            color: rgb(0, 255, 0);
            font-size: 24px;
            cursor: pointer;
            transition-property: all;
            transition-duration: 0.3s;
        }
        
        /* Bell Button */
        #bellButton.bell-button {
            display: flex;
            position: static;
            flex-direction: row;
            justify-content: center;
            align-items: center;
            width: 50px;
            height: 50px;
            margin-left: 10px;
            padding: 0px;
            border: 1.25px solid rgb(0, 255, 0);
            border-radius: 50%;
            background-color: rgba(0, 0, 0, 0.7);
            color: rgb(0, 255, 0);
            font-size: 20px;
            cursor: pointer;
            transition-property: all;
            transition-duration: 0.3s;
        }
        
        /* Settings Button */
        #settingsButton.settings-button {
            display: flex;
            position: static;
            flex-direction: row;
            justify-content: center;
            align-items: center;
            width: 50px;
            height: 50px;
            margin-left: 10px;
            padding: 0px;
            border: 1.25px solid rgb(0, 255, 0);
            border-radius: 50%;
            background-color: rgba(0, 0, 0, 0.7);
            color: rgb(0, 255, 0);
            font-size: 20px;
            cursor: pointer;
            transition-property: all;
            transition-duration: 0.3s;
        }
        
        #settingsButton:hover {
            background-color: rgb(0, 255, 0);
            color: rgb(0, 0, 0);
        }
        
        /* Save Button */
        #saveButton.save-button {
            display: flex;
            position: static;
            flex-direction: row;
            justify-content: center;
            align-items: center;
            width: 50px;
            height: 50px;
            margin-left: 10px;
            padding: 0px;
            border: 1.25px solid rgb(0, 255, 0);
            border-radius: 50%;
            background-color: rgba(0, 0, 0, 0.7);
            color: rgb(0, 255, 0);
            font-size: 20px;
            cursor: pointer;
            transition-property: all;
            transition-duration: 0.3s;
        }
        
        #saveButton:hover {
            background-color: rgb(0, 255, 0);
            color: rgb(0, 0, 0);
        }
        
        #saveButton.active {
            background-color: rgb(0, 255, 0);
            color: rgb(0, 0, 0);
            box-shadow: 0 0 20px rgba(0, 255, 0, 0.8);
        }
        
        /* Conversation Log */
        #conversationLog.conversation-log {
            display: block;
            position: static;
            width: 517.5px;
            height: 250px;
            min-height: 250px;
            max-height: 250px;
            margin: 15px 0px 0px;
            padding: 15px;
            border: 1.25px solid rgb(0, 255, 0);
            border-radius: 10px;
            background-color: rgb(17, 17, 17);
            color: rgb(0, 255, 0);
            font-size: 16px;
            text-align: start;
            overflow-x: auto;
            overflow-y: auto;
        }
        
        /* Message Styles */
        .message {
            margin-bottom: 10px;
            padding: 8px 12px;
            border-radius: 5px;
        }
        
        .message.user-message {
            background-color: rgba(0, 255, 0, 0.1);
            border-left: 2.5px solid rgb(0, 255, 0);
        }
        
        .message.bot-message {
            background-color: rgba(0, 150, 255, 0.1);
            border-left: 2.5px solid rgb(0, 150, 255);
            color: rgb(0, 200, 255);
        }
        
        .bot-message .timestamp {
            color: rgba(0, 150, 255, 0.6);
        }
        
        /* Timestamp */
        .timestamp {
            display: inline;
            margin-right: 10px;
            color: rgb(102, 102, 102);
            font-size: 12px;
        }
        
        /* Token Usage Box */
        #tokenUsageBox.token-usage-box {
            display: block;
            position: static;
            width: 517.333px;
            max-width: 100%;
            height: 92.6667px;
            margin: 15px 0px 0px;
            padding: 15px;
            border: 1.33333px solid rgb(0, 255, 0);
            border-radius: 8px;
            background-color: rgb(17, 17, 17);
            color: rgb(0, 255, 0);
            text-shadow: rgba(0, 255, 0, 0.84) 0px 0px 21.9524px, rgba(0, 255, 0, 0.157) 0px 0px 7.80969px;
            box-sizing: border-box;
        }
        
        /* Token Header */
        .token-header {
            display: block;
            position: static;
            width: 485px;
            max-width: 100%;
            height: 21.25px;
            margin: 0px 0px 10px;
            font-size: 16px;
            font-weight: 700;
            text-align: center;
            background-color: rgba(0, 0, 0, 0);
        }
        
        /* Token Content */
        .token-content {
            display: grid;
            position: static;
            width: 484.667px;
            max-width: 100%;
            height: 28.6667px;
            margin: 0px;
            padding: 0px;
            background-color: rgba(0, 0, 0, 0);
            gap: 10px;
            grid-template-columns: 1fr 1fr;
        }
        
        /* Token Item */
        .token-item {
            display: flex;
            position: static;
            flex-direction: row;
            justify-content: space-between;
            align-items: center;
            height: 28.6667px;
            margin: 0px;
            padding: 5px;
            background-color: rgb(10, 10, 10);
            border-radius: 4px;
            box-sizing: border-box;
        }
        
        /* Token Label */
        .token-label {
            display: block;
            position: static;
            margin: 0px;
            padding: 0px;
            margin-right: 10px;
            color: rgb(153, 153, 153);
            font-size: 14px;
            font-weight: 400;
            background-color: rgba(0, 0, 0, 0);
        }
        
        /* Token Value */
        .token-value {
            display: block;
            position: static;
            margin: 0px;
            padding: 0px;
            color: rgb(0, 255, 0);
            font-size: 14px;
            font-weight: 700;
            background-color: rgba(0, 0, 0, 0);
        }
        
        /* Info */
        .info {
            display: block;
            position: static;
            width: 517.5px;
            height: 45px;
            margin: 20px 0px 0px;
            padding: 0px;
            border: 0px none;
            background-color: rgba(0, 0, 0, 0);
            color: rgb(0, 170, 0);
            font-size: 14px;
            text-align: center;
        }
        
        /* Version */
        .version {
            position: absolute;
            bottom: 10px;
            right: 10px;
            color: rgb(68, 68, 68);
            font-size: 12px;
            opacity: 0.7;
        }
        
        /* Modal */
        #newTabModal.modal {
            display: none;
            position: fixed;
            flex-direction: row;
            justify-content: center;
            align-items: center;
            width: 100%;
            height: 100%;
            top: 0px;
            left: 0px;
            margin: 0px;
            padding: 0px;
            border: 0px none;
            border-radius: 0px;
            background-color: rgba(0, 0, 0, 0.9);
            color: rgb(0, 255, 0);
            z-index: 1000;
            overflow: visible;
        }
        
        /* Modal Content */
        .modal-content {
            display: block;
            position: relative;
            min-width: 400px;
            margin: 0px;
            padding: 30px;
            border: 1.25px solid rgb(0, 255, 0);
            border-radius: 10px;
            background-color: rgb(17, 17, 17);
            color: rgb(0, 255, 0);
        }
        
        /* Modal Close Button */
        .modal-close {
            display: flex;
            position: absolute;
            flex-direction: row;
            justify-content: center;
            align-items: center;
            width: 30px;
            height: 30px;
            top: 10px;
            right: 10px;
            margin: 0px;
            padding: 10px 20px;
            border: 0px none;
            border-radius: 5px;
            background-color: rgb(0, 255, 0);
            color: rgb(0, 0, 0);
            font-size: 28px;
            font-weight: 700;
            text-align: center;
            cursor: pointer;
        }
        
        /* Modal H3 */
        .modal-content h3 {
            display: block;
            position: static;
            margin: 0px 0px 20px;
            padding: 0px;
            border: 0px none;
            background-color: rgba(0, 0, 0, 0);
            color: rgb(0, 255, 0);
            font-size: 18.72px;
            font-weight: 700;
            text-align: start;
        }
        
        /* Project Name Input */
        #projectName {
            display: inline-block;
            position: static;
            width: 100%;
            margin: 0px 0px 20px;
            padding: 12px;
            border: 1.25px solid rgb(0, 255, 0);
            border-radius: 5px;
            background-color: rgb(0, 0, 0);
            color: rgb(0, 255, 0);
            font-size: 16px;
            font-weight: 400;
            text-align: start;
            overflow-x: clip;
            overflow-y: clip;
        }
        
        /* Modal Buttons Container */
        .modal-buttons {
            display: flex;
            position: static;
            flex-direction: row;
            justify-content: flex-end;
            align-items: normal;
            margin: 0px;
            padding: 0px;
            border: 0px none;
            background-color: rgba(0, 0, 0, 0);
            gap: 10px;
        }
        
        /* Modal Buttons */
        .modal-buttons button {
            padding: 10px 20px;
            border: 1.25px solid rgb(0, 255, 0);
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .modal-buttons button.cancel {
            background-color: rgb(51, 51, 51);
            color: rgb(0, 255, 0);
        }
        
        .modal-buttons button:not(.cancel) {
            background-color: rgb(0, 255, 0);
            color: rgb(0, 0, 0);
        }
        
    </style>
</head>
<body>
    <!-- Tab Bar -->
    <div id="tabBar" class="tab-bar">
        <div class="tab active" id="tab_1">
            <span class="tab-name">Tab 1</span>
            <input type="text" class="tab-rename-input" value="Tab 1">
        </div>
        <div class="tab" id="tab_2">
            <span class="tab-name">Tab 2</span>
            <input type="text" class="tab-rename-input" value="Tab 2">
        </div>
        <div class="tab" id="tab_3">
            <span class="tab-name">Tab 3</span>
            <input type="text" class="tab-rename-input" value="Tab 3">
        </div>
        <div class="tab" id="tab_4">
            <span class="tab-name">Tab 4</span>
            <input type="text" class="tab-rename-input" value="Tab 4">
        </div>
        <div class="add-tab">+</div>
    </div>
    
    <!-- Debug Box -->
    <div id="debugBox">
        <button onclick="document.getElementById('debugBox').style.display='none'" 
                style="position: absolute; top: 2px; right: 2px; background: transparent; 
                       border: none; color: #0f0; font-size: 16px; cursor: pointer;">×</button>
        <div>Tab Bar Children: <span id="debugTabCount">4</span></div>
        <div>Tabs Object: <span id="debugTabsObject">{}</span></div>
        <button onclick="testAddTab()" style="margin-top: 5px; background: #0f0; 
                color: #000; border: none; padding: 5px 10px; cursor: pointer;">Test Add Tab</button>
    </div>
    
    <!-- Main Container -->
    <div class="container">
        <div class="main-card">
            <!-- Connection Indicator -->
            <div class="connection-indicator">
                <div id="connectionDot" class="connection-dot connected"></div>
                <span id="connectionStatus" class=""></span>
            </div>
            
            <!-- Tab Count -->
            <div id="tabCount" class="tab-count">Tabs: 4/4</div>
            
            <!-- Title -->
            <h1>Claude Voice Assistant</h1>
            
            <!-- Subtitle -->
            <div id="subtitle" class="subtitle">Multi-session voice interface</div>
            
            <!-- Mic Container -->
            <div class="mic-container">
                <button id="micButton" class="mic-button" onclick="toggleRecording()">🎤</button>
            </div>
            
            <!-- Status -->
            <div id="status" class="status">Ready</div>
            
            <!-- Text Input -->
            <div class="text-input-container">
                <input type="text" 
                       class="text-input" 
                       id="textInput" 
                       placeholder="Type your message here..." 
                       onkeypress="handleTextInputKeyPress(event)">
                <button class="send-button" 
                        id="sendButton" 
                        onclick="sendTextMessage()">
                    Send
                </button>
            </div>
            
            <!-- Controls Row -->
            <div class="controls-row">
                <select id="voiceSelect" class="voice-select">
                    <option value="en-US-AriaNeural">Aria (Female, US)</option>
                    <option value="en-US-JennyNeural">Jenny (Female, US)</option>
                    <option value="en-US-GuyNeural">Guy (Male, US)</option>
                    <option value="en-US-DavisNeural">Davis (Male, US)</option>
                    <option value="en-GB-SoniaNeural">Sonia (Female, UK)</option>
                    <option value="en-GB-RyanNeural">Ryan (Male, UK)</option>
                    <option value="en-AU-NatashaNeural">Natasha (Female, AU)</option>
                    <option value="en-AU-WilliamNeural">William (Male, AU)</option>
                    <option value="en-US-AmberNeural">Amber (Female, US)</option>
                    <option value="en-US-AshleyNeural">Ashley (Female, US)</option>
                    <option value="en-US-BrandonNeural">Brandon (Male, US)</option>
                    <option value="en-US-ChristopherNeural">Christopher (Male, US)</option>
                    <option value="en-US-CoraNeural">Cora (Female, US)</option>
                </select>
                <button id="muteButton" class="mute-button" onclick="toggleMute()">🔊</button>
                <button id="bellButton" class="bell-button" onclick="toggleBell()">🔔</button>
                <button id="settingsButton" class="settings-button" onclick="toggleSettings()">⚙️</button>
                <button id="saveButton" class="save-button" onclick="toggleSave()">💾</button>
            </div>
            
            <!-- Conversation Log -->
            <div id="conversationLog" class="conversation-log"></div>
            
            <!-- Token Usage Box -->
            <div id="tokenUsageBox" class="token-usage-box">
                <div class="token-header">📊 Stats</div>
                <div class="token-content">
                    <div class="token-item">
                        <span class="token-label">Time:</span>
                        <span class="token-value" id="realtimeTime">-</span>
                    </div>
                    <div class="token-item">
                        <span class="token-label">Tokens:</span>
                        <span class="token-value" id="realtimeTokens">-</span>
                    </div>
                </div>
            </div>
            
            <!-- Info -->
            <div class="info">
                Multi-tab support • Up to 4 simultaneous sessions • Real-time voice interaction
            </div>
            
            <!-- Unnamed div (spacer) -->
            <div style="display: block; width: 517.5px; height: 33.4766px; margin: 20px 0px 0px;"></div>
        </div>
    </div>
    
    <!-- New Tab Modal -->
    <div id="newTabModal" class="modal">
        <div class="modal-content">
            <button class="modal-close">×</button>
            <h3>Create New Tab</h3>
            <input type="text" id="projectName" placeholder="Enter project name...">
            <div class="modal-buttons">
                <button class="cancel">Cancel</button>
                <button>Create</button>
            </div>
        </div>
    </div>
    
    <!-- Settings Modal -->
    <div id="settingsModal" class="modal">
        <div class="modal-content">
            <button class="modal-close" onclick="closeSettings()">×</button>
            <h3>Settings</h3>
            
            <div class="settings-section">
                <h4>Notification Sound</h4>
                <label style="display: block; margin: 10px 0;">
                    <input type="radio" name="notifSound" value="chime" checked id="chimeOption">
                    Default Chime
                </label>
                <label style="display: block; margin: 10px 0;">
                    <input type="radio" name="notifSound" value="voice" id="voiceOption">
                    Voice Announcement (Tab Name)
                </label>
            </div>
            
            <div class="settings-section" id="chimeSettings" style="margin-top: 20px;">
                <h4>Chime Sound</h4>
                <select id="chimeSelect" onchange="updateChimeSound()" style="width: 100%; padding: 8px; margin: 10px 0;">
                    <option value="default">Default</option>
                    <option value="bell">Bell</option>
                    <option value="ding">Ding</option>
                    <option value="soft">Soft Chime</option>
                </select>
                <button onclick="testChime()" style="padding: 8px 16px;">Test Sound</button>
            </div>
            
            <div class="modal-buttons" style="margin-top: 20px;">
                <button class="cancel" onclick="closeSettings()">Cancel</button>
                <button onclick="saveSettings()">Save Settings</button>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <script>
        // Initialize Socket.IO
        const socket = io();
        
        // Global variables
        let activeTabId = 'tab_1';
        let recordingTabId = null; // Track which tab started recording
        let isRecording = false;
        let isMuted = false;
        let bellEnabled = true;
        let saveEnabled = false; // Track save state
        let notificationMode = 'chime'; // 'chime' or 'voice'
        let chimeSound = 'default';
        let recognition = null;
        let currentAudio = null;
        let audioContext = null;
        
        // Store conversations for each tab
        const tabConversations = {
            'tab_1': [],
            'tab_2': [],
            'tab_3': [],
            'tab_4': []
        };
        
        // Tab Management
        const tabs = document.querySelectorAll('.tab');
        tabs.forEach(tab => {
            // Click to switch tabs
            tab.addEventListener('click', function() {
                switchTab(this.id);
            });
            
            // Double-click to rename
            tab.addEventListener('dblclick', function(e) {
                e.stopPropagation();
                const span = this.querySelector('span');
                const currentText = span.textContent;
                
                // Create input field
                const input = document.createElement('input');
                input.type = 'text';
                input.value = currentText;
                input.style.background = 'transparent';
                input.style.border = '1px solid rgb(0, 255, 0)';
                input.style.color = 'inherit';
                input.style.fontSize = 'inherit';
                input.style.fontFamily = 'inherit';
                input.style.width = '100%';
                input.style.textAlign = 'center';
                input.style.padding = '2px';
                
                // Replace span with input
                span.style.display = 'none';
                this.appendChild(input);
                input.focus();
                input.select();
                
                // Save on blur or enter
                const saveText = () => {
                    const newText = input.value.trim() || currentText;
                    span.textContent = newText;
                    span.style.display = '';
                    input.remove();
                };
                
                input.addEventListener('blur', saveText);
                input.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        saveText();
                    }
                });
            });
        });
        
        function switchTab(tabId) {
            // If recording is active and we have a transcript, send it to the recording tab
            if (isRecording && finalTranscript.trim() && recordingTabId !== tabId) {
                // Send the current transcript to the tab that started recording
                sendCommand(finalTranscript.trim(), recordingTabId);
                finalTranscript = '';
                // Stop recording
                stopRecording();
            }
            
            // Remove active class from all tabs
            tabs.forEach(t => t.classList.remove('active'));
            // Add active class to clicked tab
            const activeTab = document.getElementById(tabId);
            activeTab.classList.add('active');
            // Clear unread indicator
            activeTab.classList.remove('has-unread');
            activeTabId = tabId;
            
            // Clear status if switching away from recording tab
            if (recordingTabId && recordingTabId !== tabId) {
                document.getElementById('status').textContent = 'Ready';
            }
            
            // Display conversation for this tab
            displayConversation();
            
            
            // Emit tab switch event
            socket.emit('switch_tab', { tab_id: activeTabId });
        }
        
        // Initialize speech recognition
        let silenceTimer = null;
        let finalTranscript = '';
        
        if ('webkitSpeechRecognition' in window) {
            recognition = new webkitSpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = 'en-US';
            
            recognition.onresult = (event) => {
                // Clear any existing silence timer
                if (silenceTimer) {
                    clearTimeout(silenceTimer);
                }
                
                // Process results
                let interimTranscript = '';
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const transcript = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        finalTranscript += transcript + ' ';
                    } else {
                        interimTranscript = transcript;
                    }
                }
                
                // Update status with current speech only if on recording tab
                if (interimTranscript && activeTabId === recordingTabId) {
                    document.getElementById('status').textContent = 'Listening: ' + interimTranscript;
                }
                
                // Start silence timer - stop after 2 seconds of silence
                silenceTimer = setTimeout(() => {
                    if (finalTranscript.trim()) {
                        sendCommand(finalTranscript.trim(), recordingTabId);
                        finalTranscript = '';
                    }
                    stopRecording();
                }, 2000);
            };
            
            recognition.onend = () => {
                // Recognition ended
                stopRecording();
            };
            
            recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                stopRecording();
            };
        }
        
        // Button Functions
        function toggleRecording() {
            if (isRecording) {
                stopRecording();
            } else {
                startRecording();
            }
        }
        
        function startRecording() {
            if (!recognition) {
                alert('Speech recognition not supported in this browser');
                return;
            }
            
            isRecording = true;
            recordingTabId = activeTabId;  // Remember which tab started recording
            finalTranscript = '';  // Reset transcript
            document.getElementById('micButton').classList.add('recording');
            document.getElementById('status').textContent = 'Listening...';
            recognition.start();
        }
        
        function stopRecording() {
            isRecording = false;
            recordingTabId = null;  // Clear the recording tab
            document.getElementById('micButton').classList.remove('recording');
            document.getElementById('status').textContent = 'Ready';
            if (recognition) {
                recognition.stop();
            }
        }
        
        function toggleMute() {
            isMuted = !isMuted;
            const button = document.getElementById('muteButton');
            button.textContent = isMuted ? '🔇' : '🔊';
            // Update button appearance if needed
            if (isMuted) {
                button.style.backgroundColor = 'rgba(255, 0, 0, 0.2)';
            } else {
                button.style.backgroundColor = 'rgb(17, 17, 17)';
            }
        }
        
        function toggleBell() {
            bellEnabled = !bellEnabled;
            const button = document.getElementById('bellButton');
            button.textContent = bellEnabled ? '🔔' : '🔕';
            // Save preference
            localStorage.setItem('bellEnabled', bellEnabled);
        }
        
        async function toggleSave() {
            saveEnabled = !saveEnabled;
            const button = document.getElementById('saveButton');
            
            if (saveEnabled) {
                button.classList.add('active');
                // Save current state immediately
                saveAllSessions();
            } else {
                button.classList.remove('active');
                // Clear saved sessions when disabling
                try {
                    await fetch('/clear_sessions', {
                        method: 'POST'
                    });
                } catch (error) {
                    console.error('Error clearing sessions:', error);
                }
            }
            
            // Save preference
            localStorage.setItem('saveEnabled', saveEnabled);
        }
        
        // Text Input Functions
        function sendTextMessage() {
            const input = document.getElementById('textInput');
            const text = input.value.trim();
            
            if (!text || !activeTabId) return;
            
            sendCommand(text);
            input.value = '';
            input.focus();
        }
        
        function handleTextInputKeyPress(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendTextMessage();
            }
        }
        
        // Send command to server
        function sendCommand(text, targetTabId = null) {
            const tabId = targetTabId || activeTabId;
            if (!text || !tabId) return;
            
            // Add message to conversation log for the target tab
            const originalActiveTab = activeTabId;
            if (targetTabId && targetTabId !== activeTabId) {
                // Temporarily switch context to add message to correct tab
                activeTabId = targetTabId;
            }
            addMessage('user', text);
            activeTabId = originalActiveTab;
            
            // Send to server
            fetch('/send_command', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    command: text,
                    tab_id: tabId.replace('-', '_')  // Ensure underscore format
                })
            });
        }
        
        // Add message to conversation log
        function addMessage(type, text) {
            // Store message in current tab's conversation
            tabConversations[activeTabId].push({
                type: type,
                text: text,
                timestamp: new Date().toLocaleTimeString()
            });
            
            // Only display if this is the active tab
            displayConversation();
        }
        
        function displayConversation() {
            const log = document.getElementById('conversationLog');
            log.innerHTML = '';
            
            // Display messages for active tab
            tabConversations[activeTabId].forEach(msg => {
                const message = document.createElement('div');
                message.className = `message ${msg.type}-message`;
                
                const timestamp = document.createElement('span');
                timestamp.className = 'timestamp';
                timestamp.textContent = msg.timestamp;
                
                const prefix = msg.type === 'bot' ? '🤖 ' : '👤 ';
                
                message.appendChild(timestamp);
                message.appendChild(document.createTextNode(prefix + msg.text));
                
                log.appendChild(message);
            });
            
            log.scrollTop = log.scrollHeight;
        }
        
        // Socket.IO Event Handlers
        socket.on('connect', () => {
            document.getElementById('connectionDot').classList.add('connected');
            document.getElementById('connectionStatus').textContent = 'Connected';
        });
        
        socket.on('disconnect', () => {
            document.getElementById('connectionDot').classList.remove('connected');
            document.getElementById('connectionStatus').textContent = 'Disconnected';
        });
        
        socket.on('response', (data) => {
            console.log('[SOCKET] Received response:', data);
            // Fix tab_id comparison - ensure both use underscores
            const normalizedTabId = data.tab_id.replace('-', '_');
            const normalizedActiveTab = activeTabId.replace('-', '_');
            
            if (data.text) {
                // Store message in the appropriate tab's conversation
                const targetTabId = normalizedTabId.replace('_', '_'); // Already normalized
                if (tabConversations[targetTabId]) {
                    tabConversations[targetTabId].push({
                        type: 'bot',
                        text: data.text,
                        timestamp: new Date().toLocaleTimeString()
                    });
                }
                
                // Always play chime for any tab response if bell is enabled
                if (bellEnabled) {
                    playChime(data.tab_id);
                }
                
                // If this is the active tab, update display and speak
                if (normalizedTabId === normalizedActiveTab) {
                    displayConversation();
                    // Speak the response using TTS
                    speakText(data.text);
                } else {
                    // Visual indicator for unread messages on other tabs
                    const tab = document.getElementById(targetTabId);
                    if (tab && !tab.classList.contains('has-unread')) {
                        tab.classList.add('has-unread');
                    }
                }
                
                // Auto-save if enabled
                if (saveEnabled) {
                    saveAllSessions();
                }
            }
        });
        
        // Format tokens with k notation for large numbers
        function formatTokens(tokens) {
            if (tokens === 0 || !tokens) return '0';
            if (tokens < 1000) return tokens.toString();
            
            const k = tokens / 1000;
            if (k < 10) {
                // Show one decimal place for < 10k
                return k.toFixed(1) + 'k';
            } else {
                // No decimal places for >= 10k
                return Math.floor(k) + 'k';
            }
        }
        
        // Format duration in mm:ss or hh:mm:ss
        function formatDuration(seconds) {
            if (!seconds || seconds === 0) return '0:00';
            
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            const secs = Math.floor(seconds % 60);
            
            if (hours > 0) {
                return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
            } else {
                return `${minutes}:${secs.toString().padStart(2, '0')}`;
            }
        }
        
        socket.on('realtime_stats', (data) => {
            console.log('Received realtime_stats:', data);
            if (data.tab_id === activeTabId) {
                // Update time with proper formatting
                const timeElement = document.getElementById('realtimeTime');
                if (timeElement && data.duration !== undefined) {
                    timeElement.textContent = formatDuration(data.duration);
                    // Add processing indicator if actively processing
                    if (data.is_processing) {
                        timeElement.textContent += ' ⏳';
                    }
                } else if (timeElement) {
                    timeElement.textContent = '-';
                }
                
                // Update tokens with k notation
                const tokensElement = document.getElementById('realtimeTokens');
                if (tokensElement && data.tokens !== undefined) {
                    tokensElement.textContent = formatTokens(data.tokens);
                } else if (tokensElement) {
                    tokensElement.textContent = '-';
                }
            }
        });
        
        // Create sessions on load
        window.addEventListener('load', async () => {
            // Load bell preference
            const savedBell = localStorage.getItem('bellEnabled');
            if (savedBell !== null) {
                bellEnabled = savedBell === 'true';
                if (!bellEnabled) {
                    toggleBell();
                }
            }
            
            // Load notification settings
            const savedMode = localStorage.getItem('notificationMode');
            if (savedMode) {
                notificationMode = savedMode;
            }
            
            const savedChime = localStorage.getItem('chimeSound');
            if (savedChime) {
                chimeSound = savedChime;
            }
            
            // Check if saved sessions exist on server
            const hasSavedData = await loadSessions(true);
            
            if (hasSavedData) {
                // If saved data exists, enable save mode automatically
                saveEnabled = true;
                document.getElementById('saveButton').classList.add('active');
                // Load the saved sessions
                await loadSessions(false);
                
                // Note: Sessions will be created on-demand when first message is sent
                console.log('Saved sessions loaded - orchestrator sessions will be created on first message');
            } else {
                // Otherwise, check localStorage preference
                const savedSaveState = localStorage.getItem('saveEnabled');
                if (savedSaveState !== null) {
                    saveEnabled = savedSaveState === 'true';
                    if (saveEnabled) {
                        document.getElementById('saveButton').classList.add('active');
                    }
                }
            }
            
            // Add event listeners for settings radio buttons
            document.querySelectorAll('input[name="notifSound"]').forEach(radio => {
                radio.addEventListener('change', updateSettingsVisibility);
            });
            
            // Only create new sessions if we're not loading saved data
            if (!hasSavedData) {
                // Create sessions for all tabs
                const tabNames = ['Tab 1', 'Tab 2', 'Tab 3', 'Tab 4'];
                const tabIds = ['tab_1', 'tab_2', 'tab_3', 'tab_4'];
                
                tabIds.forEach((tabId, index) => {
                    fetch('/create_session', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            tab_id: tabId,
                            project_name: tabNames[index]
                        })
                    });
                });
            }
        });
        
        // Audio Functions
        function initAudioContext() {
            if (!audioContext) {
                audioContext = new (window.AudioContext || window.webkitAudioContext)();
            }
        }
        
        // Play notification chime using Web Audio API
        function playChime(tabId = null) {
            if (!bellEnabled) return;
            
            // If voice mode is enabled, speak the tab name instead
            if (notificationMode === 'voice' && tabId) {
                speakTabName(tabId);
                return;
            }
            
            initAudioContext();
            
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            // Configure different chime sounds
            switch(chimeSound) {
                case 'bell':
                    oscillator.type = 'sine';
                    oscillator.frequency.setValueAtTime(1200, audioContext.currentTime);
                    oscillator.frequency.exponentialRampToValueAtTime(800, audioContext.currentTime + 0.3);
                    gainNode.gain.setValueAtTime(0.4, audioContext.currentTime);
                    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
                    oscillator.start(audioContext.currentTime);
                    oscillator.stop(audioContext.currentTime + 0.3);
                    break;
                    
                case 'ding':
                    oscillator.type = 'triangle';
                    oscillator.frequency.setValueAtTime(1500, audioContext.currentTime);
                    gainNode.gain.setValueAtTime(0.5, audioContext.currentTime);
                    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);
                    oscillator.start(audioContext.currentTime);
                    oscillator.stop(audioContext.currentTime + 0.1);
                    break;
                    
                case 'soft':
                    oscillator.type = 'sine';
                    oscillator.frequency.setValueAtTime(600, audioContext.currentTime);
                    oscillator.frequency.exponentialRampToValueAtTime(400, audioContext.currentTime + 0.2);
                    gainNode.gain.setValueAtTime(0.2, audioContext.currentTime);
                    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2);
                    oscillator.start(audioContext.currentTime);
                    oscillator.stop(audioContext.currentTime + 0.2);
                    break;
                    
                default: // default
                    oscillator.type = 'sine';
                    oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
                    oscillator.frequency.exponentialRampToValueAtTime(1200, audioContext.currentTime + 0.1);
                    oscillator.frequency.exponentialRampToValueAtTime(1000, audioContext.currentTime + 0.15);
                    gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
                    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.15);
                    oscillator.start(audioContext.currentTime);
                    oscillator.stop(audioContext.currentTime + 0.15);
                    break;
            }
        }
        
        // Speak text using TTS
        async function speakText(text) {
            if (isMuted || !text) return;
            
            // Cancel any ongoing audio
            if (currentAudio) {
                currentAudio.pause();
                currentAudio = null;
            }
            
            try {
                const voice = document.getElementById('voiceSelect').value;
                const protocol = window.location.protocol;
                const ttsUrl = protocol === 'https:' 
                    ? 'https://192.168.40.232:5001/tts'
                    : 'http://192.168.40.232:5001/tts';
                
                const response = await fetch(ttsUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        text: text,
                        voice: voice,
                        rate: '+0%',
                        pitch: '+0Hz',
                        volume: '+0%'
                    })
                });
                
                if (response.ok) {
                    const blob = await response.blob();
                    const audioUrl = URL.createObjectURL(blob);
                    currentAudio = new Audio(audioUrl);
                    currentAudio.play();
                    
                    // Clean up blob URL after playback
                    currentAudio.addEventListener('ended', () => {
                        URL.revokeObjectURL(audioUrl);
                        currentAudio = null;
                    });
                }
            } catch (error) {
                console.error('TTS error:', error);
                // Fallback to browser speech synthesis
                if ('speechSynthesis' in window) {
                    const utterance = new SpeechSynthesisUtterance(text);
                    speechSynthesis.speak(utterance);
                }
            }
        }
        
        // Test function for debug box
        function testAddTab() {
            console.log('Test Add Tab clicked');
        }
        
        // Settings functions
        function toggleSettings() {
            document.getElementById('settingsModal').style.display = 'flex';
            
            // Update UI to reflect current settings
            document.getElementById('chimeOption').checked = notificationMode === 'chime';
            document.getElementById('voiceOption').checked = notificationMode === 'voice';
            document.getElementById('chimeSelect').value = chimeSound;
            
            // Show/hide chime settings based on mode
            updateSettingsVisibility();
        }
        
        function closeSettings() {
            document.getElementById('settingsModal').style.display = 'none';
        }
        
        function updateSettingsVisibility() {
            const chimeSettings = document.getElementById('chimeSettings');
            const isChimeMode = document.querySelector('input[name="notifSound"]:checked').value === 'chime';
            chimeSettings.style.display = isChimeMode ? 'block' : 'none';
        }
        
        function updateChimeSound() {
            chimeSound = document.getElementById('chimeSelect').value;
        }
        
        function testChime() {
            playChime();
        }
        
        function saveSettings() {
            // Get selected notification mode
            notificationMode = document.querySelector('input[name="notifSound"]:checked').value;
            chimeSound = document.getElementById('chimeSelect').value;
            
            // Save to localStorage
            localStorage.setItem('notificationMode', notificationMode);
            localStorage.setItem('chimeSound', chimeSound);
            
            closeSettings();
        }
        
        // Speak tab name function
        async function speakTabName(tabId) {
            if (isMuted) return;
            
            // Get tab name
            const tab = document.getElementById(tabId);
            if (!tab) return;
            
            const tabName = tab.querySelector('.tab-name').textContent;
            const voiceSelect = document.getElementById('voiceSelect');
            const selectedVoice = voiceSelect ? voiceSelect.value : 'en-US-AriaNeural';
            
            // Announce which tab received a response
            const announcement = `${tabName} responded`;
            
            try {
                const response = await fetch('/tts', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        text: announcement,
                        voice: selectedVoice
                    })
                });
                
                if (response.ok) {
                    const audioBlob = await response.blob();
                    const audioUrl = URL.createObjectURL(audioBlob);
                    
                    // Play the audio
                    const audio = new Audio(audioUrl);
                    audio.play();
                    
                    // Clean up
                    audio.addEventListener('ended', () => {
                        URL.revokeObjectURL(audioUrl);
                    });
                }
            } catch (error) {
                console.error('Error speaking tab name:', error);
            }
        }
        
        // Save all sessions to server
        async function saveAllSessions() {
            if (!saveEnabled) return;
            
            const sessionData = {
                conversations: tabConversations,
                tabNames: {}
            };
            
            // Get tab names
            ['tab_1', 'tab_2', 'tab_3', 'tab_4'].forEach(tabId => {
                const tab = document.getElementById(tabId);
                if (tab) {
                    sessionData.tabNames[tabId] = tab.querySelector('.tab-name').textContent;
                }
            });
            
            try {
                const response = await fetch('/save_sessions', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(sessionData)
                });
                
                if (response.ok) {
                    console.log('Sessions saved successfully');
                }
            } catch (error) {
                console.error('Error saving sessions:', error);
            }
        }
        
        // Load sessions from server
        async function loadSessions(checkOnly = false) {
            try {
                const response = await fetch('/load_sessions');
                
                if (response.ok) {
                    const data = await response.json();
                    
                    if (data.success) {
                        // If just checking, return whether data exists
                        if (checkOnly) {
                            return data.hasData;
                        }
                        
                        // If data exists and we're not just checking, restore it
                        if (data.hasData) {
                            // Restore conversations
                            Object.assign(tabConversations, data.conversations);
                            
                            // Restore tab names
                            Object.entries(data.tabNames || {}).forEach(([tabId, name]) => {
                                const tab = document.getElementById(tabId);
                                if (tab) {
                                    tab.querySelector('.tab-name').textContent = name;
                                }
                            });
                            
                            // Update display
                            displayConversation();
                            
                            console.log('Sessions loaded successfully');
                        }
                    }
                }
                return false;
            } catch (error) {
                console.error('Error loading sessions:', error);
                return false;
            }
        }
        
        // Terminal preview functionality
        let terminalContents = {
            'tab_1': '',
            'tab_2': '',
            'tab_3': '',
            'tab_4': ''
        };
        
        
        // Update switchTab to show/hide terminal preview
        const originalSwitchTab = switchTab;
        switchTab = function(tabId) {
            originalSwitchTab(tabId);
        };
        
    </script>
    
    <!-- Version -->
    <div class="version">v2.3.0</div>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

# Global state
response_queues = {}  # tab_id -> queue
capture_threads = {}  # tab_id -> thread
stats_threads = {}  # tab_id -> thread

def capture_responses(session_id, tab_id):
    """Capture responses from Claude for a specific session"""
    print(f"[CAPTURE] Started capture thread for tab {tab_id}, session {session_id}")
    last_content = ""
    last_seen_lines = set()
    processed_responses = set()
    
    while True:
        if tab_id not in capture_threads:
            print(f"[CAPTURE] Stopping capture thread for tab {tab_id}")
            break
            
        try:
            content = orchestrator.capture_response(session_id)
            
            if content:
                print(f"[CAPTURE DEBUG] Got content for tab {tab_id}: {content[:100]}", flush=True)
            
            if content and content != last_content:
                # Debug: Show first 200 chars of new content
                if len(content) > len(last_content) + 10:
                    print(f"[CAPTURE] New content for tab {tab_id}: {content[-200:]}")
                    
                lines = content.split('\n')
                
                # Look for complete multi-line responses
                response_started = False
                full_response_lines = []
                
                for i, line in enumerate(lines):
                    line_hash = hash(line)
                    cleaned_line = line.strip()
                    
                    # Check if this is the start of a Claude response
                    if cleaned_line.startswith('●'):
                        # If we already had a response building, emit it first
                        if response_started and full_response_lines:
                            full_response = '\n'.join(full_response_lines)
                            response_hash = hash(full_response)
                            if response_hash not in processed_responses:
                                processed_responses.add(response_hash)
                                print(f"[CAPTURE] Emitting complete response for tab {tab_id}: {len(full_response)} chars", flush=True)
                                print(f"[CAPTURE] Response text: '{full_response}'", flush=True)
                                socketio.emit('response', {
                                    'tab_id': tab_id,
                                    'text': full_response
                                })
                        
                        # Start new response
                        response_started = True
                        full_response_lines = [cleaned_line[1:].strip()]
                        print(f"[CAPTURE] Found ● response start for tab {tab_id}")
                        
                    elif response_started and cleaned_line:
                        # This line is part of the ongoing response
                        # Stop collecting if we hit another marker
                        if cleaned_line.startswith('User:') or cleaned_line.startswith('Human:'):
                            # Emit the collected response
                            if full_response_lines:
                                full_response = '\n'.join(full_response_lines)
                                response_hash = hash(full_response)
                                if response_hash not in processed_responses:
                                    processed_responses.add(response_hash)
                                    print(f"[CAPTURE] Emitting complete response for tab {tab_id}: {len(full_response)} chars")
                                    socketio.emit('response', {
                                        'tab_id': tab_id,
                                        'text': full_response
                                    })
                            response_started = False
                            full_response_lines = []
                        else:
                            # Add this line to the response
                            full_response_lines.append(cleaned_line)
                    
                    # Mark line as seen
                    if line_hash not in last_seen_lines:
                        last_seen_lines.add(line_hash)
                
                # Emit any remaining response
                if response_started and full_response_lines:
                    full_response = '\n'.join(full_response_lines)
                    response_hash = hash(full_response)
                    if response_hash not in processed_responses:
                        processed_responses.add(response_hash)
                        print(f"[CAPTURE] Emitting complete response for tab {tab_id}: {len(full_response)} chars")
                        socketio.emit('response', {
                            'tab_id': tab_id,
                            'text': full_response
                        })
                
                last_content = content
                
        except Exception as e:
            print(f"[CAPTURE] Error for tab {tab_id}: {e}")
            
        time.sleep(0.5)

def emit_realtime_stats(tab_id):
    """Emit real-time stats for a tab"""
    print(f"[STATS] Started stats thread for tab {tab_id}")
    last_emit_time = 0
    
    while tab_id in stats_threads:
        try:
            current_time = time.time()
            
            # Emit stats every 0.5 seconds
            if current_time - last_emit_time >= 0.5:
                session_info = orchestrator.get_session_info(tab_id)
                
                if session_info:
                    # Use is_processing from orchestrator
                    is_processing = session_info.get('is_processing', False)
                    
                    # Emit stats - now using per-request metrics
                    stats_data = {
                        'tab_id': tab_id,
                        'duration': session_info.get('duration', 0),  # Changed from session_duration
                        'tokens': session_info.get('tokens', 0),      # Changed from total_tokens
                        'is_processing': is_processing
                    }
                    print(f"[STATS] Emitting for {tab_id}: duration={stats_data['duration']:.1f}s, tokens={stats_data['tokens']}, processing={is_processing}", flush=True)
                    socketio.emit('realtime_stats', stats_data)
                    
                last_emit_time = current_time
                
        except Exception as e:
            print(f"[STATS] Error emitting stats for tab {tab_id}: {e}")
            
        time.sleep(0.5)
    
    print(f"[STATS] Stopped stats thread for tab {tab_id}")

@app.route('/create_session', methods=['POST'])
def create_session():
    try:
        data = request.json
        tab_id = data.get('tab_id')
        project_name = data.get('project_name', 'Claude Session')
        
        print(f"[CREATE_SESSION] Creating session for tab {tab_id}, project: {project_name}")
        
        # Create session in orchestrator
        bot_session = orchestrator.create_session(tab_id, project_name)
        session_id = bot_session.session_id if hasattr(bot_session, 'session_id') else str(bot_session)
        print(f"[CREATE_SESSION] Session created: {session_id}")
        
        # Start response capture thread if not already running
        if tab_id not in capture_threads:
            thread = threading.Thread(
                target=capture_responses, 
                args=(session_id, tab_id),
                daemon=True
            )
            capture_threads[tab_id] = thread  # Add to dict BEFORE starting
            thread.start()
            print(f"[CREATE] Started capture thread for tab {tab_id}, session {session_id}")
        
        # Start stats thread if not already running
        if tab_id not in stats_threads:
            stats_thread = threading.Thread(
                target=emit_realtime_stats,
                args=(tab_id,),
                daemon=True
            )
            stats_threads[tab_id] = stats_thread  # Add to dict BEFORE starting
            stats_thread.start()
            print(f"[CREATE] Started stats thread for tab {tab_id}")
        
        return jsonify({
            'success': True,
            'session_id': session_id
        })
    except Exception as e:
        print(f"[CREATE_SESSION] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/send_command', methods=['POST'])
def send_command():
    print("[SEND] Received send_command request")
    try:
        data = request.json
        print(f"[SEND] Request data: {data}")
        tab_id = data.get('tab_id')
        command = data.get('command')
        
        print(f"[SEND] Sending '{command}' to tab {tab_id}")
        
        # Check if we need to start threads for this tab
        session = orchestrator.get_session_info(tab_id)
        if not session:
            print(f"[SEND] No session for tab {tab_id}, creating one")
            # Create session if it doesn't exist
            bot_session = orchestrator.create_session(tab_id, f"Tab {tab_id}")
            session_id = bot_session.session_id
            print(f"[SEND] Created session: {session_id}")
            
            # Start capture thread for new session
            if tab_id not in capture_threads:
                thread = threading.Thread(
                    target=capture_responses, 
                    args=(session_id, tab_id),
                    daemon=True
                )
                capture_threads[tab_id] = thread  # Add to dict BEFORE starting
                thread.start()
                print(f"[SEND] Started capture thread for tab {tab_id}")
            
            # Start stats thread for new session
            if tab_id not in stats_threads:
                stats_thread = threading.Thread(
                    target=emit_realtime_stats,
                    args=(tab_id,),
                    daemon=True
                )
                stats_threads[tab_id] = stats_thread  # Add to dict BEFORE starting
                stats_thread.start()
                print(f"[SEND] Started stats thread for tab {tab_id}")
        
        # Route message through orchestrator
        session_id = orchestrator.route_message(tab_id, command)
        print(f"[SEND] Message sent to session {session_id}")
        
        return jsonify({
            'success': True,
            'session_id': session_id
        })
    except Exception as e:
        print(f"[SEND] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/get_session_stats', methods=['POST'])
def get_session_stats():
    try:
        all_stats = {}
        for tab_id in ['tab_1', 'tab_2', 'tab_3', 'tab_4']:
            session_info = orchestrator.get_session_info(tab_id)
            if session_info:
                all_stats[tab_id] = {
                    'active': True,
                    'duration': session_info.get('session_duration_formatted', '00:00'),
                    'tokens': session_info.get('total_tokens', 0)
                }
            else:
                all_stats[tab_id] = {
                    'active': False,
                    'duration': '00:00',
                    'tokens': 0
                }
        return jsonify(all_stats)
    except Exception as e:
        return jsonify({}), 500

@socketio.on('switch_tab')
def handle_tab_switch(data):
    """Handle tab switching"""
    tab_id = data.get('tab_id')
    if tab_id:
        orchestrator.switch_tab(tab_id)

@app.route('/save_sessions', methods=['POST'])
def save_sessions():
    """Save all session data to file"""
    try:
        data = request.json
        
        # Save to a JSON file
        import json
        save_file = 'saved_sessions.json'
        
        # Add save state preference
        data['saveEnabled'] = True
        
        # Add orchestrator session data
        data['orchestrator_sessions'] = {}
        for tab_id in ['tab_1', 'tab_2', 'tab_3', 'tab_4']:
            session_info = orchestrator.get_session_info(tab_id)
            if session_info:
                data['orchestrator_sessions'][tab_id] = {
                    'session_id': session_info.get('session_id'),
                    'project_name': session_info.get('project_name'),
                    'message_count': session_info.get('message_count', 0),
                    'total_tokens': session_info.get('total_tokens', 0),
                    'total_duration': session_info.get('total_duration', 0)
                }
        
        with open(save_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"[SAVE] Error saving sessions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/load_sessions', methods=['GET'])
def load_sessions():
    """Load saved session data from file"""
    try:
        import json
        save_file = 'saved_sessions.json'
        
        if os.path.exists(save_file):
            with open(save_file, 'r') as f:
                data = json.load(f)
            
            return jsonify({
                'success': True,
                'hasData': True,
                'conversations': data.get('conversations', {}),
                'tabNames': data.get('tabNames', {}),
                'orchestrator_sessions': data.get('orchestrator_sessions', {})
            })
        else:
            return jsonify({
                'success': True,
                'hasData': False,
                'conversations': {},
                'tabNames': {},
                'orchestrator_sessions': {}
            })
    except Exception as e:
        print(f"[LOAD] Error loading sessions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/clear_sessions', methods=['POST'])
def clear_sessions():
    """Clear saved session data"""
    try:
        import json
        save_file = 'saved_sessions.json'
        
        if os.path.exists(save_file):
            os.remove(save_file)
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"[CLEAR] Error clearing sessions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/tts', methods=['POST'])
def tts():
    """Text-to-speech endpoint"""
    data = request.json
    text = data.get('text', '')
    voice = data.get('voice', 'en-US-AriaNeural')
    
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    
    try:
        # Use edge-tts to generate speech
        import edge_tts
        import asyncio
        
        async def generate_speech():
            tts = edge_tts.Communicate(text, voice)
            audio_data = b''
            async for chunk in tts.stream():
                if chunk['type'] == 'audio':
                    audio_data += chunk['data']
            return audio_data
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio_data = loop.run_until_complete(generate_speech())
        
        # Return audio as response
        return Response(audio_data, mimetype='audio/mpeg')
        
    except Exception as e:
        print(f"[TTS] Error: {e}")
        return jsonify({'error': str(e)}), 500



if __name__ == '__main__':
    # Create SSL context for HTTPS
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    cert_file = '/home/corp06/software_projects/ClaudeVoiceBot/current/cert.pem'
    key_file = '/home/corp06/software_projects/ClaudeVoiceBot/current/key.pem'
    
    if os.path.exists(cert_file) and os.path.exists(key_file):
        context.load_cert_chain(cert_file, key_file)
        print("\n" + "="*60)
        print("🎙️ MULTI-TAB CLAUDE VOICE ASSISTANT - EXACT REPLICA")
        print("="*60)
        print("✨ Built from exact UI specifications")
        print("📱 Access at: https://192.168.40.232:8444")
        print("="*60 + "\n")
        
        socketio.run(app, host='0.0.0.0', port=8444, ssl_context=context, allow_unsafe_werkzeug=True)
    else:
        print("SSL certificates not found. Running on HTTP.")
        print("\n" + "="*60)
        print("🎙️ MULTI-TAB CLAUDE VOICE ASSISTANT - EXACT REPLICA")
        print("="*60)
        print("✨ Built from exact UI specifications")
        print("📱 Access at: http://192.168.40.232:8444")
        print("="*60 + "\n")
        
        socketio.run(app, host='0.0.0.0', port=8444, allow_unsafe_werkzeug=True)