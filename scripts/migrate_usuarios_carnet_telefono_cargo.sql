-- Añade a la tabla usuarios: carnet_identidad, telefono, cargo (todos opcionales).
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS carnet_identidad text;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS telefono text;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS cargo text;
