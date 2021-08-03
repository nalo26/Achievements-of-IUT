DROP TABLE IF EXISTS done;
DROP TABLE IF EXISTS achievement;
DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS discord_user;

CREATE TABLE discord_user (
   id_user INTEGER PRIMARY KEY,
   firstname TEXT NOT NULL,
   lastname TEXT NOT NULL,
   year INTEGER NOT NULL,
   avatar TEXT NOT NULL
);

CREATE TABLE user (
   id_user INTEGER PRIMARY KEY,
   joindate DATETIME DEFAULT CURRENT_TIMESTAMP,
   score INTEGER DEFAULT 0,
   FOREIGN KEY(id_user) REFERENCES discord_user(id_user)
);

CREATE TABLE achievement(
   id_achievement INTEGER PRIMARY KEY AUTOINCREMENT,
   name TEXT NOT NULL,
   lore TEXT DEFAULT '',
   difficulty INTEGER NOT NULL,
   auto_complete BOOLEAN NOT NULL CHECK (auto_complete in (0, 1)) DEFAULT 0,
   parent_id INTEGER,
   FOREIGN KEY(parent_id) REFERENCES achievement(id_achievement)
);

CREATE TABLE done(
   id_user INTEGER,
   id_achievement INTEGER,
   PRIMARY KEY(id_user, id_achievement),
   FOREIGN KEY(id_user) REFERENCES user(id_user),
   FOREIGN KEY(id_achievement) REFERENCES achievement(id_achievement)
);

