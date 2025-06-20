from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn
import random
import time
import traceback
import os
import json
import hashlib # For Emojidex

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- Game Constants & Logger ---
GRID_WIDTH = 50
GRID_HEIGHT = 50
PLAYER_CHAR = "@"
DEFAULT_FLOOR = '.'
DEFAULT_WALL = '#'
MAX_SCRIPT_EXEC_TIME = 2.0
SCRIPTS_DIR = "player_scripts"
GEN_SCRIPTS_SUBDIR = "generation"
ENTITY_SCRIPTS_SUBDIR = "entities"
ENTITY_TEMPLATES_DIR = os.path.join(SCRIPTS_DIR, "entity_templates")
LABYRINTH_MAPS_DIR = "labyrinth_maps"

game_log_messages = ["Game initialized."]
def log_game_message(message, max_log_size=20):
    game_log_messages.insert(0, str(message))
    if len(game_log_messages) > max_log_size: game_log_messages.pop()

os.makedirs(os.path.join(SCRIPTS_DIR, GEN_SCRIPTS_SUBDIR), exist_ok=True)
os.makedirs(os.path.join(SCRIPTS_DIR, ENTITY_SCRIPTS_SUBDIR), exist_ok=True)
os.makedirs(ENTITY_TEMPLATES_DIR, exist_ok=True)
os.makedirs(LABYRINTH_MAPS_DIR, exist_ok=True)

# --- Emojidex Seeding System (Simulated) ---
EMOJIDEX_MASTER_LIST = {
    "🔥": {"seed_add": 1000, "params_mod": {"theme": "fire", "intensity": 0.5, "wall_char": "F"}},
    "💎": {"seed_add": 2000, "params_mod": {"treasure_density": 0.8, "room_value": 100}},
    "✨": {"seed_add": 500,  "params_mod": {"magic_level": 0.3, "brightness": 0.7}},
    "🌲": {"seed_add": 3000, "params_mod": {"theme": "forest", "density": 0.6, "floor_char": "f"}},
    "🌊": {"seed_add": 4000, "params_mod": {"theme": "water", "fluidity": 0.9, "floor_char": "w"}},
    "💀": {"seed_add": 666,  "params_mod": {"difficulty_mod": 1.2, "undead_presence": 0.7, "theme": "crypt"}},
    "🤖": {"seed_add": 5000, "params_mod": {"tech_level": 0.8, "metallic": True, "wall_char": "M"}}
}

def process_emoji_string(emoji_str: str) -> tuple[int, dict]:
    base_seed = 0; combined_params = {}; unrecognized_emojis = []
    string_hash_val = int(hashlib.md5(emoji_str.encode('utf-8')).hexdigest(), 16) % 100000
    base_seed += string_hash_val
    for emoji_char in emoji_str:
        if emoji_char in EMOJIDEX_MASTER_LIST:
            data = EMOJIDEX_MASTER_LIST[emoji_char]
            base_seed += data.get("seed_add", 0)
            param_mods = data.get("params_mod", {})
            for key, value in param_mods.items():
                if isinstance(value,(int,float)) and key in combined_params and isinstance(combined_params[key],(int,float)):
                    combined_params[key] = combined_params.get(key, 0) + value
                else: combined_params[key] = value
        else: unrecognized_emojis.append(emoji_char); base_seed += ord(emoji_char)
    if unrecognized_emojis: log_game_message(f"Emojidex: Unrecognized emojis: {', '.join(unrecognized_emojis)}")
    final_seed = base_seed % (2**31 -1)
    log_game_message(f"Emojidex processed '{emoji_str}': seed={final_seed}, params={combined_params}")
    return final_seed, combined_params

# --- Level Creator Data Models ---
class Connection:
    def __init__(self, id: str, target_room_id: str, target_entry_coords: tuple[int, int], source_exit_coords: tuple[int, int]):
        self.id=id; self.target_room_id=target_room_id; self.target_entry_coords=target_entry_coords; self.source_exit_coords=source_exit_coords
    def to_dict(self): return self.__dict__
    @classmethod
    def from_dict(cls, data: dict): return cls(**data)

class RoomNode:
    def __init__(self, room_id: str, display_name: str, generator_script_name: str, room_params: dict = None):
        self.id=room_id; self.display_name=display_name; self.generator_script_name=generator_script_name
        self.room_params=room_params if room_params else {}; self.connections={}
    def add_connection(self, connection: Connection): self.connections[connection.id]=connection; log_game_message(f"Room '{self.id}': Conn '{connection.id}' to '{connection.target_room_id}'.")
    def to_dict(self): return {"id":self.id,"display_name":self.display_name,"generator_script_name":self.generator_script_name,"room_params":self.room_params,"connections":{cid:conn.to_dict() for cid,conn in self.connections.items()}}
    @classmethod
    def from_dict(cls, data: dict):
        node=cls(data['id'],data['display_name'],data['generator_script_name'],data.get('room_params',{}))
        for cid,conn_data in data.get('connections',{}).items(): node.add_connection(Connection.from_dict(conn_data))
        return node

class LabyrinthMap:
    def __init__(self, map_id: str, name: str = "My Labyrinth"):
        self.map_id=map_id; self.name=name; self.rooms={}; self.start_room_id=None
    def add_room(self, room_node: RoomNode, is_start_room: bool = False):
        if room_node.id in self.rooms: log_game_message(f"Map Error: Room ID '{room_node.id}' exists."); return False
        self.rooms[room_node.id]=room_node
        if is_start_room or not self.start_room_id: self.start_room_id=room_node.id
        log_game_message(f"Map '{self.map_id}': Added room '{room_node.id}'. Start: '{self.start_room_id}'."); return True
    def get_room(self, room_id: str) -> RoomNode | None: return self.rooms.get(room_id)
    def connect_rooms(self, from_id, exit_id, exit_coords, to_id, entry_coords, bidirectional=True):
        from_r,to_r=self.get_room(from_id),self.get_room(to_id)
        if not from_r or not to_r: log_game_message(f"Connect Error: Room not found."); return False
        from_r.add_connection(Connection(exit_id,to_id,entry_coords,exit_coords))
        if bidirectional: to_r.add_connection(Connection(f"ret_{exit_id}",from_id,exit_coords,entry_coords))
        log_game_message(f"Map '{self.map_id}': Connected '{from_id}' to '{to_id}'. Bi: {bidirectional}."); return True
    def to_json_dict(self):
        return {"map_id":self.map_id,"name":self.name,"start_room_id":self.start_room_id,"rooms":{rid:r.to_dict() for rid,r in self.rooms.items()}}
    @classmethod
    def from_dict(cls, data: dict):
        lm=cls(data['map_id'],data['name']); lm.start_room_id=data.get('start_room_id')
        for rid,r_data in data.get('rooms',{}).items(): lm.add_room(RoomNode.from_dict(r_data))
        return lm

loaded_labyrinth_maps: dict[str, LabyrinthMap] = {}
active_labyrinth_map_id: str | None = None

def _initialize_example_labyrinth():
    global active_labyrinth_map_id, loaded_labyrinth_maps; map_id="tutorial_labyrinth"
    if map_id in loaded_labyrinth_maps:return
    log_game_message(f"Init example map: {map_id}..."); new_map=LabyrinthMap(map_id=map_id,name="Tutorial Labyrinth")
    r1=RoomNode("entry","Entry","default_room"); r2=RoomNode("corridor","Corridor","default_room",{"internal_walls":5})
    r3=RoomNode("treasure","Treasure Room","default_room",{"internal_walls":20, "emoji_seed_string": "💎✨"})
    new_map.add_room(r1,True); new_map.add_room(r2); new_map.add_room(r3)
    new_map.connect_rooms("entry","exit_e",(GRID_WIDTH-1,GRID_HEIGHT//2),"corridor",(0,GRID_HEIGHT//2))
    new_map.connect_rooms("corridor","exit_n",(GRID_WIDTH//2,0),"treasure",(GRID_WIDTH//2,GRID_HEIGHT-1))
    loaded_labyrinth_maps[map_id]=new_map; active_labyrinth_map_id=map_id; log_game_message(f"Example map '{map_id}' created.")

# --- Labyrinth Map Persistence Functions ---
def get_labyrinth_map_path(map_id: str) -> str:
    safe_filename="".join(c for c in map_id if c.isalnum() or c in ('_','-')).rstrip();
    if not safe_filename: raise ValueError("Invalid map ID.")
    return os.path.join(LABYRINTH_MAPS_DIR,f"{safe_filename}.json")
def save_labyrinth_map_data(map_id: str, map_data_dict: dict) -> bool:
    path=get_labyrinth_map_path(map_id)
    try:
        with open(path,"w") as f: json.dump(map_data_dict,f,indent=2)
        log_game_message(f"Labyrinth Map '{map_id}' saved.");
        if map_id in loaded_labyrinth_maps: loaded_labyrinth_maps[map_id]=LabyrinthMap.from_dict(map_data_dict)
        return True
    except Exception as e: log_game_message(f"Error saving Map '{map_id}': {e}"); traceback.print_exc(); return False
def load_labyrinth_map_data(map_id: str) -> LabyrinthMap | None:
    path=get_labyrinth_map_path(map_id)
    try:
        if os.path.exists(path):
            with open(path,"r") as f: data=json.load(f); labyrinth_map=LabyrinthMap.from_dict(data)
            loaded_labyrinth_maps[map_id]=labyrinth_map; log_game_message(f"Map '{map_id}' loaded."); return labyrinth_map
        return None
    except Exception as e: log_game_message(f"Error loading Map '{map_id}': {e}"); traceback.print_exc(); return None
def list_labyrinth_map_files() -> list[str]:
    try: return [f.replace(".json","") for f in os.listdir(LABYRINTH_MAPS_DIR) if f.endswith(".json")] if os.path.exists(LABYRINTH_MAPS_DIR) else []
    except Exception as e: log_game_message(f"Error list Maps: {e}"); return []

# --- Scrap Code Definitions ---
PREDEFINED_SCRAP_CODE = {
    "random_walk_function": { "name": "Random Walk Func", "description": "A func `do_random_walk(api,sx,sy,len,char)`...", "type": "function_snippet", "code": "def do_random_walk(api, start_x, start_y, length, walk_char):\n    x, y = start_x, start_y\n    for _ in range(length):\n        direction = random.randint(0,3)\n        if direction==0 and y>0: y-=1\n        elif direction==1 and x<api.GRID_WIDTH-1: x+=1\n        elif direction==2 and y<api.GRID_HEIGHT-1: y+=1\n        elif direction==3 and x>0: x-=1\n    return x,y"},
    "place_player_snippet": { "name": "Place Player Center", "description": "Places 'player' entity at grid center.", "type": "action_block", "code": "px=game.GRID_WIDTH//2; py=game.GRID_HEIGHT//2\ngame.place_entity('player_0','player',px,py,'@',{'faction_id':'player_faction_1','health':100})"},
    "simple_sentry_loop": { "name": "Basic Sentry AI (Entity)", "description": "Simple on_tick() to find targets.", "type": "entity_script_template", "code": "def on_tick():\n    nearby=game.get_entities_in_radius(5)\n    if nearby: game.log_message(f'Sentry sees {len(nearby)} entities.')"}
}
# --- Sandboxed Game API for Room Generation ---
class GenerationGameAPI:
    def __init__(self, seed, room_params):
        self.grid = [[DEFAULT_FLOOR for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]; self.entities = {}; self.seed = seed; self.room_params = room_params; random.seed(seed)
        self.GRID_WIDTH = GRID_WIDTH; self.GRID_HEIGHT = GRID_HEIGHT; self.action_log = []
    def _log_api_action(self,m): self.action_log.append(m)
    def set_tile(self,x,y,char,p=None):
        if not(0<=x<GRID_WIDTH and 0<=y<GRID_HEIGHT): raise ValueError(f"set_tile out of bounds")
        self.grid[y][x]=char; self._log_api_action(f"set_tile({x},{y},'{char}',p={p})")
    def get_tile(self,x,y):
        if not(0<=x<GRID_WIDTH and 0<=y<GRID_HEIGHT): raise ValueError(f"get_tile out of bounds")
        return self.grid[y][x]
    def draw_line(self,x1,y1,x2,y2,char,p=None):
        self._log_api_action(f"draw_line({x1},{y1} to {x2},{y2},'{char}')")
        if x1==x2: [self.set_tile(x1,y,char,p) for y in range(min(y1,y2),max(y1,y2)+1)]
        elif y1==y2: [self.set_tile(x,y1,char,p) for x in range(min(x1,x2),max(x1,x2)+1)]
        else: raise NotImplementedError("Diagonal lines not yet in draw_line.")
    def fill_rect(self,x,y,w,h,char,p=None):
        self._log_api_action(f"fill_rect({x},{y},w={w},h={h},'{char}')")
        for i in range(w):
            for j in range(h): self.set_tile(x+i,y+j,char,p)
    def place_entity(self,eid,type,x,y,char,p=None):
        if not(0<=x<GRID_WIDTH and 0<=y<GRID_HEIGHT): raise ValueError(f"place_entity out of bounds")
        edata={"id":eid,"type":type,"x":x,"y":y,"char":char}; edata.update(p or {}); edata.setdefault('faction_id',self.room_params.get('default_faction','neutral'))
        self.entities[eid]=edata; self._log_api_action(f"Placed {eid}({type}) at ({x},{y})")
    def get_random_int(self,m,n): return random.randint(m,n)
    def get_random_coord(self): return (random.randint(0,GRID_WIDTH-1),random.randint(0,GRID_HEIGHT-1))
    def display_generation_message(self,msg): self._log_api_action(f"Msg: {msg}")
    def get_generated_data(self): return self.grid,self.entities,self.action_log
    def call_fractal_bloom(self, params: dict) -> dict:
        log_msg = f"Generation API: call_fractal_bloom({params}) called (Placeholder)."
        self._log_api_action(log_msg)
        dummy_pattern = {"pattern_type":"simple_line_set","lines":[{"x1":5,"y1":5,"x2":15,"y2":5,"char":"~"},{"x1":5,"y1":6,"x2":15,"y2":6,"char":"-"}],"message":"Placeholder fractal pattern."}
        return dummy_pattern
    def get_gateway_info(self, gateway_id: str) -> dict:
        log_msg = f"Generation API: get_gateway_info('{gateway_id}') called (Placeholder)."
        self._log_api_action(log_msg)
        dummy_info = {"id":gateway_id,"status":"conceptual","target_realm_type":"unknown_dimension","activation_code_hint":"✨🌲🤖","message":f"Placeholder info for Gateway '{gateway_id}'."}
        if gateway_id=="main_exit": dummy_info["target_realm_type"]="next_level_hub"
        return dummy_info

# --- Procedural Generation (default, uses GenerationGameAPI) ---
def generate_room_default(seed, room_params):
    api=GenerationGameAPI(seed,room_params); api.fill_rect(0,0,GRID_WIDTH,1,DEFAULT_WALL); api.fill_rect(0,GRID_HEIGHT-1,GRID_WIDTH,1,DEFAULT_WALL)
    api.fill_rect(0,1,1,GRID_HEIGHT-2,DEFAULT_WALL); api.fill_rect(GRID_WIDTH-1,1,1,GRID_HEIGHT-2,DEFAULT_WALL)
    px,py = room_params.get("player_start_x",GRID_WIDTH//2), room_params.get("player_start_y",GRID_HEIGHT//2)
    if api.get_tile(px,py)==DEFAULT_WALL: px,py = GRID_WIDTH//2+1,GRID_HEIGHT//2+1
    api.place_entity("player_0","player",px,py,PLAYER_CHAR,{"faction_id":room_params.get("player_faction","player_faction_1"),"health":100})
    for _ in range(room_params.get("internal_walls",10)):
        wx,wy=api.get_random_coord()
        if (wx,wy)!=(px,py) and wx not in [0,GRID_WIDTH-1] and wy not in [0,GRID_HEIGHT-1]: api.set_tile(wx,wy,DEFAULT_WALL)
    return api.get_generated_data()

# --- Runtime Game API ---
class RuntimeGameAPI:
    def __init__(self, entity_id, current_game_state):
        self.entity_id=entity_id; self.game_state=current_game_state; self.action_log=[]
        self.GRID_WIDTH=GRID_WIDTH; self.GRID_HEIGHT=GRID_HEIGHT
    def _log_api_action(self,m): self.action_log.append(m)
    def get_self_id(self): return self.entity_id
    def get_self_properties(self): return self.game_state["entities"].get(self.entity_id,{}).copy()
    def get_self_property(self,pname): return self.game_state["entities"].get(self.entity_id,{}).get(pname)
    def set_self_property(self,pname,val):
        if self.entity_id in self.game_state["entities"]: self.game_state["entities"][self.entity_id][pname]=val; self._log_api_action(f"set_self_prop('{pname}',{val})")
        else: self._log_api_action(f"Error: Entity {self.entity_id} not found to set property.")
    def get_entity_properties(self,target_id): entity=self.game_state["entities"].get(target_id); return entity.copy() if entity else None
    def get_player_position(self): player=self.game_state["entities"].get(self.game_state["player_id"]); return (player["x"],player["y"]) if player else None
    def move_self(self,dx,dy):
        entity=self.game_state["entities"].get(self.entity_id)
        if not entity: self._log_api_action(f"move_self failed: entity {self.entity_id} not found."); return False
        ox,oy=entity["x"],entity["y"]; nx,ny=ox+dx,oy+dy
        if not(0<=nx<GRID_WIDTH and 0<=ny<GRID_HEIGHT): self._log_api_action(f"move_self({dx},{dy}) failed: out of bounds."); return False
        if self.game_state["current_room_grid"][ny][nx]==DEFAULT_WALL: self._log_api_action(f"move_self({dx},{dy}) failed: wall at ({nx},{ny})."); return False
        for oid,oentity in self.game_state["entities"].items():
            if oid!=self.entity_id and oentity["x"]==nx and oentity["y"]==ny: self._log_api_action(f"move_self({dx},{dy}) failed: entity collision at ({nx},{ny})."); return False
        entity["x"],entity["y"]=nx,ny; self._log_api_action(f"move_self({dx},{dy}) to ({nx},{ny})."); return True
    def get_tile_info(self,x,y):
        if not(0<=x<GRID_WIDTH and 0<=y<GRID_HEIGHT): raise ValueError("get_tile_info out of bounds.")
        char=self.game_state["current_room_grid"][y][x]; return {"char":char, "is_wall":char==DEFAULT_WALL}
    def get_entities_in_radius(self,radius,ttype=None,tfaction=None):
        nearby=[]; sprops=self.game_state["entities"].get(self.entity_id);
        if not sprops: return []
        for eid,edata in self.game_state["entities"].items():
            if eid==self.entity_id: continue
            d_sq=(sprops["x"]-edata["x"])**2 + (sprops["y"]-edata["y"])**2
            if d_sq <= radius**2:
                if ttype and edata.get("type")!=ttype: continue
                if tfaction and edata.get("faction_id")!=tfaction: continue
                nearby.append(edata.copy())
        return nearby
    def log_message(self,msg): self._log_api_action(f"Log: {str(msg)}")
    def get_action_log(self): return self.action_log
    def call_procast_engine(self, task_type: str, params: dict) -> dict:
        log_msg = f"Runtime API (Entity '{self.entity_id}'): call_procast_engine('{task_type}', {params}) (Placeholder)."
        self._log_api_action(log_msg)
        dummy_result = {"task_id":f"proc_{task_type}_{random.randint(1000,9999)}","status":"pending_conceptual_execution","outcome_hint":"something interesting might happen later...","message":f"Placeholder task '{task_type}' submitted."}
        if task_type=="generate_lore_fragment": dummy_result["outcome_hint"]="a new legend was whispered."; dummy_result["lore_fragment_id"]=f"lore_{random.randint(1,100)}"
        return dummy_result
    def get_zero_gears_state(self, component_id: str) -> dict:
        log_msg = f"Runtime API (Entity '{self.entity_id}'): get_zero_gears_state('{component_id}') (Placeholder)."
        self._log_api_action(log_msg)
        dummy_state = {"component_id":component_id,"status":"nominal_placeholder","energy_level":random.uniform(0.5,1.0) if "engine" in component_id else random.uniform(0.1,0.5),"output_value":random.randint(0,100),"message":f"Placeholder state for ZG component '{component_id}'."}
        return dummy_state
    def spawn_entity(self, type: str, x: int, y: int, sprite_char: str, properties: dict) -> str | None:
        new_entity_id = properties.get("id", f"{type}_{random.randint(10000,99999)}")
        if new_entity_id in self.game_state["entities"]: self._log_api_action(f"spawn_entity failed: ID '{new_entity_id}' exists."); return None
        if not (0<=x<self.GRID_WIDTH and 0<=y<self.GRID_HEIGHT): self._log_api_action(f"spawn_entity failed: ({x},{y}) out of bounds."); return None
        if self.game_state["current_room_grid"][y][x]==DEFAULT_WALL: self._log_api_action(f"spawn_entity failed: wall at ({x},{y})."); return None
        for other_entity in self.game_state["entities"].values():
            if other_entity["x"]==x and other_entity["y"]==y: self._log_api_action(f"spawn_entity failed: entity collision at ({x},{y})."); return None
        entity_data={"id":new_entity_id,"type":type,"x":x,"y":y,"char":sprite_char}; entity_data.update(properties)
        entity_data.setdefault('faction_id',self.game_state["entities"].get(self.entity_id,{}).get('faction_id','neutral'))
        self.game_state["entities"][new_entity_id]=entity_data; self._log_api_action(f"Spawned '{new_entity_id}' at ({x},{y})."); return new_entity_id

# --- Entity Script Execution (as before) ---
MAX_ENTITY_SCRIPT_EXEC_TIME = 0.1
processed_entity_scripts = {}
def execute_entity_script(eid,code,state):
    api=RuntimeGameAPI(eid,state); g={"game":api,"__builtins__":{k:v for k,v in __builtins__.__dict__.items() if k in ["abs","all","any","bin","bool","bytearray","bytes","callable","chr","complex","dict","divmod","enumerate","filter","float","format","frozenset","getattr","hasattr","hash","hex","int","isinstance","issubclass","iter","len","list","map","max","min","next","object","oct","ord","pow","print","range","repr","reversed","round","set","slice","sorted","str","sum","super","tuple","type","zip","ValueError","TypeError","NotImplementedError","AttributeError","KeyError","IndexError","Exception"]}}; g["__builtins__"]["print"]=api.log_message; g["__builtins__"]["random"]=random; l={}
    fn_name="on_tick"
    try:
        exec(code,g,l); func=l.get(fn_name) or g.get(fn_name)
        if not callable(func): raise NameError(f"Script must define callable '{fn_name}()'")
        st=time.time(); func()
        if time.time()-st > MAX_ENTITY_SCRIPT_EXEC_TIME: raise TimeoutError(f"Exec time > {MAX_ENTITY_SCRIPT_EXEC_TIME}s")
    except Exception as e: err_msg=f"Entity Script Error ({eid}): {type(e).__name__}: {e}\n{traceback.format_exc(limit=2)}"; log_game_message(err_msg); api._log_api_action(f"ERROR: {err_msg}")
    return api.get_action_log()

# --- Game Loop / Turn System (as before) ---
def process_game_tick():
    log_game_message("--- Processing Game Tick ---")
    eids = list(game_state["entities"].keys())
    for eid in eids:
        if eid not in game_state["entities"]: continue
        entity = game_state["entities"][eid]; sname = entity.get("script_name")
        if sname:
            scode = processed_entity_scripts.get(sname)
            if not scode:
                loaded = load_player_script(sname,ENTITY_SCRIPTS_SUBDIR)
                if loaded: scode=loaded; processed_entity_scripts[sname]=scode
                else: log_game_message(f"Warning: Could not load script '{sname}' for '{eid}'."); continue
            if scode:
                actions = execute_entity_script(eid,scode,game_state)
                if actions: [log_game_message(f"Entity '{eid}' ({sname}): {a}") for a in actions]
    log_game_message("--- Game Tick Processed ---")

# --- Game State Initialization (as before, uses Emojidex if present in room_params) ---
game_state = {}
default_room_params = {"player_start_x":GRID_WIDTH//2,"player_start_y":GRID_HEIGHT//2,"player_faction":"player_faction_1","internal_walls":15,"default_faction":"neutral_generated"}
def initialize_global_game_state():
    global game_state, active_labyrinth_map_id, loaded_labyrinth_maps, game_log_messages, default_room_params
    _initialize_example_labyrinth()
    current_options = game_state.get("current_game_options", {"game_mode": "sandbox"})
    game_state["current_game_options"] = current_options
    log_game_message(f"Initializing game with mode: {current_options.get('game_mode')}")
    current_map_to_load = active_labyrinth_map_id
    if not current_map_to_load or current_map_to_load not in loaded_labyrinth_maps:
        log_game_message(f"No valid active map ('{current_map_to_load}'). Defaulting to example map for init.")
        _initialize_example_labyrinth(); current_map_to_load = active_labyrinth_map_id
        if not current_map_to_load or current_map_to_load not in loaded_labyrinth_maps:
            log_game_message("CRITICAL: Example map failed. Defaulting to single room."); cseed=int(time.time()); cparams=default_room_params.copy()
            grid,entities,_=generate_room_default(cseed,cparams); pid=next((i for i,d in entities.items() if d.get("type")=="player"),"player_fallback")
            if pid=="player_fallback" and pid not in entities: entities[pid]={"id":pid,"x":GRID_WIDTH//2,"y":GRID_HEIGHT//2,"char":PLAYER_CHAR,"type":"player"}
            game_state.update({"current_labyrinth_map_id":None,"current_room_id":"standalone_room","player_id":pid,"player_x":entities[pid]["x"],"player_y":entities[pid]["y"],"current_room_grid":grid,"entities":entities,"current_seed":cseed,"current_room_params":cparams,"current_script_name":"default_room"})
            log_game_message("Initialized with single fallback room."); return
    current_map = loaded_labyrinth_maps[current_map_to_load]; start_room_id = current_map.start_room_id; start_room_node = current_map.get_room(start_room_id)
    if not start_room_node:
        log_game_message(f"CRITICAL: Start room '{start_room_id}' not in map. Falling back.");
        if current_map.rooms: start_room_id = list(current_map.rooms.keys())[0]; start_room_node = current_map.get_room(start_room_id); log_game_message(f"Using first room '{start_room_id}' as start.")
        else: active_labyrinth_map_id = None; initialize_global_game_state(); return
    cseed=int(time.time()); cparams=start_room_node.room_params.copy(); cparams.setdefault("player_faction","player_faction_1")
    emoji_seed_str = cparams.get("emoji_seed_string")
    if emoji_seed_str: log_game_message(f"Room '{start_room_id}' Emojidex: '{emoji_seed_str}'"); emoji_s,emoji_p=process_emoji_string(emoji_seed_str); cseed=emoji_s; cparams.update(emoji_p)
    elif cparams.get("fixed_seed") is not None: cseed = cparams["fixed_seed"]
    gen_script_code = load_player_script(start_room_node.generator_script_name, GEN_SCRIPTS_SUBDIR)
    if not gen_script_code:
        if start_room_node.generator_script_name == "default_room": grid,entities,_ = generate_room_default(cseed, cparams)
        else: log_game_message(f"ERROR: Script for room '{start_room_id}' not found. Using fallback."); grid,entities,_ = generate_room_default(cseed, default_room_params.copy())
    else:
        grid_data, ent_data, _, error_msg = execute_generation_script(gen_script_code, cseed, cparams)
        if error_msg: log_game_message(f"ERROR script for room '{start_room_id}': {error_msg}. Using fallback."); grid,entities,_ = generate_room_default(cseed, default_room_params.copy())
        else: grid,entities = grid_data, ent_data
    pid=next((i for i,d in entities.items() if d.get("type")=="player"),None)
    if not pid:
        log_game_message(f"Warning: Start room script no player. Adding default."); px,py=GRID_WIDTH//2,GRID_HEIGHT//2
        if grid[py][px]==DEFAULT_WALL: px,py=next((x for x_ in range(1,GRID_WIDTH-1) for y_ in range(1,GRID_HEIGHT-1) if grid[y_][x_]!=DEFAULT_WALL),GRID_WIDTH//2+1), next((y for x_ in range(1,GRID_WIDTH-1) for y_ in range(1,GRID_HEIGHT-1) if grid[y_][x_]!=DEFAULT_WALL),GRID_HEIGHT//2+1)
        pid="player_map_fallback"; entities[pid]={"id":pid,"x":px,"y":py,"char":PLAYER_CHAR,"type":"player","faction_id":cparams.get("player_faction","player_faction_1")}
    game_state.update({"current_labyrinth_map_id":current_map_to_load,"current_room_id":start_room_id,"player_id":pid,"player_x":entities[pid]["x"],"player_y":entities[pid]["y"],"current_room_grid":grid,"entities":entities,"current_seed":cseed,"current_room_params":cparams,"current_script_name":start_room_node.generator_script_name})
    if "current_game_options" not in game_state: game_state["current_game_options"]={"game_mode":"sandbox"}
    log_game_message(f"Initialized Labyrinth: '{current_map_to_load}', Room: '{start_room_id}'. Mode: {game_state['current_game_options']['game_mode']}. Seed: {cseed}")
initialize_global_game_state()

# --- Script Persistence (as before) ---
def get_script_path(sname,stype=GEN_SCRIPTS_SUBDIR): safe_fn="".join(c for c in sname if c.isalnum() or c in ('_','-')).rstrip(); if not safe_fn: raise ValueError("Invalid script name."); return os.path.join(SCRIPTS_DIR,stype,f"{safe_fn}.py")
def save_player_script(sname,scode,stype=GEN_SCRIPTS_SUBDIR): path=get_script_path(sname,stype); try: open(path,"w").write(scode); log_game_message(f"Script '{sname}' saved."); return True; except Exception as e: log_game_message(f"Error saving '{sname}': {e}"); return False
def load_player_script(sname,stype=GEN_SCRIPTS_SUBDIR): path=get_script_path(sname,stype); try: return open(path,"r").read() if os.path.exists(path) else None; except Exception as e: log_game_message(f"Error loading '{sname}': {e}"); return None
def list_player_scripts(stype=GEN_SCRIPTS_SUBDIR): dpath=os.path.join(SCRIPTS_DIR,stype); try: return [f.replace(".py","") for f in os.listdir(dpath) if f.endswith(".py")] if os.path.exists(dpath) else []; except Exception as e: log_game_message(f"Error list scripts: {e}"); return []

# --- Sandboxed Generation Script Execution (as before) ---
def execute_generation_script(scode,seed,params):
    api=GenerationGameAPI(seed,params); g={"game":api,"__builtins__":{k:v for k,v in __builtins__.__dict__.items() if k in ["abs","all","any","bin","bool","bytearray","bytes","callable","chr","complex","dict","divmod","enumerate","filter","float","format","frozenset","getattr","hasattr","hash","hex","int","isinstance","issubclass","iter","len","list","map","max","min","next","object","oct","ord","pow","print","range","repr","reversed","round","set","slice","sorted","str","sum","super","tuple","type","zip","ValueError","TypeError","NotImplementedError","AttributeError","KeyError","IndexError","Exception"]}}; g["__builtins__"]["print"]=api.display_generation_message; l={}
    err_msg=None; stime=time.time()
    try:
        exec(scode,g,l); gen_func=l.get('generate_room') or g.get('generate_room')
        if not callable(gen_func): raise NameError("Script must define 'generate_room(seed,room_params)'")
        gen_func(api.seed,api.room_params)
        if time.time()-stime > MAX_SCRIPT_EXEC_TIME: raise TimeoutError(f"Exec time > {MAX_SCRIPT_EXEC_TIME}s")
    except Exception as e: err_msg=f"Script Error: {type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}"; log_game_message(err_msg); return None,None,api.action_log,err_msg
    return api.get_generated_data() + (err_msg,)

# --- API Models (ScriptPayload updated for Emojidex) ---
class MovePayload(BaseModel): direction: str
class ScriptPayload(BaseModel): script_code: str; script_name: str=None; seed:int=None; room_params:dict=None; emoji_seed_string: str = None
class RagQueryPayload(BaseModel): query_text: str
class LoadScriptPayload(BaseModel): script_name: str
class GameOptionsPayload(BaseModel): game_mode: str = "sandbox"
class EntityTemplatePayload(BaseModel): template_name:str; sprite_char:str; entity_type:str; properties:dict
class LabyrinthMapPayload(BaseModel): map_id:str; name:str; start_room_id:str|None=None; rooms:dict

# --- Entity Template Persistence Functions (as before) ---
def get_entity_template_path(template_name: str) -> str:
    safe_filename = "".join(c for c in template_name if c.isalnum() or c in ('_', '-')).rstrip()
    if not safe_filename: raise ValueError("Invalid entity template name.")
    return os.path.join(ENTITY_TEMPLATES_DIR, f"{safe_filename}.json")
def save_entity_template_data(template_name: str, template_data: dict) -> bool:
    path = get_entity_template_path(template_name)
    try:
        full_data_to_save = {"template_name":template_name, "sprite_char":template_data.get("sprite_char"), "entity_type":template_data.get("entity_type"), "properties":template_data.get("properties",{})}
        with open(path,"w") as f: json.dump(full_data_to_save,f,indent=2)
        log_game_message(f"Entity Template '{template_name}' saved."); return True
    except Exception as e: log_game_message(f"Error saving entity template '{template_name}': {e}"); return False
def load_entity_template_data(template_name: str) -> dict | None:
    path = get_entity_template_path(template_name)
    try: return json.load(open(path,"r")) if os.path.exists(path) else None
    except Exception as e: log_game_message(f"Error loading entity template '{template_name}': {e}"); return None
def list_entity_template_files() -> list[str]:
    try: return [f.replace(".json","") for f in os.listdir(ENTITY_TEMPLATES_DIR) if f.endswith(".json")] if os.path.exists(ENTITY_TEMPLATES_DIR) else []
    except Exception as e: log_game_message(f"Error listing entity templates: {e}"); return []

# --- Helper function to load/switch to a new room (Updated for Emojidex) ---
def switch_to_room(target_room_id: str, entry_coords: tuple[int, int], player_entity_data: dict):
    global game_state, active_labyrinth_map_id, loaded_labyrinth_maps, default_room_params
    if not active_labyrinth_map_id or active_labyrinth_map_id not in loaded_labyrinth_maps:
        log_game_message(f"Error switching room: No active labyrinth map '{active_labyrinth_map_id}'."); return False
    current_map = loaded_labyrinth_maps[active_labyrinth_map_id]
    target_room_node = current_map.get_room(target_room_id)
    if not target_room_node:
        log_game_message(f"Error switching room: Target room '{target_room_id}' not in map '{active_labyrinth_map_id}'."); return False

    room_final_seed = int(time.time())
    room_final_params = target_room_node.room_params.copy() if target_room_node.room_params else default_room_params.copy()
    emoji_seed_str_from_room = room_final_params.get("emoji_seed_string")
    if emoji_seed_str_from_room:
        log_game_message(f"Room '{target_room_id}' uses Emojidex string: '{emoji_seed_str_from_room}'")
        emoji_seed, emoji_params = process_emoji_string(emoji_seed_str_from_room)
        room_final_seed = emoji_seed
        if emoji_params: room_final_params.update(emoji_params)
        log_game_message(f"Emojidex seed for room '{target_room_id}': {room_final_seed}, merged params: {room_final_params}")
    elif room_final_params.get("fixed_seed") is not None: room_final_seed = room_final_params["fixed_seed"]

    gen_script_code = load_player_script(target_room_node.generator_script_name, GEN_SCRIPTS_SUBDIR)
    if not gen_script_code:
        if target_room_node.generator_script_name == "default_room": new_grid, new_entities, _ = generate_room_default(room_final_seed, room_final_params)
        else: log_game_message(f"Error: Script '{target_room_node.generator_script_name}' not found for room '{target_room_id}'."); return False
    else:
        grid_data, ent_data, _, error_msg = execute_generation_script(gen_script_code, room_final_seed, room_final_params)
        if error_msg: log_game_message(f"Error executing gen script for room '{target_room_id}': {error_msg}."); return False
        new_grid, new_entities = grid_data, ent_data

    game_state["current_room_id"] = target_room_id; game_state["current_room_grid"] = new_grid
    game_state["current_seed"] = room_final_seed; game_state["current_room_params"] = room_final_params
    game_state["current_script_name"] = target_room_node.generator_script_name
    temp_new_room_entities = new_entities.copy(); game_state["entities"] = {}
    for eid, edata in temp_new_room_entities.items():
        if edata.get("type") == "player": continue
        game_state["entities"][eid] = edata
    player_entity_data["x"], player_entity_data["y"] = entry_coords[0], entry_coords[1]
    game_state["entities"][game_state["player_id"]] = player_entity_data
    game_state["player_x"], game_state["player_y"] = entry_coords[0], entry_coords[1]
    log_game_message(f"Switched to room: '{target_room_id}'. Player at ({entry_coords[0]},{entry_coords[1]}). Seed: {room_final_seed}."); return True

# --- API Endpoints ---
@app.get("/",response_class=HTMLResponse)
async def read_root(r:Request): dgrid=[row[:] for row in game_state["current_room_grid"]]; p=game_state["entities"].get(game_state["player_id"]); if p: dgrid[p["y"]][p["x"]]=p["char"]; return templates.TemplateResponse("index.html",{"request":r,"initial_grid":dgrid,"GRID_WIDTH":GRID_WIDTH,"GRID_HEIGHT":GRID_HEIGHT,"TILE_SIZE":15})

@app.get("/level-creator-view", response_class=HTMLResponse)
async def level_creator_page(request: Request): return templates.TemplateResponse("level_creator.html", {"request": request})

@app.get("/get_game_state",response_class=JSONResponse)
async def get_game_state_endpoint(): return {"room_grid":game_state["current_room_grid"],"entities":game_state["entities"],"player_id":game_state["player_id"],"game_log":game_log_messages,"current_script_name":game_state.get("current_script_name","default_room"), "current_game_options": game_state.get("current_game_options", {"game_mode": "sandbox"})}

@app.post("/move_player", response_class=JSONResponse)
async def move_player_endpoint(payload: MovePayload):
    player_id = game_state["player_id"]; player = game_state["entities"].get(player_id)
    if not player: log_game_message(f"Move Error: Player '{player_id}' not found."); raise HTTPException(status_code=500, detail="Player entity not found")
    player_copy_for_transition = player.copy()
    old_x, old_y = player["x"], player["y"]; new_x, new_y = old_x, old_y
    direction = payload.direction.lower(); moved_within_room = False
    if direction=="up" and new_y>0: new_y-=1; moved_within_room=True
    elif direction=="down" and new_y<GRID_HEIGHT-1: new_y+=1; moved_within_room=True
    elif direction=="left" and new_x>0: new_x-=1; moved_within_room=True
    elif direction=="right" and new_x<GRID_WIDTH-1: new_x+=1; moved_within_room=True
    else:
        if not moved_within_room and direction in ["up","down","left","right"]: log_game_message(f"Player move {direction} blocked at boundary.")
        else: log_game_message(f"Invalid move direction: {payload.direction}"); raise HTTPException(status_code=400, detail=f"Invalid direction: {payload.direction}")
        return JSONResponse(status_code=200, content={"message":"Move blocked by boundary or invalid.","player_x":old_x,"player_y":old_y,"room_grid":game_state["current_room_grid"],"entities":game_state["entities"],"game_log":game_log_messages})
    if not moved_within_room: return JSONResponse(status_code=400, detail="Move failed unexpectedly pre-collision.")
    if game_state["current_room_grid"][new_y][new_x] == DEFAULT_WALL:
        log_game_message(f"Movement blocked by wall at ({new_x},{new_y}).")
        return JSONResponse(status_code=200, content={"message": f"Blocked by wall at ({new_x},{new_y}).", "player_x": old_x, "player_y": old_y, "room_grid": game_state["current_room_grid"], "entities": game_state["entities"], "game_log": game_log_messages})
    room_transitioned = False
    if active_labyrinth_map_id and active_labyrinth_map_id in loaded_labyrinth_maps:
        current_map = loaded_labyrinth_maps[active_labyrinth_map_id]; current_room_node = current_map.get_room(game_state["current_room_id"])
        if current_room_node:
            for conn_id, conn_data in current_room_node.connections.items():
                if conn_data.source_exit_coords == (new_x, new_y):
                    log_game_message(f"Player at exit '{conn_id}' to room '{conn_data.target_room_id}' at ({new_x},{new_y}).")
                    if switch_to_room(conn_data.target_room_id, conn_data.target_entry_coords, player_copy_for_transition):
                        room_transitioned = True
                        return {"message": f"Transitioned to room '{game_state['current_room_id']}' via '{conn_id}'.", "room_grid": game_state["current_room_grid"], "entities": game_state["entities"], "player_id": game_state["player_id"], "game_log": game_log_messages, "room_switched": True, "current_script_name": game_state["current_script_name"], "current_room_params": game_state["current_room_params"], "current_seed": game_state["current_seed"]}
                    else:
                        log_game_message(f"Room transition via '{conn_id}' failed."); return JSONResponse(status_code=200, content={"message": f"Failed to transition via portal '{conn_id}'.", "player_x": old_x, "player_y": old_y, "room_grid": game_state["current_room_grid"], "entities": game_state["entities"], "game_log": game_log_messages})
                    break
    if not room_transitioned:
        player["x"],player["y"]=new_x,new_y; game_state["player_x"],game_state["player_y"]=new_x,new_y
        log_game_message(f"Player moved {direction} to ({new_x},{new_y}) in room '{game_state['current_room_id']}'.")
        return {"message":f"Player moved {direction}.","room_grid":game_state["current_room_grid"],"entities":game_state["entities"],"game_log":game_log_messages}
    return JSONResponse(status_code=500, content={"error": "Unexpected error in move player endpoint."})

@app.post("/generate_room_script", response_class=JSONResponse)
async def generate_room_script_endpoint(payload: ScriptPayload):
    log_game_message(f"Request to generate room from script '{payload.script_name or 'untitled'}'.")
    final_seed = payload.seed
    final_params = payload.room_params if payload.room_params is not None else default_room_params.copy()
    if payload.emoji_seed_string:
        log_game_message(f"Processing emoji seed string: '{payload.emoji_seed_string}'")
        emoji_seed, emoji_params = process_emoji_string(payload.emoji_seed_string)
        final_seed = emoji_seed
        if emoji_params: final_params.update(emoji_params)
        log_game_message(f"Using Emojidex seed: {final_seed}, merged params: {final_params}")
    elif final_seed is None: final_seed = int(time.time()); log_game_message(f"No seed provided, using time-based: {final_seed}")
    new_grid, new_entities, script_actions, error = execute_generation_script(payload.script_code, final_seed, final_params)
    if script_actions: [log_game_message(f"Script Action: {a}") for a in actions]
    if error: log_game_message(f"Script gen failed: {error}"); return JSONResponse(400,{"error":error,"game_log":game_log_messages,"script_actions":script_actions})
    game_state["current_room_grid"]=new_grid; game_state["entities"]=new_entities; game_state["current_seed"]=final_seed
    game_state["current_room_params"]=final_params; game_state["current_script_name"]=payload.script_name or "untitled_live_script"
    npid=next((i for i,d in new_entities.items() if d.get("type")=="player"),None)
    if npid: game_state["player_id"]=npid; game_state["player_x"]=new_entities[npid]["x"]; game_state["player_y"]=new_entities[npid]["y"]
    else:
        log_game_message("Warning: Gen room no player. Adding default."); px,py=GRID_WIDTH//2,GRID_HEIGHT//2
        # Ensure grid is accessible for the check, might need to use new_grid if it's the most current
        current_grid_for_check = new_grid if new_grid is not None else game_state["current_room_grid"]
        if current_grid_for_check[py][px]==DEFAULT_WALL: px,py=next((x for x_ in range(1,GRID_WIDTH-1) for y_ in range(1,GRID_HEIGHT-1) if current_grid_for_check[y_][x_]!=DEFAULT_WALL),GRID_WIDTH//2+1), next((y for x_ in range(1,GRID_WIDTH-1) for y_ in range(1,GRID_HEIGHT-1) if current_grid_for_check[y_][x_]!=DEFAULT_WALL),GRID_HEIGHT//2+1)
        game_state["player_id"]="player_fallback"; game_state["entities"]["player_fallback"]={"id":"player_fallback","x":px,"y":py,"char":PLAYER_CHAR,"type":"player","faction_id":final_params.get("player_faction","player_faction_1")}
        game_state["player_x"],game_state["player_y"]=px,py; new_grid[py][px]=PLAYER_CHAR
    log_game_message(f"Player '{game_state['player_id']}' at ({game_state['player_x']},{game_state['player_y']}).")
    log_game_message(f"Room gen and loaded from script '{payload.script_name or 'untitled'}'. Seed: {final_seed}")
    return {"message":"Room generated & loaded!","room_grid":new_grid,"entities":new_entities,"player_id":game_state["player_id"],"seed_used":final_seed,"params_used":final_params,"game_log":game_log_messages,"script_actions":script_actions}

@app.post("/save_script",response_class=JSONResponse)
async def save_script_endpoint(pld:ScriptPayload):
    if not pld.script_name: raise HTTPException(400,"Script name required.")
    if save_player_script(pld.script_name,pld.script_code,GEN_SCRIPTS_SUBDIR): return {"message":f"Script '{pld.script_name}' saved.","game_log":game_log_messages}
    return JSONResponse(500,{"error":f"Failed to save script '{pld.script_name}'.","game_log":game_log_messages})

@app.get("/list_scripts/{script_type}",response_class=JSONResponse)
async def list_scripts_endpoint(stype:str):
    if stype not in [GEN_SCRIPTS_SUBDIR,ENTITY_SCRIPTS_SUBDIR]: raise HTTPException(400,"Invalid script type.")
    return {"scripts":list_player_scripts(stype),"game_log":game_log_messages}

@app.post("/load_script",response_class=JSONResponse)
async def load_script_endpoint(pld:LoadScriptPayload):
    scode=load_player_script(pld.script_name,GEN_SCRIPTS_SUBDIR)
    if scode is not None: log_game_message(f"Script '{pld.script_name}' loaded."); return {"script_name":pld.script_name,"script_code":scode,"game_log":game_log_messages}
    log_game_message(f"Failed to load script '{pld.script_name}'."); return JSONResponse(404,{"error":f"Script '{pld.script_name}' not found.","game_log":game_log_messages})

@app.post("/rag_query", response_class=JSONResponse)
async def rag_query_endpoint(payload: RagQueryPayload):
    log_game_message(f"RAG Query received: {payload.query_text}")
    query = payload.query_text.lower()
    response_text = f"RAG: I'm not sure about '{payload.query_text}'. Try 'help quest', 'sandbox editor', 'level creator', 'game modes', 'emojidex', 'fractal_bloom', 'gateways', 'procast_engine', 'zero_gears', or specific API functions."

    if "help quest" in query or "list quests" in query:
        response_text = """
RAG: Available Quests:
1.  **My First Custom Bot:** (Keywords: 'custom bot quest')
2.  **Connecting Worlds:** (Keywords: 'connecting worlds quest')
3.  **Faction Skirmish Setup:** (Keywords: 'faction skirmish quest')
NEW: Ask about 'emojidex quest' for seeding with emojis.
Ask about a specific quest by its keywords.
        """
    elif "custom bot quest" in query: response_text = "RAG Quest: My First Custom Bot\nObjective: Create an entity template using the Sandbox Editor, then place instances of it using a room generation script.\nSteps:\n1.  Go to Sandbox Editor. Define Template (Name, Char 'W', Type \"bot\", Script 'random_walker.py', Props `{\"faction_id\":\"player_bots\"}`). Save.\n2.  Room Gen Script: Use `game.place_entity(\"worker1\", \"bot\", 10,10,\"W\", {\"script_name\":\"random_walker\", \"faction_id\":\"player_bots\"})`.\n3.  Run Script. Your WorkerBot should appear."
    elif "connecting worlds quest" in query: response_text = "RAG Quest: Connecting Worlds\nObjective: Use Level Creator to make two rooms and connect them. Navigate between them.\nSteps:\n1.  Go to Level Creator. Create New Map (e.g., \"MyMultiRoom\").\n2.  Add Room 1 (ID \"roomA\", Script \"default_room\"). Add Room 2 (ID \"roomB\", Script \"default_room\").\n3.  Connect: Shift-click Room A. Conn ID \"exit_roomB\", Source Coords \"49,25\", Target \"roomB\", Target Entry \"0,25\". Bidirectional. Add.\n4.  Save Map. Set Active.\n5.  Main Game: Ensure \"roomA\" script (or default_room) has a door char 'D' at (49,25). Move player to 'D'."
    elif "faction skirmish quest" in query: response_text = "RAG Quest: Faction Skirmish Setup\nObjective: Use Game Options for 'Attrition' mode. Design a room with two opposing spawners.\nSteps:\n1.  Game Options: Set Mode to 'Attrition'. Apply.\n2.  Sandbox Editor (Recommended): Create \"FighterBot\" template (Char 'F', Type 'combat_bot', Script 'sentry.py', Props `{\"health\":20}`). Create \"Spawner\" template (Char 'S', Type 'spawner', Script `faction_spawner.py`, Props for spawning your FighterBot for a faction).\n3.  Room Gen Script: Place two Spawners with different `faction_id` & `spawn_faction_to_assign` properties.\n4.  Run Game. Tick game to see units spawn.\n`faction_spawner.py` example in Design Doc or ask 'faction_spawner example'."
    elif "faction_spawner example" in query: response_text = "RAG: faction_spawner.py on_tick(): if tick % interval == 0: props=game.get_self_properties(); game.spawn_entity(type='bot', x=props['x'], y=props['y']+1, char=props.get('spawn_char','u'), props={'health':10, 'faction_id':props.get('spawn_faction_to_assign'), 'script_name':props.get('spawn_script_name')})"
    elif "emojidex" in query or "emoji seed" in query or "emojidex quest" in query: response_text = "RAG: Emojidex Seeding: Use emoji strings (e.g., 🔥💎) in Level Creator (room params) or Main Page (override input) to influence room generation seed and parameters. Check game log for processed seed/params."
    elif "fractal_bloom" in query: response_text = "RAG: `game.call_fractal_bloom(params)` (Gen API - Placeholder). Calls external system for complex patterns. Returns dummy line data for now. Use its output (e.g., lines) to draw in your room."
    elif "gateway" in query: response_text = "RAG: `game.get_gateway_info(id)` (Gen API - Placeholder). Gets info about inter-world gateways. Returns dummy status. Use to theme portals."
    elif "procast_engine" in query: response_text = "RAG: `game.call_procast_engine(task, params)` (Runtime API - Placeholder). For entities to trigger procedural events/narrative. Returns dummy task status."
    elif "zero_gears" in query: response_text = "RAG: `game.get_zero_gears_state(id)` (Runtime API - Placeholder). For entities to query complex machinery state. Returns dummy component status."
    elif "sandbox editor" in query: response_text = "RAG: 'Sandbox Editor': Define entity templates (name, char, type, script, properties). Save/load them."
    elif "level creator" in query: response_text = "RAG: 'Level Creator' (`/level-creator-view`): Manage maps. Add rooms. Connect rooms."
    elif "game modes" in query: response_text = "RAG: 'Game Options': Set game mode (Sandbox, Attrition). Apply. May need reset."
    elif "set_tile" in query: response_text = "RAG: `game.set_tile(x,y,char,props)` (Gen API)."
    elif "place_entity" in query: response_text = "RAG: `game.place_entity(id,type,x,y,char,props)` (Gen API). Props: `script_name`, `faction_id`, `health`, etc."
    elif "move_self" in query: response_text = "RAG: `game.move_self(dx,dy)` (Runtime API)."
    elif "harvest_tile" in query: response_text = "RAG: `game.harvest_tile(x,y)` / `game.analyze_tile_code(x,y)` (Runtime API)."
    elif "spawn_entity" in query: response_text = "RAG: `game.spawn_entity(type,x,y,char,props)` (Runtime API for spawners)."
    elif "scrap code" in query: response_text = "RAG: View scraps in UI, copy to editor, adapt, integrate."
    elif "faction" in query: response_text = "RAG: Entities have `faction_id`. Set in `place_entity` (Gen) or `get_self_property` (Runtime)."

    log_game_message(f"RAG Dummy Response: {response_text[:100]}...")
    return {"rag_response": response_text, "game_log": game_log_messages}

@app.post("/set_game_options", response_class=JSONResponse)
async def set_game_options_endpoint(payload: GameOptionsPayload):
    global game_state
    game_state["current_game_options"] = {"game_mode": payload.game_mode.lower()}
    log_game_message(f"Game options updated: Mode set to {game_state['current_game_options']['game_mode']}.")
    return {"message": f"Game mode set to {game_state['current_game_options']['game_mode']}. May need manual reset/new room.",
            "updated_options": game_state["current_game_options"], "game_log": game_log_messages}

@app.post("/save_entity_template", response_class=JSONResponse)
async def save_entity_template_endpoint(payload: EntityTemplatePayload):
    if not payload.template_name.strip(): raise HTTPException(status_code=400, detail="Template name cannot be empty.")
    template_data_dict = {"sprite_char": payload.sprite_char, "entity_type": payload.entity_type, "properties": payload.properties}
    if save_entity_template_data(payload.template_name, template_data_dict):
        return {"message": f"Entity Template '{payload.template_name}' saved.", "game_log": game_log_messages}
    return JSONResponse(status_code=500, content={"error": f"Failed to save template '{payload.template_name}'.", "game_log": game_log_messages})

@app.get("/list_entity_templates", response_class=JSONResponse)
async def list_entity_templates_endpoint():
    templates = list_entity_template_files()
    return {"entity_templates": templates, "game_log": game_log_messages}

@app.get("/load_entity_template/{template_name}", response_class=JSONResponse)
async def load_entity_template_endpoint(template_name: str):
    template_data = load_entity_template_data(template_name)
    if template_data:
        log_game_message(f"Entity Template '{template_name}' loaded for editing.")
        return {"template_data": template_data, "game_log": game_log_messages}
    log_game_message(f"Failed to load entity template '{template_name}'.")
    return JSONResponse(status_code=404, content={"error": f"Entity Template '{template_name}' not found.", "game_log": game_log_messages})

@app.get("/get_available_scraps", response_class=JSONResponse)
async def get_available_scraps_endpoint():
    return {"available_scraps": PREDEFINED_SCRAP_CODE, "game_log": game_log_messages}

@app.post("/tick_game",response_class=JSONResponse)
async def tick_game_endpoint():
    process_game_tick()
    return {"message":"Game tick processed.","room_grid":game_state["current_room_grid"],"entities":game_state["entities"],"player_id":game_state["player_id"],"game_log":game_log_messages}

# Labyrinth Map Persistence API Endpoints
@app.post("/save_labyrinth_map", response_class=JSONResponse)
async def save_labyrinth_map_endpoint(payload: LabyrinthMapPayload):
    map_id = payload.map_id
    if not map_id.strip(): raise HTTPException(status_code=400, detail="Map ID cannot be empty.")
    map_data_as_dict = payload.dict()
    if save_labyrinth_map_data(map_id, map_data_as_dict):
        return {"message": f"Labyrinth Map '{map_id}' saved.", "game_log": game_log_messages}
    return JSONResponse(status_code=500, content={"error": f"Failed to save Labyrinth Map '{map_id}'.", "game_log": game_log_messages})

@app.get("/list_labyrinth_maps", response_class=JSONResponse)
async def list_labyrinth_maps_endpoint():
    maps = list_labyrinth_map_files()
    return {"labyrinth_maps": maps, "game_log": game_log_messages}

@app.get("/load_labyrinth_map/{map_id}", response_class=JSONResponse)
async def load_labyrinth_map_endpoint(map_id: str):
    labyrinth_map_obj = load_labyrinth_map_data(map_id)
    if labyrinth_map_obj:
        return {"labyrinth_map_data": labyrinth_map_obj.to_json_dict(), "game_log": game_log_messages}
    return JSONResponse(status_code=404, content={"error": f"Labyrinth Map '{map_id}' not found.", "game_log": game_log_messages})

@app.post("/set_active_labyrinth_map/{map_id}", response_class=JSONResponse)
async def set_active_labyrinth_map_endpoint(map_id: str):
    global active_labyrinth_map_id
    if not load_labyrinth_map_data(map_id):
         raise HTTPException(status_code=404, detail=f"Labyrinth map '{map_id}' not found or failed to load.")
    active_labyrinth_map_id = map_id
    log_game_message(f"Active labyrinth map set to: {map_id}.")
    initialize_global_game_state()
    return {"message": f"Active labyrinth map changed to '{map_id}'. Game re-initialized.", "active_map_id": active_labyrinth_map_id,
            "current_room_id": game_state.get("current_room_id"), "player_id": game_state.get("player_id"), "game_log": game_log_messages}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
