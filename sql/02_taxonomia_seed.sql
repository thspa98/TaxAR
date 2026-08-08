-- ============================================================
-- Seed: taxonomía canónica inicial (clasificación económica)
-- Basada en la Base Caja mensual que Nación ya publica.
-- Las provincias, cuando reporten por finalidad y función,
-- se cargan como clasificacion='funcional' (categorías separadas,
-- ver nota en 01_schema.sql sobre por qué no se mezclan).
-- ============================================================

-- INGRESOS — nivel 1 (rubros grandes)
INSERT INTO categorias (nombre, slug, tipo, clasificacion, nivel_jerarquia, orden_visualizacion) VALUES
('Tributarios',        'ing-tributarios',        'ingreso', 'economica', 1, 1),
('No tributarios',     'ing-no-tributarios',     'ingreso', 'economica', 1, 2),
('Ingresos de capital','ing-capital',            'ingreso', 'economica', 1, 3);

-- INGRESOS — nivel 2 (subrubros, hijos de Tributarios)
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Seguridad Social (aportes y contribuciones)', 'ing-trib-seg-social', 'ingreso', 'economica', id, 2, 1 FROM categorias WHERE slug='ing-tributarios';
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Ganancias', 'ing-trib-ganancias', 'ingreso', 'economica', id, 2, 2 FROM categorias WHERE slug='ing-tributarios';
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'IVA neto de reintegros', 'ing-trib-iva', 'ingreso', 'economica', id, 2, 3 FROM categorias WHERE slug='ing-tributarios';
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Débitos y créditos', 'ing-trib-debcred', 'ingreso', 'economica', id, 2, 4 FROM categorias WHERE slug='ing-tributarios';
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Derechos de exportación', 'ing-trib-derexp', 'ingreso', 'economica', id, 2, 5 FROM categorias WHERE slug='ing-tributarios';
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Derechos de importación', 'ing-trib-derimp', 'ingreso', 'economica', id, 2, 6 FROM categorias WHERE slug='ing-tributarios';
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Impuestos internos', 'ing-trib-internos', 'ingreso', 'economica', id, 2, 7 FROM categorias WHERE slug='ing-tributarios';
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Bienes personales', 'ing-trib-bienpers', 'ingreso', 'economica', id, 2, 8 FROM categorias WHERE slug='ing-tributarios';
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Resto tributarios', 'ing-trib-resto', 'ingreso', 'economica', id, 2, 9 FROM categorias WHERE slug='ing-tributarios';

-- INGRESOS — nivel 2 (subrubros, hijos de No tributarios)
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Rentas de la propiedad', 'ing-notrib-rentas', 'ingreso', 'economica', id, 2, 1 FROM categorias WHERE slug='ing-no-tributarios';
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Ingresos no tributarios (general)', 'ing-notrib-general', 'ingreso', 'economica', id, 2, 2 FROM categorias WHERE slug='ing-no-tributarios';
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Otros ingresos corrientes', 'ing-notrib-otros', 'ingreso', 'economica', id, 2, 3 FROM categorias WHERE slug='ing-no-tributarios';

-- GASTOS — nivel 1 (rubros grandes)
INSERT INTO categorias (nombre, slug, tipo, clasificacion, nivel_jerarquia, orden_visualizacion) VALUES
('Prestaciones sociales',   'gas-prestaciones',   'gasto', 'economica', 1, 1),
('Subsidios económicos',    'gas-subsidios',      'gasto', 'economica', 1, 2),
('Transferencias corrientes','gas-transferencias','gasto', 'economica', 1, 3),
('Remuneraciones (salarios)','gas-remuneraciones','gasto', 'economica', 1, 4),
('Gastos de capital',       'gas-capital',        'gasto', 'economica', 1, 5),
('Otros gastos corrientes', 'gas-otros',          'gasto', 'economica', 1, 6);

-- GASTOS — nivel 2 (hijos de Prestaciones sociales)
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Jubilaciones y pensiones contributivas', 'gas-prest-jubilaciones', 'gasto', 'economica', id, 2, 1 FROM categorias WHERE slug='gas-prestaciones';
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Pensiones no contributivas', 'gas-prest-noncontrib', 'gasto', 'economica', id, 2, 2 FROM categorias WHERE slug='gas-prestaciones';
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Asignación Universal para Protección Social', 'gas-prest-auh', 'gasto', 'economica', id, 2, 3 FROM categorias WHERE slug='gas-prestaciones';
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Prestaciones del INSSJP (PAMI)', 'gas-prest-inssjp', 'gasto', 'economica', id, 2, 4 FROM categorias WHERE slug='gas-prestaciones';
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Otros programas sociales', 'gas-prest-otros', 'gasto', 'economica', id, 2, 5 FROM categorias WHERE slug='gas-prestaciones';

-- GASTOS — nivel 2 (hijos de Subsidios económicos)
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Energía', 'gas-sub-energia', 'gasto', 'economica', id, 2, 1 FROM categorias WHERE slug='gas-subsidios';
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Transporte', 'gas-sub-transporte', 'gasto', 'economica', id, 2, 2 FROM categorias WHERE slug='gas-subsidios';
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Otros subsidios', 'gas-sub-otros', 'gasto', 'economica', id, 2, 3 FROM categorias WHERE slug='gas-subsidios';

-- GASTOS — nivel 2 (hijos de Transferencias corrientes)
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'A provincias', 'gas-transf-provincias', 'gasto', 'economica', id, 2, 1 FROM categorias WHERE slug='gas-transferencias';
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'A universidades', 'gas-transf-universidades', 'gasto', 'economica', id, 2, 2 FROM categorias WHERE slug='gas-transferencias';
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Al sector privado', 'gas-transf-privado', 'gasto', 'economica', id, 2, 3 FROM categorias WHERE slug='gas-transferencias';

-- ============================================================
-- CATEGORÍAS ESPECÍFICAS DEL NIVEL PROVINCIAL
-- La distinción "impuestos propios vs coparticipación" es políticamente
-- central: mide cuánto depende cada provincia de la Nación.
-- ============================================================
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Impuestos provinciales (propios)', 'ing-prov-impuestos-propios', 'ingreso', 'economica', id, 2, 10 FROM categorias WHERE slug='ing-tributarios';
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Coparticipación e impuestos nacionales', 'ing-prov-coparticipacion', 'ingreso', 'economica', id, 2, 11 FROM categorias WHERE slug='ing-tributarios';
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Transferencias corrientes recibidas', 'ing-prov-transf-corrientes', 'ingreso', 'economica', id, 2, 4 FROM categorias WHERE slug='ing-no-tributarios';

INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Bienes y servicios', 'gas-bienes-servicios', 'gasto', 'economica', NULL, 1, 7 FROM categorias LIMIT 1;
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'A municipios', 'gas-transf-municipios', 'gasto', 'economica', id, 2, 4 FROM categorias WHERE slug='gas-transferencias';
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Regalías', 'ing-prov-regalias', 'ingreso', 'economica', id, 2, 5 FROM categorias WHERE slug='ing-no-tributarios';

-- ============================================================
-- CLASIFICACIÓN FUNCIONAL (Finalidad y Función)
-- Es la que permite comparar "gasto en Salud" o "en Educación"
-- ENTRE jurisdicciones. Se mantiene separada de la económica
-- (ver nota en 01_schema.sql): son dos sistemas distintos y
-- sumarlos entre sí duplicaría el gasto.
-- Nomenclatura estándar de Finalidad usada por provincias y Nación.
-- ============================================================

-- FUNCIONAL — nivel 1 (Finalidades)
INSERT INTO categorias (nombre, slug, tipo, clasificacion, nivel_jerarquia, orden_visualizacion) VALUES
('Administración Gubernamental',   'fun-administracion', 'gasto', 'funcional', 1, 1),
('Servicios de Seguridad y Justicia','fun-seguridad',     'gasto', 'funcional', 1, 2),
('Servicios Sociales',             'fun-sociales',       'gasto', 'funcional', 1, 3),
('Servicios Económicos',           'fun-economicos',     'gasto', 'funcional', 1, 4),
('Deuda Pública',                  'fun-deuda',          'gasto', 'funcional', 1, 5),
('A Clasificar',                   'fun-a-clasificar',   'gasto', 'funcional', 1, 9);

-- FUNCIONAL — nivel 2 (Funciones dentro de Servicios Sociales)
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Salud', 'fun-soc-salud', 'gasto', 'funcional', id, 2, 1 FROM categorias WHERE slug='fun-sociales';
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Educación y Cultura', 'fun-soc-educacion', 'gasto', 'funcional', id, 2, 2 FROM categorias WHERE slug='fun-sociales';
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Promoción y Asistencia Social', 'fun-soc-promocion', 'gasto', 'funcional', id, 2, 3 FROM categorias WHERE slug='fun-sociales';
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Seguridad Social', 'fun-soc-segsocial', 'gasto', 'funcional', id, 2, 4 FROM categorias WHERE slug='fun-sociales';
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Vivienda y Urbanismo', 'fun-soc-vivienda', 'gasto', 'funcional', id, 2, 5 FROM categorias WHERE slug='fun-sociales';
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Agua Potable y Alcantarillado', 'fun-soc-agua', 'gasto', 'funcional', id, 2, 6 FROM categorias WHERE slug='fun-sociales';

-- FUNCIONAL — nivel 2 (dentro de Seguridad y Justicia)
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Seguridad Interior', 'fun-seg-interior', 'gasto', 'funcional', id, 2, 1 FROM categorias WHERE slug='fun-seguridad';
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Sistema Penal', 'fun-seg-penal', 'gasto', 'funcional', id, 2, 2 FROM categorias WHERE slug='fun-seguridad';
INSERT INTO categorias (nombre, slug, tipo, clasificacion, categoria_padre_id, nivel_jerarquia, orden_visualizacion)
SELECT 'Justicia', 'fun-seg-justicia', 'gasto', 'funcional', id, 2, 3 FROM categorias WHERE slug='fun-seguridad';
