// In static/js/level_creator.js

// Add to existing consts at the top
const mapIdInput = document.getElementById('mapIdInput');
const savedMapsList = document.getElementById('savedMapsList');
const currentMapIdDisplay = document.getElementById('currentMapIdDisplay');
const currentMapDataDisplay = document.getElementById('currentMapData');
const roomListUl = document.getElementById('roomList');

const roomCountDisplay = document.getElementById('roomCountDisplay');
const roomEditorArea = document.querySelector('.room-editor-area');
const roomEditorTitle = document.getElementById('roomEditorTitle');
const editingRoomIdInput = document.getElementById('editingRoomId');
const roomIdInput = document.getElementById('roomIdInput');
const roomDisplayNameInput = document.getElementById('roomDisplayNameInput');
const roomGeneratorScriptSelect = document.getElementById('roomGeneratorScriptSelect');
const roomParamsTextarea = document.getElementById('roomParamsTextarea');
const roomEmojiSeedInput = document.getElementById('roomEmojiSeedInput'); // Added
const deleteRoomButton = document.getElementById('deleteRoomButton');

const connectionEditorArea = document.querySelector('.connection-editor-area');
const connSelectedRoomDisplay = document.getElementById('connSelectedRoomDisplay');
const connIdInput = document.getElementById('connIdInput');
const connSourceCoordsInput = document.getElementById('connSourceCoordsInput');
const connTargetRoomSelect = document.getElementById('connTargetRoomSelect');
const connTargetEntryCoordsInput = document.getElementById('connTargetEntryCoordsInput');
const connBidirectionalCheckbox = document.getElementById('connBidirectionalCheckbox');

let currentLabyrinthMap = null;
let selectedRoomIdForEditing = null;
let selectedRoomIdForConnection = null;

// --- Room Editor Functions ---
function lc_showAddRoomForm() {
    roomEditorTitle.textContent = "Add New Room";
    editingRoomIdInput.value = "";
    roomIdInput.value = "";
    roomIdInput.disabled = false;
    roomDisplayNameInput.value = "";
    roomGeneratorScriptSelect.value = "default_room"; // Default to "default_room"
    roomParamsTextarea.value = "{}";
    roomEmojiSeedInput.value = ""; // Clear emoji seed input
    deleteRoomButton.style.display = 'none';
    roomEditorArea.style.display = 'block';
    connectionEditorArea.style.display = 'none';
    selectedRoomIdForEditing = null;
}

function lc_editRoom(roomId) {
    if (!currentLabyrinthMap || !currentLabyrinthMap.rooms[roomId]) {
        alert("Room not found in current map data.");
        return;
    }
    const roomData = currentLabyrinthMap.rooms[roomId];
    selectedRoomIdForEditing = roomId;

    roomEditorTitle.textContent = `Edit Room: ${roomData.display_name || roomId}`;
    editingRoomIdInput.value = roomId;
    roomIdInput.value = roomId;
    roomIdInput.disabled = true;
    roomDisplayNameInput.value = roomData.display_name || '';
    roomGeneratorScriptSelect.value = roomData.generator_script_name || 'default_room';

    // Separate emoji_seed_string from other room_params for display
    let displayParams = {...(roomData.room_params || {})};
    roomEmojiSeedInput.value = displayParams.emoji_seed_string || "";
    delete displayParams.emoji_seed_string; // Don't show it in the main JSON params box
    roomParamsTextarea.value = JSON.stringify(displayParams, null, 2);

    deleteRoomButton.style.display = 'inline-block';
    roomEditorArea.style.display = 'block';
    connectionEditorArea.style.display = 'none';
}

function lc_hideRoomEditor() {
    roomEditorArea.style.display = 'none';
    selectedRoomIdForEditing = null;
}

function lc_saveRoomDetails() {
    if (!currentLabyrinthMap) {
        alert("Load or create a map first.");
        return;
    }
    const roomId = roomIdInput.value.trim();
    const isEditing = !!editingRoomIdInput.value && editingRoomIdInput.value === roomId;

    if (!roomId) { alert("Room ID is required."); return; }

    if (!isEditing && currentLabyrinthMap.rooms[roomId]) {
        alert(`Room ID '${roomId}' already exists. Choose a different ID.`);
        return;
    }
    let roomParams = {};
    try {
        roomParams = JSON.parse(roomParamsTextarea.value.trim() || "{}");
    } catch (e) {
        alert("Room Params field contains invalid JSON. Please correct it.");
        return;
    }

    const emojiSeed = roomEmojiSeedInput.value.trim();
    if (emojiSeed) {
        roomParams.emoji_seed_string = emojiSeed;
    } else {
        delete roomParams.emoji_seed_string;
    }

    const roomData = {
        id: roomId,
        display_name: roomDisplayNameInput.value.trim(),
        generator_script_name: roomGeneratorScriptSelect.value,
        room_params: roomParams,
        connections: (isEditing && currentLabyrinthMap.rooms[roomId]) ? (currentLabyrinthMap.rooms[roomId].connections || {}) : {}
    };

    currentLabyrinthMap.rooms[roomId] = roomData;

    if (Object.keys(currentLabyrinthMap.rooms).length === 1 && !currentLabyrinthMap.start_room_id) {
        currentLabyrinthMap.start_room_id = roomId;
        alert(`Room '${roomId}' added and set as start room.`);
    } else if (!currentLabyrinthMap.start_room_id && Object.keys(currentLabyrinthMap.rooms).length > 0) {
         if(confirm(`Room '${roomId}' added. Make this the start room for the map?`)){
            currentLabyrinthMap.start_room_id = roomId;
         }
    }

    updateMapDisplay();
    lc_hideRoomEditor();
    console.log(`Room '${roomId}' details saved to local map data (including emoji seed if any).`);
}

function lc_deleteSelectedRoom() {
    if (!selectedRoomIdForEditing || !currentLabyrinthMap || !currentLabyrinthMap.rooms[selectedRoomIdForEditing]) {
        alert("No room selected or map not loaded.");
        return;
    }
    if (confirm(`Are you sure you want to delete room '${selectedRoomIdForEditing}'? This will also remove connections involving it.`)) {
        delete currentLabyrinthMap.rooms[selectedRoomIdForEditing];
        for (const rId in currentLabyrinthMap.rooms) {
            const room = currentLabyrinthMap.rooms[rId];
            const newConnections = {};
            for (const cId in room.connections) {
                if (room.connections[cId].target_room_id !== selectedRoomIdForEditing) {
                    newConnections[cId] = room.connections[cId];
                }
            }
            room.connections = newConnections;
        }

        if (currentLabyrinthMap.start_room_id === selectedRoomIdForEditing) {
            currentLabyrinthMap.start_room_id = null;
            alert("Deleted start room. Please set a new one.");
        }
        updateMapDisplay();
        lc_hideRoomEditor();
        console.log(`Room '${selectedRoomIdForEditing}' deleted.`);
    }
}

// --- Connection Editor Functions ---
function lc_selectRoomForConnection(roomId) {
    if (!currentLabyrinthMap || !currentLabyrinthMap.rooms[roomId]) return;
    selectedRoomIdForConnection = roomId;
    connSelectedRoomDisplay.textContent = `${currentLabyrinthMap.rooms[roomId].display_name || roomId} (${roomId})`;

    connTargetRoomSelect.innerHTML = '<option value="">-- Select Target Room --</option>';
    for (const rId in currentLabyrinthMap.rooms) {
        if (rId === roomId) continue;
        const option = document.createElement('option');
        option.value = rId;
        option.textContent = `${currentLabyrinthMap.rooms[rId].display_name || rId} (${rId})`;
        connTargetRoomSelect.appendChild(option);
    }
    connectionEditorArea.style.display = 'block';
    roomEditorArea.style.display = 'none';
}

function lc_addConnection() {
    if (!currentLabyrinthMap || !selectedRoomIdForConnection) {
        alert("Select a source room for the connection first (Shift+Click a room in list).");
        return;
    }
    const sourceRoomId = selectedRoomIdForConnection;
    const connId = connIdInput.value.trim();
    const sourceCoordsStr = connSourceCoordsInput.value.trim();
    const targetRoomId = connTargetRoomSelect.value;
    const targetCoordsStr = connTargetEntryCoordsInput.value.trim();
    const bidirectional = connBidirectionalCheckbox.checked;

    if (!connId || !sourceCoordsStr || !targetRoomId || !targetCoordsStr) {
        alert("All connection fields are required."); return;
    }

    const parseCoords = (str) => str.split(',').map(s => parseInt(s.trim(), 10));
    const sourceCoords = parseCoords(sourceCoordsStr);
    const targetCoords = parseCoords(targetCoordsStr);

    if (sourceCoords.length !== 2 || sourceCoords.some(isNaN) || targetCoords.length !== 2 || targetCoords.some(isNaN)) {
        alert("Coordinates must be two numbers separated by a comma (e.g., 10,25)."); return;
    }

    const sourceRoom = currentLabyrinthMap.rooms[sourceRoomId];
    if (!sourceRoom.connections) sourceRoom.connections = {};

    sourceRoom.connections[connId] = {
        id: connId, target_room_id: targetRoomId,
        target_entry_coords: targetCoords, source_exit_coords: sourceCoords
    };

    if (bidirectional) {
        const targetRoom = currentLabyrinthMap.rooms[targetRoomId];
        if (!targetRoom.connections) targetRoom.connections = {};
        const reverseConnId = `conn_from_${targetRoomId}_to_${sourceRoomId}_at_${targetCoords[0]}_${targetCoords[1]}`;
        targetRoom.connections[reverseConnId] = {
            id: reverseConnId, target_room_id: sourceRoomId,
            target_entry_coords: sourceCoords, source_exit_coords: targetCoords
        };
    }
    updateMapDisplay();
    console.log(`Connection '${connId}' added from '${sourceRoomId}' to '${targetRoomId}'.`);
    alert("Connection added/updated. Save the map to persist changes.");
}

// --- Script List for Room Editor ---
async function lc_refreshGenScriptsForRoomEditor() {
    console.log("Refreshing generation script list for Room Editor...");
    try {
        const response = await fetch('/list_scripts/generation');
        if (!response.ok) throw new Error(`HTTP error! ${response.status}`);
        const data = await response.json();

        roomGeneratorScriptSelect.innerHTML = '<option value="default_room">default_room (Built-in)</option>';
        if (data.scripts && data.scripts.length > 0) {
            data.scripts.forEach(name => {
                const option = document.createElement('option');
                option.value = name; option.textContent = name + ".py";
                roomGeneratorScriptSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error("Error refreshing generation script list:", error);
        roomGeneratorScriptSelect.innerHTML = '<option disabled>Error loading scripts</option>';
    }
}

// --- Existing Map Management JS (lc_refreshMapList, etc.) ---
async function lc_refreshMapList() {
    console.log("Refreshing map list...");
    try {
        const response = await fetch('/list_labyrinth_maps');
        if (!response.ok) throw new Error(`HTTP error! ${response.status}`);
        const data = await response.json();
        savedMapsList.innerHTML = '<option value="">-- Select a map --</option>';
        if (data.labyrinth_maps && data.labyrinth_maps.length > 0) {
            data.labyrinth_maps.forEach(mapId => {
                const option = document.createElement('option');option.value = mapId;option.textContent = mapId;
                savedMapsList.appendChild(option);
            });
        } else {
            const option = document.createElement('option');option.disabled = true;option.textContent = "No maps saved yet";
            savedMapsList.appendChild(option);
        }
    } catch (error) { console.error("Error refreshing map list:", error);alert(`Error map list: ${error.message}`);savedMapsList.innerHTML = '<option disabled>Error loading maps</option>'; }
}
function lc_createNewMap() {
    const newMapId = mapIdInput.value.trim();
    if (!newMapId) { alert("Please enter an ID/Name for the new map."); return; }
    currentLabyrinthMap = { map_id: newMapId, name: newMapId, start_room_id: null, rooms: {} };
    mapIdInput.value = ""; updateMapDisplay();
    console.log("New map structure created in browser:", newMapId);
    alert(`New map '${newMapId}' initialized locally. Add rooms and save.`);
}
async function lc_loadSelectedMap() {
    const mapId = savedMapsList.value; if (!mapId) { alert("Please select a map to load."); return; }
    console.log(`Loading map: ${mapId}`);
    try {
        const response = await fetch(`/load_labyrinth_map/${mapId}`);
        if (!response.ok) { const errData = await response.json(); throw new Error(errData.error || `HTTP error! ${response.status}`);}
        const data = await response.json(); currentLabyrinthMap = data.labyrinth_map_data;
        updateMapDisplay(); alert(`Map '${mapId}' loaded successfully.`);
    } catch (error) { console.error("Error loading map:", error); alert(`Error loading map '${mapId}': ${error.message}`); currentLabyrinthMap = null; updateMapDisplay(); }
}
async function lc_saveCurrentMap() {
    if (!currentLabyrinthMap || !currentLabyrinthMap.map_id) { alert("No map data to save. Create or load map first."); return; }
    console.log(`Saving map: ${currentLabyrinthMap.map_id}`);
    try {
        const response = await fetch('/save_labyrinth_map', {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(currentLabyrinthMap)
        });
        const data = await response.json();
        if (!response.ok) { throw new Error(data.error || `HTTP error! ${response.status}`); }
        alert(data.message || `Map '${currentLabyrinthMap.map_id}' saved.`); lc_refreshMapList();
    } catch (error) { console.error("Error saving map:", error); alert(`Error saving map '${currentLabyrinthMap.map_id}': ${error.message}`); }
}
async function lc_setActiveMap() {
    if (!currentLabyrinthMap || !currentLabyrinthMap.map_id) { alert("Load/create map first."); return; }
    const mapId = currentLabyrinthMap.map_id; console.log(`Setting active map: ${mapId}`);
    try {
        const response = await fetch(`/set_active_labyrinth_map/${mapId}`, { method: 'POST' });
        const data = await response.json();
        if (!response.ok) { throw new Error(data.error || data.detail || `HTTP error! ${response.status}`);}
        alert(data.message || `Map '${mapId}' is now active.`);
    } catch (error) { console.error("Error setting active map:", error); alert(`Error setting active map: ${error.message}`); }
}

function updateMapDisplay() {
    if (currentLabyrinthMap && currentLabyrinthMap.map_id) {
        currentMapIdDisplay.textContent = currentLabyrinthMap.map_id + (currentLabyrinthMap.name ? ` (${currentLabyrinthMap.name})` : '');
        currentMapDataDisplay.textContent = JSON.stringify(currentLabyrinthMap, null, 2);
        roomListUl.innerHTML = '';
        const rooms = currentLabyrinthMap.rooms || {};
        roomCountDisplay.textContent = Object.keys(rooms).length;
        if (Object.keys(rooms).length > 0) {
            for (const roomId in rooms) {
                const room = rooms[roomId];
                const li = document.createElement('li');
                let text = `${room.display_name || roomId} (Script: ${room.generator_script_name || 'N/A'})`;
                if (roomId === currentLabyrinthMap.start_room_id) text += " [START]";
                li.textContent = text; li.dataset.roomId = roomId;
                li.onclick = (event) => {
                    if (event.shiftKey) { lc_selectRoomForConnection(roomId); }
                    else { lc_editRoom(roomId); }
                };
                roomListUl.appendChild(li);
            }
        } else { roomListUl.innerHTML = '<li>No rooms in this map yet.</li>'; }
    } else {
        currentMapIdDisplay.textContent = "None"; currentMapDataDisplay.textContent = "No map loaded.";
        roomListUl.innerHTML = '<li>No map loaded.</li>'; roomCountDisplay.textContent = "0";
    }
    if (!currentLabyrinthMap) { lc_hideRoomEditor(); connectionEditorArea.style.display = 'none'; }
    if (!selectedRoomIdForConnection && connectionEditorArea) { connectionEditorArea.style.display = 'none'; } // Also hide if no src room
}

// Initial load
document.addEventListener('DOMContentLoaded', () => {
    lc_refreshMapList();
    lc_refreshGenScriptsForRoomEditor();
    updateMapDisplay();
    if(roomEditorArea) roomEditorArea.style.display = 'none';
    if(connectionEditorArea) connectionEditorArea.style.display = 'none';
});
