BEGIN;

-- 1. Сначала удаляем все внешние ключи из sales (на всякий случай оба возможных)
ALTER TABLE sales DROP CONSTRAINT IF EXISTS sales_products_product_id_fk;
ALTER TABLE sales DROP CONSTRAINT IF EXISTS sales_products_id_fk;

-- 2. Удаляем первичный ключ из sales, если он есть
ALTER TABLE sales DROP CONSTRAINT IF EXISTS sales_pk;

-- 3. Удаляем все индексы/ограничения на products.id, valid_from, valid_to, если они создавались частично
-- Это нужно, чтобы не было конфликтов при повторном создании
ALTER TABLE products DROP CONSTRAINT IF EXISTS products_pk;
ALTER TABLE products DROP COLUMN IF EXISTS id;
ALTER TABLE products DROP COLUMN IF EXISTS valid_from;
ALTER TABLE products DROP COLUMN IF EXISTS valid_to;

-- 4. Теперь можно безопасно добавить суррогатный ключ и сделать его PK
ALTER TABLE products
    ADD COLUMN id SERIAL NOT NULL,
    ADD CONSTRAINT products_pk PRIMARY KEY (id);

-- 5. Добавляем поля SCD 2
ALTER TABLE products
    ADD COLUMN valid_from timestamptz NOT NULL DEFAULT now(),
    ADD COLUMN valid_to   timestamptz;

-- 6. В sales колонка product_id теперь будет хранить products.id
-- Таблица пустая, поэтому можно сразу NOT NULL
ALTER TABLE sales ALTER COLUMN product_id SET NOT NULL;

-- 7. Создаём новый FK: sales.product_id -> products.id
ALTER TABLE sales
    ADD CONSTRAINT sales_products_id_fk FOREIGN KEY (product_id)
        REFERENCES products(id);

-- 8. Создаём новый PK в sales: client_id + product_id
ALTER TABLE sales
    ADD CONSTRAINT sales_pk PRIMARY KEY (client_id, product_id);

COMMIT;
