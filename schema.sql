SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', 'public', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;
SET timezone = 'Europe/Paris';

SET default_tablespace = '';

DROP TABLE IF EXISTS done CASCADE;
DROP TABLE IF EXISTS event CASCADE;
DROP TABLE IF EXISTS achievement CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS discord_user CASCADE;
DROP TABLE IF EXISTS event_save_score CASCADE;
DROP TABLE IF EXISTS event_new_ach CASCADE;

CREATE TABLE discord_user (
   id_user BIGINT PRIMARY KEY,
   firstname CHARACTER VARYING(100) NOT NULL,
   lastname CHARACTER VARYING(100) NOT NULL,
   year INTEGER NOT NULL,
   avatar TEXT NOT NULL
);

CREATE TABLE users (
   id_user BIGINT PRIMARY KEY,
   joindate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
   score INTEGER DEFAULT 0,
   FOREIGN KEY(id_user) REFERENCES discord_user(id_user)
);

CREATE TABLE achievement(
   id_achievement SERIAL PRIMARY KEY,
   name CHARACTER VARYING(100) NOT NULL,
   lore TEXT DEFAULT '',
   difficulty INTEGER NOT NULL,
   auto_complete BOOLEAN NOT NULL DEFAULT FALSE,
   parent_id INTEGER,
   FOREIGN KEY(parent_id) REFERENCES achievement(id_achievement)
);

CREATE TABLE done(
   id_user BIGINT,
   id_achievement INTEGER,
   complete BOOLEAN NOT NULL DEFAULT TRUE,
   PRIMARY KEY(id_user, id_achievement),
   FOREIGN KEY(id_user) REFERENCES users(id_user),
   FOREIGN KEY(id_achievement) REFERENCES achievement(id_achievement)
);

CREATE TABLE event_save_score(
   id_event SERIAL PRIMARY KEY,
   event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
   id_user BIGINT NOT NULL,
   id_achievement INTEGER NOT NULL,
   FOREIGN KEY(id_user) REFERENCES users(id_user),
   FOREIGN KEY(id_achievement) REFERENCES achievement(id_achievement)
);

CREATE TABLE event_new_ach(
   id_event SERIAL PRIMARY KEY,
   event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
   id_achievement INTEGER NOT NULL,
   FOREIGN KEY(id_achievement) REFERENCES achievement(id_achievement)
);