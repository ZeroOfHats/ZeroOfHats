// Top of main.js, add new element getters
const playerIdDisplay = document.getElementById('playerIdDisplay');
const currentScriptNameDisplay = document.getElementById('currentScriptNameDisplay');
const scriptNameInput = document.getElementById('scriptName');
const savedScriptsList = document.getElementById('savedScriptsList');
// const codeEditor = document.getElementById('codeEditor'); // Will be replaced by CodeMirror instance
const scrapInventoryList = document.getElementById('scrapInventoryList');
const selectedScrapNameDisplay = document.getElementById('selectedScrapName');
const selectedScrapDescriptionDisplay = document.getElementById('selectedScrapDescription');
const selectedScrapCodeDisplay = document.getElementById('selectedScrapCodeDisplay');
const gameModeSelect = document.getElementById('gameModeSelect');
const currentGameModeDisplay = document.getElementById('currentGameModeDisplay');
const emojiSeedOverrideInput = document.getElementById('emojiSeedOverrideInput'); // Added

const templateNameInput = document.getElementById('templateName');
const templateSpriteCharInput = document.getElementById('templateSpriteChar');
const templateEntityTypeInput = document.getElementById('templateEntityType');
const templateEntityScriptSelect = document.getElementById('templateEntityScript');
const templatePropertiesTextarea = document.getElementById('templateProperties');
const savedEntityTemplatesList = document.getElementById('savedEntityTemplatesList');

const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
const playerPositionDisplay = document.getElementById('playerPosition');
const scriptOutputDisplay = document.getElementById('scriptOutput');
const ragResponseDisplay = document.getElementById('ragResponse');
const gameLogDisplay = document.getElementById('gameLog');

let generationCodeMirrorEditor;
let currentRoomGrid = initialGrid;
let entities = {};
let playerId = '';
let availableScraps = {};

function drawGrid() {
    canvas.width = GRID_WIDTH * TILE_SIZE;
    canvas.height = GRID_HEIGHT * TILE_SIZE;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.font = `${TILE_SIZE * 0.8}px monospace`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    for (let y = 0; y < GRID_HEIGHT; y++) {
        for (let x = 0; x < GRID_WIDTH; x++) {
            const char = currentRoomGrid[y][x];
            if (char === '#') {
                ctx.fillStyle = 'grey';
                ctx.fillRect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE);
                ctx.fillStyle = 'black';
                ctx.fillText(char, x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2);
            } else if (char === '.') {
                ctx.fillStyle = 'lightgrey';
                ctx.fillRect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE);
            } else {
                ctx.fillStyle = 'black';
                ctx.fillText(char, x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2);
            }
        }
    }
    for (const entityId in entities) {
        const entity = entities[entityId];
        ctx.fillStyle = (entity.id === playerId && entity.type ==='player') ? 'blue' : 'red';
        ctx.fillText(entity.char, entity.x * TILE_SIZE + TILE_SIZE / 2, entity.y * TILE_SIZE + TILE_SIZE / 2);
        if (entity.id === playerId) {
             playerPositionDisplay.textContent = `${entity.x}, ${entity.y}`;
             if (playerIdDisplay) playerIdDisplay.textContent = entity.id;
        }
    }
}

function updateGameLog(logArray) {
    if (Array.isArray(logArray)) {
        gameLogDisplay.textContent = logArray.join('\n');
    } else {
        gameLogDisplay.textContent = String(logArray) + '\n' + gameLogDisplay.textContent.split('\n').slice(0,19).join('\n');
    }
}

async function refreshGameState() {
    try {
        const response = await fetch('/get_game_state');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const state = await response.json();

        currentRoomGrid = state.room_grid;
        entities = state.entities;
        playerId = state.player_id;

        if(currentScriptNameDisplay) {
            let scriptNameText = state.current_script_name || 'default_room';
            if (state.current_room_params && state.current_room_params.emoji_seed_string) {
                scriptNameText += ` (Emoji: ${state.current_room_params.emoji_seed_string})`;
            } else if (state.current_seed) {
                 scriptNameText += ` (Seed: ${state.current_seed})`;
            }
            currentScriptNameDisplay.textContent = scriptNameText;
        }

        const gameOptions = state.current_game_options || { game_mode: "sandbox" };
        if(currentGameModeDisplay) currentGameModeDisplay.textContent = gameOptions.game_mode;
        if (gameModeSelect) gameModeSelect.value = gameOptions.game_mode;

        updateGameLog(state.game_log || ["State updated."]);
        drawGrid();
    } catch (error) {
        console.error("Error fetching game state:", error);
        updateGameLog(["Error fetching game state."]);
    }
}

async function movePlayer(direction) {
    try {
        const response = await fetch('/move_player', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', },
            body: JSON.stringify({ direction: direction }),
        });
        const data = await response.json();

        if(data.game_log) {
            updateGameLog(data.game_log);
        } else if (data.message) {
            updateGameLog([data.message]);
        } else if (!response.ok) {
            updateGameLog([`Move failed: ${response.statusText}`]);
        }

        if (!response.ok) {
            const errorMsg = data.detail || data.error || `HTTP error! status: ${response.status}`;
            throw new Error(errorMsg);
        }

        if (data.room_switched) {
            console.log("Room switch detected by client!");
            await refreshGameState();
            if(data.message) alert(data.message);
        } else {
            if (data.entities) entities = data.entities;
            drawGrid();
        }
    } catch (error) {
        console.error("Error moving player:", error);
        updateGameLog([`Move failed: ${error.message}`]);
    }
}

async function executeScript() {
    const scriptCode = generationCodeMirrorEditor.getValue();
    const scriptName = scriptNameInput.value || "untitled_live_run";
    const emojiSeedOverride = emojiSeedOverrideInput.value.trim();

    updateGameLog([`Executing script: ${scriptName}` + (emojiSeedOverride ? ` with Emoji Seed: ${emojiSeedOverride}` : "")]);
    scriptOutputDisplay.textContent = "Running script...";

    let payload = {
        script_code: scriptCode,
        script_name: scriptName
    };
    if (emojiSeedOverride) {
        payload.emoji_seed_string = emojiSeedOverride;
    }

    try {
        const response = await fetch('/generate_room_script', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const data = await response.json();

        let outputMessages = [];
        if(data.message) outputMessages.push(data.message);
        if(data.script_actions && data.script_actions.length > 0) {
            outputMessages.push("--- Script Actions Log ---");
            outputMessages = outputMessages.concat(data.script_actions);
        }
        if(data.error) {
             outputMessages.push("--- Error ---");
             outputMessages.push(data.error);
        }
        scriptOutputDisplay.textContent = outputMessages.join('\n');
        updateGameLog(data.game_log || ["Script execution attempted."]);

        if (!response.ok) {
            throw new Error(data.error || `Script execution failed: ${response.statusText}`);
        }

        currentRoomGrid = data.room_grid;
        entities = data.entities;
        playerId = data.player_id;
        if(currentScriptNameDisplay) {
            let scriptNameText = scriptName;
             if(data.params_used && data.params_used.emoji_seed_string) {
                scriptNameText += ` (Emoji: ${data.params_used.emoji_seed_string})`;
            } else if(data.seed_used) {
                 scriptNameText += ` (Seed: ${data.seed_used})`;
            }
            currentScriptNameDisplay.textContent = scriptNameText;
        }
        drawGrid();

    } catch (error) {
        console.error("Error executing script:", error);
        scriptOutputDisplay.textContent += `\nFrontend/Network Error: ${error.message}`;
        updateGameLog([`Script execution failed: ${error.message}`]);
    }
}

async function saveScript() {
    const scriptName = scriptNameInput.value;
    const scriptCode = generationCodeMirrorEditor.getValue();
    if (!scriptName.trim()) { alert("Please enter a script name to save."); return; }
    updateGameLog([`Saving script: ${scriptName}`]);
    try {
        const response = await fetch('/save_script', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ script_name: scriptName, script_code: scriptCode, script_type: "generation"}),
        });
        const data = await response.json();
        updateGameLog(data.game_log || [data.message || "Save attempt finished."]);
        if (!response.ok) throw new Error(data.error || `Failed to save: ${response.statusText}`);
        alert(data.message);
        refreshScriptList();
    } catch (error) { console.error("Error saving script:", error); updateGameLog([`Save failed: ${error.message}`]); alert(`Error saving script: ${error.message}`); }
}

async function refreshScriptList() {
    updateGameLog(["Refreshing generation script list..."]);
    try {
        const response = await fetch('/list_scripts/generation');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        savedScriptsList.innerHTML = '';
        if (data.scripts && data.scripts.length > 0) {
            data.scripts.forEach(name => {
                const option = document.createElement('option'); option.value = name; option.textContent = name;
                savedScriptsList.appendChild(option);
            });
        } else {
            const option = document.createElement('option'); option.textContent = "No scripts saved yet"; option.disabled = true;
            savedScriptsList.appendChild(option);
        }
        updateGameLog(data.game_log || ["Script list refreshed."]);
    } catch (error) { console.error("Error refreshing script list:", error); updateGameLog([`Failed to refresh script list: ${error.message}`]); }
}

async function loadSelectedScript() {
    const selectedScriptName = savedScriptsList.value;
    if (!selectedScriptName || savedScriptsList.options[savedScriptsList.selectedIndex].disabled) { alert("Please select a script to load."); return; }
    updateGameLog([`Loading script: ${selectedScriptName}`]);
    try {
        const response = await fetch('/load_script', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ script_name: selectedScriptName }),
        });
        const data = await response.json();
        updateGameLog(data.game_log || [data.message || "Load attempt finished."]);
        if (!response.ok) throw new Error(data.error || `Failed to load: ${response.statusText}`);

        if (data.script_code !== undefined) {
            generationCodeMirrorEditor.setValue(data.script_code);
            scriptNameInput.value = data.script_name;
            scriptOutputDisplay.textContent = `Script '${data.script_name}' loaded into editor.`;
        } else {
            generationCodeMirrorEditor.setValue('');
            scriptNameInput.value = data.script_name || '';
            scriptOutputDisplay.textContent = `Script '${data.script_name}' loaded, but content is empty or missing.`;
        }
    } catch (error) { console.error("Error loading script:", error); updateGameLog([`Load failed: ${error.message}`]); alert(`Error loading script: ${error.message}`); }
}

async function refreshScrapList() {
    updateGameLog(["Refreshing scrap inventory..."]);
    try {
        const response = await fetch('/get_available_scraps');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        availableScraps = data.available_scraps || {};
        scrapInventoryList.innerHTML = '';
        if (Object.keys(availableScraps).length > 0) {
            for (const scrapId in availableScraps) {
                const scrap = availableScraps[scrapId];
                const option = document.createElement('option'); option.value = scrapId; option.textContent = scrap.name || scrapId;
                scrapInventoryList.appendChild(option);
            }
        } else {
            const option = document.createElement('option'); option.textContent = "No scraps available"; option.disabled = true;
            scrapInventoryList.appendChild(option);
        }
        updateGameLog(data.game_log || ["Scrap inventory refreshed."]);
        displaySelectedScrapCode();
    } catch (error) { console.error("Error refreshing scrap list:", error); updateGameLog([`Failed to refresh scrap list: ${error.message}`]); scrapInventoryList.innerHTML = '<option disabled>Error loading scraps</option>'; }
}

function displaySelectedScrapCode() {
    const selectedScrapId = scrapInventoryList.value;
    if (selectedScrapId && availableScraps[selectedScrapId]) {
        const scrap = availableScraps[selectedScrapId];
        selectedScrapNameDisplay.textContent = `Name: ${scrap.name || selectedScrapId}`;
        selectedScrapDescriptionDisplay.textContent = `Description: ${scrap.description || 'N/A'}`;
        selectedScrapCodeDisplay.textContent = scrap.code || "// No code for this scrap";
    } else {
        selectedScrapNameDisplay.textContent = "Name: -"; selectedScrapDescriptionDisplay.textContent = "Description: -";
        selectedScrapCodeDisplay.textContent = "// Select a scrap to view its code";
    }
}

function copyScrapToEditor() {
    const selectedScrapId = scrapInventoryList.value;
    if (selectedScrapId && availableScraps[selectedScrapId]) {
        const scrap = availableScraps[selectedScrapId];
        if (scrap.code) {
            const currentCode = generationCodeMirrorEditor.getValue();
            const newCode = currentCode +
                            "\n\n// --- Copied Scrap: " + (scrap.name || selectedScrapId) + " ---\n" +
                            scrap.code +
                            "\n// --- End Scrap --- \n";
            generationCodeMirrorEditor.setValue(newCode);
            generationCodeMirrorEditor.setCursor(generationCodeMirrorEditor.lineCount(), 0);
            scriptOutputDisplay.textContent = `Scrap '${scrap.name || selectedScrapId}' appended to editor.`;
            updateGameLog([`Scrap '${scrap.name || selectedScrapId}' copied to editor.`]);
        } else { alert("Selected scrap has no code to copy."); }
    } else { alert("Please select a scrap from the inventory first."); }
}

async function queryRag() {
    const queryText = document.getElementById('ragQuery').value;
    if (!queryText.trim()) { ragResponseDisplay.textContent = "Please enter a query."; return; }
    updateGameLog([`Querying RAG: ${queryText}`]); ragResponseDisplay.textContent = "Fetching RAG response...";
    try {
        const response = await fetch('/rag_query', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query_text: queryText }), });
        const data = await response.json(); updateGameLog(data.game_log || ["RAG query processed."]);
        if (!response.ok) { ragResponseDisplay.textContent = `Error: ${data.detail || response.statusText}`; throw new Error(data.detail || `HTTP error! status: ${response.status}`);}
        ragResponseDisplay.textContent = data.rag_response;
    } catch (error) { console.error("Error querying RAG:", error); ragResponseDisplay.textContent = `RAG query failed: ${error.message}`; updateGameLog([`RAG query failed: ${error.message}`]); }
}

async function applyGameOptions() {
    const selectedMode = gameModeSelect.value;
    updateGameLog([`Applying game options: Mode - ${selectedMode}`]);
    try {
        const response = await fetch('/set_game_options', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ game_mode: selectedMode }),
        });
        const data = await response.json(); updateGameLog(data.game_log || [data.message || "Game options processed."]);
        if (!response.ok) { throw new Error(data.error || `Failed to set options: ${response.statusText}`); }
        if(currentGameModeDisplay) currentGameModeDisplay.textContent = data.updated_options.game_mode;
        alert(data.message);
    } catch (error) { console.error("Error applying game options:", error); updateGameLog([`Failed to apply options: ${error.message}`]); alert(`Error: ${error.message}`); }
}

async function tickGame() {
    updateGameLog(["Processing game tick..."]);
    try {
        const response = await fetch('/tick_game', { method: 'POST' });
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        await refreshGameState();
    } catch (error) {
        console.error("Error processing game tick:", error);
        updateGameLog([`Tick processing failed: ${error.message}`]);
    }
}

// --- Sandbox Editor JS Functions ---
async function refreshEntityScriptList() {
    updateGameLog(["Refreshing entity script list for Sandbox Editor..."]);
    try {
        const response = await fetch('/list_scripts/entities');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();

        templateEntityScriptSelect.innerHTML = '<option value="">-- Select Script (Optional) --</option>';
        if (data.scripts && data.scripts.length > 0) {
            data.scripts.forEach(name => {
                const option = document.createElement('option'); option.value = name; option.textContent = name + ".py";
                templateEntityScriptSelect.appendChild(option);
            });
        } else {
            const option = document.createElement('option'); option.textContent = "No entity scripts found"; option.disabled = true;
            templateEntityScriptSelect.appendChild(option);
        }
    } catch (error) {
        console.error("Error refreshing entity script list:", error);
        updateGameLog([`Failed to refresh entity script list: ${error.message}`]);
        templateEntityScriptSelect.innerHTML = '<option disabled>Error loading scripts</option>';
    }
}

async function refreshEntityTemplateList() {
    updateGameLog(["Refreshing entity template list..."]);
    try {
        const response = await fetch('/list_entity_templates');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();

        savedEntityTemplatesList.innerHTML = '';
        if (data.entity_templates && data.entity_templates.length > 0) {
            data.entity_templates.forEach(name => {
                const option = document.createElement('option'); option.value = name; option.textContent = name;
                savedEntityTemplatesList.appendChild(option);
            });
        } else {
            const option = document.createElement('option'); option.textContent = "No templates saved yet"; option.disabled = true;
            savedEntityTemplatesList.appendChild(option);
        }
    } catch (error) {
        console.error("Error refreshing entity template list:", error);
        updateGameLog([`Failed to refresh template list: ${error.message}`]);
        savedEntityTemplatesList.innerHTML = '<option disabled>Error loading templates</option>';
    }
}

async function saveCurrentEntityTemplate() {
    const templateName = templateNameInput.value;
    const spriteChar = templateSpriteCharInput.value;
    const entityType = templateEntityTypeInput.value;
    const selectedEntityScript = templateEntityScriptSelect.value;

    if (!templateName.trim()) { alert("Please enter a Template Name."); return; }
    if (!spriteChar.trim()) { alert("Please enter a Sprite Character."); return; }
    if (!entityType.trim()) { alert("Please enter an Entity Type."); return; }

    let propertiesJson = {};
    try {
        propertiesJson = templatePropertiesTextarea.value.trim() ? JSON.parse(templatePropertiesTextarea.value) : {};
    } catch (e) {
        alert("Properties field contains invalid JSON. Please correct it.");
        if(scriptOutputDisplay) scriptOutputDisplay.textContent = "Error parsing properties JSON: " + e.message;
        return;
    }

    if (selectedEntityScript) { propertiesJson.script_name = selectedEntityScript; }

    const payload = { template_name: templateName, sprite_char: spriteChar, entity_type: entityType, properties: propertiesJson };
    updateGameLog([`Saving entity template: ${templateName}`]);
    try {
        const response = await fetch('/save_entity_template', {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
        });
        const data = await response.json();
        updateGameLog(data.game_log || [data.message || "Save template attempt finished."]);
        if (!response.ok) throw new Error(data.error || `Failed to save: ${response.statusText}`);
        alert(data.message); refreshEntityTemplateList();
    } catch (error) {
        console.error("Error saving entity template:", error);
        updateGameLog([`Save template failed: ${error.message}`]); alert(`Error saving template: ${error.message}`);
    }
}

async function loadSelectedEntityTemplate() {
    const selectedTemplateName = savedEntityTemplatesList.value;
    if (!selectedTemplateName || savedEntityTemplatesList.options[savedEntityTemplatesList.selectedIndex].disabled) { alert("Please select a template to load."); return; }
    updateGameLog([`Loading entity template: ${selectedTemplateName}`]);
    try {
        const response = await fetch(`/load_entity_template/${selectedTemplateName}`);
        const data = await response.json();
        updateGameLog(data.game_log || ["Load template attempt finished."]);
        if (!response.ok) throw new Error(data.error || `Failed to load: ${response.statusText}`);

        const template = data.template_data;
        templateNameInput.value = template.template_name || '';
        templateSpriteCharInput.value = template.sprite_char || '';
        templateEntityTypeInput.value = template.entity_type || '';
        templatePropertiesTextarea.value = template.properties ? JSON.stringify(template.properties, null, 2) : '{}';
        templateEntityScriptSelect.value = template.properties?.script_name || "";
        if(scriptOutputDisplay) scriptOutputDisplay.textContent = `Entity Template '${template.template_name}' loaded.`;
    } catch (error) {
        console.error("Error loading entity template:", error);
        updateGameLog([`Load template failed: ${error.message}`]); alert(`Error loading template: ${error.message}`);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const editorTextarea = document.getElementById('codeEditor');
    if (editorTextarea) {
        generationCodeMirrorEditor = CodeMirror.fromTextArea(editorTextarea, {
            lineNumbers: true, mode: "python", theme: "material-darker",
            indentUnit: 4, smartIndent: true, lineWrapping: true,
        });
        generationCodeMirrorEditor.setSize(null, "250px");
    } else {
        console.error("CodeMirror target textarea 'codeEditor' not found.");
    }

    refreshGameState();
    refreshScriptList();
    refreshScrapList();
    refreshEntityScriptList();
    refreshEntityTemplateList();

    window.addEventListener('keydown', (event) => {
        if (event.target.tagName === 'TEXTAREA' ||
            (event.target.tagName === 'INPUT' && event.target.type === 'text') ||
            event.target === scriptNameInput ||
            event.target === templateNameInput ||
            event.target === templateSpriteCharInput ||
            event.target === templateEntityTypeInput ||
            event.target === document.getElementById('ragQuery') ||
            event.target === emojiSeedOverrideInput // Added this
           ) {
            return;
        }
        switch (event.key) {
            case 'ArrowUp': case 'w': movePlayer('up'); break;
            case 'ArrowDown': case 's': movePlayer('down'); break;
            case 'ArrowLeft': case 'a': movePlayer('left'); break;
            case 'ArrowRight': case 'd': movePlayer('right'); break;
            case 't': tickGame(); break;
        }
    });
});
