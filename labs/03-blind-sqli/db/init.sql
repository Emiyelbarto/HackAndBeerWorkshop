-- Datos sinteticos del inventario de Almacen Central.

CREATE TABLE products (
  id       INT AUTO_INCREMENT PRIMARY KEY,
  sku      INT          NOT NULL UNIQUE,
  name     VARCHAR(80)  NOT NULL,
  category VARCHAR(40)  NOT NULL,
  stock    INT          NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO products (sku, name, category, stock) VALUES
  (1001, 'Taladro percutor 800W',      'herramienta', 42),
  (1002, 'Juego de brocas 24 piezas',  'herramienta', 17),
  (1003, 'Casco de seguridad blanco',  'proteccion',  120),
  (1004, 'Guantes anticorte talla L',  'proteccion',  64),
  (1005, 'Cinta metrica 8m',           'medicion',    31),
  (1006, 'Nivel laser autonivelante',  'medicion',    9),
  (1007, 'Carretilla reforzada 90L',   'transporte',  6),
  (1008, 'Escalera telescopica 3.8m',  'transporte',  4);

CREATE TABLE vault_secrets (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  secret_name  VARCHAR(60)  NOT NULL,
  secret_value VARCHAR(120) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO vault_secrets (secret_name, secret_value) VALUES
  ('warehouse_flag', 'H&B{bl1nd_sql1_w4f_byp4ss_thr0ttl3}');

CREATE TABLE audit_log (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  actor      VARCHAR(40) NOT NULL,
  action     VARCHAR(60) NOT NULL,
  created_at DATETIME    NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO audit_log (actor, action, created_at) VALUES
  ('sucursal_norte', 'consulta de stock', '2026-04-02 09:12:00'),
  ('sucursal_sur',   'consulta de stock', '2026-04-02 10:45:00'),
  ('almacen_admin',  'alta de producto',  '2026-04-03 08:03:00');
