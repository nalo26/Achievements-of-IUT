import json

path = "static/Achievements.json"
data = []
with open(path, 'r', encoding="utf-8") as mf:
    data = json.load(mf)
mf.close()

base = open("populate.sql", 'w', encoding="utf-8")

auto_id = 0

def add(element, parent_id=None):
    global auto_id
    auto_id += 1
    
    element_id = auto_id
    
    name = element['name'].replace("'", "''")
    lore = element['lore'].replace("'", "''")
    query = f"INSERT INTO Achievement (id_achievement, name, lore, difficulty{', parent_id' if parent_id is not None else ''}) " + \
            f"VALUES ({auto_id}, '{name}', '{lore}', {element['difficulty']}{f', {parent_id}' if parent_id is not None else ''});\n"
    base.write(query)
    
    if "childs" in element.keys():
        for child in element['childs']:
            add(child, element_id)


base = open("populate.sql", 'w', encoding="utf-8")

for child in data:
    add(child)
    
base.close()
