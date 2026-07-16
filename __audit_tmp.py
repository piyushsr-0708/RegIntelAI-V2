import sqlite3, json
conn = sqlite3.connect('d:/SuRaksha-v2/regintel.db')
c = conn.cursor()

# Check MAP description (title) in DB vs maps JSON
c.execute("SELECT id, description, priority, ai_rationale, source_requirement_id FROM management_action_plans WHERE source_document_id='UP20260716_0002' LIMIT 3")
for row in c.fetchall():
    print("MAP DB:", dict(zip(['id','description','priority','ai_rationale','source_requirement_id'], row)))

print()

# Check control name in DB
c.execute("SELECT cc.control_id, cc.name, cc.objective, cc.description FROM compliance_controls cc WHERE cc.control_id LIKE 'UP20260716_0002%' LIMIT 3")
for row in c.fetchall():
    print("Control DB:", dict(zip(['control_id','name','objective','description'], row)))

print()

# Check if MAP.control_id (UUID) links to compliance_controls.id (UUID)
c.execute("SELECT map.id, map.control_id, cc.control_id as ctrl_ext_id, cc.name FROM management_action_plans map JOIN compliance_controls cc ON map.control_id = cc.id WHERE map.source_document_id='UP20260716_0002' LIMIT 3")
for row in c.fetchall():
    print("MAP->Control join:", dict(zip(['map_id','map_control_uuid','ctrl_ext_id','ctrl_name'], row)))

print()

# Check requirement in DB
c.execute("SELECT requirement_id, requirement_type, criticality FROM requirements WHERE requirement_id LIKE 'UP20260716_0002%' LIMIT 3")
for row in c.fetchall():
    print("Req DB:", dict(zip(['requirement_id','requirement_type','criticality'], row)))

print()

# Check if MAP.id in DB matches maps JSON map_id
with open('d:/SuRaksha-v2/datasets/maps/UP20260716_0002.json', 'r') as f:
    maps_json = json.load(f)
json_map_ids = {m['map_id'] for m in maps_json['maps']}
c.execute("SELECT id FROM management_action_plans WHERE source_document_id='UP20260716_0002'")
db_map_ids = {r[0] for r in c.fetchall()}
print("JSON map_ids count:", len(json_map_ids))
print("DB map ids count:", len(db_map_ids))
print("IDs in JSON but not DB:", len(json_map_ids - db_map_ids))
print("IDs in DB but not JSON:", len(db_map_ids - json_map_ids))

conn.close()
