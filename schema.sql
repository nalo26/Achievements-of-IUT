DROP TABLE IF EXISTS done;
DROP TABLE IF EXISTS achievement;
DROP TABLE IF EXISTS user;

CREATE TABLE user (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    firstname TEXT NOT NULL,
    lastname TEXT NOT NULL,
    password TEXT NOT NULL,
    year INTEGER NOT NULL,
    score INTEGER DEFAULT 0
);

CREATE TABLE achievement(
   id_achievement INTEGER PRIMARY KEY AUTOINCREMENT,
   name TEXT NOT NULL,
   lore TEXT DEFAULT '',
   difficulty INTEGER NOT NULL,
   parent_id INTEGER,
   FOREIGN KEY(parent_id) REFERENCES achievement(id_achievement)
);

CREATE TABLE done(
   id_user INTEGER,
   id_achievement INTEGER,
   PRIMARY KEY(id_user, id_achievement),
   FOREIGN KEY(id_user) REFERENCES userr(id_user),
   FOREIGN KEY(id_achievement) REFERENCES achievement(id_achievement)
);

